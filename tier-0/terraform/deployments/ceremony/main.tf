locals {
  session_nodes = toset([for session in var.ceremony_sessions : session.node_name])
}

# The content address keeps reviewed images distinct. Destroying a session never owns custody media.
resource "proxmox_virtual_environment_file" "image" {
  for_each     = local.session_nodes
  content_type = "iso"
  datastore_id = var.ceremony_iso_datastore_id
  node_name    = each.value
  overwrite    = false

  source_file {
    path      = var.ceremony_iso_path
    file_name = "ceremony-${each.value}-${var.ceremony_iso_sha256}.iso"
    checksum  = var.ceremony_iso_sha256
  }

  lifecycle {
    create_before_destroy = true
    precondition {
      condition     = var.ceremony_hypervisor_trust_accepted
      error_message = "Accept hypervisor trust explicitly, or boot the approved ISO on a separate physical offline workstation."
    }
    precondition {
      condition     = try(filesha256(var.ceremony_iso_path) == var.ceremony_iso_sha256, false)
      error_message = "The selected ISO differs from the independently accepted SHA256. Stop and review the image."
    }
  }
}

# Direct ISO resources deliberately avoid the clone module's NIC/cloud-init/OS disks.
resource "proxmox_virtual_environment_vm" "session" {
  for_each        = var.ceremony_sessions
  name            = each.key
  node_name       = each.value.node_name
  vm_id           = each.value.vm_id
  pool_id         = var.ceremony_pool_id
  description     = "On-demand public live image; console ceremony; custody media independently retained."
  tags            = ["ceremony", "offline", "maintenance"]
  started         = false
  on_boot         = false
  reboot          = false
  stop_on_destroy = false
  bios            = "seabios"
  boot_order      = ["ide2"]

  # Console power belongs to the ceremony operator, never ordinary Terraform convergence.
  lifecycle {
    ignore_changes = [started]
  }

  agent {
    enabled = false
  }
  cpu {
    cores = each.value.cores
    type  = "x86-64-v2-AES"
  }
  memory {
    dedicated = each.value.memory_mb
    floating  = 0
  }
  operating_system {
    type = "l26"
  }
  cdrom {
    file_id   = proxmox_virtual_environment_file.image[each.value.node_name].id
    interface = "ide2"
  }
  dynamic "usb" {
    for_each = each.value.usb_mappings
    content {
      mapping = usb.value
      usb3    = true
    }
  }
}
