# Step 1d: Single USB key device

**Working repository:** `<prefix>-tier-0/` on the protected controller (source: `tier-0/`).

**Branch from:** [Step 1](README.md#step-1-prepare-issuer-and-key-custody), before production keys.
**Change:** protect the issuer's original key in one local USB device.
**Return:** [Step 1, action 2](README.md#step-1-prepare-issuer-and-key-custody) for the hardware-key CSR,
then Step 2 signing. **Design:** [custody choices](../../01-architecture/08-cryptography/03-hsm-selection.md).

## Contents

- [1. Select custody and preserve key identity](#1-select-custody-and-preserve-key-identity)
- [2. Declare USB attachment and install the inactive issuer](#2-declare-usb-attachment-and-install-the-inactive-issuer)
- [3. Bind the inactive issuer to its original key](#3-bind-the-inactive-issuer-to-its-original-key)
- [4. Create a CSR from the existing key](#4-create-a-csr-from-the-existing-key)
- [5. Complete activation and acceptance](#5-complete-activation-and-acceptance)
- [References](#references)

## 1. Select custody and preserve key identity

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

An offline root stays on its offline ceremony host. The connected issuer playbook excludes
`root_ca`; do not bring offline root custody online.

## 2. Declare USB attachment and install the inactive issuer

In the existing `terraform/deployments/foundation/terraform.tfvars`, add `usb_devices` to the
original `vm_instances["ca-1"]` object, for example `[{ mapping = "ca-1-token" }]`, and set its
explicit `proxmox_node_name` to the device's node. Each entry accepts exactly one approved `host`
bus-port/ID or existing Proxmox `mapping`, with optional `usb3`. [1] The module, normalized guest
inputs and foundation root all forward that field to the native VM resource.

Retain the original issuer VMID, template, disks, inventory and state. Use an existing approved
device mapping or physical port and complete the selected
[cluster mobility restrictions](../foundation/proxmox/step-1b-cluster-ha.md#terraform-against-the-cluster);
a mapping does not copy keys or establish failover. Do not manage this issuer from the HSM pool's state.

Plan from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh foundation --terraform-only --plan-only
```

Require an attachment change without issuer/disk replacement. Apply from **`<prefix>-tier-0/`**:

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

For PicoHSM, the role installs a native Polkit rule granting only declared service users PC/SC
context access and access to the exact selected readers. It does not disable PC/SC authorization.
Obtain the reader description through the controller-run provider inspection; no guest login is
needed. Native PC/SC and physical-token acceptance must run as the real issuer service user. [8]

In the existing reviewed issuer configuration archive, select `token.ca-signer.engine: PKCS11`,
`key_store: ENGINE`, that exact `key` URI and a native `engine_section` with the selected engine
`dynamic_path`, provider `MODULE_PATH`, and `PIN = __PIN__`. Retain the protected native `secret`
reference. The supplied role validates this contract rather than editing the immutable bundle. [2]

In `issuer.yml`, keep `openxpki_required_state_paths` aligned with the original certificate,
DataVault recovery state and any persistent provider/client identity under `openxpki_data_mount`.
These are recovery records or enrolled client files, not an exported hardware private key. The
normal issuer activation guard requires the selected files to exist on the original mounted volume.

Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/issuer.yml ansible/playbooks/deployment/hsm-issuer.yml
```

Expected result: approved packages/configuration installed, original token visible to the issuer
account, native signer configuration validated, and provider environment bound to the inactive
service. No key is created/imported and issuance stays stopped. A missing token or mismatched bundle
stops the operation. YubiHSM's local connector listens only on loopback; it is not a signing API. [3]

The direct issuer, inspection and hardware-token recipes run the Tier 0 controller precheck for
setup `hsm` first, including its cryptographic dependencies, without requiring Terraform. On a
prepared disconnected controller, use `CONTROL_NODE_COLLECTIONS_MODE=check` to forbid acquisition.

## 4. Create a CSR from the existing key

Set `hsm_issuer_create_csr: true` and `hsm_issuer_common_name` in the selected hardware inputs.
Supply the existing device's application PIN through protected controller environment
`HSM_ISSUER_PIN`; for YubiHSM its format includes the authentication-key ID. [4] Never use a default
credential or put it in Git, command arguments or a PKCS#11 URI. Automated execution can inject
this environment value without an interactive prompt.

Rerun the command above from **`<prefix>-tier-0/`**. The explicit ceremony operation reads the
original key's public component and signs a path-length-zero CA CSR through OpenSSL's native
PKCS#11 engine. It verifies the CSR signature/public-key match and fetches only the public CSR to
`hsm_issuer_csr_dest` on the controller. Existing CSRs are preserved and must match; a mismatch
requires recovery. Disable the CSR flag after use and clear the injected PIN.

Review the CSR against the retained original public-key record before Step 2. No key-generation
command exists in this hardware workflow.

## 5. Complete activation and acceptance

After device commissioning and original-key recovery qualification, set
`hsm_provider_custody_ready: true` in `ansible/group_vars/issuer.yml` as well as the selected hardware
inputs. The ordinary issuer installer checks this before starting a PKCS#11-backed runtime;
an inactive installation remains permitted. Factory credentials are not accepted for direct key operations.

Return to Step 2 with the reviewed CSR. Install the signed public certificate and start the prepared
backend through the normal issuer certificate/runtime steps. Keep the original provider environment,
protected signer secret and DataVault state. Use `deployment/hsm-token.yml` for hardware activation;
the separate software token recipe checks a filesystem key.

Run each explicit operation from **`<prefix>-tier-0/`**, with the existing `HSM_ISSUER_PIN` injected:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
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

## References

Sources checked 2026-11-11.

1. [bpg native USB attachment](https://github.com/bpg/terraform-provider-proxmox/blob/main/docs/resources/virtual_environment_vm.md)
2. [OpenXPKI PKCS#11 engine and key identifier contract](https://github.com/openxpki/openxpki/blob/master/core/server/OpenXPKI/Crypto/Backend/OpenSSL/Engine/PKCS11.pm)
3. [YubiHSM connector configuration](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-tools-connector.html)
4. [YubiHSM PKCS#11 configuration and credential format](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html)
5. [PicoHSM firmware, OpenSC interface and mechanism limits](https://github.com/polhenarejos/pico-hsm)
6. [YubiHSM wrapped backup requirements](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-backup-restore.html)
7. [PicoHSM DKEK backup and restore](https://docs.picokeys.com/picohsm/backup-restore/)
8. [PC/SC maintainer's native Polkit authorization guidance](https://blog.apdu.fr/posts/2023/11/pcsc-lite-and-polkit/)
