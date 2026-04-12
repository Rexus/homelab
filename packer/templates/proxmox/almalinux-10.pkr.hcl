packer {
  required_plugins {
    proxmox = {
      source  = "github.com/hashicorp/proxmox"
      version = ">= 1.1.0"
    }
  }
}

# Minimal AlmaLinux 10 template scaffold for Proxmox.
# Prefer environment variables for sensitive runtime values such as API
# endpoints, token IDs, and token secrets.
# See: docs/reference/environment-variables.md
source "proxmox-iso" "almalinux10" {
  # Intentionally left minimal for initial scaffolding.
  # Typical sensitive inputs are better injected at runtime than stored here.
}

build {
  name    = "almalinux-10-baseline"
  sources = ["source.proxmox-iso.almalinux10"]
}
