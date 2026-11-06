# Opt-in discovery reads only. Apply commits the imports from the reviewed plan to state.
data "proxmox_virtual_environment_vms" "existing" {
  count = var.adopt_existing ? 1 : 0
}

data "proxmox_files" "existing" {
  for_each     = { for key, image in local.images : key => image if var.adopt_existing }
  node_name    = each.value.node_name
  datastore_id = each.value.image_datastore_id
  content_type = "import"
}

locals {
  existing_vms = var.adopt_existing ? {
    for vm in data.proxmox_virtual_environment_vms.existing[0].vms : tostring(vm.vm_id) => vm
  } : {}
  vm_imports = { for key, image in local.images : key => "${image.node_name}/${image.vm_id}"
    if contains(keys(local.existing_vms), tostring(image.vm_id))
  }
  file_imports = var.adopt_existing ? {
    for key, image in local.images : key => "${image.node_name}/${image.image_datastore_id}:import/${image.image_file_name}"
    if anytrue([for file in data.proxmox_files.existing[key].files :
      file.id == "${image.image_datastore_id}:import/${image.image_file_name}"
    ])
  } : {}
}

import {
  for_each = local.file_imports
  to       = module.templates.proxmox_virtual_environment_file.image[each.key]
  id       = each.value
}

import {
  for_each = local.vm_imports
  to       = module.templates.proxmox_virtual_environment_vm.template[each.key]
  id       = each.value
}
