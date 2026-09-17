terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.112.0"
    }
  }
}

resource "proxmox_virtual_environment_file" "image" {
  for_each     = var.images
  node_name    = each.value.node_name
  datastore_id = each.value.image_datastore_id
  content_type = "import"
  overwrite    = false

  source_file {
    path      = each.value.image_path
    checksum  = each.value.sha256
    file_name = "${each.value.vm_id}-${each.value.sha256}.${each.value.family == "talos" ? "raw" : "qcow2"}"
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = try(filesha256(each.value.image_path) == each.value.sha256, false)
      error_message = "The approved local image is missing or its SHA256 does not match the catalog."
    }
  }
}

resource "proxmox_virtual_environment_vm" "template" {
  for_each      = var.images
  name          = each.value.name
  node_name     = each.value.node_name
  vm_id         = each.value.vm_id
  description   = "${each.value.family} ${each.value.release}; sha256=${each.value.sha256}"
  tags          = ["tier-0", "template", each.value.family]
  template      = true
  started       = false
  on_boot       = false
  bios          = "seabios"
  scsi_hardware = "virtio-scsi-single"
  boot_order    = ["scsi0"]

  cpu {
    type  = each.value.cpu_type
    cores = each.value.cores
  }

  memory {
    dedicated = each.value.memory_mb
  }

  agent {
    enabled = each.value.qemu_agent
  }

  disk {
    datastore_id = each.value.datastore_id
    import_from  = proxmox_virtual_environment_file.image[each.key].id
    interface    = "scsi0"
    size         = each.value.disk_size_gb
    iothread     = true
    discard      = "on"
  }

  network_device {
    bridge  = each.value.bridge
    vlan_id = each.value.vlan_id
    model   = "virtio"
  }

  operating_system {
    type = "l26"
  }

  serial_device {}

  # Machine identity and cloud-init/Talos configuration belong to clones, never templates.
  lifecycle {
    prevent_destroy = true
  }
}
