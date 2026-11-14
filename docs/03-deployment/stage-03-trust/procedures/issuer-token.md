# Activate the software issuer token

Bind the separately signed public certificate to the existing software key through
controller-run Ansible. This is an explicit custodian operation, separate from routine reconciliation.
Hardware custody retains its qualified provider/token procedure.

**Working repository:** `<prefix>-tier-0/` on the protected controller.
**Prerequisites:** active backend, pinned public root/issuer certificates, recoverable
signer/DataVault secrets and the approved native CLI authentication key on the issuer.
Complete [certificate installation](issuer.md#10-start-the-prepared-backend) first.

## Contents

- [Verify identity](#verify-identity)
- [Import and check the token](#import-and-check-the-token)
- [Publish and test](#publish-and-test)
- [References](#references)

## Verify identity

The [custodian playbook](../../../../tier-0/ansible/playbooks/deployment/openxpki-token.yml)
checks the original runtime/storage binding, pinned issuer fingerprint, certificate chain
and the encrypted key's public-key match before executing a selected operation.
Private keys stay on the issuer; the existing `OPENXPKI_SIGNER_PASSWORD` is passed through
the protected input workflow and never placed in command arguments or output.

## Import and check the token

Use the operations below in order. Run from **`<prefix>-tier-0/`** with the accepted issuer inputs:

```bash
read -r -p 'Operation (inspect, import-root, import-issuer, check, publish-crl, publish-ca): ' ISSUER_OPERATION
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/issuer.yml \
  -e "openxpki_token_operation=$ISSUER_OPERATION" \
  ansible/playbooks/deployment/openxpki-token.yml
```

| Order | Operation | Expected result |
| --- | --- | --- |
| 1 | `inspect` | Existing token inventory; inspect aliases before importing |
| 2 | `import-root` | Add the already approved public root certificate once |
| 3 | `import-issuer` | Bind the public issuer certificate to its configured filesystem key; no `--key` import |
| 4 | `check` | Set `openxpki_token_alias` in `issuer.yml` to the returned alias; inspect native signer readiness |

Imports are explicit one-time CLI operations, not repeated reconciliation. If an alias already
exists or an import fails, inspect the native result and retained identifiers before another write.
The symmetric DataVault uses the separately protected master secret; no fabricated certificate is needed. [1]

## Publish and test

Run the same controller command with `publish-crl`, then `publish-ca`.
Inspect the returned workflow identifiers through completion; enqueueing alone is not publication. [1]
For signed offline root objects, set `openxpki_public_root_files` in `issuer.yml`, mapping
`root.cer` and `root.crl` to their absolute controller paths, then rerun the public-certificate recipe.
Confirm HTTP downloads, signatures, freshness and independent stale-CRL alerts.

Log in to the portal as the requester and require a second person's approval of an allowed CSR.
Reject self-approval, out-of-scope SANs, wildcards and CA profiles. Test renewal, revocation,
fresh CRL publication and rejection at an enforcing client before
[recovery acceptance](../../../05-operations/03-cryptography/issuer-recovery.md).
A ready token alone is not production acceptance.

## References

Source checked 2026-11-11.

1. [OpenXPKI CLI authentication, token import, DataVault and publication workflows](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
