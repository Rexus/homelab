# Keycloak with external FreeIPA

Install the Tier 0 identity provider after accepting the directory pair and the
Kubernetes platform. FreeIPA remains the directory authority on its dedicated VMs.
Keycloak uses its own CNPG database and verifies LDAP and database certificates.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
Run every command below from its root, using the accepted Tier 0 kubeconfig.
**Prerequisites:** working FreeIPA LDAPS, a restricted directory reader, external
certificate/credential custody, CNPG, the selected database backup path, independent
backup storage and protected cluster log delivery. None may depend on later Vault.

## Table of contents

- [Step 1: Configure the identity provider](#configure-and-install)
- [Step 2: Supply private certificates and credentials](#step-2-supply-private-certificates-and-credentials)
- [Step 3: Prepare the database and backup](#step-3-prepare-the-database-and-backup)
- [Step 4: Install Keycloak and federation](#step-4-install-keycloak-and-federation)
- [Federation and authorization](#federation-and-authorization)
- [Accept and recover](#accept-and-recover)
- [References](#references)

<a id="configure-and-install"></a>

## Step 1: Configure the identity provider

### 1. Create local inputs and select the cluster

Initialize the local file without overwriting existing selections:

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ansible/group_vars/control_applications.yml.example ansible/group_vars/control_applications.yml
export KUBECONFIG="${KUBECONFIG:-$PWD/secrets/talos/kubeconfig}"
kubectl get nodes -o wide
```

**Expected:** the intended Tier 0 nodes are listed. Stop if the kubeconfig selects another cluster.
Retain the export from Stage 4. For a manual cluster in a new shell, set `KUBECONFIG` to its existing
`secrets/<cluster-name>/kubeconfig` first; do not switch it to the Terraform workflow's fallback path.

### 2. Edit the identity-provider settings

Edit **`<prefix>-tier-0/ansible/group_vars/control_applications.yml`**. Select only `keycloak` for
this stage. The [shared product contract](../../stage-6-secrets/procedures/control-applications.md#dependencies-and-ownership)
defines dependency/certificate details; installation commands are below, so no later
stage must be deployed first.

Choose the backup method now, before preparing its certificates/Secrets: **files** uses scheduled NAS
copies, while **object** uses an existing qualified object/WAL service and Barman plugin.
[Step 3a](#step-3a-scheduled-nas-backups-main-path) and [Step 3b](#step-3b-objectwal-backups-alternative)
execute those alternatives; do not prepare/install the NAS branch before selecting object/WAL.

The installer creates `keycloak-db` on qualified Proxmox/Ceph-backed volumes with
externally issued TLS and the selected backup resources, then waits for readiness before
installing the pinned `keycloakx` chart. Two Keycloak replicas use JDBC discovery;
this is a placement configuration, not evidence of failover. The maintained chart
runs the upstream Keycloak image in production mode. [1][2]

Scheduled verified full backups can write to a separate NAS backup PVC. The database
itself does not use that PVC. Select the object/WAL path separately when continuous
point-in-time recovery is required; a file backup recovers only to a completed set.

| Input | Required selection |
| --- | --- |
| `control_applications_components`, `control_applications_action` | `[keycloak]`, `render` |
| `control_applications_kubeconfig`, `control_applications_context` | Absolute Tier 0 kubeconfig path and intended context |
| `control_applications_versions.keycloak` | Approved exact chart version, compatible with the selected image/Kubernetes release |
| `control_applications_hosts.keycloak` | Stable HTTPS name; use the same name in certificate SANs and issuer URLs |
| `control_applications_keycloak_realm` | Existing/selected human federation realm; default `platform` |
| `control_applications_ldap_url` | External FreeIPA `ldaps://` endpoint; trusted through `freeipa-ca` |
| `control_applications_ldap_users_dn` | FreeIPA user search base |
| `control_applications_ldap_groups_dn` | FreeIPA group search base |
| `control_applications_ldap_bind_dn` | Restricted directory reader; created and authorized in FreeIPA separately |
| `control_applications_ldap_bind_password` | Private controller input, used only by the Keycloak API module |
| `control_applications_keycloak_auth` | Private API administration credentials; controller must trust HTTPS |
| `control_applications_storage_class`, `control_applications_database_storage_class` | Qualified Proxmox/Ceph-backed block classes; never the NAS backup class |
| `control_applications_backup_mode`, `control_applications_backup_files_phase` | Main path: `files`, `prepare`; Step 3 commissions the backup destination |
| `control_applications_platform_accepted`, `control_applications_cluster_logging_accepted`, `control_applications_traefik_crd_accepted`, `control_applications_database_storage_accepted`, `control_applications_recovery_custody_accepted` | Set `true` only after the respective Stage 4 and independent-custody checks pass |

## Step 2: Supply private certificates and credentials

### 3. Select the Secret owner

For installer-owned bootstrap Secrets, continue with action 4. If a qualified Secret controller already
owns them, keep `control_applications_manage_secrets: false`, commission the exact Secrets below through
that owner, and continue at Step 3. Omit the private-file arguments from render/apply only for that branch.

### 4. Create and fill the encrypted bootstrap input

Run from **`<prefix>-tier-0/`**. Create the encrypted input before entering secrets:


```bash
cp -n ansible/group_vars/control_applications_secrets.yml.example ansible/group_vars/control_applications_secrets.yml
ansible-vault encrypt ansible/group_vars/control_applications_secrets.yml
ansible-vault edit ansible/group_vars/control_applications_secrets.yml
```

In that encrypted file, set `control_applications_manage_secrets: true` only when
this installer is the selected Secret owner. Retain/populate the `keycloak/*` entries
for the selected backup mode; omit unrelated Vault/NetBox/Headlamp Secret entries.
Supply the restricted LDAPS reader password and Keycloak API credentials there too.
An existing qualified Secret controller is an alternative: keep management false
and commission those exact Secrets before applying.

| Required private material | Contract |
| --- | --- |
| `keycloak-bootstrap`, `keycloak-db` | Independent bootstrap administrator and database credentials |
| `freeipa-ca`, `keycloak-tls` | Trusted LDAP CA bundle; approved HTTPS leaf/key/chain for the selected IdP DNS name |
| `keycloak-db-ca`, `keycloak-db-server`, `keycloak-db-replication` | External DB trust, server leaf covering the read/write service name, and client-auth replication identity |
| `keycloak-db-file-backup` | Files mode: client-auth CN `keycloak-db-file-backup`, matching key and server trust |
| `keycloak-db-backup` | Object/WAL alternative only: independently scoped object credentials and endpoint trust |

Use the [exact namespace/key and certificate contract](../../stage-6-secrets/procedures/control-applications.md#secrets-and-certificates).
Obtain all leaves through qualified issuance before apply; the Stage 3 TLS-server
policy does not supply client-auth profiles. No CA private key or later Vault
dependency belongs in these inputs. Keep TLS verification enabled on the controller.

## Step 3: Prepare the database and backup

Select **3a** for scheduled NAS backups or **3b** for object/WAL recovery. Follow only that branch,
then rejoin at Step 4. Live database volumes stay on the qualified block class in both cases.

### Step 3a: Scheduled NAS backups (main path)

#### 5. Render database preparation

In **`<prefix>-tier-0/ansible/group_vars/control_applications.yml`**, keep `files` / `prepare`.
Render without live changes:

Run from **`<prefix>-tier-0/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/control-applications.yml -e @ansible/group_vars/control_applications_secrets.yml --ask-vault-pass -e control_applications_action=render
```

#### 6. Inspect and prepare the database

Inspect **`<prefix>-tier-0/secrets/control-applications/`**, including the database preparation
resources and Secret references, then prepare the database:

Run from **`<prefix>-tier-0/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/control-applications.yml -e @ansible/group_vars/control_applications_secrets.yml --ask-vault-pass -e control_applications_action=apply
```

This creates `keycloak-db` and reports its system identifier. **Keycloak is not
installed yet.** Live database PVCs remain on the selected block storage.

#### 7. Commission the NAS backup destination

Complete [NAS commissioning](../../../administration/backups/postgresql.md#commission-the-nas).
Create the independent backup-only claim and marker, then set
`control_applications_backup_files.keycloak` (`claim`, `volume_handle`,
`system_identifier`, `marker`, `schedule`) in the local application file.
Set `control_applications_backup_files_accepted: true` only after those gates;
change `control_applications_backup_files_phase` to `backup`. Continue to Step 4.

### Step 3b: Object/WAL backups (alternative)

Select `control_applications_backup_mode: object`, qualify the existing Barman
plugin/native object endpoint and supply the scoped Secret/destination fields
under the [object/WAL contract](../../stage-6-secrets/procedures/control-applications.md#persistence-and-recovery).
This selects continuous WAL recovery instead of scheduled file sets; it installs
no storage gateway and does not move live database volumes. Return to Step 4.

## Step 4: Install Keycloak and federation

### 8. Render the completed selection

With the selected backup inputs complete, render from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/control-applications.yml -e @ansible/group_vars/control_applications_secrets.yml --ask-vault-pass -e control_applications_action=render
```

Inspect **`<prefix>-tier-0/secrets/control-applications/`**: database, backup, TLS, ingress and federation selections.

### 9. Install the reviewed application and federation

Run from **`<prefix>-tier-0/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/control-applications.yml -e @ansible/group_vars/control_applications_secrets.yml --ask-vault-pass -e control_applications_action=apply
```

The playbook loads `ansible/group_vars/control_applications.yml` itself. The private
extra-vars override it; keep the same file/target on render and apply. This is a
native Ansible installation with explicit `render`/`apply`, not the Linux VM
helper's interactive Terraform confirmation. CI supplies a protected Vault password
file instead of `--ask-vault-pass`; retain the render review/approval gate.

Keep the `keycloak-bootstrap` Secret under independent custody. The initial
administrator is a bootstrap/recovery account, not routine human SSO. After
acceptance, supply a supported durable API administration identity separately;
the initial bootstrap variables do not recreate a removed account in an existing
database. [2]

## Federation and authorization

Native `community.general` modules configure the realm and LDAP provider. The
provider is read-only, uses `uid` and FreeIPA `ipaUniqueID`, and maps `groupOfNames`
membership through `member` DNs. Unspecified built-in attribute mappers are
preserved. Self-registration and directory writes are disabled. [3]

The selected FreeIPA LDAPS endpoint must itself meet the availability requirement.
Supplying two directory VMs does not configure a resilient LDAP endpoint.
Verify read access, disabled-account behavior, group hierarchy and membership
removal against the real directory before accepting federation.

Later services use the same realm. Set `control_applications_register_clients`
when installing those consumers to register exact callbacks and a `groups` claim
through the native Keycloak API. Supply each confidential-client secret privately
and use the identical value in its consumer. NetBox grants no initial permissions;
Vault roles require explicit groups and policies; Headlamp uses Kubernetes RBAC.
Apply the [service SSO gate](service-sso.md) before routine access.
For Headlamp, follow the native [Kubernetes API integration](kubernetes-sso.md),
including preserved X509 authentication and cold-start issuer-outage acceptance.

## Accept and recover

### 10. Test identity, audit delivery and restoration

| Check | Evidence |
| --- | --- |
| Discovery | The HTTPS discovery document reports the exact selected issuer |
| Federation | Allowed user, denied user, disabled user and removed group membership behave as approved |
| Audit | Authentication and administrative changes arrive through protected cluster stdout collection |
| Backup | Completed verified file set, or base backup plus archived WAL for the selected object/PITR path; restore into a separate CNPG cluster and exercise a login |
| Failure | Restart one replica, test the directory endpoint failing, then test the IdP outage |
| Recovery | Independent Kubernetes and Keycloak administration, database restore inputs and TLS material remain available |

The role checks database/endpoint health and initial backup completion. Human
login, event arrival, failover and clean-target restoration remain operator
acceptance checks. Restore the existing realm/database; reinstalling an empty
realm changes identity state and is not recovery.

Return to [Stage 5, Step 3](../README.md#step-3-accept-identity-and-human-sso)
for Kubernetes human SSO and the service-access gates before Stage 6.

## References

Official/maintainer guidance checked 2026-10-26; pins live in the example inputs.

1. [Maintained Keycloak chart](https://github.com/codecentric/helm-charts/tree/master/charts/keycloakx).
2. [Keycloak production containers](https://www.keycloak.org/server/containers).
3. [Native Ansible LDAP federation module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_user_federation_module.html).
