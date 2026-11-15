# Logging bootstrap credentials

Controller-only custody for the independent logging authority variant. This role does not create a CA,
issue certificates or initialize credentials for the normal PKI-backed logging path.

The [credentials-only entry point](../../playbooks/deployment/logging-secrets.yml) reuses the syslog
workflow's workspace/backend inputs without selecting producers. It defaults to `read`; select
`logging_workflow_credential_operation` explicitly for initialization or migration. Its control-node
profile prepares Vault clients only when the selected backend requires them. Its default workspace is
`$HOME/.local/share/<actual-tier-0-repository-name>/logging/<platform_environment>` (`prod` by default),
resolved from the playbook's repository rather than the current directory or inventory location.

| Input | Contract |
| --- | --- |
| `logging_credentials_operation` | `initialize`, `read` or `migrate`; default `read` |
| `logging_credentials_backend` | Explicit `ansible_vault` or `hashicorp_vault`; no outage fallback |
| `logging_credentials_workspace` | Absolute controller-owned mode `0700` workspace |
| `logging_credentials_repository_name` | Repository basename, used for the default unlock directory |
| `logging_credentials_authority_key_file` | Actual existing independent CA key path; default `<workspace>/authority/key.pem` |
| `logging_credentials_seed` | Optional retained `{authority_passphrase: ...}` for one-time legacy adoption |
| `logging_credentials_password_directory` | Default `$HOME/.config/<repository-name>/logging`, separate from the workspace |
| `logging_credentials_vault_address` | HTTPS Vault endpoint, also accepted from `VAULT_ADDR` |
| `logging_credentials_vault_ca_file` | Existing trusted CA file, also accepted from `VAULT_CACERT` |
| `logging_credentials_vault_mount` | Existing KVv2 mount; default `secret` |
| `logging_credentials_vault_path` | Dedicated logging secret path below the mount |
| `logging_credentials_vault_token` | Externally supplied scoped token; defaults to `VAULT_TOKEN` |

Run locally without `become` or check mode. The caller prepares Ansible and, for KVv2, the already declared
`community.hashi_vault >=6.2.0,<7.0.0` collection and `hvac` in the controller interpreter. Native modules
use `ansible_playbook_python`, avoiding a different system Python selected by interpreter discovery.
Adopting a legacy key also needs the existing `community.crypto` collection and its prepared
`cryptography` library; the credentials entry point prepares them when a seed is supplied.

The encrypted YAML is `<workspace>/credentials/logging-secrets.vault.yml`; its separate unlock file is
`<password-directory>/ansible-vault.password`. Directories are `0700`; files are `0600`. Existing shared,
foreign-owned or linked inputs are refused. Back up the encrypted file and unlock file separately.
Keeping both on one controller removes repeated prompts but does not protect against compromise of that account.

`initialize` generates a random 64-character authority passphrase only for a new authority. A retained seed
of at least 20 characters (the existing authority role's minimum) can adopt an existing authority. Native
key inspection must prove that seed unlocks the existing key before saving any new secret input. A missing
or incorrect seed stops initialization. Reruns decrypt
and preserve the exact original. A leftover `.initialize-lock` means an interrupted operation: confirm no
initialization is active before removing only that lock directory and retrying.

`migrate` requires backend `hashicorp_vault`. The scoped token needs `read` and `create` on
`<mount>/data/<path>`. Native KVv2 `cas: 0` prevents races or replacing deleted/older secrets. Existing data
must match the complete document exactly. Readback precedes the metadata-only migration receipt and
`logging_credentials_migration_verified: true`. The original encrypted recovery input remains intact.
Changing the workflow's backend is a separate explicit configuration change after verified migration.

`read` returns only the selected backend's schema-validated mapping in `logging_managed_secrets`.
The caller must keep every consuming task `no_log: true`, disable diffs, and avoid caching or printing it.
HashiCorp Vault reads need no online local unlock file; an outage fails rather than falling back.
This role never rotates a credential or supplies general-purpose secret storage.

## References

1. [Native Ansible Vault CLI](https://docs.ansible.com/projects/ansible-core/2.16/cli/ansible-vault.html).
2. [Native KVv2 get module](https://docs.ansible.com/projects/ansible/latest/collections/community/hashi_vault/vault_kv2_get_module.html).
3. [Native KVv2 write module and CAS](https://docs.ansible.com/projects/ansible/latest/collections/community/hashi_vault/vault_kv2_write_module.html).
