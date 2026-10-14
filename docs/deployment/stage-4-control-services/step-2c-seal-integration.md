# Step 2c: Vault seal integration

<a id="secret-service-seal-integration"></a>

**Branch from:** [Step 2](README.md#step-2-deploy-operational-services), before accepting the secret service.
**Change:** Select a supported seal/recovery integration independently of PKI signing.
**Return:** [Step 2](README.md#step-2-deploy-operational-services) to continue with secret-service recovery and access checks.

**Design:** [seal patterns S1-S3](../../architecture/cryptography/vault-seal.md).
**Prerequisites:** selected secret-service placement, protected storage, TLS,
recovery custodians and a validated provider. This is operator integration guidance.

| Selected pattern | Implementation work | Required check |
| --- | --- | --- |
| S1: Shamir | Follow the selected product's initialization/unseal procedure; retain shares outside the service | An authorized recovery quorum restores a test instance |
| S2: Transit | Prepare an independently recoverable unseal service and scoped transit credential; configure the main service using its supported seal configuration [1] | Main service restarts; failure of the unseal service is detected; the unseal service does not depend on the main service |
| S3: Native PKCS#11 | Verify product/edition, provider library and mechanisms; use the selected product's seal procedure [2][3] | Device/provider loss, credential rotation and independent restore behave as approved |

1. Rehearse the chosen configuration with disposable data before integrating it
   into the production service. Keep keys, shares and provider PINs outside Git.
2. Test startup, denied access, provider loss and recovery using the actual client path.
3. For an existing service, use its supported seal migration process and retained
   backup; do not replace seal configuration as an untested routine Ansible change.
4. Record recovery dependencies and accepted evidence in project administration.

The shipped Vault VM role starts the S1 reference service. It does not perform a
Transit/HSM migration or implement OpenBao. A signing gateway next to Vault does
not configure its seal or certificate-signing backend.

Vault is the consumer in an HSM integration. Provision and verify any selected
[replicated HSM service](../stage-2-trust/step-1b-usb-hsm.md) independently before
accepting Vault's dependency on it. Its key-generation/signing integration and
its seal configuration require separate compatibility and availability checks.

## References

Sources checked 2026-10-08.

1. [HashiCorp Transit seal](https://developer.hashicorp.com/vault/docs/configuration/seal/transit)
2. [HashiCorp PKCS#11 seal](https://developer.hashicorp.com/vault/docs/configuration/seal/pkcs11)
3. [OpenBao PKCS#11 seal](https://openbao.org/docs/configuration/seal/pkcs11/)
