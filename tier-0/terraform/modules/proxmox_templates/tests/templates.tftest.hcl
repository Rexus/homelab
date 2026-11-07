mock_provider "proxmox" {}

variables {
  images = {
    for index, family in ["alma", "rocky", "talos"] : family => {
      family             = family
      release            = "1.2.3-test"
      schematic_id       = family == "talos" ? sha256("test schematic") : null
      vm_id              = 9100 + index
      name               = "${family}-fixture"
      node_name          = "custody-test"
      datastore_id       = "local-lvm"
      image_datastore_id = "local"
      image_path         = abspath("tests/fixtures/template-image.${family == "talos" ? "raw" : "qcow2"}")
      sha256             = filesha256("tests/fixtures/template-image.${family == "talos" ? "raw" : "qcow2"}")
      bridge             = "custody0"
    }
  }
}

run "publish_unconfigured_templates" {
  command = plan

  assert {
    condition = alltrue([
      for vm in proxmox_virtual_environment_vm.template :
      vm.template && !vm.started && !vm.on_boot && length(vm.initialization) == 0
    ])
    error_message = "Templates must stay unbooted and contain no guest initialization or machine identity."
  }

  assert {
    condition = alltrue([
      for image in proxmox_virtual_environment_file.image :
      image.content_type == "import" && !image.overwrite && length(image.source_file[0].checksum) == 64
    ])
    error_message = "Images must be verified imports and must not overwrite existing files."
  }

  assert {
    condition     = alltrue([for vm in proxmox_virtual_environment_vm.template : vm.agent[0].enabled])
    error_message = "The publisher enables QEMU agent by default; the approved image must contain it."
  }

  assert {
    condition = alltrue([for key, vm in proxmox_virtual_environment_vm.template :
      vm.network_device[0].firewall && vm.network_device[0].mtu == 1500 &&
      vm.memory[0].dedicated == 2048 && vm.memory[0].floating == 0 &&
      vm.disk[0].size == 10 &&
      vm.scsi_hardware == (key == "talos" ? "virtio-scsi-pci" : "virtio-scsi-single") &&
      vm.disk[0].iothread == (key != "talos") && output.catalog[key].scsi_hardware == vm.scsi_hardware
    ])
    error_message = "Omitted tuning must select fixed RAM, the NIC policy and OS controller profile, including matching IO thread and output."
  }

  assert {
    condition     = output.catalog["talos"].schematic_id == sha256("test schematic")
    error_message = "The candidate catalog must retain Talos provenance."
  }

  assert {
    condition = alltrue([
      for key, image in var.images :
      output.catalog[key].vm_id == image.vm_id && output.catalog[key].title == image.name
    ])
    error_message = "Candidate references must report the actual Proxmox VMID and title."
  }
}

run "build_overrides_agent_tags_and_uploaded_filename" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      family          = key == "talos" ? "talos" : "redhat", distribution = key,
      qemu_agent      = false, tags = ["approved"],
      nic_firewall    = false, nic_mtu = 9000, scsi_hardware = "virtio-scsi-pci",
      image_file_name = "${key}-original-upload.${key == "talos" ? "raw" : "qcow2"}"
    }) }
  }
  assert {
    condition = alltrue([for key, vm in proxmox_virtual_environment_vm.template :
      !vm.agent[0].enabled && contains(vm.tags, "approved") && contains(vm.tags, key) &&
      !vm.network_device[0].firewall && vm.network_device[0].mtu == 9000 &&
      vm.scsi_hardware == "virtio-scsi-pci" && !vm.disk[0].iothread &&
      proxmox_virtual_environment_file.image[key].source_file[0].file_name == "${key}-original-upload.${key == "talos" ? "raw" : "qcow2"}"
    ])
    error_message = "Build overrides must preserve agent/NIC settings, tags and existing upload names."
  }
}

run "reject_missing_storage_class_resolution" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { datastore_id = null }) }
  }
  expect_failures = [var.images]
}

run "dhcp_nocloud_media_matches_manual_templates" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      cloud_init_drive = true, cloud_init_datastore_id = "cloudinit-storage"
    }) }
  }
  assert {
    condition = alltrue([for vm in proxmox_virtual_environment_vm.template :
      length(vm.initialization) == 1 && vm.operating_system[0].type == "l26" &&
      vm.initialization[0].interface == "ide2" && vm.initialization[0].datastore_id == "cloudinit-storage" &&
      length(vm.initialization[0].user_account) == 0 && length(vm.initialization[0].ip_config) == 1 &&
      vm.initialization[0].ip_config[0].ipv4[0].address == "dhcp"
    ])
    error_message = "Template CloudInit media must retain IPv4 DHCP; accounts and static IP belong to clones."
  }
}

run "reject_image_filename_path" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { image_file_name = "../other.qcow2" }) }
  }
  expect_failures = [var.images]
}

run "publish_uefi_image_profile" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      bios = "ovmf", machine = "q35", scsi_hardware = "virtio-scsi-pci", qemu_agent = true
    }) }
  }
  assert {
    condition = alltrue([for key, vm in proxmox_virtual_environment_vm.template :
      vm.bios == "ovmf" && vm.machine == "q35" && vm.scsi_hardware == "virtio-scsi-pci" &&
      vm.memory[0].floating == 0 && !vm.disk[0].iothread &&
      length(vm.efi_disk) == 1 && vm.efi_disk[0].type == "4m" && !vm.efi_disk[0].pre_enrolled_keys &&
      vm.efi_disk[0].datastore_id == var.images[key].datastore_id
    ])
    error_message = "UEFI templates need fixed RAM and qualified live EFI storage without pre-enrolled keys."
  }
}

run "legacy_bios_publication_is_preserved" {
  command = plan
  assert {
    condition = alltrue([for vm in proxmox_virtual_environment_vm.template :
      vm.bios == "seabios" && length(vm.efi_disk) == 0
    ])
    error_message = "Omitted firmware fields must preserve existing BIOS publications."
  }
}

run "reject_wrong_checksum" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { sha256 = sha256("different bytes") }) }
  }
  expect_failures = [proxmox_virtual_environment_file.image]
}

run "reject_missing_image" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { image_path = "/missing/${key}.${key == "talos" ? "raw" : "qcow2"}" }) }
  }
  expect_failures = [proxmox_virtual_environment_file.image]
}

run "reject_duplicate_vmids" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { vm_id = 9100 }) }
  }
  expect_failures = [var.images]
}

run "reject_unpinned_release" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { release = "latest" }) }
  }
  expect_failures = [var.images]
}

run "publish_prefixed_release_without_changing_provenance" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      release = key == "talos" ? "v1.2.3-test" : image.release
    }) }
  }
  assert {
    condition     = output.catalog["talos"].release == "v1.2.3-test"
    error_message = "A pinned v-prefixed version must remain unchanged in the candidate provenance."
  }
}

run "reject_prefixed_unpinned_release" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { release = "v1.2-stable" }) }
  }
  expect_failures = [var.images]
}

run "reject_placeholder_release" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { release = "REPLACE_WITH_EXACT_VERSION" }) }
  }
  expect_failures = [var.images]
}

run "reject_small_and_fractional_vmids" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      vm_id = key == "alma" ? 99 : (key == "rocky" ? 9101.5 : image.vm_id)
    }) }
  }
  expect_failures = [var.images]
}

run "reject_unrecorded_schematic" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { schematic_id = null }) }
  }
  expect_failures = [var.images]
}

run "reject_remote_image_source" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { image_path = "https://example.invalid/image.raw" }) }
  }
  expect_failures = [var.images]
}
