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
      memory = 512
      swap   = 512
    }
    small = {
      cores  = 1
      memory = 1024
      swap   = 512
    }
    medium = {
      cores  = 2
      memory = 2048
      swap   = 1024
    }
    large = {
      cores  = 4
      memory = 4096
      swap   = 1024
    }
    xl = {
      cores  = 8
      memory = 8192
      swap   = 2048
    }
  }

  selected_size = local.size_profiles[var.size]
  selected_storage = var.storage_class_datastores[var.storage_class]
  resolved_cores = coalesce(var.cores, local.selected_size.cores)
  resolved_memory = coalesce(var.memory, local.selected_size.memory)
  resolved_swap = coalesce(var.swap, local.selected_size.swap)
  resolved_datastore_id = coalesce(var.datastore_id, local.selected_storage.vm_disk)
}

resource "proxmox_virtual_environment_container" "this" {
  node_name    = var.node_name
  description  = var.description
  tags         = var.tags
  unprivileged = var.unprivileged
  started      = var.started

  operating_system {
    template_file_id = var.template_file_id
    type             = var.operating_system_type
  }

  cpu {
    cores = local.resolved_cores
  }

  memory {
    dedicated = local.resolved_memory
    swap      = local.resolved_swap
  }

  disk {
    datastore_id = local.resolved_datastore_id
    size         = var.disk_size_gb
  }

  network_interface {
    name   = "eth0"
    bridge = var.bridge
  }

  initialization {
    hostname = var.name

    ip_config {
      ipv4 {
        address = var.ipv4_address
        gateway = var.ipv4_gateway
      }
    }
  }
}
