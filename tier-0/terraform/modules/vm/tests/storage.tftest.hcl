mock_provider "proxmox" {}

variables {
  name           = "storage-test"
  node_name      = "pve01"
  template_vm_id = 9101
  bridge         = "services"
  storage_class  = "shared"
  disk_size_gb   = 32
}

run "explicit_datastores_bypass_unused_classes" {
  command = plan

  variables {
    datastore_id             = "base-override"
    storage_class_datastores = {}
    extra_disks = [{
      interface     = "scsi1"
      size_gb       = 64
      datastore_id  = "data-override"
      storage_class = "unused-class"
    }]
  }

  assert {
    condition = (
      one([for disk in proxmox_virtual_environment_vm.this.disk :
      disk.datastore_id if disk.interface == "scsi0"]) == "base-override" &&
      one([for disk in proxmox_virtual_environment_vm.this.disk :
      disk.datastore_id if disk.interface == "scsi1"]) == "data-override" &&
      proxmox_virtual_environment_vm.this.initialization[0].datastore_id == "base-override"
    )
    error_message = "Explicit VM/data datastores must work with empty class maps and unused class references."
  }
}

run "extra_disks_inherit_the_explicit_vm_datastore_without_a_class_map" {
  command = plan

  variables {
    datastore_id             = "base-override"
    storage_class_datastores = {}
    extra_disks              = [{ interface = "scsi1", size_gb = 64 }]
  }

  assert {
    condition = (
      alltrue([for disk in proxmox_virtual_environment_vm.this.disk : disk.datastore_id == "base-override"]) &&
      proxmox_virtual_environment_vm.this.initialization[0].datastore_id == "base-override"
    )
    error_message = "Omitted data-disk classes and media must inherit the explicit VM datastore."
  }
}

run "omitted_extra_class_inherits_vm_override_while_media_keeps_its_class" {
  command = plan

  variables {
    datastore_id = "base-override"
    storage_class_datastores = {
      shared = { vm_disk = "class-vm-store", cloud_init_drive = "class-media-store" }
    }
    extra_disks = [{ interface = "scsi1", size_gb = 64 }]
  }

  assert {
    condition = (
      one([for disk in proxmox_virtual_environment_vm.this.disk :
      disk.datastore_id if disk.interface == "scsi1"]) == "base-override" &&
      proxmox_virtual_environment_vm.this.initialization[0].datastore_id == "class-media-store"
    )
    error_message = "Data disks inherit the VM datastore; a class media destination remains separate."
  }
}

run "empty_legacy_overrides_inherit_the_vm_datastore" {
  command = plan

  variables {
    datastore_id = ""
    extra_disks  = [{ interface = "scsi1", size_gb = 64, datastore_id = "", storage_class = "" }]
  }

  assert {
    condition     = alltrue([for disk in proxmox_virtual_environment_vm.this.disk : disk.datastore_id == "shared"])
    error_message = "Legacy empty overrides must act as unset values and inherit the selected VM datastore."
  }
}

run "explicit_extra_class_selects_its_datastore" {
  command = plan

  variables {
    extra_disks = [{ interface = "scsi1", size_gb = 64, storage_class = "fast" }]
  }

  assert {
    condition = one([for disk in proxmox_virtual_environment_vm.this.disk :
    disk.datastore_id if disk.interface == "scsi1"]) == "nvme"
    error_message = "A selected data-disk class must resolve to its own datastore."
  }
}

run "unknown_extra_class_cannot_fall_back_to_vm_storage" {
  command = plan

  variables {
    extra_disks = [{ interface = "scsi1", size_gb = 64, storage_class = "unknown-class" }]
  }

  expect_failures = [proxmox_virtual_environment_vm.this]
}
