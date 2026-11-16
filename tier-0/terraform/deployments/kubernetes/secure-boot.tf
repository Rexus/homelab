# Signed media is installed on fresh blank disks: EFI enrollment and TPM identity are per node.
# Guide: docs/03-deployment/stage-04-kubernetes/procedures/secure-boot.md
locals {
  secure_boot_nodes = var.secure_boot == null ? toset([]) : toset([for node in var.nodes : node.node_name])
  secure_boot_stores = {
    for node, result in data.proxmox_datastores.secure_boot : node =>
    try(one(result.datastores), null)
  }
  secure_boot_shared = length(local.secure_boot_stores) > 0 && alltrue([
    for store in local.secure_boot_stores : try(store.shared, false) == true
  ])
  secure_boot_upload_nodes = local.secure_boot_shared ? toset(slice(sort(tolist(local.secure_boot_nodes)), 0, 1)) : local.secure_boot_nodes
  # Keep custom patches from replacing the selected signed installer with a legacy image.
  secure_boot_installer_patches = var.secure_boot == null ? [] : [yamlencode({
    machine = { install = { image = var.cluster.installer_image } }
  })]
  secure_boot_volume_patches = var.secure_boot == null ? [] : (!var.secure_boot.encrypt_system_disks ? [] : [
    for volume in ["STATE", "EPHEMERAL"] : yamlencode({
      apiVersion = "v1alpha1"
      kind       = "VolumeConfig"
      name       = volume
      encryption = {
        provider = "luks2"
        keys     = [{ slot = 0, tpm = { checkSecurebootStatusOnEnroll = true } }]
      }
    })
  ])
}

data "proxmox_datastores" "secure_boot" {
  for_each  = local.secure_boot_nodes
  node_name = each.key
  filters = {
    id            = var.secure_boot.iso_datastore_id
    content_types = ["iso"]
  }
}

resource "proxmox_virtual_environment_file" "secure_boot_iso" {
  for_each     = local.secure_boot_upload_nodes
  depends_on   = [terraform_data.configuration]
  node_name    = each.key
  datastore_id = var.secure_boot.iso_datastore_id
  content_type = "iso"
  overwrite    = false
  source_file {
    path      = var.secure_boot.iso_path
    checksum  = var.secure_boot.iso_sha256
    file_name = "talos-${var.cluster.name}-${var.secure_boot.iso_sha256}-secureboot.iso"
  }
  lifecycle { prevent_destroy = true }
}

output "boot_security" {
  description = "Selected boot policy; verify-security inspects actual authenticated guest state. Preserve mode/encryption for existing nodes."
  value = {
    mode                   = var.secure_boot == null ? "template" : "secureboot"
    encrypt_system_disks   = var.secure_boot == null ? false : var.secure_boot.encrypt_system_disks
    install_media_attached = var.secure_boot == null ? false : var.secure_boot.install_media_attached
    tpm_version            = var.secure_boot == null ? null : "v2.0"
  }
}
