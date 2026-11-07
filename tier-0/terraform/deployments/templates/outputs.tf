output "template_candidates" {
  description = "Applied references synchronized to Shared; clone-test before selecting consumer templates."
  value       = module.templates.catalog
  # A VMID match alone is not permission to adopt a running or unrelated machine.
  precondition {
    condition = alltrue([for key, id in local.vm_imports :
      local.existing_vms[tostring(local.images[key].vm_id)].template &&
      local.existing_vms[tostring(local.images[key].vm_id)].status == "stopped" &&
      local.existing_vms[tostring(local.images[key].vm_id)].name == local.images[key].name &&
      local.existing_vms[tostring(local.images[key].vm_id)].node_name == local.images[key].node_name
    ])
    error_message = "Adoption requires a stopped template with exactly the catalog VMID, name and node. Fix the catalog; never adopt an unrelated VM."
  }
}

output "template_disk_sources" {
  description = "Applied template/artifact references for the Tier 0 boot-disk maintenance recipe."
  value       = module.templates.disk_sources
}
