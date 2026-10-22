# Deploy the infrastructure issuer

Install the permanent OpenXPKI Community runtime on `ca-1`, then activate the
separately signed issuer. An existing qualified issuer is also a valid prerequisite.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Design:** [certificate authority](../../../architecture/cryptography/certificate-authority.md).
**Prerequisites:** accepted logging, independent SSH/DNS, approved Debian template,
prepared data storage, production configuration bundle and authorized custodians.

## Contents

- [Step 1: Provision the host](#step-1-provision-the-host)
- [Step 2: Install the runtime](#step-2-install-the-runtime)
- [Step 3: Activate and accept issuance](#step-3-activate-and-accept-issuance)
- [IaC ownership](#iac-ownership)
- [References](#references)

## Step 1: Provision the host

1. Publish an approved Debian image using the Tier 0
   [template lifecycle](../../../administration/compute/template-lifecycle.md).
   The catalogue includes a Debian example; the image and checksum are supplied locally.
   Record the approved ID/title in Shared's consumer catalogue. The current native
   package path requires Debian 12 amd64; its LTS end is 2028-06-30. Revalidate the
   supported platform and upgrade milestone before adoption. [1][2]
2. Initialize inputs:

   ```bash
   bash scripts/init-local-files.sh --setup foundation
   cp -n ansible/group_vars/issuer.yml.example ansible/group_vars/issuer.yml
   ```

   Set `ca-1`'s per-guest `template_vm_id`, extra data disk, `issuing_ca` inventory
   entry and foundation IP. For a new Stage 2 installation, the desired guest map
   may contain only `ca-1`; later add the identity pair to this **same state**.
   The unchanged starter includes all three guests; it is not an issuer-only plan.
   Never remove an already-managed guest to match a stage label.
3. Review and provision, without running the identity recipe:

   ```bash
   bash scripts/deploy.sh foundation --plan-only
   ```

   After review:

   ```bash
   bash scripts/deploy.sh foundation --terraform-only
   ```

Retain the same `--env` context for every subsequent command if one was selected.
The foundation extra-disk input now reaches the guest module without moving state.
It attaches storage; it does not partition, format or mount it.

## Step 2: Install the runtime

For the supplied software policy, first build the private artifact using
[software PKI setup](software-pki.md#build-the-private-policy-bundle).

1. Prepare the dedicated data filesystem and its `mysql` bind mount at `/var/lib/mysql`
   before installing MariaDB. Follow the exact [runtime input and bundle contract](../../../reference/openxpki.md).
   Configure independent access and Stage 1 audit forwarding; verify a test event
   at the protected receiver before proceeding.
2. Populate ignored `ansible/group_vars/issuer.yml`: approved package versions,
   repository-key checksum, production archive checksum, mount UUID and restricted
   portal/publication networks. Supply passwords and portal TLS inputs through the
   protected controller environment or a secret-only Ansible override. No demo
   policy, account, key or password is generated. [1][3]
3. For the first empty database only, set `openxpki_initialize_database: true`, then run:

   ```bash
   bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

   Return initialization to `false` afterward. Keep `openxpki_activate_runtime: false`
   until ceremony preparation is complete. Packages, local MariaDB, TLS portal and
   restricted public-object endpoint are installed; the signing daemons remain stopped.

The role refuses unregistered existing CA configuration, a lost/partial schema,
wrong storage, changed package/configuration bindings and changed database/session
secrets. It never reformats storage, migrates a live database, creates CA keys,
imports issuer tokens, changes a schema in place or silently adopts an existing CA.

## Step 3: Activate and accept issuance

1. Select the [software/USB/network custody variant](../README.md#step-1-prepare-issuer-and-key-custody).
   Create the issuing key/CSR through its qualified provider (the software path has
   an [explicit fresh-key recipe](software-pki.md#install-and-prepare-the-issuing-key)).
   Complete the
   [offline root ceremony](offline-root.md), then use the selected OpenXPKI revision's
   native certificate/token procedure after starting the prepared backend below.
2. Place the public issuer certificate at `/srv/openxpki/identity/issuer.pem` and
   record its SHA-256 fingerprint independently. Populate `openxpki_required_state_paths`
   with actual signing-provider and DataVault recovery paths. Set
   `openxpki_activate_runtime: true` and rerun the Step 2 command. Missing material,
   a different CA certificate or an expired issuer stops runtime activation. With
   the backend running, follow the [native certificate/token procedure][3] to import
   the chain and bind the prepared signing key. This controlled operation is never
   an automatic playbook side effect; starting a daemon does not activate its CA token.
3. Verify a permitted request, denied request, renewal, revocation and fresh CRL at
   the configured `/download/` URL. Test portal TLS from an administrative workstation
   and publication from a consumer network. Complete
   [CA recovery acceptance](../../../administration/cryptography/certificate-authority.md)
   before relying on issuance. Native configuration/API checks alone are not acceptance.

The production bundle supplies workflows, approval roles, leaf profiles, provider
configuration and CRL publication policy. The playbook does not invent those security
decisions. Community's native ACME is Enterprise-only; acme2certifier requires a
separately qualified authenticated RPC adapter. RPC, ACME, SCEP and other enrollment
routes are denied by this initial Apache configuration. [4][5]

Stage 3 uses the [external FreeIPA flow](../../stage-3-identity/procedures/freeipa.md#external-ca-integration-gate)
for a sibling identity CA. Existing domains are never recreated or rechained by refresh.

## IaC ownership

| Repository | Path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/](../../../../tier-0/terraform/deployments/foundation/) | Issuer and identity VM resources/state; per-guest image and extra disks |
| Tier 0 | [ansible/roles/openxpki/](../../../../tier-0/ansible/roles/openxpki/) | Native package, local database, TLS portal, storage binding and activation checks |
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
