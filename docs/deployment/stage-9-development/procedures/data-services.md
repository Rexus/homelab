# GitLab Data Services

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
- [Provision the VMs](#provision-the-vms)
- [Prepare object storage](#prepare-object-storage)
- [Render and apply](#render-and-apply)
- [Connect the chart](#connect-the-chart)
- [Backups and recovery](#backups-and-recovery)
- [References](#references)

## Support and ownership

| Component | Supplied realization | Boundary |
| --- | --- | --- |
| Database | `gitlab-db-1`, signed CE package `postgres_role`, TCP 5432 | One tenant database; TLS and client certificate plus password |
| Queue/cache | `gitlab-redis-1`, CE package `redis_master_role`, TLS 6379 | One authenticated instance; no plaintext listener or eviction |
| Repositories | `gitlab-gitaly-1`, CE package `gitaly_role`, TLS 8076 | `default` storage on its persistent VM disk; RPC and hook secrets |
| Objects | Existing qualified object storage, ten versioned tenant buckets | S3-compatible API; separate application and toolbox identities; no Tier 0 storage-admin keys in Tier 1 |
| Recovery | Per-host encrypted restic repositories on commissioned NAS mounts or existing SFTP destinations | Systemd jobs; independent custody and separately retained keys |

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
| Recovery | Commissioned per-host NAS mount/repository, or existing scoped SFTP destination; independent encryption password, retention/snapshot custody and recovery-key copies [4] |
| Custody | Private/encrypted Ansible inputs outside source control; one accepted Secret owner and a retained recovery kit |

The baseline does not create firewall policy, issue certificates or commission the
NAS export/mount or SFTP server. Restrict each identity to its own backup area. Set
`development_data_backup_custody_accepted=true` only after independent copies and
retention are configured: a data host's writable repository alone is not protected
retention. The [storage-interface choice](../../../architecture/compute/runtime.md#storage-interfaces)
adds no storage service. An existing object endpoint is a prerequisite for the chart;
file-backed application variants do not change the chart's requirements.

## Provision the VMs

From Tier 1, initialize local inputs using the existing helper:

For an existing collection, first review/register `development-data` under the
[setup ownership contract](../../../development/generated-repositories.md#setup-ownership).

```bash
bash scripts/init-local-files.sh --setup development-data
```

Set the full IP map and service inputs in `ansible/group_vars/development_data.yml`,
guest identities in inventory, and the approved EL9 template and available VMIDs
in the dedicated [development-data Terraform root](../../../../tier-1/terraform/deployments/development-data/terraform.tfvars.example).
Its fresh example selects three data VMs using shared size profiles. This setup
has separate state from `development`, which retains the alternative Podman
`git-1` host. Do not move existing resource maps or state implicitly: existing
data VMs need an explicitly reviewed state migration/import before this root
can own them; adding dependencies must not remove or replace a live `git-1`.

Select an approved **EL9 x86_64** template explicitly through this deployment's
`default_linux_vm_template_id`, or verify that its selected shared default already
is EL9. The shared starter default is `null`, which selects no image. Tier 0's
existing generic AlmaLinux/Rocky publication recipe can publish an EL9 image:
choose its exact release/build, verified image and checksum, approve the clone,
and retain its existing approved catalog reference. No new public template slot
or catalog-ID reassignment is required. An Alma/Rocky family label alone does not
establish the major version; the data role validates the actual guest as EL9
before package installation. See [template lifecycle](../../../administration/compute/template-lifecycle.md).

```bash
bash scripts/deploy.sh development-data --plan-only
```

Review the plan's three VM identities, EL9 template, placement and persistent
disks. Apply only after confirming no existing resources will be removed or
replaced:

```bash
bash scripts/deploy.sh development-data --terraform-only
```

These commands own only the VMs, not their data-service installation.
Follow the [VM alternative](../step-1b-source-control-vm.md)
only when that separate deployment variant is selected.

## Prepare object storage

For an existing endpoint, keep buckets/identities under the storage owner's
administration and configure the `preprovisioned` endpoint/key contract below.
The same consumer path accepts a qualified NAS object endpoint, Ceph RGW or
another compatible service; it does not deploy them. Populate the private inputs
from the endpoint, CA and separate application/toolbox keys supplied by its owner.

In this mode apply checks version IDs/history, read/write/copy/range/list/delete,
multipart completion/abort and cross-tenant denial. It calls no IAM or bucket
administration APIs and uses no privileged storage profile. Qualification writes
bounded `.qualification/<unique-id>/` objects; their prior versions remain under
the storage custodian's retention policy. No S3 calls occur during render.

For an independently preprovisioned service, configure the same endpoint/key
contract, set `development_data_s3_preprovisioned_accepted=true` and list at least
one existing, inaccessible bucket in `development_data_s3_denied_buckets`.
The application key must also be denied both toolbox backup buckets.

### Optional Ceph account provisioning

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

## Render and apply

Native package downloads honor the existing
[intake proxy inputs](../../stage-1-software-intake/proxy-cache.md#how-other-paths-use-it);
approve the package host and any redirect destinations before installation.

Install the tier/shared requirements and these additional role-local dependencies
inside the accepted deployment virtual environment:

```bash
ansible-galaxy collection install -r ansible/roles/development_data/requirements.yml
python3 -m pip install 'boto3>=1.35' netaddr
```

Complete the [input example](../../../../tier-1/ansible/group_vars/development_data.yml.example).
Obtain `appVersion` with `helm show chart gitlab/gitlab --version <exact-chart-pin>`.
Use the corresponding `appVersion-ce.0.el9` package; do not fabricate a checksum
or signing fingerprint. Put the four independently generated service passwords/
tokens and S3 key pairs in `/absolute/private/gitlab-data-secrets.yml`, encrypted
with Ansible Vault or supplied through the accepted secret workflow.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deployment/development-data.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/development_data.yml -e @/absolute/private/gitlab-data-secrets.yml
```

Default `render` contacts no VMs, Kubernetes or object-storage endpoint. It verifies input files and
produces root-private `secrets/development-data/`: native Ruby configurations,
scoped JSON policies, chart endpoint/backup inputs and dependency Secret values.
Treat this whole directory as secret material.
The playbook checks module and Python dependencies before any provisioning.

After reviewing those files and network/storage prerequisites, run the same command
with `-e development_data_action=apply -e development_data_apply_confirm=true`.
For new empty restic destinations also set
`-e development_data_backup_initialize=true`; existing or inaccessible repositories
are not replaced. Apply uses signed native packages, prevents their automatic
first reconfiguration, installs per-service TLS and configures only the selected
package role. PostgreSQL creates the owned database and `amcheck`, `pg_trgm`,
`btree_gist` extensions before chart migrations. A certificate change restarts the
affected service to load its new key. No disk formatting is performed. [3][6]

## Connect the chart

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

```yaml
development_platform_secrets: "{{ bootstrap_gitlab_secrets | combine(lookup('ansible.builtin.file', 'secrets/development-data/dependency-secrets.yml') | from_yaml) }}"
```

Here `bootstrap_gitlab_secrets` is the complete private map prepared from the
existing platform secret example. Keep the four service credentials identical
on both sides, especially `gitlab-shell-auth.secret` used by Gitaly hooks.
Use port 5432 with verified server identity and client certificate, `rediss` on
6379, and external `default` Gitaly TLS on 8076. [6][7]

## Backups and recovery

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

```bash
kubectl --kubeconfig "$KUBECONFIG" -n gitlab exec deploy/gitlab-toolbox -- backup-utility
```

Use one release owner. Toolbox application backups do not preserve all Kubernetes
Secrets; export the release's Secrets/configuration into the independent recovery
kit. Copy object versions and toolbox backups under independent storage credentials; versioning
on the same object-storage deployment alone is not an independent backup. [5][8]

For first acceptance, run `systemctl start development-data-backup.service` on
each data VM, inspect timer/job results and restic snapshots, then perform a
matching-version clean-target restore of PostgreSQL, repositories, objects and
the separately retained chart Secrets. Use `restic restore <snapshot> --target
/restore` on an isolated target and GitLab's native toolbox restore procedure;
never restore raw PostgreSQL files over a running server. The three independent
component snapshots need a coordinated maintenance recovery point for joint use.
Verify SSO, denied access, push/hooks, LFS/artifacts, jobs and audit delivery after
restore. Installation and offline parsing do not establish live acceptance.

Return to [GitLab chart installation](gitlab.md#render-and-install).

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
