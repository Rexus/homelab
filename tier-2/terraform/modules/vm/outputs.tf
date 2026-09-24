output "vm_name" {
  description = "Created VM name."
  value       = proxmox_virtual_environment_vm.this.name
}

output "vm_id" {
  description = "Created VM ID."
  value       = proxmox_virtual_environment_vm.this.vm_id
}

output "node_name" {
  description = "Node hosting the VM."
  value       = proxmox_virtual_environment_vm.this.node_name
}
