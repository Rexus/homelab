# One consumer resolver for every tier. The deploy helper loads shared template
# references first; tier inputs select an ID and may retain legacy overrides.
# Reference: docs/platforms/proxmox/template-catalog.md
locals {
  template_metadata = merge(var.proxmox_template_catalog, var.linux_vm_template_catalog)

  resolved_vm_template_ids = {
    for key, vm in var.vm_instances : key => coalesce(
      try(vm.template_vm_id, null),
      var.default_vm_template_id,
      0,
    )
  }
  resolved_vm_template_catalog_ids = {
    for key, vm in var.vm_instances : key => coalesce(
      try(vm.template_catalog_id, null),
      local.resolved_vm_template_ids[key],
    )
  }
  resolved_vm_template_tags = {
    for key, vm in var.vm_instances : key => (
      try(vm.template_tags, null) == null
      ? try(
        local.template_metadata[tostring(local.resolved_vm_template_catalog_ids[key])].tags,
        [],
      )
      : vm.template_tags
    )
  }
}
