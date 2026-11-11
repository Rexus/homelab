# Step 1c: Select the Vault seal

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 1](README.md#step-1-deploy-the-secret-service), before first initialization.
**Change:** Select Shamir, an independent Transit provider or a qualified Enterprise PKCS#11 seal.
**Return:** [Step 1](README.md#step-1-deploy-the-secret-service), selected 1a Kubernetes or 1b VM installation, then recovery checks.
**Design:** [seal patterns and dependency boundaries](../../01-architecture/08-cryptography/06-vault-seal.md).

<a id="secret-service-seal-integration"></a>

## Step 1: Choose the provider

| Choice | Existing interface supplied by its custodian | IaC configuration |
| --- | --- | --- |
| S1: Shamir, default | Independent share custodians | Leave seal type `shamir`; perform the protected initialization/unseal ceremony |
| S2: Transit | Independently recoverable HTTPS Vault, existing Transit key, narrow renewable encrypt/decrypt token and CA | Select `transit`; the installer renders HCL, transfers trust and injects the private token [1] |
| S3: PKCS#11 | Qualified device/network provider, licensed Vault Enterprise package or digest-pinned container with its provider library, original key labels and PIN | Select `pkcs11`; install declared provider packages on the VM or use the qualified container artifact, render the public seal stanza and inject the PIN [2] |

The provider must remain recoverable without the service it unlocks. A signing gateway
does not automatically provide a compatible seal. No key creation, provider reinitialization
or conversion to OpenBao is performed by these installers.

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
Provision a local USB device through the [hardware option](../stage-3-trust/step-1d-single-usb.md)
before configuring its provider.

Return to **1b** and run its normal `bash scripts/deploy.sh vault` command.

## Step 3: Verify recovery

1. Initialize only a new service; retain provider recovery material separately.
2. Restart the disposable service and verify automatic unseal or the Shamir quorum.
3. Test provider loss, credential rotation and independent clean-target recovery. Record the
   dependency, original key identity and measured recovery limits in project records.

**Existing initialized services:** ordinary apply rejects a changed seal stanza. Follow the
vendor's migration ceremony with retained data/keys first; `vault_seal_migration_accepted` or
`control_applications_vault_seal_migration_accepted` explicitly permits that reviewed configuration
change. The flag does not perform migration, rekeying or recovery. [3]

## References

1. [HashiCorp Transit seal](https://developer.hashicorp.com/vault/docs/configuration/seal/transit).
2. [HashiCorp PKCS#11 seal and Enterprise requirements](https://developer.hashicorp.com/vault/docs/configuration/seal/pkcs11).
3. [HashiCorp seal migration](https://developer.hashicorp.com/vault/docs/concepts/seal#seal-migration).
