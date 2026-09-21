packer {
  required_plugins {
    proxmox = {
      source  = "github.com/hashicorp/proxmox"
      version = ">= 1.1.0"
    }
  }
}

# Minimal Enterprise Linux 10 template scaffold for Proxmox.
# Prefer environment variables for sensitive runtime values such as API
# endpoints, token IDs, and token secrets.
# See: docs/reference/environment-variables.md
source "proxmox-iso" "el10" {
  # Intentionally left minimal for initial scaffolding.
  # Typical sensitive inputs are better injected at runtime than stored here.
}

build {
  name    = "el10-baseline"
  sources = ["source.proxmox-iso.el10"]
}
