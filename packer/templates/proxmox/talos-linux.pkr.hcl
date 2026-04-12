packer {
  required_plugins {
    proxmox = {
      source  = "github.com/hashicorp/proxmox"
      version = ">= 1.1.0"
    }
  }
}

# Minimal Talos Linux template scaffold for Proxmox.
# Talos often works well as a Terraform-driven VM deployment target too, so use
# this template only if you want a reusable image workflow rather than a direct
# provisioning flow.
# Prefer environment variables for sensitive runtime values.
# See: docs/reference/environment-variables.md
source "proxmox-iso" "taloslinux" {
  # Intentionally left minimal for initial scaffolding.
}

build {
  name    = "talos-linux-baseline"
  sources = ["source.proxmox-iso.taloslinux"]
}
