terraform {
  required_version = ">= 1.6.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = ">= 0.66.0"
    }
  }
}

# Prefer environment variables for sensitive provider authentication, for example:
# - TF_VAR_proxmox_api_url
# - TF_VAR_proxmox_api_token_id
# - TF_VAR_proxmox_api_token_secret
# See: ../../../docs/reference/environment-variables.md
provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true
}

locals {
  common_tags = [
    var.cluster_name,
    "terraform",
    "lab",
    "el10",
  ]
}

module "environment" {
  source = "../../modules/environment_guests"

  template_vm_id_el10          = var.template_vm_id_el10
  proxmox_storage_classes      = var.proxmox_storage_classes
  network_zones                = var.network_zones
  default_vm_network_zone_key  = var.default_vm_network_zone_key
  default_lxc_network_zone_key = var.default_lxc_network_zone_key
  ssh_public_keys              = var.ssh_public_keys
  common_tags                  = local.common_tags
  ansible_inventory_path       = var.ansible_inventory_path
  vm_instances                 = var.vm_instances
  lxc_instances                = var.lxc_instances
}
