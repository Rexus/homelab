terraform {
  required_providers {
    proxmox = {
      source = "bpg/proxmox"
    }
  }
}

locals {
  # Shared supplies size profiles; resources and state belong to this tier.
  size_profiles = jsondecode(file("${path.module}/../../../../shared/config/guest-sizes.json")).vm

  selected_size         = local.size_profiles[var.size]
  selected_storage      = lookup(var.storage_class_datastores, var.storage_class, null)
  resolved_cores        = coalesce(var.cores, local.selected_size.cores)
  resolved_memory       = coalesce(var.memory, local.selected_size.memory)
  resolved_disk_size_gb = var.disk_size_gb
  resolved_datastore_id = (
    var.datastore_id != null && var.datastore_id != "" ? var.datastore_id : local.selected_storage.vm_disk
  )
  resolved_initialization_datastore_id = coalesce(
    var.initialization_datastore_id,
    try(local.selected_storage.cloud_init_drive, null),
    local.resolved_datastore_id,
  )
  resolved_extra_disks = [
    for disk in var.extra_disks : {
      interface = disk.interface
      size_gb   = disk.size_gb
      datastore_id = disk.datastore_id != null && disk.datastore_id != "" ? disk.datastore_id : (
        disk.storage_class == null || disk.storage_class == "" ? local.resolved_datastore_id :
        try(var.storage_class_datastores[disk.storage_class].vm_disk, null)
      )
      iothread = coalesce(
        try(disk.iothread, null),
        try(var.firmware.scsi_hardware, "virtio-scsi-single") == "virtio-scsi-single",
      )
      discard = coalesce(try(disk.discard, null), "on")
      ssd     = coalesce(try(disk.ssd, null), true)
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
  bios            = try(var.firmware.bios, null)
  machine         = try(var.firmware.machine, null)
  scsi_hardware   = try(var.firmware.scsi_hardware, null)
  boot_order      = var.firmware == null ? null : ["scsi0"]

  clone {
    vm_id     = var.template_vm_id
    node_name = var.template_node_name
    full      = var.full_clone
  }

  dynamic "efi_disk" {
    for_each = try(var.firmware.bios, "seabios") == "ovmf" ? [true] : []
    content {
      datastore_id      = local.resolved_datastore_id
      type              = "4m"
      pre_enrolled_keys = var.firmware.efi_pre_enrolled_keys
    }
  }

  # Placement after creation belongs to Proxmox, including HA failover and maintenance.
  lifecycle {
    ignore_changes = [node_name]

    precondition {
      condition = alltrue([
        for disk in var.extra_disks : disk.datastore_id != null && disk.datastore_id != "" ? true : (
          disk.storage_class == null || disk.storage_class == "" ? true :
          contains(keys(var.storage_class_datastores), disk.storage_class)
        )
      ])
      error_message = "Each extra disk must select an existing storage class, an explicit datastore_id, or inherit the VM datastore."
    }
  }

  cpu {
    cores   = local.resolved_cores
    sockets = var.sockets
    type    = "x86-64-v3"
  }

  memory {
    dedicated = local.resolved_memory
    floating  = 0
  }

  agent {
    enabled = var.qemu_agent
  }

  disk {
    datastore_id = local.resolved_datastore_id
    interface    = "scsi0"
    size         = local.resolved_disk_size_gb
    iothread     = try(var.firmware.scsi_hardware, "virtio-scsi-single") == "virtio-scsi-single"
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
    bridge   = var.bridge
    model    = "virtio"
    vlan_id  = var.vlan_id
    firewall = var.nic_firewall
  }

  dynamic "usb" {
    for_each = var.usb_devices

    content {
      host    = usb.value.host
      mapping = usb.value.mapping
      usb3    = usb.value.usb3
    }
  }

  initialization {
    datastore_id = local.resolved_initialization_datastore_id

    user_account {
      username = var.ci_username
      keys = distinct(concat(var.ssh_public_keys, [
        for path in var.ssh_public_key_files : trimspace(file(pathexpand(path)))
      ]))
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
