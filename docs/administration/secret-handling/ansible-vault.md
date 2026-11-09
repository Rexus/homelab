# Ansible secret-file operations

<a id="ansible-bootstrap-secrets"></a>


Use a separate encrypted file for Ansible-only passwords. Inventory and host-IP
inputs remain readable by Terraform. This is Ansible Vault file encryption,
not the HashiCorp Vault service.

**Run from:** the owning generated tier repository on its protected execution host.
**Before starting:** working Ansible tools, independent recovery custody and an
editor configured without plaintext backup/swap files for secret editing.

<a id="table-of-contents"></a>

## Tasks

- [Which files can be encrypted?](#which-files-can-be-encrypted)
- [How are bootstrap passwords injected without a secret file?](#environment-injection)
- [How is an encrypted secret file created and used?](#encrypted-secret-file)
- [How is a stored password edited?](#how-is-a-stored-password-edited)
- [How is the file-encryption password rotated?](#how-is-the-file-encryption-password-rotated)
- [What stops a change or requires rollback?](#usage-notes)
- [References](#references)

<a id="purpose"></a>
<a id="local-file-pattern"></a>
<a id="shared-inputs-stay-plain-yaml"></a>

## Which files can be encrypted?

| File | Rule |
| --- | --- |
| `ansible/inventory/hosts.yml`, host/IP setup files | Do not encrypt inventory or host-IP inputs; keep plain YAML for Terraform, which cannot decrypt Ansible Vault or evaluate Jinja [1] |
| `secrets/ansible-bootstrap-vars.yml` | Secret-only Ansible override; no inventory, names or IP maps |
| Product-specific Ansible-only secret files | Encrypt when the owning recipe accepts them explicitly; follow that recipe's command |

`deploy.sh --ansible-vars` normally passes files to both tools. Supply an encrypted
override **only with `--ansible-only` or maintenance**. Existing encrypted inventory
needs deliberate separation; refresh does not rewrite local inputs.

<a id="environment-injection"></a>

## How are bootstrap passwords injected without a secret file?

For FreeIPA, on the Tier 0 execution host:

1. Remove conflicting placeholder assignments from `.env.local`; it is loaded by
   the wrapper. The existing `foundation.yml` reads these variables through Ansible. [2]
2. Enter the independently retained passwords without adding them to shell history:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   read -r -s -p 'Directory Manager password: ' FREEIPA_DM_PASSWORD; echo
   read -r -s -p 'FreeIPA administrator password: ' FREEIPA_ADMIN_PASSWORD; echo
   export FREEIPA_DM_PASSWORD FREEIPA_ADMIN_PASSWORD
   ```

3. Continue the selected [FreeIPA phase](../../deployment/stage-5-identity/procedures/freeipa.md).
   Changing these inputs does not itself rotate an already-installed domain's passwords.

<a id="suggested-environment-variable"></a>
<a id="encrypted-secret-file"></a>

## How is an encrypted secret file created and used?

### 1. Prepare the encryption password

Create the protected password file **outside the repository** using the local credential-custody
procedure. It must remain available without the service being deployed. [3]

### 2. Select that password file

Run from **the owning `<prefix>-tier-0/`, `<prefix>-tier-1/` or `<prefix>-tier-2/` repository**:

```bash
read -r -e -p 'Absolute existing Vault password-file path: ' ANSIBLE_VAULT_PASSWORD_FILE
export ANSIBLE_VAULT_PASSWORD_FILE
```

### 3. Create the encrypted input

From **the same repository and shell**, open the new encrypted file:

```bash
umask 077
mkdir -p secrets
ansible-vault create secrets/ansible-bootstrap-vars.yml
```

For the FreeIPA example, enter only these fields with the actual protected values, then save and close:

```yaml
foundation_freeipa_dm_password: REPLACE_WITH_EXISTING_PROTECTED_PASSWORD
foundation_freeipa_admin_password: REPLACE_WITH_EXISTING_PROTECTED_PASSWORD
```

The saved file is encrypted. Do not add inventory, host names or IP maps.

### 4. Provision separately from secret injection

For **FreeIPA in `<prefix>-tier-0/`**, use Terraform without the encrypted override:

```bash
bash scripts/deploy.sh foundation --terraform-only
```

Review the plan and confirm only the intended resources. Use the original inputs/state for existing guests.

### 5. Run the selected Ansible phase

From **`<prefix>-tier-0/`**, retain the selected [FreeIPA CSR/completion phase](../../deployment/stage-5-identity/procedures/freeipa.md).
The external-signing pause is still required:

```bash
bash scripts/deploy.sh foundation --ansible-only --ansible-vars secrets/ansible-bootstrap-vars.yml
```

Use the same `--env NAME` on both commands when operating a named environment.
For another product, use its owning recipe's secret-file argument instead of this FreeIPA command.

## How is a stored password edited?

1. Back up the encrypted file under the independent retention policy.
2. Edit it without a plaintext export: [3]

   Run from the selected **`<prefix>-tier-0/`**, `<prefix>-tier-1/` or `<prefix>-tier-2/` repository.

   ```bash
   ansible-vault edit secrets/ansible-bootstrap-vars.yml
   ```

3. Run the **owning service's** credential-change procedure and verify its consumers.
   Editing YAML alone does not rotate an existing account. OpenXPKI's pinned
   database/session secrets cannot be changed by routine reconciliation.

## How is the file-encryption password rotated?

This changes file encryption only, not any account password stored inside it. [3]

### 1. Preserve the old recovery pair

Retain the current encrypted file and its old password in independent custody.
Prepare a different protected password file outside Git.

### 2. Select the password files

Run from **the owning `<prefix>-tier-0/`, `<prefix>-tier-1/` or `<prefix>-tier-2/` repository**:

```bash
read -r -e -p 'Absolute current Vault password-file path: ' ANSIBLE_VAULT_PASSWORD_FILE
read -r -e -p 'Absolute new Vault password-file path: ' NEW_ANSIBLE_VAULT_PASSWORD_FILE
```

### 3. Rekey the encrypted file

From **the same repository and shell**:

```bash
ansible-vault rekey --vault-password-file "$ANSIBLE_VAULT_PASSWORD_FILE" --new-vault-password-file "$NEW_ANSIBLE_VAULT_PASSWORD_FILE" secrets/ansible-bootstrap-vars.yml
```

### 4. Verify decryption without displaying secrets

From **the same repository and shell**:

```bash
ansible-vault view --vault-password-file "$NEW_ANSIBLE_VAULT_PASSWORD_FILE" secrets/ansible-bootstrap-vars.yml >/dev/null
```

Expect a zero exit status. On failure, keep the old password reference and use [rollback](#usage-notes).

### 5. Update the active password-file reference

Only after successful validation, run from **the same repository and shell**:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE="$NEW_ANSIBLE_VAULT_PASSWORD_FILE"
```

Update the corresponding local/runner or `.env.local` path reference without storing the password there.
Rekey other files deliberately; old encrypted backups still need their old password.

<a id="usage-notes"></a>

## What stops a change or requires rollback?

- Stop on a missing password source, decryption failure or an override containing host/IP inputs.
- If rekey validation fails, restore the previous encrypted file and old password
  reference. Keep both versions until recovery is verified; do not decrypt files into Git.
- If a service rejects a changed credential, use that service's recovery path.
  Reverting the file is insufficient after the service has already changed its account.
- Keep private keys and independent recovery copies outside Git and CI logs.
  See the [credential operations map](strategy.md) for service-specific routes.

## References

CLI interfaces checked 2026-11-08.

1. [Terraform `yamldecode`](https://developer.hashicorp.com/terraform/language/functions/yamldecode).
2. [Ansible controller environment lookup](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/env_lookup.html).
3. [Ansible Vault create, edit, view and rekey](https://docs.ansible.com/projects/ansible/latest/cli/ansible-vault.html).
