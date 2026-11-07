output "catalog" {
  description = "Template candidates; clone testing and promotion remain explicit operator gates."
  value = {
    for key, image in var.images : key => {
      vm_id         = proxmox_virtual_environment_vm.template[key].vm_id
      title         = image.name
      node_name     = image.node_name
      family        = image.family
      distribution  = coalesce(image.distribution, image.family)
      release       = image.release
      sha256        = image.sha256
      schematic_id  = image.schematic_id
      bios          = image.bios
      machine       = image.machine
      scsi_hardware = proxmox_virtual_environment_vm.template[key].scsi_hardware
    }
  }
}

output "disk_sources" {
  description = "Applied template and immutable artifact identities for explicit boot-disk maintenance."
  value = { for key, image in var.images : key => {
    vm_id           = proxmox_virtual_environment_vm.template[key].vm_id
    name            = proxmox_virtual_environment_vm.template[key].name
    node_name       = proxmox_virtual_environment_vm.template[key].node_name
    image_path      = image.image_path
    sha256          = image.sha256
    image_volume_id = "${image.image_datastore_id}:import/${proxmox_virtual_environment_file.image[key].file_name}"
    datastore_id    = image.datastore_id
    disk_size_gb    = image.disk_size_gb
    iothread        = local.scsi_hardware[key] == "virtio-scsi-single"
    discard         = proxmox_virtual_environment_vm.template[key].disk[0].discard
    cache           = proxmox_virtual_environment_vm.template[key].disk[0].cache
  } }
}
