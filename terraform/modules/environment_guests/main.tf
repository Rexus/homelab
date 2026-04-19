locals {
  resolved_vm_instances = {
    for key, vm in var.vm_instances : key => merge(
      {
        size             = "small"
        storage_class    = "local"
        network_zone_key = var.default_vm_network_zone_key
        ipv4_address     = "dhcp"
        tags             = []
      },
      vm,
    )
  }

  resolved_lxc_instances = {
    for key, lxc in var.lxc_instances : key => merge(
      {
        size             = "small"
        storage_class    = "local"
        network_zone_key = var.default_lxc_network_zone_key
        ipv4_address     = "dhcp"
        tags             = []
      },
      lxc,
    )
  }
}

module "vms" {
  for_each = local.resolved_vm_instances
  source   = "../vm"

  name                     = each.value.name
  node_name                = each.value.node_name
  template_vm_id           = coalesce(try(each.value.template_vm_id, null), var.template_vm_id_el10)
  storage_class            = each.value.storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.network_zones[each.value.network_zone_key].bridge
  vlan_id                  = try(var.network_zones[each.value.network_zone_key].vlan_id, null)
  size                     = each.value.size
  disk_size_gb             = each.value.disk_size_gb
  ipv4_address             = each.value.ipv4_address
  ipv4_gateway = each.value.ipv4_address == "dhcp"
    ? null
    : coalesce(
        try(each.value.ipv4_gateway, null),
        try(var.network_zones[each.value.network_zone_key].gateway_ipv4, null),
      )
  ssh_public_keys = var.ssh_public_keys
  tags = concat(
    var.common_tags,
    compact([try(each.value.role, null)]),
    each.value.tags,
  )
}

module "lxcs" {
  for_each = local.resolved_lxc_instances
  source   = "../lxc"

  name                     = each.value.name
  node_name                = each.value.node_name
  template_file_id         = each.value.template_file_id
  storage_class            = each.value.storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.network_zones[each.value.network_zone_key].bridge
  size                     = each.value.size
  disk_size_gb             = each.value.disk_size_gb
  ipv4_address             = each.value.ipv4_address
  ipv4_gateway = each.value.ipv4_address == "dhcp"
    ? null
    : coalesce(
        try(each.value.ipv4_gateway, null),
        try(var.network_zones[each.value.network_zone_key].gateway_ipv4, null),
      )
  tags = concat(
    var.common_tags,
    compact([try(each.value.role, null)]),
    each.value.tags,
  )
}
