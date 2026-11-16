# Step 1d: Single USB key device

**Expected result — IaC and Manual:** `ca-1` in the
[issuer view](README.md#figure-1-offline-root-and-online-issuer) keeps its original issuing key in one
host-local USB device. IaC attaches the accepted device and configures its provider; physical/key
commissioning and independent recovery remain custodial work. No provider-pool VMs are added.

**Working repository:** `<prefix>-tier-0/` on the protected controller (source: `tier-0/`).

**Branch from:** [Step 1](README.md#step-1-prepare-issuer-and-key-custody), before production keys.
**Change:** protect the issuer's original key in one local USB device.
**Return:** [action 10b](README.md#step-10-prepare-the-issuing-request) for the hardware-key CSR,
then action 11 signing. **Design:** [custody choices](../../01-architecture/08-cryptography/03-hsm-selection.md).

**First installation:** complete device commissioning in action 1 now. Initialize and edit the USB
attachment in action 2 before [Stage 2 actions 4–6](README.md#step-4-prepare-the-private-policy),
so the immutable policy names the commissioned original key. Provision once at Stage 2 action 7,
then install the inactive runtime at action 9. Return to this option's actions 3–4 at
[10b](README.md#step-10-prepare-the-issuing-request). Action 5 rejoins signing and token activation.

## Contents

- [1. Select custody and preserve key identity](#1-select-custody-and-preserve-key-identity)
- [2. Declare USB attachment and install the inactive issuer](#2-declare-usb-attachment-and-install-the-inactive-issuer)
- [3. Bind the inactive issuer to its original key](#3-bind-the-inactive-issuer-to-its-original-key)
- [4. Create a CSR from the existing key](#4-create-a-csr-from-the-existing-key)
- [5. Complete activation and acceptance](#5-complete-activation-and-acceptance)
- [Later: expand to a provider pool](#later-expand-to-a-provider-pool)
- [References](#references)

## 1. Select custody and preserve key identity

Choose the device-specific preparation, then use the shared VM/provider steps below:

| Device | Prepare before attaching it to the issuer |
| --- | --- |
| **YubiHSM 2** | Complete the [first-key recovery choices](#yubihsm-first-key-recovery-choices) below before creating the issuer key; retain the original wrapped objects and wrap key [4][6] |
| **PicoHSM, blank board** | Complete [firmware, DKEK, initial key and wrapped backup](procedures/picohsm.md); return here with its serial, key ID and public fingerprint |
| **PicoHSM, existing key or additional board** | Preserve the original key; use [wrapped-key restoration](../../05-operations/03-cryptography/picohsm-replica.md) for an additional device |

Select `picohsm` (OpenSC's `sc-hsm` driver) or `yubihsm2`, approved middleware and recovery policy.
Physical attachment, device initialization and custodial creation/import/backup are explicit
manufacturer/custodian operations. Retain the original issuer key, object identity and public-key
record. If unavailable, recover that key or perform a separately approved CA rollover; deployment
must never generate a replacement silently. One device provides no device/host failover.

Change factory credentials during physical commissioning before setting
`hsm_provider_custody_ready: true`. Issuer CSR/token operations reject PicoHSM's factory user PIN
and YubiHSM's factory authentication-key/password value; they never reset the device. [4][5]
YubiHSM 2 is not a YubiKey PIV token. PicoHSM has its own firmware and hardware threat model;
this profile does not claim certified tamper resistance. [5]

| Profile | PKI signing and mechanism qualification | Custody/identity |
| --- | --- | --- |
| `yubihsm2` | Native Yubico PKCS#11 RSA/ECDSA; qualify the actual key, mechanism and OpenSSL engine | Connector selects hardware serial; PKCS#11 serial/object ID and original SPKI pin the signing identity; wrapped backup requires the original wrap policy/capabilities [4][6] |
| `picohsm` | OpenSC `sc-hsm` RSA/ECDSA; exact mechanisms depend on firmware and middleware | PC/SC reader authorization plus PKCS#11 serial/object ID; DKEK custody governs supported wrapped recovery [5][7] |

Firmware capabilities are not necessarily exposed by the selected module. PicoHSM documents
RSA-PKCS/RSA-PSS and ECDSA, but its additional AES modes use the PicoHSM Python tool, and its
CMAC/key-derivation features have PKCS#11 module limitations. Do not infer AES-GCM or a Vault
seal mechanism from this RSA/ECDSA issuer path; qualify the precise consumer and module. [5]
YubiHSM wrapped backups and PicoHSM DKEK backups are not interchangeable. A same-key pool uses
two qualified devices from one family; the other family can serve a different key domain.

### YubiHSM first-key recovery choices

Run this physical commissioning on the protected ceremony host with only the intended device
available, using the approved SDK's native shell and the vendor backup procedure. Do this **before
the original production key is created**, even if only one device is available now. [6][9]

1. Record firmware/SDK, device serial and PKCS#11 serial separately. Replace/delete the factory
   administrator credential after testing its replacement. Create a signing-only application
   authentication key in the issuer's selected domain; retain separate administrative/backup custody.
2. For a future same-key replica, create the original asymmetric issuer key with its required signing
   capabilities **and `exportable-under-wrap`**. For example, an ECDSA issuer needs `sign-ecdsa` plus
   `exportable-under-wrap`. Keep the signing credential free of backup, import, deletion and key-generation
   privileges. Do not assume these object capabilities can be added to an existing key later. [9][10]
3. Provision a retained wrap key under independent protected custody. For the vendor's symmetric
   backup route, the destination must later receive the **same wrap-key material**. Give the backup
   wrap object `export-wrapped`/`import-wrapped`, the required object domains and delegated capabilities
   covering the original objects. The backup operator's authentication key also needs the matching
   permissions/domains. A wrap key generated only inside a lost device is not an independent backup. [6]
4. Export the approved original issuer object with native `get-wrapped`. Retain its object type/ID,
   label, algorithm, domains/capabilities, public SPKI/fingerprint and any PKCS#11 metadata objects needed
   by the selected SDK. Back up required authentication objects or document tested independent
   reprovisioning; do not clone administrator credentials into an online signing role. [6][11]
5. Rehearse native `put-wrap-key`/`put-wrapped` on an isolated compatible recovery device and require
   the original public fingerprint, signing and denied-operation tests. Keep the original wrap material,
   wrapped objects and recovery credentials outside the controller and independently recoverable.
   With no recovery device, record that qualification remains outstanding; do not assert readiness.

This permits **vendor-wrapped backup only**, not plaintext private-key export to the controller.
Yubico maps PKCS#11 `CKA_EXTRACTABLE` to wrapped-export permission; do not force a generic
`CKA_EXTRACTABLE=false` policy and also promise later replication. If policy forbids even wrapped
export, retain that restriction and plan a new-key issuer rollover when the sole device is lost or
capacity changes. A lost original wrap key/blob cannot be replaced by generating another. [6][11]

An offline root stays on its offline ceremony host. The connected issuer playbook excludes
`root_ca`; do not bring offline root custody online.

## 2. Declare USB attachment and install the inactive issuer

Initialize the common inputs from **`<prefix>-tier-0/`**:

```bash
bash scripts/init-local-files.sh --setup foundation --setup hsm
```

This prepares `foundation.yml`, `issuer.yml` and `hsm.yml` without deploying guests.
The `hsm` Terraform starter is for a later provider pool; the single-device issuer stays in the
existing **foundation** state.

In **`terraform/deployments/foundation/terraform.tfvars`**, add these fields inside the existing
`vm_instances["ca-1"]` object. Replace `pve01` with the node holding the device and `ca-1-token`
with its approved **Datacenter → Resource Mappings → USB** mapping:

```hcl
proxmox_node_name = "pve01"
usb_devices      = [{ mapping = "ca-1-token" }]
```

Each entry accepts exactly one approved `host`
bus-port/ID or existing Proxmox `mapping`, with optional `usb3`. [1] The module, normalized guest
inputs and foundation root all forward that field to the native VM resource.

For the routine provisioning token, use `mapping` and complete its
[scoped mapping permission](../foundation/proxmox/api-access.md#usb-mapping-access) before apply.
The mapping must exist and identify the intended physical device on that node.

Retain the original issuer VMID, template, disks, inventory and state. Use an existing approved
device mapping or physical port and complete the selected
[cluster mobility restrictions](../foundation/proxmox/step-1b-cluster-ha.md#terraform-against-the-cluster);
a mapping does not copy keys or establish failover. Do not manage this issuer from the HSM pool's state.

Plan from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh foundation --terraform-only --plan-only
```

For an existing issuer, require an attachment change without issuer/disk replacement. On a fresh
installation, include these fields before Stage 2 action 7 and use that first provisioning run.
Apply a pending attachment change from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh foundation --terraform-only
```

The unattended variant is `--auto-approve` on the same apply command. Terraform attaches the
selected USB device; no manual guest or Proxmox attachment command is required.

Install the inactive runtime through the [issuer procedure](procedures/issuer.md), including its
Terraform-owned data disk and Ansible-managed mount. Keep `openxpki_create_issuer_key: false` and
`openxpki_activate_runtime: false`. Skip the software key-creation step for this hardware branch.

## 3. Bind the inactive issuer to its original key

Configure `ansible/group_vars/hsm.yml` using the
[provider example and defaults](../../../tier-0/ansible/group_vars/hsm.yml.example):

| Input | Required selection |
| --- | --- |
| `hsm_provider`, `hsm_provider_mode` | `picohsm` or `yubihsm2`, with `usb`; legacy `opensc`/`yubihsm` aliases remain accepted |
| Packages and library | Approved middleware, exact library and OpenSSL PKCS#11 engine package/path |
| Device identity | `hsm_provider_expected_serial`; also `hsm_yubihsm_serial` for a local YubiHSM connector |
| Application identity | `hsm_provider_user: openxpki`, `hsm_provider_group: openxpki` |
| `hsm_issuer_key` | Original private-key PKCS#11 URI, including token serial and object ID; no PIN in the URI |
| `hsm_issuer_engine_library` | Installed OpenSSL engine, distinct from the device's PKCS#11 library |
| PicoHSM PC/SC access | `hsm_provider_pcsc_readers`: exact accepted reader names, with `hsm_provider_pcsc_users` defaulting to the selected nonroot provider user |
| Production custody | `hsm_provider_custody_ready: true` after changed credentials and independently tested recovery |

For **PicoHSM on the Debian 12 amd64 issuer**, replace the device-specific fields in
**`ansible/group_vars/hsm.yml`** with:

```yaml
hsm_provider: picohsm
hsm_provider_mode: usb
hsm_provider_packages: [opensc, libengine-pkcs11-openssl]
hsm_provider_library: /usr/lib/x86_64-linux-gnu/opensc-pkcs11.so
hsm_provider_expected_serial: "COPY_THE_TOKEN_SERIAL"
hsm_provider_user: openxpki
hsm_provider_group: openxpki
hsm_provider_pcsc_readers: ["COPY_THE_EXACT_READER_NAME"]
hsm_issuer_engine_library: /usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so
hsm_issuer_key: "pkcs11:serial=COPY_THE_TOKEN_SERIAL;id=%01;type=private"
hsm_issuer_create_csr: false
```

Use the actual commissioned token serial twice; `%01` selects the public-record key ID `01`.
For the reader name on this VM, run the preparatory inspection from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/foundation.yml ansible/playbooks/deployment/hsm-prepare.yml
```

It installs middleware/CCID support and prints public reader/token inventory as root, without
changing keys or granting application access. Copy that exact reader name into the field above.
The normal binding below then verifies access as `openxpki`. Retain YubiHSM's separate connector
settings when selecting that profile instead.

For **YubiHSM on that Debian issuer**, select its approved SDK packages from the configured package
source and replace the device fields in **`ansible/group_vars/hsm.yml`** with:

```yaml
hsm_provider: yubihsm2
hsm_provider_mode: usb
hsm_provider_packages: [yubihsm-connector, yubihsm-pkcs11, libengine-pkcs11-openssl]
hsm_provider_library: /usr/lib/x86_64-linux-gnu/pkcs11/yubihsm_pkcs11.so
hsm_provider_expected_serial: "COPY_THE_PKCS11_TOKEN_SERIAL"
hsm_yubihsm_serial: "COPY_THE_PHYSICAL_DEVICE_SERIAL"
hsm_provider_user: openxpki
hsm_provider_group: openxpki
hsm_issuer_engine_library: /usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so
hsm_issuer_key: "pkcs11:serial=COPY_THE_PKCS11_TOKEN_SERIAL;id=%00%01;type=private"
hsm_issuer_create_csr: false
```

Verify package/library paths against the accepted SDK. The URI example assumes the module reports
key ID `0001`; percent-encode the **actual CKA_ID bytes**, retaining leading zero bytes when reported.
The signing key ID, application authentication-key ID and physical/PKCS#11 serials are separate
identities. Retrieve the original key's ID/public fingerprint from commissioning, and use its
least-privilege authentication login, not an administrator or wrap credential. [4][9][11]

For PicoHSM, the role installs a native Polkit rule granting only declared service users PC/SC
context access and access to the exact selected readers. It does not disable PC/SC authorization.
Obtain the reader description through the controller-run provider inspection; no guest login is
needed. Native PC/SC and physical-token acceptance must run as the real issuer service user. [8]

The native PKCS#11 policy built at [Stage 2 actions 4–6](README.md#step-4-prepare-the-private-policy)
must already use the same key URI, module and engine paths. The supplied builder selects
`token.ca-signer.engine: PKCS11`, `key_store: ENGINE` and a protected native PIN secret.
The binding role validates that immutable artifact instead of editing it on the running host. [2]
Retain that accepted archive and checksum. If its key or paths differ, correct the selected policy
before the first runtime installation; an installed immutable deployment needs its qualified change procedure.

In **`ansible/group_vars/issuer.yml`**, select the generated bundle's CLI and real hardware-state paths:

```yaml
openxpki_managed_cli: true
openxpki_required_state_paths:
  - /srv/openxpki/identity/issuer.pem
  - "{{ openxpki_release_dir }}/config.d/realm/{{ openxpki_realm }}/crypto.yaml"
  - "{{ openxpki_release_dir }}/config.d/system/crypto.yaml"
```

These retain the public issuer identity and immutable signer/DataVault configuration; the private
signing key stays on the device. Independently retain device wrapping material and credentials too.
The activation guard requires these files on the original mounted data volume.

Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml ansible/playbooks/deployment/hsm-issuer.yml
```

Expected result: approved packages/configuration installed, original token visible to the issuer
account, native signer configuration validated, and provider environment bound to the inactive
service. No key is created/imported and issuance stays stopped. A missing token or mismatched bundle
stops the operation. YubiHSM's local connector listens only on loopback; it is not a signing API. [3]

Load `foundation.yml` after `hsm.yml` so the issuer uses its existing `platform_host_ips` map.
For a named environment, also load `all.<env>.yml` and `foundation.<env>.yml` after these base
inputs, before `issuer.yml`.

The direct issuer, inspection and hardware-token recipes run the Tier 0 controller precheck for
setup `hsm` first, including its cryptographic dependencies, without requiring Terraform. On a
prepared disconnected controller, use `CONTROL_NODE_COLLECTIONS_MODE=check` to forbid acquisition.

## 4. Create a CSR from the existing key

Set `hsm_issuer_create_csr: true` and `hsm_issuer_common_name` in **`ansible/group_vars/hsm.yml`**,
for example `Example Infrastructure Issuing CA`. Set `hsm_issuer_csr_dest` to a protected absolute
controller file, for example `/home/automation/.local/share/pki-ceremony/ca-1-issuer.csr`.
Supply the existing device's application PIN through protected controller environment
`HSM_ISSUER_PIN`; for YubiHSM its format includes the authentication-key ID. [4] Never use a default
credential or put it in Git, command arguments or a PKCS#11 URI. Automated execution can inject
this environment value without an interactive prompt.

Rerun the command above from **`<prefix>-tier-0/`**. The explicit ceremony operation reads the
original key's public component and signs a path-length-zero CA CSR through OpenSSL's native
PKCS#11 engine. It verifies the CSR signature/public-key match and fetches only the public CSR to
`hsm_issuer_csr_dest` on the controller. Existing CSRs are preserved and must match; a mismatch
requires recovery. Disable the CSR flag after use and clear the injected PIN.

Review the CSR against the retained original public-key record before action 11. No key-generation
command exists in this hardware workflow.

## 5. Complete activation and acceptance

After device commissioning and original-key recovery qualification, set
`hsm_provider_custody_ready: true` in `ansible/group_vars/issuer.yml` as well as the selected hardware
inputs. The ordinary issuer installer checks this before starting a PKCS#11-backed runtime;
an inactive installation remains permitted. Factory credentials are not accepted for direct key operations.

Continue at [Stage 2, action 11](README.md#step-11-sign-the-approved-request-offline) with the reviewed CSR. Install the signed public certificate and start the prepared
backend through the normal issuer certificate/runtime steps. Keep the original provider environment,
protected signer secret and DataVault state. Use `deployment/hsm-token.yml` for hardware activation;
the separate software token recipe checks a filesystem key.

Reload the original device credential after the offline ceremony. Run from **`<prefix>-tier-0/`**:

```bash
read -r -s -p 'Existing HSM application PIN: ' HSM_ISSUER_PIN; printf '\n'
export HSM_ISSUER_PIN
```

Run each explicit operation from the same protected Tier 0 shell:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml -e openxpki_token_operation=inspect \
  ansible/playbooks/deployment/hsm-token.yml
```

Repeat in order with `openxpki_token_operation=import-root`, then `import-issuer`, then `check`.
Before `check`, set `openxpki_token_alias` in the issuer inputs to the alias returned by import.
Finally select `publish-crl` and `publish-ca`, following returned workflow identifiers through
completion. Imports are explicit one-time CLI writes; inspect an existing alias before repeating them.
The recipe checks the pinned certificate, original hardware public-key match and public chain before
any selected token operation; it never exports or replaces the private key.

Qualify disposable sign/verify, denied operations, token removal, service restart and independent
restore before production use. Match the signed issuer certificate to the original hardware public
key. Optional [shared remote access](procedures/pkcs11-remoting.md) follows this local acceptance;
it is not a prerequisite for PKI or HashiCorp Vault. A backup token is not automatic failover.

## Later: expand to a provider pool

Start with the local issuer device and retain its wrapping/recovery material from the first key.
For PicoHSM, add boards by [restoring the same wrapped key](../../05-operations/03-cryptography/picohsm-replica.md),
then follow [single device to provider pool](../../05-operations/03-cryptography/usb-hsm.md#single-device-to-pool).
YubiHSM uses its own original wrap key and backup format instead. Never generate a new issuing key
just to add capacity; device replication and CA/database replication are separate operations.

## References

Sources checked 2026-11-16; device commissioning and restoration require physical qualification.

1. [bpg native USB attachment](https://github.com/bpg/terraform-provider-proxmox/blob/main/docs/resources/virtual_environment_vm.md)
2. [OpenXPKI PKCS#11 engine and key identifier contract](https://github.com/openxpki/openxpki/blob/master/core/server/OpenXPKI/Crypto/Backend/OpenSSL/Engine/PKCS11.pm)
3. [YubiHSM connector configuration](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-tools-connector.html)
4. [YubiHSM PKCS#11 configuration and credential format](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html)
5. [PicoHSM firmware, OpenSC interface and mechanism limits](https://github.com/polhenarejos/pico-hsm)
6. [YubiHSM wrapped backup requirements](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-backup-restore.html)
7. [PicoHSM DKEK backup and restore](https://docs.picokeys.com/picohsm/backup-restore/)
8. [PC/SC maintainer's native Polkit authorization guidance](https://blog.apdu.fr/posts/2023/11/pcsc-lite-and-polkit/)
9. [YubiHSM domains, object capabilities and separate operator/backup roles](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-intro-access-control.html)
10. [YubiHSM immutable object properties](https://developers.yubico.com/YubiHSM2/Releases/Known_issues.html)
11. [YubiHSM PKCS#11 attribute mapping and metadata objects](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-tools-pkcs11.html)
