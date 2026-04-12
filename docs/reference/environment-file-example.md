# Environment file example

Use a local ignored file such as `.env.local` for bootstrap secrets.

Minimal example:

```dotenv docs/reference/environment-file-example.md
PROXMOX_API_URL=https://proxmox.example.internal:8006/api2/json
PROXMOX_API_TOKEN_ID=automation@pve!packer
PROXMOX_API_TOKEN_SECRET=ChangeMe-Proxmox-Token-12345
ANSIBLE_VAULT_PASSWORD_FILE=secrets/ansible-vault-password.txt
```

Read more in:

- [Environment variable conventions](environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
