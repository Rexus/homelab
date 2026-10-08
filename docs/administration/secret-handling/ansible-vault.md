# Ansible bootstrap secrets

Keep inventory and host IP files readable by both Terraform and Ansible.
Supply passwords through protected controller inputs or a separate encrypted
Ansible-only file. Neither method requires the future secret platform.

## Table of contents

- [Shared inputs stay plain YAML](#shared-inputs-stay-plain-yaml)
- [Environment injection](#environment-injection)
- [Encrypted secret file](#encrypted-secret-file)
- [Usage notes](#usage-notes)
- [References](#references)

<a id="purpose"></a>
<a id="local-file-pattern"></a>

## Shared inputs stay plain YAML

Do not encrypt inventory or the automatically loaded `ansible/group_vars/*.yml`
files. Terraform's `yamldecode` cannot decrypt Ansible Vault content or evaluate
Jinja expressions [1]. Keep host keys, names and IP maps as plain values.
Ansible-only settings can contain quoted lookups, which Terraform leaves unevaluated.

`--ansible-vars` normally passes the same file to both tools. An encrypted file
is valid with that flag **only during `--ansible-only` or maintenance execution**.
Secret-only overrides must not change inventory, names or IPs.

## Environment injection

The FreeIPA example reads `FREEIPA_DM_PASSWORD` and `FREEIPA_ADMIN_PASSWORD`
through Ansible's controller-side environment lookup [2]. Inject these using
protected runner variables or the ignored tier-local `.env.local`.
Missing or empty values retain the rejected `change-me` placeholder.

Run the normal deployment command after configuring those inputs. The YAML file
contains lookup expressions, not secret values; Terraform reads only the host inputs.

<a id="suggested-environment-variable"></a>

## Encrypted secret file

For an Ansible Vault workflow, keep a secret-only file such as
`secrets/ansible-bootstrap-vars.yml`. It contains the two
`foundation_freeipa_*_password` values, not `platform_host_ips`.
Keep the vault password outside the repository and set an **absolute** path:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE="$HOME/.config/homelab/ansible-vault-password.txt"
ansible-vault create secrets/ansible-bootstrap-vars.yml
```

Create the protected password file and the ignored `secrets/` directory first.
Ansible uses the password source to decrypt encrypted vars at execution time [3].
From the owning Tier 0 repository root, split provisioning and configuration:

```bash
bash scripts/deploy.sh foundation --env test --terraform-only
bash scripts/deploy.sh foundation --env test --ansible-only --ansible-vars secrets/ansible-bootstrap-vars.yml
```

Use the same setup and environment in both commands; omit `--env test` in both
for production. The first command uses plain inventory inputs; only the second
loads the encrypted secret overrides.

## Usage notes

- Keep vault passwords, plaintext secrets and private keys out of Git.
- Use absolute password-file paths because the wrapper runs Ansible from `ansible/`.
- Keep independent recovery copies outside the services being created.
- Move long-lived service secrets to the secret platform when available.

Existing encrypted group-var files need deliberate separation before Terraform
can consume them. Refresh does not rewrite local inputs.
See the [secret strategy](strategy.md) for the long-term operating model.

## References

1. [Terraform yamldecode](https://developer.hashicorp.com/terraform/language/functions/yamldecode)
2. [Ansible environment lookup](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/env_lookup.html)
3. [Ansible encrypted content](https://docs.ansible.com/projects/ansible/latest/vault_guide/vault_using_encrypted_content.html)
