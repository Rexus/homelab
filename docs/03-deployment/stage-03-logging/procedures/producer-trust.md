# Logging authority and secret custody

The [main deployment](../README.md#step-4-deploy-and-approve-certificates) prepares keys, requests,
source bindings and acceptance from configuration. These are authority choices, not additional
mandatory manual steps.

**Working repository:** `<prefix>-tier-0` on the bootstrap/controller.

## Choose the authority

Edit **Tier 0 `ansible/group_vars/syslog.yml`**, preserving existing trust on an installed system:

| `logging_workflow_issuer` | Starting state | Result |
| --- | --- | --- |
| `infrastructure`, main | Active Stage 2 OpenXPKI issuer with logging leaf profiles | Reuses issuer settings; submits/resumes native enrollment and retrieves verified public certificates after separate RA approval |
| `independent` | New explicitly separate logging authority, or its original recovery material | Generates and encrypts a retained CA passphrase; signs exact derived CSRs locally; does not depend on later Vault/SSO |
| `provided` | Existing qualified external issuer | Creates the public request manifest and waits for its signed public handoff; no invented CA API or approval bypass |

An existing independent CA is not migrated by switching this value. Keep its original root, keys,
revocations and issued identities until a separately planned trust cutover is accepted.

## Infrastructure enrollment

**Before first enrollment:** build and activate the [Stage 2 issuer bundle](../../stage-02-trust/README.md)
containing `logging_client` and `logging_server` profiles. The requester cannot approve its own request.
An older installed bundle without these profiles needs a separately qualified configuration upgrade;
the current runtime installer deliberately rejects a changed configuration binding. This change does
not supply that upgrade. Retain its original database, signing/DataVault state and CLI identity, or
use a qualified existing issuer through the provided-handoff mode. Do not edit the live profile
directory, rewrite deployment bindings or replace the issuer key to bypass that check.

The logging run reads **`ansible/group_vars/issuer.yml`** and uses the issuer's existing
**`foundation.yml`** guest placement. It validates the active runtime binding, pinned native CLI,
profile powers and separate approver policy before submission. The approved descriptor binds the
CSR key, exact CN, SAN and client/server EKU. Public requests are reviewed in the configured
OpenXPKI portal using the printed native workflow IDs; rerunning resumes those same workflows.

`logging_workflow_generation: initial` retains retry identity. An intentional renewal selects a new
generation, for example `renew-2027-01`, then follows the same approval and acceptance path.
A failed or pending workflow does not authorize certificate installation.

## Independent authority

For a **new** independent installation, set **`logging_workflow_issuer: independent`** in
**Tier 0 `ansible/group_vars/syslog.yml`**, then run in **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh syslog
```

The workflow retains an encrypted signing key and an Ansible Vault encrypted secret document;
it generates the passphrase and a separate private unlock file once. Retries reuse both.
Missing original credentials, a wrong unlock file or a partial authority cause failure rather than rotation.
The root remains separate from infrastructure PKI and needs its own recovery custody.

For an existing installation, retain the old directory and original passphrase. Use the
[legacy authority inputs](../../../../tier-0/ansible/group_vars/logging_authority.yml.example)
and direct [authority recipe](../../../../tier-0/ansible/playbooks/deployment/logging-authority.yml)
until a reviewed custody adoption is completed. Changing paths to an empty workspace is not recovery.

## Existing external issuer

Set **`logging_workflow_issuer: provided`** in **Tier 0 `ansible/group_vars/syslog.yml`**.
Prepare requests from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh syslog --ansible-only --playbook deployment/logging-prepare.yml
```

The run prints `requests.json` and the protected `public` directory. The issuer signs those exact
CSRs with the declared client/server EKUs and receiver DNS SAN. Return **`ca.pem`** (issuer/root
trust chain), **`revoked.pem`** (current issuer CRL), and **`<request-name>.pem`** for every request to
that printed directory. Receiver private keys and producer private keys are not handed to the issuer.
Then rerun the normal syslog command. The installed certificate/key, chain, purpose and revocation
checks reject an incomplete or mismatched handoff.

## Secret custody and Vault migration

For the default infrastructure path, signer secrets remain under the existing PKI's custody;
there is no second logging-root passphrase.

For the independent path, retain these **separate** recovery inputs:

| Input | Default location on controller |
| --- | --- |
| Signing key, receipt, encrypted secret and receiver keys | `~/.local/share/<actual-tier-0-repo>/logging/prod/` |
| Ansible Vault unlock password | `~/.config/<actual-tier-0-repo>/logging/ansible-vault.password` |
| Producer private keys and queue/cursor state | Each producer's `/etc/log-forwarder` and `/var/lib/rsyslog/forwarder` |

Use separate protected backup custody for the unlock file and ciphertext. A bootstrap VM backup
alone must not be the only copy. No private keys, tokens or heartbeat capability URLs belong in Git.
The later [Vault deployment](../../stage-06-secrets/README.md) does not erase this independent recovery path.
The [credential operation](../../../../tier-0/ansible/roles/logging_credentials/defaults/main.yml)
provides explicit verified KVv2 migration/readback, rejects a different destination secret and retains
local encrypted recovery material; use the migration runbook after Vault is available.

After Vault is deployed, set these non-secret fields in **Tier 0 `ansible/group_vars/syslog.yml`**:
`logging_credentials_vault_address`, `logging_credentials_vault_ca_file`,
`logging_credentials_vault_mount` and `logging_credentials_vault_path`.
Example destination: mount `secret`, dedicated path `platform/logging/authority`.
Supply an externally held, scoped `VAULT_TOKEN`; keep it out of the file.

Run in **`<prefix>-tier-0/`** to migrate the retained local secret:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/deployment/logging-secrets.yml -e @ansible/group_vars/syslog.yml \
  -e logging_workflow_credential_operation=migrate \
  -e logging_workflow_credential_backend=hashicorp_vault
```

**Expected:** verified readback matches the original secret; ciphertext and separate unlock file remain intact.
Set `logging_workflow_credential_backend: hashicorp_vault` in **`syslog.yml`** only after success.
Then verify the selected backend from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/deployment/logging-secrets.yml -e @ansible/group_vars/syslog.yml \
  -e logging_workflow_credential_operation=read
```

The run prints status and recovery locations, not secret values. A Vault outage fails the selected
remote read; it never silently initializes new secrets or falls back to the local recovery copy.
For a separately approved recovery, explicitly select `ansible_vault` and restore the original material.

[Return to deployment](../README.md#step-5-verify-collection).

## Renewal, revocation and recovery

| Operation | Action |
| --- | --- |
| Infrastructure leaf renewal | Change the intentional request generation, resume enrollment and separate approval, then rerun acceptance |
| Independent leaf renewal | Rerun the workflow before expiry; retained keys and CSRs are reused, default leaves renew within 30 days of expiry |
| Independent CRL refresh | Rerun and distribute at least every three days; its signed CRL validity is seven days |
| Immediate withdrawal | Remove the binding from receiver inputs and reconcile the direct receiver before re-enrollment; preserve all evidence and queued state |
| Independent revocation | Append serial, UTC revocation date and reason to `logging_authority_revocations`; rerun and distribute the cumulative CRL |
| Compromised key | Withdraw/revoke, preserve evidence, deliberately replace the host key, then approve a new CSR |
| Authority loss | Restore the original authority and separate secret custody; initialization is not a recovery procedure |

CRLs are enforced on new TLS handshakes. Reapplication restarts changed units to close old sessions;
a previously established session is not retroactively authenticated. Record scheduled renewal/CRL
ownership, independent expiry monitoring and a tested trust-rollover plan.
