terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
  }
}

locals {
  size_profiles = {
    tiny = {
      cores  = 1
      memory = 1024
    }
    small = {
      cores  = 2
      memory = 2048
    }
    medium = {
      cores  = 2
      memory = 4096
    }
    large = {
      cores  = 4
      memory = 8192
    }
    xl = {
      cores  = 8
      memory = 16384
    }
  }

  selected_size = local.size_profiles[var.size]
  selected_storage = var.storage_class_datastores[var.storage_class]
  resolved_cores = coalesce(var.cores, local.selected_size.cores)
  resolved_memory = coalesce(var.memory, local.selected_size.memory)
  resolved_disk_size_gb = var.disk_size_gb
  resolved_datastore_id = coalesce(var.datastore_id, local.selected_storage.vm_disk)
  resolved_initialization_datastore_id = coalesce(
    var.initialization_datastore_id,
    local.selected_storage.initialization,
  )
}

resource "proxmox_virtual_environment_vm" "this" {
  name      = var.name
  node_name = var.node_name
  tags      = var.tags

  clone {
    vm_id = var.template_vm_id
    full  = true
  }

  cpu {
    cores   = local.resolved_cores
    sockets = var.sockets
    type    = "x86-64-v3"
  }

  memory {
    dedicated = local.resolved_memory
  }

  agent {
    enabled = var.qemu_agent
  }

  disk {
    datastore_id = local.resolved_datastore_id
    interface    = "scsi0"
    size         = local.resolved_disk_size_gb
    iothread     = true
    discard      = "on"
    ssd          = true
  }

  network_device {
    bridge = var.bridge
    model  = "virtio"
  }

  initialization {
    datastore_id = local.resolved_initialization_datastore_id

    user_account {
      username = var.ci_username
      keys     = var.ssh_public_keys
      password = var.ci_password
    }

    ip_config {
      ipv4 {
        address = var.ipv4_address
        gateway = var.ipv4_gateway
      }
    }
  }
}
