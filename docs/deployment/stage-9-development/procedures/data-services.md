# GitLab Data Services

**Stage route:** [Stage 9, Step 1a](../README.md#step-1-deploy-source-control-and-sso), before the GitLab chart.
**Return:** after the chart-input handoff, continue with [GitLab installation](gitlab.md).
After GitLab is installed, finish [joint recovery checks](#backups-and-recovery), then return to Stage 9 Step 1.

**Working repository:** `<prefix>-tier-1`; upstream implementation: `tier-1/`.
This procedure supplies PostgreSQL, Redis and Gitaly on dedicated VMs for the
[GitLab CE chart](gitlab.md). The main path consumes versioned tenant buckets and
keys from [existing object storage](../../foundation/storage/README.md).
Its `preprovisioned` mode receives no storage-administrator credentials and
qualifies the S3-compatible data APIs with restricted tenant keys. Ceph RGW account
provisioning remains an explicit alternative, not a requirement for every existing
object endpoint. A NAS file share alone cannot satisfy the object API contract. [1][2]
This is GitLab application-object storage, not just its backup destination.
The data VMs' encrypted recovery copies use a separate file/SFTP repository.

## Contents

- [Support and ownership](#support-and-ownership)
- [Prerequisites](#prerequisites)
- [1. Create local inputs](#provision-the-vms)
- [2. Select the data hosts](#2-select-the-data-hosts)
- [3. Provision only the VMs](#3-provision-only-the-vms)
- [4. Prepare object storage](#prepare-object-storage)
- [5. Install controller dependencies](#render-and-apply)
- [6. Match the chart and package](#6-match-the-chart-and-package)
- [7. Prepare private credentials](#7-prepare-private-credentials)
- [8. Render data-service configuration](#8-render-data-service-configuration)
- [9. Review and apply data services](#9-review-and-apply-data-services)
- [10. Connect the chart inputs](#connect-the-chart)
- [Backups and recovery](#backups-and-recovery)
- [References](#references)

## Support and ownership

| Component | Supplied realization | Boundary |
| --- | --- | --- |
| Database | `db-1`, signed CE package `postgres_role`, TCP 5432 | One tenant database; TLS and client certificate plus password |
| Queue/cache | `kv-1`, CE package `redis_master_role`, TLS 6379 | One authenticated instance; no plaintext listener or eviction |
| Repositories | `repo-1`, CE package `gitaly_role`, TLS 8076 | `default` storage on its persistent VM disk; RPC and hook secrets |
| Objects | Existing qualified object storage, ten versioned tenant buckets | S3-compatible API; separate application and toolbox identities; no Tier 0 storage-admin keys in Tier 1 |
| Recovery | Per-host encrypted restic repositories on commissioned NAS shares or existing SFTP destinations | Native guest mount setup and systemd jobs; independent custody and retained keys |

These are GitLab's native Linux-package roles on EL9 x86_64; this recipe validates
AlmaLinux, Rocky Linux or RHEL 9. The exact CE package application version must
match the selected chart's `appVersion`. Upgrade Gitaly before its clients and
follow GitLab's required upgrade stops. No PostgreSQL/Redis Kubernetes support
claim, replication or HA is implied. The reference sizes follow the hybrid service
shape; qualify actual repository I/O, memory and disk growth locally. [1][3]

Tier 1 owns guest inventory, Terraform state, configuration and GitLab tenant data.
Tier 0 retains hypervisor, image and storage administration. GitLab administrators,
data/backup custodians and administrators able to alter GitLab hosting are accepted
Tier 0 authorities when direct infrastructure CI is enabled. Ordinary tenants
receive GitLab project permissions, never database, Gitaly, S3-admin or recovery keys.

## Prerequisites

| Input | Required preparation |
| --- | --- |
| Foundation | Existing deployment machine, Proxmox access, local Tier 1/shared inputs and approved EL9 template; use the [platform input contract](../../../reference/platform-inputs.md) |
| Software intake | Exact signed `gitlab-ce` EL9 RPM URL, real SHA256 and independently verified signing-key fingerprint; approved repositories providing restic >=0.17, psycopg2 and SELinux tooling |
| PKI | Server certificate/key for each endpoint, `serverAuth` and DNS SAN; database client certificate with `CN=gitlab`, `clientAuth`; trusted CA bundle for GitLab callbacks and dependencies |
| Network | DNS for the three hosts; permit only actual Tier 1 cluster client/SNAT CIDRs to 5432, 6379, 8076; Gitaly must reach itself and the GitLab HTTPS callback |
| Object storage | Approved existing endpoint or Tier 0 tenant handoff; S3-compatible API, versioned buckets, verified TLS and qualified multipart/data APIs; Ceph provisioning mode alone requires account IAM APIs [2] |
| Recovery | Commissioned per-host NAS share/repository/marker, or scoped SFTP destination; encryption password, retention/snapshot custody and recovery-key copies [4] |
| Custody | Private/encrypted Ansible inputs outside source control; one accepted Secret owner and a retained recovery kit |

The baseline does not create firewall policy, issue certificates or commission the
NAS export/share, marker or SFTP server. IaC sets up the guest NAS mount from its
per-host contract; no manual guest mount is required for the normal route.
Restrict each identity to its own backup area. Set
`development_data_backup_custody_accepted=true` only after independent copies and
retention are configured: a data host's writable repository alone is not protected
retention. The [storage-interface choice](../../../architecture/data/README.md#storage-interfaces)
adds no storage service. An existing object endpoint is a prerequisite for the chart;
file-backed application variants do not change the chart's requirements.

<a id="provision-the-vms"></a>
<a id="step-1-provision-the-vms"></a>

## 1. Create local inputs

For an existing collection, first review/register `development-data` under the
[setup ownership contract](../../../development/generated-repositories.md#setup-ownership).

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/init-local-files.sh --setup development-data
```

The dedicated [development-data root](../../../../tier-1/terraform/deployments/development-data/terraform.tfvars.example)
selects three data VMs using shared size profiles. This setup
has separate state from `development`, which retains the alternative Podman
`git-1` host. Do not move existing resource maps or state implicitly: existing
data VMs need an explicitly reviewed state migration/import before this root
can own them; adding dependencies must not remove or replace a live `git-1`.

## 2. Select the data hosts

Edit in **`<prefix>-tier-1/`**.

- `terraform/deployments/development-data/terraform.tfvars`: The three VM entries, unused VMIDs, accepted
  storage and explicitly approved EL9 `default_linux_vm_template_id`
- `ansible/inventory/hosts.yml`: All three matching host keys in `development_data`
- `ansible/group_vars/development_data.yml`: Matching `platform_host_ips` and `development_data_hosts`
  host/component maps, actual endpoints and package/TLS/backup inputs below
- `.env.local`: Tier 1 API credentials and local `TF_VAR_ssh_public_key_files` paths

Select an approved **EL9 x86_64** template explicitly through this deployment's
`default_linux_vm_template_id`, or verify that its selected shared default already
is EL9. The shared starter default is `null`, which selects no image. Tier 0's
existing generic AlmaLinux/Rocky publication recipe can publish an EL9 image:
choose its exact release/build, verified image and checksum, approve the clone,
and retain its existing approved catalog reference. No new public template slot
or catalog-ID reassignment is required. An Alma/Rocky family label alone does not
establish the major version; the data role validates the actual guest as EL9
before package installation. See [template lifecycle](../../../administration/virtual-machines/template-lifecycle.md).

## 3. Provision only the VMs

The product installation in Step 9 has a separate apply gate.

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/deploy.sh development-data --terraform-only
```

Review Terraform's plan and enter `yes` only for the intended VM/disk changes.
`--terraform-only` deliberately stops before service configuration. Add `--plan-only`
for preview, or `--auto-approve` only in an approved unattended job.
Follow the [VM alternative](../step-1b-source-control-vm.md)
only when that separate deployment variant is selected.

<a id="prepare-object-storage"></a>
<a id="step-2-prepare-object-storage"></a>

## 4. Prepare object storage

Choose **4a** for existing tenant buckets/keys or **4b** for explicit Ceph account provisioning.
Both continue at Step 5; neither installs an object-storage service.

### 4a. Existing tenant buckets and keys

Keep buckets/identities under the storage owner's
administration and configure the `preprovisioned` endpoint/key contract below.
The same consumer path accepts a qualified NAS object endpoint, Ceph RGW or
another compatible service; it does not deploy them. Populate the private inputs
from the endpoint, CA and separate application/toolbox keys supplied by its owner.

In **`<prefix>-tier-1/`**, edit `ansible/group_vars/development_data.yml`:

| Field | Set |
| --- | --- |
| `development_data_s3_mode` | `preprovisioned` for the main path |
| `development_data_s3_endpoint`, `development_data_s3_ca_src` | Existing HTTPS object API and local trusted CA file |
| `development_data_s3_denied_buckets` | An existing bucket outside both supplied identities |
| `development_data_s3_preprovisioned_accepted` | `true` only after tenant/bucket access is commissioned |

Keep both key pairs in the private extra-vars file prepared in Step 7, never in tracked examples.

In this mode apply checks version IDs/history, read/write/copy/range/list/delete,
multipart completion/abort and cross-tenant denial. It calls no IAM or bucket
administration APIs and uses no privileged storage profile. Qualification writes
bounded `.qualification/<unique-id>/` objects; their prior versions remain under
the storage custodian's retention policy. No S3 calls occur during render.

List at least one existing, inaccessible bucket in `development_data_s3_denied_buckets`.
The application key must also be denied both toolbox backup buckets. Continue at Step 5.

<a id="optional-ceph-account-provisioning"></a>

### 4b. Optional Ceph account provisioning

Choose `development_data_s3_mode=ceph-rgw` only for an existing separately owned
Ceph RGW account. Existing Ceph endpoints can also use `preprovisioned`; this
alternative is only for account-level bucket/policy management. It does not install
RGW on Proxmox. Use it only with that account's independently authorized
provisioning profile, never a general Tier 0 storage-administrator credential.

The storage administrator supplies a dedicated Ceph RGW **account root** profile
`gitlab-provisioner` on the deployment machine and trusts the endpoint CA. A legacy
RGW user outside an account is not enough for the IAM API. That privileged profile
is used only for bucket/policy provisioning, never exported into chart Secrets.

Set `GITLAB_S3_ENDPOINT` and `AWS_CA_BUNDLE` to the actual HTTPS endpoint and CA.
Using an approved AWS CLI, create the two fresh users and their keys once:

Run on **the independent storage custodian's execution host**.

```bash
umask 077
aws --profile gitlab-provisioner --endpoint-url "$GITLAB_S3_ENDPOINT" iam create-user --user-name gitlab-app
aws --profile gitlab-provisioner --endpoint-url "$GITLAB_S3_ENDPOINT" iam create-user --user-name gitlab-backup
aws --profile gitlab-provisioner --endpoint-url "$GITLAB_S3_ENDPOINT" iam create-access-key --user-name gitlab-app > /absolute/private/gitlab-app-key.json
aws --profile gitlab-provisioner --endpoint-url "$GITLAB_S3_ENDPOINT" iam create-access-key --user-name gitlab-backup > /absolute/private/gitlab-backup-key.json
```

For existing users, use `iam get-user` and `iam list-access-keys`; retain existing
keys rather than rerunning key creation. Use dedicated non-root users with no
groups, other policies or administrative capabilities. Copy their returned key
pairs into encrypted `development_data_s3_keys.application` and `.backup` inputs.
The role installs scoped inline policies and creates/version-enables all ten
buckets with native Ansible modules. It never deletes buckets or object versions.
The supplied keys are checked against each dedicated user's active IAM keys.
Application credentials cover only the eight application buckets. Toolbox
credentials cover those buckets plus `gitlab-backups` and `gitlab-backup-tmp`,
because backup and restore read/write application objects. Neither policy grants
bucket administration, IAM actions or deletion of historical object versions.
Storage custody must separately protect and copy historical data. [2][5]

Continue at Step 5 with the tenant key pairs, not the privileged provisioning profile.

<a id="render-and-apply"></a>
<a id="step-3-render-and-apply-data-services"></a>

## 5. Install controller dependencies

Native package downloads honor the existing
[intake proxy inputs](../../stage-1-software-intake/proxy-cache.md#how-other-paths-use-it);
approve the package host and any redirect destinations before installation.

Use **the prepared deployment virtual environment**, from **`<prefix>-tier-1/`**.
Install the tier and role-local collections from approved sources:

Run from **`<prefix>-tier-1/`**.

```bash
ansible-galaxy collection install -r ansible/requirements.yml
ansible-galaxy collection install -r ansible/roles/development_data/requirements.yml
```

Install the Python dependencies in that same environment, from **`<prefix>-tier-1/`**:

```bash
python3 -m pip install -r ansible/requirements.txt
python3 -m pip install 'boto3>=1.35' netaddr
```

## 6. Match the chart and package

On **the deployment host**, enter the accepted GitLab chart pin; this reads metadata, not a release:

```bash
read -r -p 'Accepted GitLab chart version: ' GITLAB_CHART_VERSION
helm show chart gitlab --repo https://charts.gitlab.io --version "$GITLAB_CHART_VERSION"
```

Use the same pin later as `development_platform_gitlab_version`. Read `appVersion` from the output.
Use the corresponding `appVersion-ce.0.el9` package; do not fabricate a checksum
or signing fingerprint. [9]

In **`<prefix>-tier-1/`**, complete `ansible/group_vars/development_data.yml`:

| Field in `ansible/group_vars/development_data.yml` | Required value |
| --- | --- |
| `development_data_chart_app_version`, `development_data_package_*` | Matching signed EL9 CE package, exact URL/checksum and verified signing key/fingerprint |
| `development_data_endpoints`, `development_data_client_cidrs` | Real DNS names and only the cluster clients that reach these VMs |
| `development_data_ca_src`, `development_data_tls`, PostgreSQL client certificate/key paths | Preissued leaf material; no CA private key |
| `development_data_backup_transport`, `development_data_backup_repository` | Commissioned SFTP repositories or NAS shares; live data stays on VM block disks |
| `development_data_backup_filesystem` | Per-host mount/source/type, UID/GID, independent marker and `manage_mount: true`; CIFS also needs private `credentials_src` |
| `development_data_backup_*_src`, `development_data_backup_custody_accepted` | Independently retained encryption/transport material and verified custody |

Require commissioned TLS, permitted client CIDRs and a usable backup destination before apply.
Use the accepted signed package repository/proxy, including required redirect hosts.

## 7. Prepare private credentials

On **the deployment host**, create an encrypted extra-vars file through the accepted secret workflow.
The commands below use `/absolute/private/gitlab-data-secrets.yml`; replace that path with the real file.

The file supplies `development_data_postgresql_password`,
`development_data_redis_password`, `development_data_gitaly_token`,
`development_data_shell_token` and `development_data_s3_keys`. Generate each service credential
independently; do not reuse the object-storage key pairs as service passwords. Encrypt before use
and retain decryption/recovery material separately.

## 8. Render data-service configuration

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/deployment/development-data.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/development_data.yml \
  -e @/absolute/private/gitlab-data-secrets.yml --ask-vault-pass -e development_data_action=render
```

Default `render` contacts no VMs, Kubernetes or object-storage endpoint. It verifies input files and
produces root-private `secrets/development-data/`: native Ruby configurations,
scoped JSON policies, chart endpoint/backup inputs and dependency Secret values.
Treat this whole directory as secret material.
The playbook checks module and Python dependencies before any provisioning.

## 9. Review and apply data services

In **`<prefix>-tier-1/`**, review `secrets/development-data/`: native service configuration,
endpoints, certificate paths, scoped policies and backup destinations. Then install using the same inputs:

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/deployment/development-data.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/development_data.yml \
  -e @/absolute/private/gitlab-data-secrets.yml --ask-vault-pass \
  -e development_data_action=apply -e development_data_apply_confirm=true
```

The explicit confirmation flag authorizes installation; there is no additional interactive approval.
For approved unattended jobs, use an Ansible Vault identity instead of `--ask-vault-pass`.
For new empty restic destinations only, also set
`-e development_data_backup_initialize=true`; existing or inaccessible repositories
are not replaced. Apply uses signed native packages, prevents their automatic
first reconfiguration, installs per-service TLS and configures only the selected
package role. PostgreSQL creates the owned database and `amcheck`, `pg_trgm`,
`btree_gist` extensions before chart migrations. A certificate change restarts the
affected service to load its new key. No disk formatting is performed. [3][6]

<a id="connect-the-chart"></a>
<a id="step-4-connect-the-chart-and-verify-backups"></a>

## 10. Connect the chart inputs

Load rendered `platform-inputs.yml` after the authored development-platform inputs
when running the [GitLab installer](gitlab.md#render-and-install), on every render
and apply. It also sets `development_platform_gitlab_backup_enabled=true` and
`development_platform_gitlab_backup_schedule='30 2 * * *'`; the installer includes
the native toolbox backup CronJob settings in its ordinary GitLab values. Merge
`dependency-secrets.yml` into the chosen owner's complete Secret map; preserve its
root, ingress TLS and OIDC entries. This file contains only dependency entries,
not an entire replacement for `development_platform_secrets`. For a controller,
provision the same namespace-scoped names and keys through that controller alone.
The generated CA bundle includes both platform and S3 trust roots. No cluster
Secrets are created by the data-service playbook. [7]

For bootstrap Secret ownership, the native merge is:

In **`<prefix>-tier-1/`**, add this to the private GitLab Secret input prepared in
[GitLab Step 5b](gitlab.md#5b-encrypted-bootstrap-inputs):

```yaml
development_platform_secrets: "{{ bootstrap_gitlab_secrets | combine(lookup('ansible.builtin.file', 'secrets/development-data/dependency-secrets.yml') | from_yaml) }}"
```

Here `bootstrap_gitlab_secrets` is the complete private map prepared from the
existing platform secret example. Keep the four service credentials identical
on both sides, especially `gitlab-shell-auth.secret` used by Gitaly hooks.
Use port 5432 with verified server identity and client certificate, `rediss` on
6379, and external `default` Gitaly TLS on 8076. [6][7]

## Backups and recovery

Complete this section after [GitLab installation](gitlab.md#render-and-install), when the toolbox exists.
The data-service installation alone does not deploy the toolbox.

Each VM receives a root-only restic job and `development-data-backup.timer`.
Select [direct NAS file storage or existing SFTP](../../../administration/backups/gitlab-data.md)
and qualify the mount, independent credentials, schedule and failure budget.
Live PostgreSQL/Redis/Gitaly data stays on Proxmox/Ceph-backed VM disks.
The job's cold component copy causes a maintenance outage, not an atomic GitLab-wide
recovery point. No automatic forget/prune runs.

The [main GitLab installer](gitlab.md#render-and-install) reconciles the native
toolbox backup CronJob through `platform-inputs.yml`, enabled with schedule
`30 2 * * *`. Keep that handoff in the installer's input set for every
reconciliation; no separate Helm overlay or manual Helm upgrade is required.
For first acceptance, trigger an application backup explicitly:

Run from **`<prefix>-tier-1/`** with `KUBECONFIG` set to the accepted Tier 1 cluster.
For the default `gitlab` namespace/release:

```bash
kubectl --kubeconfig "$KUBECONFIG" -n gitlab exec deploy/gitlab-toolbox -- backup-utility
```

Use one release owner. Toolbox application backups do not preserve all Kubernetes
Secrets; export the release's Secrets/configuration into the independent recovery
kit. Copy object versions and toolbox backups under independent storage credentials; versioning
on the same object-storage deployment alone is not an independent backup. [5][8]

For first acceptance, run on **each data VM** (`db-1`, `kv-1`, `repo-1`) during the accepted maintenance window:

```bash
sudo systemctl start development-data-backup.service
sudo systemctl status development-data-backup.service development-data-backup.timer --no-pager
```

Require successful jobs and inspect restic snapshots. Then perform a
matching-version clean-target restore of PostgreSQL, repositories, objects and
the separately retained chart Secrets. Use `restic restore <snapshot> --target
/restore` on an isolated target and GitLab's native toolbox restore procedure;
never restore raw PostgreSQL files over a running server. The three independent
component snapshots need a coordinated maintenance recovery point for joint use.
Verify SSO, denied access, push/hooks, LFS/artifacts, jobs and audit delivery after
restore. Installation and offline parsing do not establish live acceptance.

Return to [Stage 9, Step 1 acceptance](../README.md#step-1-deploy-source-control-and-sso),
then continue with Step 2. Do not reinstall GitLab after these joint recovery checks.

## References

Checked 2026-10-26; qualify exact package, chart and storage versions together.

1. [GitLab hybrid reference architecture](https://docs.gitlab.com/administration/reference_architectures/2k_users/).
2. [Ceph RGW account IAM API](https://docs.ceph.com/en/squid/radosgw/iam/).
3. [GitLab Linux-package roles](https://docs.gitlab.com/omnibus/roles/).
4. [Restic SFTP repositories and encryption](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#sftp).
5. [GitLab external object storage](https://docs.gitlab.com/charts/advanced/external-object-storage/).
6. [Gitaly TLS](https://docs.gitlab.com/administration/gitaly/tls_support/) and [Redis TLS](https://docs.gitlab.com/administration/redis/tls/).
7. [External PostgreSQL](https://docs.gitlab.com/charts/advanced/external-db/) and [PostgreSQL TLS](https://docs.gitlab.com/omnibus/settings/database/#configuring-ssl).
8. [GitLab chart backup and restore](https://docs.gitlab.com/charts/backup-restore/).
9. [Helm chart metadata and exact version selection](https://helm.sh/docs/helm/helm_show_chart/), checked 2026-11-09.
