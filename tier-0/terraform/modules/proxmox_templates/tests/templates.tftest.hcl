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
    condition     = !proxmox_virtual_environment_vm.template["talos"].agent[0].enabled
    error_message = "The QEMU agent must be opt-in for reviewed Talos schematics."
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
