# Deploy the infrastructure issuer

Install the permanent OpenXPKI Community runtime on `ca-1`, then activate the
separately signed issuer. An existing qualified issuer is also a valid prerequisite.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Design:** [certificate authority](../../../01-architecture/08-cryptography/01-certificate-authority.md).
**Prerequisites:** accepted logging, independent SSH/DNS, approved Debian template,
an attached dedicated data disk, production configuration bundle and authorized custodians.

## Contents

- [Step 1: Provision the host](#step-1-provision-the-host)
- [Step 2: Install the runtime](#step-2-install-the-runtime)
- [Step 3: Activate and accept issuance](#step-3-activate-and-accept-issuance)
- [IaC ownership](#iac-ownership)
- [References](#references)

## Step 1: Provision the host

### 1. Select the issuer image

Publish an approved Debian image using the Tier 0
[template lifecycle](../../../05-operations/01-hosting/templates/template-lifecycle.md).
Record its approved ID/title in **`<prefix>-shared/templates/proxmox-catalog.tfvars`**.
The catalogue's Debian example needs a locally supplied image and checksum.

**OS exception:** this native package path requires Debian 12 amd64, not the EL10 image used for
other Linux services. Its LTS end is 2028-06-30; revalidate support and the upgrade milestone. [1][2]

### 2. Initialize foundation inputs

Run from **`<prefix>-tier-0/`**, retaining the same `--env` context on subsequent commands if selected:

```bash
bash scripts/init-local-files.sh --setup foundation
```

Create the missing issuer input file from **the same Tier 0 root**:

```bash
cp -n ansible/group_vars/issuer.yml.example ansible/group_vars/issuer.yml
```

Existing local files remain unchanged.

### 3. Edit the host inputs

Edit in **`<prefix>-tier-0/`**:

| File | Set |
| --- | --- |
| `terraform/deployments/foundation/terraform.tfvars` | `vm_instances["ca-1"].template_vm_id` to the approved Debian VMID; unused `vm_id`, placement/storage and `extra_disks` capacity |
| `ansible/inventory/hosts.yml` | `ca-1` under `issuing_ca`; retain directory and other groups |
| `ansible/group_vars/foundation.yml` | Reserved `platform_host_ips.ca-1`; retain existing directory IPs |
| `terraform/common.tfvars` | Actual `network_zones.cryptography` attachment and prefix/gateway, or applied SDN lookup |
| `.env.local` | Real Proxmox endpoint/token and existing `TF_VAR_ssh_public_key_files` path; use its matching private key for Ansible |

For a fresh Stage 3 installation, the guest map may contain only `ca-1`; later add the identity pair to
this **same state**. The unchanged starter includes all three guests. Never remove an already-managed guest
to match a stage label.

### 4. Provision the host and data disk

Run from **`<prefix>-tier-0/`**. Review the whole-state plan and enter `yes` only for intended resources:

```bash
bash scripts/deploy.sh foundation --terraform-only
```

Add `--plan-only` for an optional preview, or `--auto-approve` for an approved unattended provisioning job.
Neither authorizes a CA ceremony. **Expected:** allocated host/disks; the identity recipe has not run.
Terraform attaches the data disk. The runtime installer below prepares its filesystem and database bind.

## Step 2: Install the runtime

### 5. Build the policy and prepare storage

For software custody, build the private artifact using
[software PKI Step 2](software-pki.md#build-the-private-policy-bundle), then return here.
If that guide already built the bundle, reuse its reviewed path/checksum.

Select the dedicated disk in the inputs below. The installer uses Shared's guarded volume role to
create XFS on an undeclared blank disk, mount it persistently by UUID, and bind its `mysql` subdirectory
at `/var/lib/mysql` before MariaDB packages are installed. Existing compatible storage is retained;
files in an unmounted database directory or conflicting mount declarations stop the installation.
See the [storage contract](../../../08-reference/openxpki.md#storage) for existing-volume and recovery rules.
Configure independent access and [Stage 2 forwarding](../../stage-2-logging/procedures/sources.md) on **`ca-1`**.

**Gate:** verify an issuer-host test event at protected intake before continuing.

### 6. Set the runtime inputs

Edit **`<prefix>-tier-0/ansible/group_vars/issuer.yml`**. No demo policy, account, key or password
is generated. Supply passwords and portal TLS through the protected controller environment or a
secret-only Ansible override. [1][3]

| Field | Enter |
| --- | --- |
| `openxpki_data_device`, `openxpki_data_mount` | Dedicated `scsi1` disk selected by its `/dev/disk/by-id/` link, and `/srv/openxpki` |
| `openxpki_data_fstype` | `xfs` for a new disk; set `ext4` explicitly when retaining a qualified ext4 filesystem |
| `openxpki_data_uuid` | Optional existing-volume UUID pin; leave empty for a new disk. The installer persists its UUID |
| `openxpki_configuration_src`, `openxpki_configuration_sha256` | Absolute private bundle path and reviewed archive SHA256 |
| `openxpki_repository_key_sha256`, `openxpki_package_versions` | Independently approved key hash and exact native package versions |
| `openxpki_admin_networks`, `openxpki_publication_networks` | Restricted portal clients and approved public-object readers |
| `openxpki_initialize_database`, `openxpki_activate_runtime` | First empty-database initialization only; activation remains `false` until Step 3 |

### 7. Load stable credentials and portal TLS paths

In the protected execution shell, run from **`<prefix>-tier-0/`**. Restore the existing values on reruns;
changing them is not password rotation or database recovery:

```bash
read -r -s -p 'Issuer database password: ' OPENXPKI_DATABASE_PASSWORD; echo
read -r -s -p 'Issuer session database password: ' OPENXPKI_SESSION_PASSWORD; echo
read -r -s -p 'Issuer session secret: ' OPENXPKI_SESSION_SECRET; echo
read -r -e -p 'Absolute portal TLS certificate path: ' OPENXPKI_TLS_CERT_FILE
read -r -e -p 'Absolute matching portal TLS key path: ' OPENXPKI_TLS_KEY_FILE
export OPENXPKI_DATABASE_PASSWORD OPENXPKI_SESSION_PASSWORD OPENXPKI_SESSION_SECRET
export OPENXPKI_TLS_CERT_FILE OPENXPKI_TLS_KEY_FILE
```

The software bundle supplies bootstrap-only `portal-bootstrap.pem` / `portal-key.pem` in its private build
directory. Verify the fingerprint independently as directed by the policy guide; replace that temporary
certificate before normal operations. Retain passwords/session secrets outside the issuer.

### 8. Install the runtime without activating signing

For the **first empty database only**, set `openxpki_initialize_database: true` in
**`<prefix>-tier-0/ansible/group_vars/issuer.yml`**. Run from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
```

After success, return `openxpki_initialize_database` to `false`; keep `openxpki_activate_runtime: false`.
**Expected:** packages, local MariaDB, TLS portal and restricted publication endpoint installed;
signing daemons stopped.

The role refuses unregistered existing CA configuration, a lost/partial schema,
wrong storage, changed package/configuration bindings and changed database/session
secrets. It never reformats storage, migrates a live database, creates CA keys,
imports issuer tokens, changes a schema in place or silently adopts an existing CA.

## Step 3: Activate and accept issuance

### 9. Create and sign the issuer request

Use the [custody variant selected in Stage 3](../README.md#step-1-prepare-issuer-and-key-custody).
Create the issuer key/CSR through its qualified provider; software custody uses the
[fresh-key recipe](software-pki.md#install-and-prepare-the-issuing-key).
Complete the authorized [offline root ceremony](offline-root.md), then return here with only public certificates.

### 10. Start the prepared backend

In **Tier 0 `ansible/group_vars/issuer.yml`**, set `openxpki_issuer_certificate_src`,
`openxpki_root_certificate_src` to the public ceremony outputs on the controller and set
their independently recorded `openxpki_issuer_fingerprint` and `openxpki_root_fingerprint`.
From **`<prefix>-tier-0/`**, install those public files through IaC:

```bash
bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki-certificates.yml --ansible-vars ansible/group_vars/issuer.yml
```

The recipe verifies the fingerprints and chain, refuses a different existing identity,
and copies no private signing keys.

Edit **`<prefix>-tier-0/ansible/group_vars/issuer.yml`**: populate `openxpki_required_state_paths`
with the actual signing-provider and DataVault recovery paths, then set `openxpki_activate_runtime: true`.
From **`<prefix>-tier-0/`**, rerun the installation command in action 8.

**Expected:** missing material, a different CA certificate or an expired issuer stops activation.
Starting the backend does not activate its CA token.

### 11. Activate the token and accept issuance

For the supplied software-key bundle, from the **Tier 0 controller**, complete
[native certificate/token activation](issuer-token.md) for the selected revision. [3]
Hardware-backed keys need their qualified provider/token procedure; the filesystem-key commands do not bind an HSM.
Chain import and key binding are controlled operations, never automatic playbook side effects.

Verify a permitted request, denied request, renewal, revocation and fresh CRL at the configured `/download/` URL.
Test portal TLS from an **administrative workstation** and publication from a **consumer network**.
Complete [CA recovery acceptance](../../../05-operations/03-cryptography/certificate-authority.md)
before relying on issuance. Configuration/API checks alone are insufficient.

The production bundle supplies workflows, approval roles, leaf profiles, provider
configuration and CRL publication policy. The playbook does not invent those security
decisions. Community's native ACME is Enterprise-only; acme2certifier requires a
separately qualified authenticated RPC adapter. RPC, ACME, SCEP and other enrollment
routes are denied by this initial Apache configuration. [4][5]

Stage 5 uses the [external FreeIPA flow](../../stage-5-identity/procedures/freeipa.md#external-ca-integration-gate)
for a sibling identity CA. Existing domains are never recreated or rechained by refresh.

## IaC ownership

| Repository | Path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/](../../../../tier-0/terraform/deployments/foundation) | Issuer and identity VM resources/state; per-guest image and extra disks |
| Tier 0 | [ansible/roles/openxpki/](../../../../tier-0/ansible/roles/openxpki) | Native package, local database, TLS portal, storage binding and activation checks |
| Tier 0 | [deployment/openxpki.yml](../../../../tier-0/ansible/playbooks/deployment/openxpki.yml), [maintenance/openxpki.yml](../../../../tier-0/ansible/playbooks/maintenance/openxpki.yml) | Issuer-only deployment and read-only inspection |
| Tier 0 | [issuer.yml.example](../../../../tier-0/ansible/group_vars/issuer.yml.example) | Local production input contract |
| Shared | [scripts/deploy.sh](../../../../shared/scripts/deploy.sh) | Reusable execution only; `--playbook` does not select new Terraform state |

## References

Sources checked 2026-10-17.

[1]: https://github.com/openxpki/openxpki/blob/master/QUICKSTART.md
[3]: https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md

1. [OpenXPKI native packages and production configuration][1]
2. [Debian Bookworm lifecycle](https://www.debian.org/releases/bookworm/)
3. [OpenXPKI configuration, schema, token and DataVault setup][3]
4. [OpenXPKI endpoint and edition boundaries](https://openxpki.readthedocs.io/en/master/frontend/endpoints.html)
5. [acme2certifier OpenXPKI integration](https://github.com/grindsa/acme2certifier/blob/master/docs/openxpki.md)
