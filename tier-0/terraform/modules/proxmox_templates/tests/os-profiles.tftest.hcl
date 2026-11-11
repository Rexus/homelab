mock_provider "proxmox" {}

variables {
  images = { for index, family in [
    "redhat", "rhel", "debian", "suse", "archlinux", "alpine", "gentoo",
    "slackware", "nixos", "void", "linux", "talos", "windows", "other"
    ] : family => {
    family             = family
    distribution       = family == "other" ? "other" : "${family}-derivative"
    release            = "2026.11.01"
    schematic_id       = family == "talos" ? sha256("test schematic") : null
    vm_id              = 9300 + index
    name               = "${family}-fixture"
    node_name          = "pve01"
    datastore_id       = "ceph-vm"
    image_datastore_id = "cephfs"
    image_path         = abspath("tests/fixtures/template-image.${family == "talos" ? "raw" : "qcow2"}")
    sha256             = filesha256("tests/fixtures/template-image.${family == "talos" ? "raw" : "qcow2"}")
    cloud_init_drive   = true
  } }
}

run "publish_linux_families_windows_and_other" {
  command = plan
  assert {
    condition = alltrue([for key, vm in proxmox_virtual_environment_vm.template :
      vm.operating_system[0].type == (key == "windows" ? "win11" : (key == "other" ? "other" : "l26")) &&
      output.catalog[key].os_type == vm.operating_system[0].type &&
      output.catalog[key].family == var.images[key].family &&
      output.catalog[key].distribution == var.images[key].distribution &&
      vm.template && !vm.started && vm.memory[0].floating == 0 &&
      length(vm.initialization[0].user_account) == 0 && length(vm.tpm_state) == 0
    ])
    error_message = "OS classification must reach the guest type and catalog without booting or adding identities/TPMs."
  }
}

run "raw_images_keep_their_format_for_linux_and_windows" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      image_path = abspath("tests/fixtures/template-image.raw")
      sha256     = filesha256("tests/fixtures/template-image.raw")
    }) }
  }
  assert {
    condition = alltrue([for key, file in proxmox_virtual_environment_file.image :
      file.source_file[0].file_name == "${var.images[key].vm_id}-${var.images[key].sha256}.raw"
    ])
    error_message = "Upload names must reflect raw source bytes for every family, not only Talos."
  }
}

run "windows_firmware_tpm_and_older_guest_override" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      os_type               = key == "windows" ? "win10" : null
      bios                  = key == "windows" ? "ovmf" : "seabios"
      machine               = key == "windows" ? "q35" : null
      efi_pre_enrolled_keys = key == "windows"
      tpm_version           = key == "windows" ? "v2.0" : null
    }) }
  }
  assert {
    condition = (
      proxmox_virtual_environment_vm.template["windows"].operating_system[0].type == "win10" &&
      proxmox_virtual_environment_vm.template["windows"].efi_disk[0].pre_enrolled_keys &&
      proxmox_virtual_environment_vm.template["windows"].tpm_state[0].version == "v2.0" &&
      proxmox_virtual_environment_vm.template["windows"].tpm_state[0].datastore_id == "ceph-vm" &&
      proxmox_virtual_environment_vm.template["windows"].machine == "q35" &&
      alltrue([for key, vm in proxmox_virtual_environment_vm.template :
        length(vm.efi_disk) == 0 && length(vm.tpm_state) == 0 if key != "windows"
      ])
    )
    error_message = "Windows overrides must configure the selected guest/firmware/TPM without changing Linux defaults."
  }
}

run "unlisted_distribution_and_other_guest_override" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      distribution = key == "other" ? "freebsd" : (key == "alpine" ? "Alpine" : "new-derivative")
      os_type      = key == "other" ? "other" : null
    }) }
  }
  assert {
    condition = (
      contains(proxmox_virtual_environment_vm.template["other"].tags, "freebsd") &&
      contains(proxmox_virtual_environment_vm.template["alpine"].tags, "alpine") &&
      contains(proxmox_virtual_environment_vm.template["suse"].tags, "new-derivative")
    )
    error_message = "Distribution identifiers must remain open-ended and generate image tags."
  }
}

run "reject_windows_guest_type_for_linux" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      os_type = key == "debian" ? "win11" : null
    }) }
  }
  expect_failures = [var.images]
}

run "reject_linux_guest_type_for_windows" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      os_type = key == "windows" ? "l26" : null
    }) }
  }
  expect_failures = [var.images]
}

run "reject_distribution_that_cannot_be_a_tag" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      distribution = key == "other" ? "bad;injected-tag" : image.distribution
    }) }
  }
  expect_failures = [var.images]
}

run "reject_efi_key_enrollment_without_uefi" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { efi_pre_enrolled_keys = true }) }
  }
  expect_failures = [var.images]
}
