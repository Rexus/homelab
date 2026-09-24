output "vm_instances" {
  description = "Resolved VM instances with names, network values, and placement."
  value       = local.resolved_vm_instances

  precondition {
    condition     = alltrue([for id in values(local.resolved_vm_template_ids) : id > 0])
    error_message = "Select an approved Linux template ID in the shared catalog or a tier-local override."
  }

  precondition {
    condition = alltrue([
      for id in values(local.resolved_vm_template_ids) :
      try(var.proxmox_template_catalog[tostring(id)].family, "linux") != "talos"
    ])
    error_message = "Talos templates need Talos machine configuration, not the Linux cloud-init VM module."
  }
}

output "lxc_instances" {
  description = "Resolved LXC instances with names, network values, and placement."
  value       = local.resolved_lxc_instances
}
