terraform {
  required_providers {
    external = {
      source  = "hashicorp/external"
      version = "~> 2.4.2"
    }
  }
}

locals {
  used_network_keys = toset(concat(
    [for vm in var.vm_instances : coalesce(vm.network_zone_key, var.default_vm_network_zone_key)],
    [for lxc in var.lxc_instances : coalesce(lxc.network_zone_key, var.default_lxc_network_zone_key)],
  ))
  effective_network_zones = {
    for key, network in var.network_zones : key => merge(
      network, try(data.external.sdn_network[key].result, {}),
    )
  }
  invalid_sdn_guest_ips = [
    for key, guest in merge(local.resolved_vm_instances, local.resolved_lxc_instances) : key
    if try(var.network_zones[guest.network_zone_key].sdn_lookup, false) &&
    local.platform_host_ips[key] != "dhcp" && !try(
      cidrhost(local.effective_network_zones[guest.network_zone_key].cidr_ipv4, 0) ==
      cidrhost(guest.ipv4_address, 0) &&
      !contains([
        cidrhost(local.effective_network_zones[guest.network_zone_key].cidr_ipv4, 0),
        cidrhost(local.effective_network_zones[guest.network_zone_key].cidr_ipv4, -1),
        guest.ipv4_gateway,
      ], local.platform_host_ips[key]), false
    )
  ]
}

# Stateless discovery only; Shared owns no inventory, network resources or state.
# The native subnet data source requires the CIDR that this lookup discovers.
# Reference: docs/08-reference/network-inputs.md#sdn-subnet-lookup
data "external" "sdn_network" {
  for_each = {
    for key, network in var.network_zones : key => network
    if network.sdn_lookup && contains(local.used_network_keys, key)
  }
  program = ["python3", "${path.module}/../../../../shared/scripts/proxmox-sdn.py"]
  query   = { vnet = each.value.bridge }
}
