# Logging trust maintenance

The first deployment prepares receiver/producer requests, review and signing in
[Stage 2, Steps 6–10](../README.md#step-6-prepare-the-receiver-key-and-request).
This page maintains that accepted independent authority and its public handoff.
Producer private keys stay on their hosts; the authority exports only signed public results.

**Working repository:** `<prefix>-tier-0`, on the protected signing controller.
**Prerequisites:** original protected authority directory/key, separately held passphrase,
approved request history and cumulative revocations. Restore missing authority material;
never initialize a replacement over an operating installation.

## Contents

- [Existing authority and request approval](#existing-authority-and-request-approval)
- [Sign approved requests](#sign-approved-requests)
- [Renewal and revocation](#renewal-and-revocation)
- [References](#references)

<a id="1-establish-custody"></a>
<a id="2-issue-the-receiver-identity"></a>
<a id="3-approve-producer-requests"></a>

## Existing authority and request approval

Keep the original encrypted key, CA, issued leaves and CRL in the independent recovery kit;
keep the passphrase separately. Never use a collector, general runner or application host as the authority.
Native control-node preparation handles declared collections before signing runs.

For a receiver request, use [Step 6](../README.md#step-6-prepare-the-receiver-key-and-request).
For an additional producer, use [source preparation](sources.md#1-prepare-tier-owned-streams).
Review the actual public CSR metadata and independently confirm its key fingerprint as shown in
[Step 8](../README.md#step-8-review-the-public-requests). Append only exact approved descriptors to
`logging_authority_requests`; preserve previous requests and `logging_authority_revocations`.
Do not infer approval from a filename or copy producer private keys into the signing host.

<a id="sign-approved-requests"></a>

## Sign approved requests

Select the original directory and passphrase on **the signing controller, from `<prefix>-tier-0/`**:

```bash
read -r -e -p 'Original protected authority directory: ' LOGGING_AUTHORITY_DIR
read -r -s -p 'Authority key passphrase: ' LOGGING_AUTHORITY_PASSPHRASE
export LOGGING_AUTHORITY_DIR LOGGING_AUTHORITY_PASSPHRASE
```

Run from **the same Tier 0 root**, after reviewing the local request/revocation file:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/logging-authority.yml -e @ansible/group_vars/logging_authority.yml
```

**Expected:** the accepted `public/ca.pem`, fresh signed `public/revoked.pem` and approved
`public/<name>.pem` leaves. Return only public files through authenticated custody.
Keep the authority key on the signing controller. An existing externally managed authority can
supply the same qualified interfaces; its renewal/revocation policy remains with its owner.

For a new source, continue with [source installation](sources.md#2-install-and-test-forwarding).
The receiver catalogue/CRL must be updated before the new sender is enabled.
For first installation, resume [Step 10](../README.md#step-10-register-the-source-and-tls-inputs).

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

The Stage 3 [software PKI policy](../../stage-3-trust/procedures/software-pki.md#decisions-and-recovery-kit)
currently issues TLS-server leaves only. Retain the independent producer authority
until a client-auth profile, custody and rollover are qualified.

## References

Sources checked 2026-10-19.

1. [Ansible protected own-CA workflow](https://docs.ansible.com/projects/ansible/latest/collections/community/crypto/docsite/guide_ownca.html)
2. [Ansible cumulative CRL generation](https://docs.ansible.com/projects/ansible/latest/collections/community/crypto/x509_crl_module.html)
