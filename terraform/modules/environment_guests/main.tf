locals {
  ansible_inventory = try(yamldecode(file(var.ansible_inventory_path)), {})
  ansible_group_vars = merge(concat(
    [{}],
    [
      for vars_path in var.ansible_group_vars_paths :
      try(yamldecode(file(vars_path)), {})
    ]
  )...)
  ansible_inventory_children = try(local.ansible_inventory.all.children, {})
  ansible_inventory_hosts = merge(concat(
    [{}],
    [
      for _, group in local.ansible_inventory_children : try(group.hosts, {})
    ]
  )...)
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
  platform_hostname_suffix = trimspace(tostring(try(
    local.ansible_group_vars.platform_hostname_suffix,
    "",
  )))
  platform_hostname_prefix_normalized = (
    local.platform_hostname_prefix == "" ? "" : "${local.platform_hostname_prefix}-"
  )
  platform_hostname_suffix_normalized = (
    local.platform_hostname_suffix == "" ? "" : "-${local.platform_hostname_suffix}"
  )
  inventory_host_keys = setunion(
    keys(var.vm_instances),
    keys(var.lxc_instances),
  )
  inventory_host_name_matches = {
    for key in local.inventory_host_keys :
    key => regexall("^(.*)-([0-9]+)$", key)
  }
  platform_hostnames = {
    for key, matches in local.inventory_host_name_matches :
    key => (
      local.platform_hostname_suffix == "" || length(matches) == 0
      ? "${local.platform_hostname_prefix_normalized}${key}"
      : format(
        "%s%s%s-%s",
        local.platform_hostname_prefix_normalized,
        matches[0][0],
        local.platform_hostname_suffix_normalized,
        matches[0][1],
      )
    )
  }
  platform_host_ips = try(local.ansible_group_vars.platform_host_ips, {})
  missing_static_gateway_zones = toset(concat(
    [
      for key, vm in var.vm_instances :
      coalesce(try(vm.network_zone_key, null), var.default_vm_network_zone_key)
      if local.platform_host_ips[key] != "dhcp"
      && try(var.network_zones[
        coalesce(try(vm.network_zone_key, null), var.default_vm_network_zone_key)
      ].gateway_ipv4, null) == null
    ],
    [
      for key, lxc in var.lxc_instances :
      coalesce(try(lxc.network_zone_key, null), var.default_lxc_network_zone_key)
      if local.platform_host_ips[key] != "dhcp"
      && try(var.network_zones[
        coalesce(try(lxc.network_zone_key, null), var.default_lxc_network_zone_key)
      ].gateway_ipv4, null) == null
    ],
  ))

  resolved_vm_instances = {
    for key, vm in var.vm_instances : key => {
      name           = local.platform_hostnames[key]
      inventory_host = local.ansible_inventory_hosts[key]
      node_name = coalesce(
        try(vm.proxmox_node_name, null),
        var.default_platform_node_name,
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
      name           = local.platform_hostnames[key]
      inventory_host = local.ansible_inventory_hosts[key]
      node_name = coalesce(
        try(lxc.proxmox_node_name, null),
        var.default_platform_node_name,
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

check "static_guest_gateways" {
  assert {
    condition     = length(local.missing_static_gateway_zones) == 0
    error_message = "Static guest networks require gateway_ipv4 in network_zones for: ${join(", ", sort(tolist(local.missing_static_gateway_zones)))}."
  }
}
