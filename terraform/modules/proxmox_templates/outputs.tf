output "catalog" {
  description = "Template candidates; clone testing and promotion remain explicit operator gates."
  value = {
    for key, image in var.images : key => {
      vm_id        = proxmox_virtual_environment_vm.template[key].vm_id
      node_name    = image.node_name
      family       = image.family
      release      = image.release
      sha256       = image.sha256
      schematic_id = image.schematic_id
    }
  }
}
