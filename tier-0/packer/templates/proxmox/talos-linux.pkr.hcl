packer {
  required_plugins {
    proxmox = {
      source  = "github.com/hashicorp/proxmox"
      version = ">= 1.1.0"
    }
  }
}

# Optional, incomplete custom ISO-build scaffold, not the template publication path.
# Use Tier 0 terraform/deployments/templates/ for verified NoCloud raw-image imports.
# Reference: docs/platforms/proxmox/talos-template.md
# Prefer environment variables for sensitive runtime values.
# See: docs/reference/environment-variables.md
source "proxmox-iso" "taloslinux" {
  # Intentionally left minimal for initial scaffolding.
}

build {
  name    = "talos-linux-baseline"
  sources = ["source.proxmox-iso.taloslinux"]
}
