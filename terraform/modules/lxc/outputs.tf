output "container_name" {
  description = "Created container hostname."
  value       = proxmox_virtual_environment_container.this.initialization[0].hostname
}

output "container_id" {
  description = "Created container VM ID."
  value       = proxmox_virtual_environment_container.this.vm_id
}

output "node_name" {
  description = "Node hosting the container."
  value       = proxmox_virtual_environment_container.this.node_name
}
