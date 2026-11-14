# One consumer resolver for every tier. The deploy helper loads shared template
# references first; tier inputs select an ID and may retain legacy overrides.
# Reference: docs/08-reference/template-catalog.md
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
  # Firmware follows the actual clone source, never the separate tag/catalog alias.
  resolved_vm_firmware = {
    for key, vm in var.vm_instances : key => (
      vm.firmware != null ? vm.firmware : (
        try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].bios, null) == null
        ? null
        : {
          bios          = var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].bios
          machine       = var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].machine
          scsi_hardware = var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].scsi_hardware
          efi_pre_enrolled_keys = coalesce(
            var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].efi_pre_enrolled_keys, false,
          )
        }
      )
    )
  }
  incomplete_vm_template_firmware = [
    for key, vm in var.vm_instances : key
    if vm.firmware == null &&
    anytrue([for field in ["bios", "machine", "scsi_hardware", "efi_pre_enrolled_keys"] :
      try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])][field], null) != null
      ]) && (
      try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].bios, null) == null ||
      try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].scsi_hardware, null) == null ||
      (try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].bios, null) == "ovmf" &&
      try(var.proxmox_template_catalog[tostring(local.resolved_vm_template_ids[key])].efi_pre_enrolled_keys, null) == null)
    )
  ]
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
