output "vm_instances" {
  description = "Resolved VM instances with names, network values, and placement."
  value       = local.resolved_vm_instances
}

output "lxc_instances" {
  description = "Resolved LXC instances with names, network values, and placement."
  value       = local.resolved_lxc_instances
}
