# Step 1c: Select the Vault seal

**Expected result — IaC:** the selected [cluster Vault](README.md#figure-control-applications) or
[VM Vault](step-1b-vault-vm.md#figure-vault-vm) uses its declared seal and independent recovery custody.
Transit and PKCS#11 consume an already qualified provider; this configuration does not install or
initialize that provider. Choose the seal before the first Vault initialization.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 1](README.md#step-1-select-vault-placement-and-seal), before first initialization.
**Change:** Select Shamir, an independent Transit provider or a qualified Enterprise PKCS#11 seal.
**Return:** [Step 1](README.md#step-1-select-vault-placement-and-seal), selected 1a Kubernetes or 1b VM installation, then recovery checks.
**Design:** [seal patterns and dependency boundaries](../../01-architecture/08-cryptography/06-vault-seal.md).

<a id="secret-service-seal-integration"></a>

## Contents

- [Step 1: Choose the provider](#step-1-choose-the-provider)
- [Review single-device growth before adding consumers](#review-single-device-growth-before-adding-consumers)
- [Step 2a: Configure Kubernetes](#step-2a-configure-kubernetes)
- [Step 2b: Configure a VM](#step-2b-configure-a-vm)
- [Step 3: Verify recovery](#step-3-verify-recovery)
- [References](#references)

## Step 1: Choose the provider

| Choice | Existing interface supplied by its custodian | IaC configuration |
| --- | --- | --- |
| S1: Shamir, default | Independent share custodians | Leave seal type `shamir`; perform the protected initialization/unseal ceremony |
| S2: Transit | Independently recoverable HTTPS Vault, existing Transit key, narrow renewable encrypt/decrypt token and CA | Select `transit`; the installer renders HCL, transfers trust and injects the private token [1] |
| S3: PKCS#11 | Qualified device/network provider, licensed Vault Enterprise package or digest-pinned container with its provider library, original key labels and PIN | Select `pkcs11`; install declared provider packages on the VM or use the qualified container artifact, render the public seal stanza and inject the PIN [2] |

The provider must remain recoverable without the service it unlocks. A signing gateway
does not automatically provide a compatible seal. No key creation, provider reinitialization
or conversion to OpenBao is performed by these installers.

Vault **Community** can retain Shamir or use the independent Transit seal; direct PKCS#11 auto-unseal
requires the licensed **Enterprise** runtime. A PicoHSM/YubiHSM pool, PKCS#11 library, or separate
OpenBao signing API does not enable that feature in Community. [1][2]

For Enterprise, qualify the exact firmware, SDK/module, mechanisms, seal objects and login policy.
An issuer's ECDSA signing key cannot perform seal encryption/decryption. Provision separate recoverable
seal objects/credentials, including HMAC when the chosen mechanism requires it; preserve all objects
needed to decrypt existing data. Keep key generation disabled for a precommissioned seal and test its
original-object backup before initialization. Successful issuer signing does not qualify a seal. [2]

Yubico's AES-CBC PKCS#11 support is firmware/SDK-version dependent; vendor AES-CCM wrapping alone
is not a Vault seal qualification. PicoHSM's additional AES modes are not all exposed through the
selected OpenSC interface. Compare the module's mechanisms with Vault's required encryption/HMAC
pair and rehearse recovery; neither repository issuer profile is an accepted seal profile. [2][4][5]

### Review single-device growth before adding consumers

If Stage 2 started with one USB issuer device, this is a useful point to review capacity, host-loss
and recovery requirements. Follow the existing [single-device to provider-pool upgrade](../../05-operations/03-cryptography/usb-hsm.md#single-device-to-pool):
retain the original wrapped key/material, commission same-family destinations, deploy independent
hosts, authorize transport/policy, then rehearse consumer migration and rollback. Keep the issuer's
key, certificates, history and offline root separation intact.

The pool is optional for Shamir/Transit and remains a signing-provider upgrade. The supplied
`hsm_remote` profile exposes a dedicated signing token and checks one original private key; it is
**not a qualified Vault seal transport**. Adding endpoints does not migrate an issuer or a Vault
seal. Pool members keep different physical serials; a consumer bound to one stays bound to it.
Qualify explicit consumer switching separately from transport reconnection and Enterprise Seal HA.

## Step 2a: Configure Kubernetes

Edit **`<prefix>-tier-0/ansible/group_vars/control_applications.yml`**. For Transit:

```yaml
control_applications_vault_seal_type: transit
control_applications_vault_provider_accepted: true
control_applications_vault_transit:
  address: https://unseal.lab.example.com:8200
  key_name: control-unseal
  mount_path: transit/
  tls_server_name: unseal.lab.example.com
```

In the existing **private bootstrap Secrets file**, supply `vault/vault-seal` with
`VAULT_TRANSIT_SEAL_TOKEN` and `ca.crt`. Select its established Secret owner through
`control_applications_manage_secrets`; the [application recipe](procedures/control-applications.md#secrets-and-certificates)
creates or checks it before Helm. Credentials are absent from rendered Helm values.

For PKCS#11, set `control_applications_vault_provider_image.repository` and a digest-pinned
`tag`, `control_applications_vault_seal_hcl` to the qualified `seal "pkcs11"` stanza and
`vault/vault-seal.VAULT_HSM_PIN` in private Secrets. Keep PINs/tokens out of HCL. The image must
contain the declared provider library and licensed runtime; USB devices are not automatically
available to cluster pods. Use a qualified reachable provider or the VM placement for
host-bound devices. Do not select this path with a Community image.

Return to **1a** and use its existing render/review/apply commands. There is one Helm owner.

## Step 2b: Configure a VM

Edit **`<prefix>-tier-0/ansible/group_vars/vault.yml`**. For Transit:

```yaml
vault_seal_type: transit
vault_provider_accepted: true
vault_transit:
  address: https://unseal.lab.example.com:8200
  key_name: control-unseal
  mount_path: transit/
  tls_server_name: unseal.lab.example.com
  ca_src: /absolute/controller/path/unseal-ca.pem
vault_seal_environment:
  VAULT_TRANSIT_SEAL_TOKEN: "{{ lookup('ansible.builtin.env', 'VAULT_TRANSIT_SEAL_TOKEN') }}"
```

Supply the token through the protected controller environment or encrypted local inputs.
The role copies the CA and writes a root-only systemd environment file; no guest shell edits are needed.

For PKCS#11, select the approved Enterprise `vault_package_name`, `vault_provider_packages`,
`vault_provider_accepted: true`, credential-free `vault_seal_hcl` and private
`vault_seal_environment.VAULT_HSM_PIN`. Existing software intake supplies the qualified packages.

For a qualified **local USB seal**, attach its separately commissioned device to the Vault VM,
not `ca-1`. In **`terraform/deployments/vault/terraform.tfvars`**, inside the existing
`vm_instances["vault-1"]`, select the real physical node and existing USB resource mapping:

```hcl
proxmox_node_name = "pve02"
usb_devices      = [{ mapping = "vault-1-seal" }]
```

Use `bash scripts/deploy.sh vault --terraform-only --plan-only` from **`<prefix>-tier-0/`** and
require the intended attachment without replacement of an existing VM/data disk. The Vault root
already forwards `usb_devices`; keep the issuer attachment in foundation state and provider-pool
attachments in HSM state. A physical token can belong to only one guest. Enforce host affinity and
qualify every Vault member's access rather than assuming a mapping provides failover.

`vault_provider_packages` installs packages only. Native connector/PCSC authorization, library
configuration and required service environment are a separately qualified integration for the
`vault` service account; this installer does not invoke the issuer's `hsm-issuer.yml` or configure
a local HSM provider automatically. Complete that integration before starting a PKCS#11-sealed
runtime. If it is unavailable, retain Shamir or the accepted independent Transit provider.

Return to **1b** and run its normal `bash scripts/deploy.sh vault` command.

## Step 3: Verify recovery

1. Initialize only a new service; retain provider recovery material separately.
2. Restart the disposable service and verify automatic unseal or the Shamir quorum.
3. Test provider loss, credential rotation and independent clean-target recovery. Record the
   dependency, original key identity and measured recovery limits in project records.

Auto-unseal recovery shares cannot replace a lost seal key/provider. Retain independent recovery
of the original seal objects and service data; their permanent loss can make even snapshots
unrecoverable. Include startup and runtime provider outages in acceptance. [3]

**Existing initialized services:** ordinary apply rejects a changed seal stanza. Follow the
vendor's migration ceremony with retained data/keys first; `vault_seal_migration_accepted` or
`control_applications_vault_seal_migration_accepted` explicitly permits that reviewed configuration
change. The flag does not perform migration, rekeying or recovery. [3]

## References

Sources checked 2026-11-16; physical seal compatibility and migration remain deployment-specific.

1. [HashiCorp Transit seal](https://developer.hashicorp.com/vault/docs/configuration/seal/transit).
2. [HashiCorp PKCS#11 seal and Enterprise requirements](https://developer.hashicorp.com/vault/docs/configuration/seal/pkcs11).
3. [HashiCorp seal migration](https://developer.hashicorp.com/vault/docs/concepts/seal#seal-migration).
4. [YubiHSM firmware and SDK PKCS#11 limits](https://developers.yubico.com/YubiHSM2/Releases/Known_issues.html).
5. [PicoHSM mechanisms and interface limitations](https://github.com/polhenarejos/pico-hsm).
