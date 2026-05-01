terraform {
  required_version = ">= 1.6.0"

  backend "local" {}

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
  effective_default_platform_node_name = coalesce(
    var.default_platform_node_name,
    var.default_proxmox_node_name,
  )
  common_tags = [
    var.cluster_name,
    "terraform",
    "foundation",
    "linux",
  ]
}

module "environment" {
  source = "../../modules/environment_guests"

  network_zones                = var.network_zones
  default_platform_node_name   = local.effective_default_platform_node_name
  default_vm_network_zone_key  = var.default_vm_network_zone_key
  default_lxc_network_zone_key = var.default_lxc_network_zone_key
  ansible_inventory_path       = var.ansible_inventory_path
  ansible_group_vars_paths     = var.ansible_group_vars_paths
  vm_instances                 = var.vm_instances
  lxc_instances                = var.lxc_instances
}

module "vms" {
  for_each = module.environment.vm_instances
  source   = "../../modules/vm"

  name                     = each.value.name
  node_name                = each.value.node_name
  template_vm_id = coalesce(
    try(each.value.template_vm_id, null),
    var.default_linux_vm_template_id,
  )
  storage_class            = each.value.storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.network_zones[each.value.network_zone_key].bridge
  vlan_id                  = try(var.network_zones[each.value.network_zone_key].vlan_id, null)
  size                     = each.value.size
  disk_size_gb             = each.value.disk_size_gb
  ipv4_address             = each.value.ipv4_address
  ipv4_gateway = each.value.ipv4_address == "dhcp" ? null : try(
    var.network_zones[each.value.network_zone_key].gateway_ipv4,
    null,
  )
  ssh_public_keys          = var.ssh_public_keys
  tags                     = concat(local.common_tags, each.value.tags)
}

module "lxcs" {
  for_each = module.environment.lxc_instances
  source   = "../../modules/lxc"

  name                     = each.value.name
  node_name                = each.value.node_name
  template_file_id         = each.value.template_file_id
  storage_class            = each.value.storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.network_zones[each.value.network_zone_key].bridge
  size                     = each.value.size
  disk_size_gb             = each.value.disk_size_gb
  ipv4_address             = each.value.ipv4_address
  ipv4_gateway = each.value.ipv4_address == "dhcp" ? null : try(
    var.network_zones[each.value.network_zone_key].gateway_ipv4,
    null,
  )
  tags                     = concat(local.common_tags, each.value.tags)
}
