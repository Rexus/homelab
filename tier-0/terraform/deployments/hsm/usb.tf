output "hsm_usb_devices" {
  description = "Selected USB attachments, not evidence of token/key identity or host failover."
  value = {
    for key, vm in var.vm_instances : key => vm.usb_devices if length(vm.usb_devices) > 0
  }

  precondition {
    condition = alltrue([
      for key, vm in var.vm_instances :
      length(vm.usb_devices) == 0 ? true : vm.proxmox_node_name != null
    ])
    error_message = "Set proxmox_node_name explicitly for every USB-attached VM; physical placement must be reviewed."
  }
}
