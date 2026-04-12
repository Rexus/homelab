# Terraform modules

Store reusable Terraform modules here. Keep modules provider-agnostic where it
makes sense, and isolate platform-specific details where it improves clarity.

Current modules:

- `vm/` - clone a Proxmox VM template with cloud-init-ready inputs
- `lxc/` - create a Proxmox LXC container from a template file
