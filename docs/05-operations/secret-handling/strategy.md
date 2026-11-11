# Credential handling and rotation

<a id="secret-strategy"></a>


Keep bootstrap/recovery credentials independent of the services they unlock.
Use the accepted secret service for normal credential delivery after commissioning.
The [cryptography design](../../01-architecture/16-cryptography/README.md) explains the boundaries;
this page identifies the operating task and its supported procedure.

**Run from:** the credential-owning tier repository on its authorized execution host.
**Before starting:** identify the credential's issuer, consumers, recovery copy and
revocation owner. Never replace an unknown credential merely because it is unavailable.

<a id="table-of-contents"></a>

## Tasks

- [Where is each credential kept?](#what-goes-where)
- [What is required before Vault exists?](#bootstrap-minimum)
- [How are Flux bootstrap secrets maintained?](#gitops-bootstrap-secrets)
- [When can applications use the secret service?](#secret-platform-deployment-milestone)
- [How is an existing credential rotated?](#secret-platform-operating-target)
- [What happens after a leak or lost credential?](#what-happens-after-a-leak-or-lost-credential)
- [References](#references)

<a id="purpose"></a>
<a id="design-goal"></a>
<a id="what-goes-where"></a>

## Where is each credential kept?

| Material | Location / owning procedure |
| --- | --- |
| Host inventories, IPs and network settings | Tier-local plain inputs; Shared owns no inventory |
| Bootstrap API tokens/passwords | Protected shell/runner injection or ignored `.env.local`; [Ansible-only encryption](ansible-vault.md) when selected |
| Routine service credentials | Accepted secret service with scoped workload access |
| TLS private keys | Owning service's protected files/Secrets and independent encrypted backups |
| SOPS payloads | Ciphertext in private Git; age private identities outside Git and independently backed up |
| Vault unseal/recovery material | Separate authorized custody, outside Git and Vault itself |
| Root keys, issuer keys and DataVault recovery secrets | Their separate CA/HSM custody and [issuer recovery set](../cryptography/issuer-recovery.md), never ordinary CI variables |

<a id="bootstrap-minimum"></a>

## What is required before Vault exists?

1. Retain independent SSH, verified Proxmox API trust, state access and the small
   credential set required by the current stage. Use local ignored inputs or
   protected runner variables, not tracked examples.
2. Supply FreeIPA passwords through [environment injection or an encrypted override](ansible-vault.md).
   Keep inventory/IP files plain for Terraform.
3. Record independent recovery holders and copies before deploying stateful services.
   Never make bootstrap depend on later SSO, hosted Git or the Vault instance being created.

<a id="gitops-bootstrap-secrets"></a>

## How are Flux bootstrap secrets maintained?

1. In Tier 0, follow [Flux/SOPS Steps 1-2](../../03-deployment/stage-4-kubernetes/procedures/flux-sops.md)
   for the exact Git URL/commit, read-only credential and age Secret inputs.
2. Commit only ciphertext/public recipient settings. Keep the private identity and
   source-access recovery outside the cluster. Verify the encrypted canary after changes. [1]
3. For recipient changes, retain the old identity until all affected ciphertext,
   deployed Secrets and retained backups have qualified recovery. Use the native
   SOPS/Flux procedure; no repository-wide automatic key rotation is supplied.

SOPS can remain the bootstrap channel after Vault is installed. Controller
installation alone does not migrate existing credentials or configure external-secret delivery.

<a id="secret-platform-deployment-milestone"></a>

## When can applications use the secret service?

1. Complete [Stage 6 Secrets](../../03-deployment/stage-6-secrets/README.md) using the
   selected Kubernetes or VM path. Initialization/unseal remains an operator ceremony.
2. Verify TLS, scoped access, protected audit delivery, backups and independent recovery.
3. Enable each consumer's accepted authentication/injection path. Move a credential
   only after testing its consumer; keep the minimum recovery set outside Vault.

<a id="secret-platform-operating-target"></a>

## How is an existing credential rotated?

Select one operation; the commands and gates differ:

| Operation | Procedure / limit |
| --- | --- |
| Ansible encrypted-file password | [Rekey the file](ansible-vault.md#how-is-the-file-encryption-password-rotated); account values inside it remain unchanged |
| TLS-server leaf/key | [Renew the service certificate](../cryptography/certificate-authority.md#how-is-a-service-certificate-renewed); the supplied private CA policy is TLS-server only |
| Infrastructure issuer/root key | [CA change and recovery](../cryptography/certificate-authority.md#change-and-recovery); a new-key ceremony/rollover, not a file edit |
| HSM custody | [Hardware migration](../cryptography/hardware-migration.md); provider and native token lifecycle must be qualified |
| Proxmox provisioning token | Follow the [API access procedure](../../03-deployment/foundation/proxmox/api-access.md); retain scoped grants and verify consumers before revoking the old token |
| Service database/API password | Use that product's native account change and update every consumer; storing another value does not perform the change |
| OpenXPKI database/session/DataVault secrets | Routine playbooks reject binding changes; a tested product-specific migration is required |
| Vault seal/unseal material | Separate native operator ceremony under the selected [seal design](../../01-architecture/16-cryptography/06-vault-seal.md); never rerun initialization |

For supported product rotations:

1. Back up the original binding and identify every consumer and expiry/revocation deadline.
2. Use the product's supported overlap/change procedure with the narrowest existing privileges.
3. Update the owning ignored/private inputs, apply only that consumer's accepted recipe
   and verify authorized/denied use plus protected audit events.
4. Revoke the old credential only after cutover verification; retain recovery copies
   under policy. No generic batch rotation or account-migration installer is supplied.

## What happens after a leak or lost credential?

Stop routine rotation and preserve evidence. Revoke/isolate exposed authority using
the [incident path](../cryptography/security-controls.md#detect-and-respond), then
recover/reissue under independent custody. Removing a value from Git history or
reverting `.env.local` cannot revoke a leaked credential.

If a routine cutover fails before revocation, return consumers to the still-valid
old credential using the product's rollback procedure. After revocation or suspected
compromise, recover/reissue instead of restoring the exposed credential.

## References

1. [Flux SOPS bootstrap, decryption identities and recovery](https://fluxcd.io/flux/guides/mozilla-sops/), checked 2026-11-08.
