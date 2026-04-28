locals {
  ansible_inventory = try(yamldecode(file(var.ansible_inventory_path)), {})
  ansible_group_vars = merge(
    {},
    [
      for vars_path in var.ansible_group_vars_paths :
      try(yamldecode(file(vars_path)), {})
    ]...,
  )
  ansible_inventory_children = try(local.ansible_inventory.all.children, {})
  ansible_inventory_hosts = merge(
    {},
    [
      for _, group in local.ansible_inventory_children : try(group.hosts, {})
    ]...,
  )
  network_zone_ipv4_prefixes = {
    for zone_key, zone in var.network_zones : zone_key => try(
      split("/", zone.cidr_ipv4)[1],
      null,
    )
  }
  platform_hostname_prefix = trimspace(tostring(try(
    local.ansible_group_vars.platform_hostname_prefix,
    "",
  )))
  platform_host_ips = try(local.ansible_group_vars.platform_host_ips, {})

  resolved_vm_instances = {
    for key, vm in var.vm_instances : key => {
      name           = "${local.platform_hostname_prefix}${key}"
      inventory_host = local.ansible_inventory_hosts[key]
      node_name = coalesce(
        try(vm.proxmox_node_name, null),
        var.default_proxmox_node_name,
      )
      template_vm_id = try(vm.template_vm_id, null)
      size           = coalesce(try(vm.size, null), "small")
      storage_class  = coalesce(try(vm.storage_class, null), "local")
      disk_size_gb   = vm.disk_size_gb
      network_zone_key = coalesce(
        try(vm.network_zone_key, null),
        var.default_vm_network_zone_key,
      )
      ipv4_address = local.platform_host_ips[key] == "dhcp" ? "dhcp" : format(
        "%s/%s",
        local.platform_host_ips[key],
        local.network_zone_ipv4_prefixes[
          coalesce(try(vm.network_zone_key, null), var.default_vm_network_zone_key)
        ],
      )
      tags = try(vm.tags, [])
    }
  }

  resolved_lxc_instances = {
    for key, lxc in var.lxc_instances : key => {
      name           = "${local.platform_hostname_prefix}${key}"
      inventory_host = local.ansible_inventory_hosts[key]
      node_name = coalesce(
        try(lxc.proxmox_node_name, null),
        var.default_proxmox_node_name,
      )
      template_file_id = lxc.template_file_id
      size             = coalesce(try(lxc.size, null), "small")
      storage_class    = coalesce(try(lxc.storage_class, null), "local")
      disk_size_gb     = lxc.disk_size_gb
      network_zone_key = coalesce(
        try(lxc.network_zone_key, null),
        var.default_lxc_network_zone_key,
      )
      ipv4_address = local.platform_host_ips[key] == "dhcp" ? "dhcp" : format(
        "%s/%s",
        local.platform_host_ips[key],
        local.network_zone_ipv4_prefixes[
          coalesce(try(lxc.network_zone_key, null), var.default_lxc_network_zone_key)
        ],
      )
      tags = try(lxc.tags, [])
    }
  }
}

module "vms" {
  for_each = local.resolved_vm_instances
  source   = "../vm"

  name                     = each.value.name
  node_name                = each.value.node_name
  template_vm_id = coalesce(
    try(each.value.template_vm_id, null),
    var.template_vm_id_el10,
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
  ssh_public_keys = var.ssh_public_keys
  tags = concat(
    var.common_tags,
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
  ipv4_gateway = each.value.ipv4_address == "dhcp" ? null : try(
    var.network_zones[each.value.network_zone_key].gateway_ipv4,
    null,
  )
  tags = concat(
    var.common_tags,
    each.value.tags,
  )
}
