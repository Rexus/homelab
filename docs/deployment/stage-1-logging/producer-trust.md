# Independent logging trust

Issue receiver and producer certificates before the platform PKI exists. Producer
private keys stay on their owning hosts; Tier 0 signs reviewed public requests.
This authority is separate from the infrastructure root and requires no cluster or SSO.

**Working repository:** `<prefix>-tier-0`, on the protected signing controller.
**Prerequisites:** [local Ansible tools](../../development/local-setup.md),
`community.crypto`, Python cryptography, independently authenticated host access,
protected local storage and separately held encrypted backups/passphrase.

## Contents

- [1. Establish custody](#1-establish-custody)
- [2. Issue the receiver identity](#2-issue-the-receiver-identity)
- [3. Approve producer requests](#3-approve-producer-requests)
- [Renewal and revocation](#renewal-and-revocation)
- [References](#references)

## 1. Establish custody

1. Select a dedicated protected signing directory outside Git. Never use a general
   runner, collector or application host as the authority. Keep the encrypted key,
   original CA, issued leaves and cumulative CRL in the recovery kit; keep the
   passphrase separately. Record the CA fingerprint through an independent channel.
2. Select local paths and the passphrase without putting secret values in history:

   ```bash
   read -r -e -p 'Protected authority directory: ' LOGGING_AUTHORITY_DIR
   read -r -s -p 'Authority key passphrase: ' LOGGING_AUTHORITY_PASSPHRASE
   export LOGGING_AUTHORITY_DIR LOGGING_AUTHORITY_PASSPHRASE
   cp ansible/group_vars/logging_authority.yml.example ansible/group_vars/logging_authority.yml
   ```

3. Review the local file, then approve first initialization on an empty directory:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/logging-authority.yml -e @ansible/group_vars/logging_authority.yml -e logging_authority_initialize=true
   ```

Normal reruns omit the initialization flag. Missing/partial authority material blocks
execution; restore the original rather than silently replacing trust. The role uses
native `community.crypto` primitives and exports only `public/`. [1]

## 2. Issue the receiver identity

1. On the protected deployment controller, prepare its server key/request. These are
   outside Git; the unencrypted service key is later installed only on the receiver:

   ```bash
   read -r -e -p 'Protected receiver credential directory: ' LOGGING_RECEIVER_DIR
   read -r -p 'Receiver inventory name: ' LOGGING_RECEIVER_NAME
   read -r -p 'Approved receiver DNS name: ' LOGGING_RECEIVER_DNS
   export LOGGING_RECEIVER_DIR LOGGING_RECEIVER_NAME LOGGING_RECEIVER_DNS
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/logging-receiver-request.yml
   ```

   Reruns preserve the existing service key and reconcile only its CSR. Deliberate key
   rotation is a separate approved operation. The GnuTLS sender profile requires a DNS SAN:
   connect to a fixed receiver IP with the exact DNS peer if bootstrap DNS is absent.
   Address routing and certificate identity are separate; platform DNS is not required.
2. Transfer the public CSR through authenticated custody to the signing controller.
   Inspect its native metadata there:

   ```bash
   read -r -e -p 'Reviewed public CSR path: ' LOGGING_CSR
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible localhost -i localhost, -c local -m community.crypto.openssl_csr_info -a "path=$LOGGING_CSR"
   ```

   Independently confirm `public_key_fingerprints.sha256`, host identity and intended
   purpose. Add the exact `name`, `profile: server`, CSR path, colon-separated key
   fingerprint and SAN list to `logging_authority_requests`. The signer rejects other
   subjects, CA powers, usages, keys or names; approval is not inferred from a filename.
3. Run the normal signing command below. Transfer `public/ca.pem`, `public/revoked.pem`
   and the named leaf back; never transfer `key.pem` from the authority. Select these
   files and the receiver service key in [receiver Step 2](receiver.md#step-2-register-trust-and-producers).

## 3. Approve producer requests

1. Run [source preparation](sources.md#1-prepare-tier-owned-streams) in the owning tier.
   Only CSRs are fetched; private keys remain on each producer.
2. Review each public request as above. Add `profile: client`, the approved source
   name, CSR path and independently confirmed fingerprint to the Tier 0 request list.
   Match the Tier 0 receiver catalogue's CN, observed address, tier and classification.
3. On the signing controller, issue or renew the approved requests and refresh the CRL:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/logging-authority.yml -e @ansible/group_vars/logging_authority.yml
   ```

   Transfer public results into a protected public handoff directory for the owning
   tier, then follow [source installation](sources.md#2-install-and-test-forwarding).
   Do not copy another tier's inventory, private keys or state into Shared.

## Renewal and revocation

| Operation | Required action |
| --- | --- |
| Routine leaf renewal | Reuse the host key/CSR; rerun signing before expiry. Leaves default to 90 days and renew inside 30 days; deploy public results and test continuity |
| CRL refresh | Run signing and distribute the signed CRL to receiver and all producers at least every three days; its validity is seven days. Restart/reapply units to close old sessions |
| Immediate source withdrawal | Remove the source from the receiver allowlist and redeploy the receiver first; this closes existing connections. Preserve its queued/history files and review stale firewall grants |
| Revocation | Add the certificate serial, absolute UTC revocation date and reason to `logging_authority_revocations`; rerun and distribute. The cumulative CRL never removes an earlier entry automatically |
| Compromised host/key | Withdraw and revoke, preserve evidence, deliberately replace the producer key, prepare/review a new CSR, then re-admit. Never silently reset its queue/cursor |
| Authority loss/expiry | Restore the original protected authority; planned CA rollover requires overlapping trust and a separately tested migration, not first-initialization on an active installation |

CRLs are enforced on new TLS handshakes; an existing session is not retroactively
reauthenticated. Native receiver/source reapplication restarts changed instances.
Record scheduled renewal/CRL ownership and external expiry checks in the project runbook.
This workflow is operator-invoked, not an unattended authority with resident credentials.

The Stage 2 [software PKI policy](../stage-2-trust/procedures/software-pki.md#decisions-and-recovery-kit)
currently issues TLS-server leaves only. Retain the independent producer authority
until a client-auth profile, custody and rollover are qualified.

## References

Sources checked 2026-10-19.

1. [Ansible protected own-CA workflow](https://docs.ansible.com/projects/ansible/latest/collections/community/crypto/docsite/guide_ownca.html)
2. [Ansible cumulative CRL generation](https://docs.ansible.com/projects/ansible/latest/collections/community/crypto/x509_crl_module.html)
