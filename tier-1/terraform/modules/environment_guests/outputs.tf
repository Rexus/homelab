output "vm_instances" {
  description = "Resolved VM instances with names, network values, and placement."
  value       = local.resolved_vm_instances

  precondition {
    condition     = alltrue([for vm in values(local.resolved_vm_instances) : vm.node_name != null])
    error_message = "Set default_platform_node_name in Shared config/platform.tfvars or proxmox_node_name per VM. Missing initial placement: ${join(", ", [for key, vm in local.resolved_vm_instances : key if vm.node_name == null])}."
  }

  precondition {
    condition     = length(local.invalid_sdn_guest_ips) == 0
    error_message = "Inventory IPs must be usable, non-gateway addresses in the selected SDN IPv4 subnet: ${join(", ", local.invalid_sdn_guest_ips)}."
  }

  precondition {
    condition     = alltrue([for id in values(local.resolved_vm_template_ids) : id > 0])
    error_message = "Select an approved Linux template ID in the shared catalog or a tier-local override."
  }

  precondition {
    condition = alltrue([
      for id in values(local.resolved_vm_template_ids) :
      !contains(["talos", "windows", "other"], try(var.proxmox_template_catalog[tostring(id)].family, "linux"))
    ])
    error_message = "Select a Linux cloud-init image for this module. Talos, Windows and other guests require their own provisioning path."
  }
}

output "lxc_instances" {
  description = "Resolved LXC instances with names, network values, and placement."
  value       = local.resolved_lxc_instances

  precondition {
    condition     = alltrue([for lxc in values(local.resolved_lxc_instances) : lxc.node_name != null])
    error_message = "Set default_platform_node_name in Shared config/platform.tfvars or proxmox_node_name per container. Missing initial placement: ${join(", ", [for key, lxc in local.resolved_lxc_instances : key if lxc.node_name == null])}."
  }

  precondition {
    condition     = length(local.invalid_sdn_guest_ips) == 0
    error_message = "Inventory IPs must be usable, non-gateway addresses in the selected SDN IPv4 subnet: ${join(", ", local.invalid_sdn_guest_ips)}."
  }
}
