output "ceremony_sessions" {
  description = "Stopped console-only sessions. Inspect the hardware before starting; no signing operation is driven by Terraform."
  value = { for name, session in proxmox_virtual_environment_vm.session : name => {
    vm_id        = session.vm_id
    node_name    = session.node_name
    iso_sha256   = var.ceremony_iso_sha256
    usb_mappings = var.ceremony_sessions[name].usb_mappings
  } }
}
