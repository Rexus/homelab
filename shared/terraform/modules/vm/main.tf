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
    "tiny-mem" = {
      cores  = 1
      memory = 4096
    }
    small = {
      cores  = 2
      memory = 2048
    }
    "small-mem" = {
      cores  = 2
      memory = 8192
    }
    medium = {
      cores  = 2
      memory = 4096
    }
    "medium-mem" = {
      cores  = 4
      memory = 16384
    }
    large = {
      cores  = 4
      memory = 8192
    }
    "large-mem" = {
      cores  = 8
      memory = 32768
    }
    xl = {
      cores  = 8
      memory = 16384
    }
    "xl-mem" = {
      cores  = 16
      memory = 65536
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
    try(local.selected_storage.cloud_init_drive, null),
    local.selected_storage.vm_disk,
  )
  resolved_extra_disks = [
    for disk in var.extra_disks : {
      interface = disk.interface
      size_gb   = disk.size_gb
      datastore_id = coalesce(
        try(disk.datastore_id, null),
        try(
          var.storage_class_datastores[
            coalesce(try(disk.storage_class, null), var.storage_class)
          ].vm_disk,
          null,
        ),
        local.resolved_datastore_id,
      )
      iothread = coalesce(try(disk.iothread, null), true)
      discard  = coalesce(try(disk.discard, null), "on")
      ssd      = coalesce(try(disk.ssd, null), true)
    }
  ]
}

resource "proxmox_virtual_environment_vm" "this" {
  name            = var.name
  node_name       = var.node_name
  vm_id           = var.vm_id
  tags            = var.tags
  started         = var.template ? false : var.started
  template        = var.template
  stop_on_destroy = var.stop_on_destroy

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

  dynamic "disk" {
    for_each = local.resolved_extra_disks

    content {
      datastore_id = disk.value.datastore_id
      interface    = disk.value.interface
      size         = disk.value.size_gb
      iothread     = disk.value.iothread
      discard      = disk.value.discard
      ssd          = disk.value.ssd
    }
  }

  network_device {
    bridge  = var.bridge
    model   = "virtio"
    vlan_id = var.vlan_id
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
