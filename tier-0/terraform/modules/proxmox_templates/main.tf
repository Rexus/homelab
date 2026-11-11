terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.112.0"
    }
  }
}

locals {
  distributions  = { for key, image in var.images : key => lower(coalesce(image.distribution, image.family)) }
  major_versions = { for key, image in var.images : key => try(regex("^v?([0-9]+)", image.release)[0], "") }
  os_types = { for key, image in var.images : key => coalesce(
    image.os_type, image.family == "windows" ? "win11" : (image.family == "other" ? "other" : "l26")
  ) }
  image_file_names = { for key, image in var.images : key => coalesce(
    image.image_file_name,
    "${image.vm_id}-${image.sha256}.${endswith(image.image_path, ".raw") ? "raw" : "qcow2"}"
  ) }
  # Enterprise Linux shares a major track; Fedora/Ubuntu keep their independent release numbers.
  release_tracks = { for key, image in var.images : key => format("%s%s",
    contains(["redhat", "rhel", "alma", "rocky"], image.family) &&
    contains(["alma", "almalinux", "rocky", "rhel", "centos", "centos-stream", "oraclelinux"], local.distributions[key])
    ? "el" : local.distributions[key], local.major_versions[key]
  ) }
  template_tags = { for key, image in var.images : key => sort(distinct(concat(compact([
    local.release_tracks[key], local.distributions[key],
    lower(image.cpu_type),
    image.cloud_init_drive ? "cloud-init" : null,
  ]), image.tags))) }

  # Talos uses the non-Single controller; other images default to Single unless overridden.
  scsi_hardware = { for key, image in var.images : key => coalesce(
    image.scsi_hardware, image.family == "talos" ? "virtio-scsi-pci" : "virtio-scsi-single"
  ) }
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
    file_name = local.image_file_names[each.key]
  }

  lifecycle {
    prevent_destroy = true
    # Upload metadata is write-once and absent after import; never re-upload an adopted artifact.
    # New revisions need a new catalog key/VMID, not an in-place source change.
    ignore_changes = [source_file]
    precondition {
      condition     = try(filesha256(each.value.image_path) == each.value.sha256, false)
      error_message = "The approved local image is missing or its SHA256 does not match the catalog."
    }
    postcondition {
      condition     = self.file_name == local.image_file_names[each.key]
      error_message = "The existing image filename differs from the catalog. Preserve its exact name or publish a new revision."
    }
  }
}

resource "proxmox_virtual_environment_vm" "template" {
  for_each      = var.images
  name          = each.value.name
  node_name     = each.value.node_name
  vm_id         = each.value.vm_id
  description   = "${each.value.family} ${each.value.release}; sha256=${each.value.sha256}"
  tags          = local.template_tags[each.key]
  template      = true
  started       = false
  on_boot       = false
  bios          = each.value.bios
  machine       = each.value.machine
  scsi_hardware = local.scsi_hardware[each.key]
  boot_order    = ["scsi0"]

  cpu {
    # Leave architecture implicit; setting it explicitly requires root@pam on Proxmox.
    type  = each.value.cpu_type
    cores = each.value.cores
  }

  memory {
    dedicated = each.value.memory_mb
    floating  = 0
  }

  dynamic "efi_disk" {
    for_each = each.value.bios == "ovmf" ? [true] : []
    content {
      datastore_id      = each.value.datastore_id
      type              = "4m"
      pre_enrolled_keys = each.value.efi_pre_enrolled_keys
    }
  }

  dynamic "tpm_state" {
    for_each = each.value.tpm_version == null ? [] : [each.value.tpm_version]
    content {
      datastore_id = each.value.datastore_id
      version      = tpm_state.value
    }
  }

  agent {
    enabled = each.value.qemu_agent
  }

  disk {
    datastore_id = each.value.datastore_id
    import_from  = proxmox_virtual_environment_file.image[each.key].id
    interface    = "scsi0"
    size         = each.value.disk_size_gb
    iothread     = local.scsi_hardware[each.key] == "virtio-scsi-single"
    discard      = "on"
  }

  network_device {
    bridge   = each.value.bridge
    vlan_id  = each.value.vlan_id
    firewall = each.value.nic_firewall
    mtu      = each.value.nic_mtu
    model    = "virtio"
  }

  dynamic "initialization" {
    for_each = each.value.cloud_init_drive ? [true] : []
    content {
      datastore_id = coalesce(each.value.cloud_init_datastore_id, each.value.datastore_id)
      interface    = "ide2"
      # Proxmox defaults to NoCloud for Linux and ConfigDrive2 for Windows.
      # Preserve the computed format: making an implicit type explicit forces replacement.
      ip_config {
        ipv4 {
          address = "dhcp"
        }
      }
    }
  }

  operating_system {
    type = local.os_types[each.key]
  }

  serial_device {}

  # DHCP is reusable template policy; identities and static networking belong to clones.
  lifecycle {
    prevent_destroy = true
  }
}
