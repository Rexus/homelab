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
  template_vm_id = var.template_vm_id_el10 != null
    ? var.template_vm_id_el10
    : var.template_vm_id_almalinux_10

  common_tags = [
    var.cluster_name,
    "terraform",
    "vault",
    "el10",
  ]

  use_shared_guest_inputs = var.network_zones != null
    || length(var.vm_instances) > 0
    || length(var.lxc_instances) > 0

  legacy_network_zones = {
    management = {
      description = "Management, operator access, and early infrastructure control."
      bridge      = var.proxmox_network_bridge
      cidr_ipv4   = var.management_cidr
    }
    application = {
      description = "Shared internal application or workload-facing guest network."
      bridge      = var.proxmox_network_bridge
      cidr_ipv4   = var.workload_cidr
    }
    dmz = {
      description = "Edge or DMZ-facing guest network."
      bridge      = var.proxmox_network_bridge
      cidr_ipv4   = var.edge_cidr
    }
  }

  effective_network_zones = var.network_zones != null
    ? var.network_zones
    : local.legacy_network_zones

  effective_ssh_public_keys = length(var.ssh_public_keys) > 0
    ? var.ssh_public_keys
    : var.instance_ssh_public_keys

  legacy_vm_instances = local.use_shared_guest_inputs ? {} : {
    primary = {
      name             = var.instance_name
      node_name        = var.proxmox_node_name
      size             = var.instance_size
      storage_class    = var.instance_storage_class
      disk_size_gb     = var.instance_disk_size_gb
      network_zone_key = var.default_vm_network_zone_key
      ipv4_address     = var.instance_ipv4_address
      ipv4_gateway     = var.instance_ipv4_gateway
      role             = "vault"
      tags             = []
    }
  }

  legacy_lxc_instances = local.use_shared_guest_inputs || var.container_template_file_id == null ? {} : {
    support = {
      name             = var.container_name
      node_name        = var.proxmox_node_name
      template_file_id = var.container_template_file_id
      size             = var.container_size
      storage_class    = var.container_storage_class
      disk_size_gb     = var.container_disk_size_gb
      network_zone_key = var.default_lxc_network_zone_key
      ipv4_address     = var.container_ipv4_address
      ipv4_gateway     = var.container_ipv4_gateway
      role             = "support"
      tags             = []
    }
  }

  effective_vm_instances = local.use_shared_guest_inputs
    ? var.vm_instances
    : local.legacy_vm_instances

  effective_lxc_instances = local.use_shared_guest_inputs
    ? var.lxc_instances
    : local.legacy_lxc_instances
}

module "environment" {
  source = "../../modules/environment_guests"

  template_vm_id_el10          = local.template_vm_id
  proxmox_storage_classes      = var.proxmox_storage_classes
  network_zones                = local.effective_network_zones
  default_vm_network_zone_key  = var.default_vm_network_zone_key
  default_lxc_network_zone_key = var.default_lxc_network_zone_key
  ssh_public_keys              = local.effective_ssh_public_keys
  common_tags                  = local.common_tags
  vm_instances                 = local.effective_vm_instances
  lxc_instances                = local.effective_lxc_instances
}
