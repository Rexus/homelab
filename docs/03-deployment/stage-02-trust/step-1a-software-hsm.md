# 1a: Software PKCS#11 issuer with SoftHSM2

Use this no-hardware path for a **fresh online issuer, `ca-1`**, running Debian 12 amd64.
SoftHSM2 stores its token on the issuer's dedicated data disk. The
[trust overview figure](README.md#figure-1-offline-root-and-online-issuer) still applies:
the offline root is separate and signs only the subordinate CA request.

> [!IMPORTANT]
> SoftHSM2 provides the PKCS#11 interface, **not hardware isolation**. Host root or a compromise of
> the issuer account can compromise its keys. Retain encrypted independent recovery copies. Existing
> encrypted-PEM issuers keep their current path; this procedure does not migrate or replace their keys. [1]

> [!TIP]
> **Recovery and maintenance:** use the [stopped full-VM backup and restore path](../../05-operations/06-resilience/backups/virtual-machines.md)
> with **all VM disks included**. The [logical issuer archive](../../05-operations/03-cryptography/issuer-recovery.md)
> omits SoftHSM token files and cannot recover this option by itself.
> See [recovery requirements below](#7-retain-and-rehearse-recovery) before enabling issuance.

**Working repository:** `<prefix>-tier-0/` on bootstrap. All guest actions run through Ansible.
**Branch from:** [Stage 2 Step 1](README.md#step-1-prepare-issuer-and-key-custody).
**Return:** after initialization, [Step 6: policy](README.md#step-6-prepare-policy-and-secrets);
after inactive runtime installation, [Step 10a: CSR](README.md#10a-software-hsm-selected-1a).
**Starting point:** the offline root is prepared, `ca-1` is provisioned through the foundation
Terraform root, and its dedicated `scsi1` data disk is attached. No issuer runtime or signer exists yet.
Use this commissioning procedure **before building the immutable issuer policy bundle**; the real
token serial is needed in that bundle. Do not invent a serial or build a temporary PEM issuer.

## Contents

- [1. Initialize editable inputs](#1-initialize-editable-inputs)
- [2. Prepare the disk and middleware](#2-prepare-the-disk-and-middleware)
- [3. Explicitly create the token and signing key](#3-explicitly-create-the-token-and-signing-key)
- [4. Return to issuer policy creation](#4-return-to-issuer-policy-creation)
- [5. Bind the installed inactive issuer](#5-bind-the-installed-inactive-issuer)
- [6. Create and sign the issuer request](#6-create-and-sign-the-issuer-request)
- [7. Retain and rehearse recovery](#7-retain-and-rehearse-recovery)
- [Later hardware and pool growth](#later-hardware-and-pool-growth)
- [References](#references)

## 1. Initialize editable inputs

Run from **`<prefix>-tier-0/`**:

```bash
bash scripts/init-local-files.sh --setup hsm-software
```

Edit **`ansible/group_vars/issuer.yml`**: select `openxpki_data_device`, `openxpki_data_fstype`
and any retained `openxpki_data_uuid` for `ca-1`'s existing Terraform-owned disk. The default device
is `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`, independent of Linux `sda`/`sdb` order.
Keep `openxpki_activate_runtime: false` and `openxpki_create_issuer_key: false`.

Edit **`ansible/group_vars/hsm_software.yml`**: choose the token/key labels, hexadecimal
`hsm_software_key_id` and `hsm_software_rsa_bits` (`3072` or `4096`). The supplied `01` key ID
and `ca-signer` label are suitable for a new issuer. Leave the two identity pins empty until step 3.
Once initialized, these choices identify the existing key and must be preserved.

## 2. Prepare the disk and middleware

Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml -e @ansible/group_vars/hsm_software.yml \
  ansible/playbooks/deployment/hsm-software.yml
```

Expected: guarded data-volume preparation, native `softhsm2`, `opensc`, OpenSSL engine and Python
bindings installed; **no token or key created**. Copy the printed filesystem UUID into
`openxpki_data_uuid` in **`issuer.yml`**. Keep that same disk for runtime installation.

The token directory starts root-only. Ansible grants `openxpki` access only after the inactive
runtime creates that account; it does not pre-create a conflicting package account.
For a named environment, load `all.<env>.yml` and `foundation.<env>.yml` after their base files
in every command here. A prepared offline controller may use `CONTROL_NODE_COLLECTIONS_MODE=check`.

## 3. Explicitly create the token and signing key

Obtain **two independent new PINs**, each 16–255 bytes, from your protected secret store:
the security-officer PIN for recovery/administration and the application PIN for signing.
Use printable ASCII; exclude quotes, backslashes and dollar signs from the application PIN to
match the existing OpenXPKI policy contract.
There are no factory/default PINs. Enter them from **bootstrap, `<prefix>-tier-0/`**:

```bash
read -r -s -p 'New SoftHSM security-officer PIN: ' SOFTHSM_SO_PIN; printf '\n'
read -r -s -p 'New issuer application PIN: ' HSM_ISSUER_PIN; printf '\n'
export SOFTHSM_SO_PIN HSM_ISSUER_PIN
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml -e @ansible/group_vars/hsm_software.yml \
  -e hsm_software_operation=initialize ansible/playbooks/deployment/hsm-software.yml
unset SOFTHSM_SO_PIN
```

Expected: one native token and RSA signing key, a verified sign/verify test, and a **public** result
containing `serial`, `spki_sha256` and `key_uri`. For example, the URI has this form:
`pkcs11:token=infrastructure-issuer;serial=<printed-serial>;id=%01;type=private`.

Copy the actual printed values into **`ansible/group_vars/hsm_software.yml`**:

| Printed result | Input to set |
| --- | --- |
| `serial` | `hsm_software_expected_serial` |
| `spki_sha256` | `hsm_software_expected_spki_sha256` |
| `key_uri` | `hsm_issuer_key` |

Initialization passes PINs through protected Ansible standard input, not command arguments.
Repeating it with the original application PIN verifies the same identity and creates nothing.
Interrupted initialization, unknown existing token files, a missing original token or mismatched
pins stop the operation. Preserve that state for recovery; never delete its record to force a retry.

## 4. Return to issuer policy creation

Return to [Stage 2 Step 6](README.md#step-6-prepare-policy-and-secrets), which creates the private
policy file. In that file set:

```yaml
openxpki_bundle_signer_backend: pkcs11
openxpki_bundle_pkcs11_key_uri: 'COPY_THE_EXACT_PRINTED_KEY_URI'
openxpki_bundle_pkcs11_library: /usr/lib/softhsm/libsofthsm2.so
openxpki_bundle_pkcs11_engine_library: /usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so
```

Keep `HSM_ISSUER_PIN` available to the policy builder and independently supply its DataVault secret.
The immutable bundle contains protected application credentials and stays outside Git.
Follow the main guide's **policy/bundle build and inactive runtime installation** next, using
this same `ca-1` and data disk. Skip encrypted-PEM key creation.

In **`issuer.yml`**, select `openxpki_managed_cli: true` and retain these state paths:

```yaml
openxpki_required_state_paths:
  - /srv/openxpki/identity/issuer.pem
  - /srv/openxpki/softhsm2/identity.json
  - /srv/openxpki/softhsm2/tokens
  - "{{ openxpki_release_dir }}/config.d/realm/{{ openxpki_realm }}/crypto.yaml"
  - "{{ openxpki_release_dir }}/config.d/system/crypto.yaml"
```

Use your selected `openxpki_data_mount` instead of `/srv/openxpki` if customized. Issuance stays inactive
until the offline root signs the request and the accepted certificates are installed.

## 5. Bind the installed inactive issuer

After runtime installation, run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml -e @ansible/group_vars/hsm_software.yml \
  -e hsm_software_operation=bind ansible/playbooks/deployment/hsm-software.yml
```

Expected: the original token/public-key pins match, only the issuer account can access the token
files, and the immutable PKCS#11 policy agrees with the recorded URI/library. Ansible binds
`SOFTHSM2_CONF` to the inactive service. No key is regenerated and no issuer service is started.

## 6. Create and sign the issuer request

After independently retaining/rehearsing recovery, set **`hsm_software.yml`**:
`hsm_provider_custody_ready: true`, `hsm_issuer_create_csr: true`, and the approved
`hsm_issuer_common_name`, for example `Example Infrastructure Issuing CA`.
Reload the **original** application PIN into `HSM_ISSUER_PIN` if you have opened a new shell.
Rerun step 5's bind command. It signs the CSR using the existing token key and fetches only
the public CSR to the controller; the printed destination defaults beneath `.local/share/pki-ceremony/`.
Return `hsm_issuer_create_csr` to `false` afterward.

Continue with the main guide's **offline signing and certificate installation**. For native token
activation, set **`hsm_provider_custody_ready: true` in `issuer.yml` too**: the normal runtime
activation command reads that file without the provider inputs. Keep the token pins/URI and other
provider settings owned only by `hsm_software.yml`.

After signed certificates are installed and the backend is active, run from **`<prefix>-tier-0/`**
with the original application PIN still loaded:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/issuer.yml -e @ansible/group_vars/hsm_software.yml \
  -e openxpki_token_operation=inspect ansible/playbooks/deployment/hsm-token.yml
```

Repeat that command with `openxpki_token_operation=import-root`, then `import-issuer`. Set
`openxpki_token_alias` in **`issuer.yml`** to the returned alias, then select `check`, `publish-crl`
and `publish-ca` in order. Inspect existing aliases before repeating an import, and follow returned
publication workflow identifiers through completion. This is the existing
[PKCS#11 activation contract](step-1d-single-usb.md#5-complete-activation-and-acceptance);
the PEM-only `openxpki-token.yml` recipe is not used. Clear `HSM_ISSUER_PIN` after ceremony work.

## 7. Retain and rehearse recovery

1. Retain **both PINs separately**, the public serial/SPKI/URI record, original policy bundle,
   issuer database/history, public certificates and DataVault/session credentials.
2. Capture an encrypted independent **stopped full-VM backup including all data disks**. It must
   include the entire `/srv/openxpki/softhsm2/` directory (`tokens`, `identity.json` and any pending
   marker), `/etc/hsm-provider/softhsm2.conf`, and the issuer's EFI/TPM state where used.
   SoftHSM's documented file-copy backup applies only to a quiesced complete token store. [1]
   Verify that the backup includes the token, its serial/SPKI record, database/history and original
   configuration together. Retain the encrypted backup independently of the source cluster.
3. Follow the linked Proxmox recovery path to restore the **complete VM and every disk** into
   isolation with issuance stopped. Preserve the original UUID/pins and provider configuration.
   Run this recipe with
   `-e hsm_software_operation=inspect`. It must return the original serial, URI and SPKI hash.
   Keep the restored service/provider binding and test issuance on that isolated copy using the
   [CA acceptance checks](../../05-operations/03-cryptography/certificate-authority.md#acceptance-evidence).
   Never run both restored and original issuers in production or initialize an empty replacement token.

The logical OpenXPKI application archive omits `softhsm2`; its PKCS#11 restore requires the original
key to be available separately. It is **not a standalone SoftHSM recovery path**. This option uses
the stopped full-VM recovery above. A new empty token cannot substitute for the original signing
identity. Keep the PINs independently recoverable; token files alone are insufficient.

Routine reapplication uses the preparation command in step 2 with issuance inactive; it never
creates a token/key. Use `inspect` for read-only identity checks while the issuer is active.
Treat loss of the root-owned identity record or an `initialization.pending` marker as a recovery
incident; an operator must determine whether key generation completed before any explicit repair.

## Later hardware and pool growth

SoftHSM token files can be restored to compatible SoftHSM software, **not copied into a PicoHSM or
YubiHSM**. The PKCS#11 sensitive/non-extractable attributes used here do not create a hardware
security boundary or guarantee that host compromise cannot disclose keys.

Moving an established issuer to hardware needs a separately qualified import/wrapping procedure
supported by both providers, or a planned **new intermediate key/certificate** with overlapping
publication and trust transition. This procedure promises neither export nor seamless hardware migration.
For a fresh installation intending later same-key USB expansion, start with
[single USB custody](step-1d-single-usb.md) and retain its vendor-specific wrapping material instead.
At Vault installation, review [device-pool growth and consumer boundaries](../stage-06-secrets/step-1c-seal-integration.md#review-single-device-growth-before-adding-consumers).
SoftHSM does not add a supported Vault auto-unseal path or replicated signing service.

## References

Sources checked 2026-11-17. Native lifecycle and CSR tests do not qualify a live CA recovery.

1. [SoftHSM2 initialization, PKCS#11 use and complete token-directory backup](https://github.com/softhsm/SoftHSMv2/blob/main/README.md)
2. [Debian 12 SoftHSM configuration and SOFTHSM2_CONF](https://manpages.debian.org/bookworm/softhsm2/softhsm2.conf.5.en.html)
3. [Debian 12 libsofthsm2 installed library paths](https://packages.debian.org/bookworm/amd64/libsofthsm2/filelist)
4. [Native PyKCS11 token initialization and key-generation API](https://pkcs11wrap.sourceforge.io/api/api.html)
