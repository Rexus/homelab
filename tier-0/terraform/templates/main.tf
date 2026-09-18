terraform {
  required_version = ">= 1.6.0"

  backend "local" {}

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.112.0"
    }
  }
}

# Provider-native PROXMOX_VE_ENDPOINT and PROXMOX_VE_API_TOKEN are supplied at runtime.
# Reference: docs/platforms/proxmox/template-lifecycle.md
provider "proxmox" {
  insecure = false
}

module "templates" {
  source = "../../../shared/terraform/modules/proxmox_templates"
  images = yamldecode(file(var.catalog_file)).templates
}
