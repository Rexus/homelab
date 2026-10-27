# Guide: docs/deployment/stage-4-kubernetes/procedures/api-endpoint.md
# Tier 0 owns the independent gateway pair; Shared supplies only approved references.
module "environment" {
  source = "../../modules/environment_guests"

  network_zones               = merge(var.shared_network_zones, var.network_zones)
  default_platform_node_name  = var.default_platform_node_name
  default_vm_template_id      = var.default_linux_vm_template_id
  proxmox_template_catalog    = var.proxmox_template_catalog
  linux_vm_template_catalog   = var.linux_vm_template_catalog
  default_vm_network_zone_key = var.default_vm_network_zone_key
  ansible_inventory_path      = var.ansible_inventory_path
  ansible_group_vars_paths    = var.ansible_group_vars_paths
  vm_instances                = var.vm_instances
}

resource "terraform_data" "gateway_contract" {
  lifecycle {
    precondition {
      condition = toset(keys(var.vm_instances)) == toset(keys(try(
        yamldecode(file(var.ansible_inventory_path)).all.children.cluster_endpoint.hosts,
        {},
      )))
      error_message = "Gateway VM keys must exactly match this Tier 0 inventory's cluster_endpoint pair."
    }

    precondition {
      condition = alltrue([
        for vm in values(module.environment.vm_instances) : can(cidrhost(vm.ipv4_address, 0))
        ]) && length(toset([
          for vm in values(module.environment.vm_instances) : vm.ipv4_address
      ])) == 2
      error_message = "Both gateway hosts require distinct static addresses in local group vars."
    }

    precondition {
      condition = length(toset([
        for vm in values(module.environment.vm_instances) : vm.network_zone_key
      ])) == 1
      error_message = "The private VIP gateway pair must share one selected network attachment."
    }
  }
}

module "vms" {
  for_each = module.environment.vm_instances
  source   = "../../modules/vm"

  name                     = each.value.name
  node_name                = each.value.node_name
  vm_id                    = each.value.vm_id
  template_vm_id           = each.value.template_vm_id
  template_node_name       = each.value.template_node_name
  storage_class            = each.value.storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = each.value.bridge
  vlan_id                  = each.value.vlan_id
  size                     = each.value.size
  cores                    = each.value.cores
  memory                   = each.value.memory
  disk_size_gb             = each.value.disk_size_gb
  ipv4_address             = each.value.ipv4_address
  ipv4_gateway             = each.value.ipv4_gateway
  ssh_public_keys          = var.ssh_public_keys
  ssh_public_key_files     = var.ssh_public_key_files
  tags                     = each.value.tags

  depends_on = [terraform_data.gateway_contract]
}
