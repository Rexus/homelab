mock_provider "proxmox" {}

variables {
  name               = "placement-test"
  node_name          = "pve02"
  template_vm_id     = 9100
  template_node_name = "pve01"
  vm_id              = 2100
  bridge             = "services"
  storage_class      = "shared"
  disk_size_gb       = 32
}

run "create_on_selected_node_from_remote_template" {
  command = apply

  assert {
    condition     = proxmox_virtual_environment_vm.this.network_device[0].firewall
    error_message = "Clones must explicitly retain NIC firewall participation instead of the provider's false default."
  }

  assert {
    condition     = proxmox_virtual_environment_vm.this.node_name == "pve02"
    error_message = "The initial target node must be honored."
  }

  assert {
    condition     = proxmox_virtual_environment_vm.this.clone[0].node_name == "pve01"
    error_message = "The source template node must be independent of target placement."
  }

  assert {
    condition     = proxmox_virtual_environment_vm.this.memory[0].floating == 0
    error_message = "Server VMs must use fixed RAM with ballooning disabled."
  }
}

run "retain_current_placement_but_manage_hardware" {
  command = plan

  variables {
    node_name = "pve03"
    memory    = 8192
  }

  assert {
    condition     = proxmox_virtual_environment_vm.this.node_name == "pve02"
    error_message = "Changing initial placement must not move an existing VM."
  }

  assert {
    condition = (
      proxmox_virtual_environment_vm.this.memory[0].dedicated == 8192 &&
      proxmox_virtual_environment_vm.this.memory[0].floating == 0
    )
    error_message = "RAM overrides must stay managed and retain disabled ballooning."
  }
}

run "explicit_firmware_and_interface_inputs_reach_the_vm" {
  command = plan

  variables {
    firmware = {
      bios                  = "ovmf"
      machine               = "q35"
      scsi_hardware         = "virtio-scsi-pci"
      efi_pre_enrolled_keys = false
    }
    initialization_datastore_id = "vm-storage"
    nic_firewall                = false
    full_clone                  = false
  }

  assert {
    condition = (
      proxmox_virtual_environment_vm.this.bios == "ovmf" &&
      proxmox_virtual_environment_vm.this.machine == "q35" &&
      proxmox_virtual_environment_vm.this.scsi_hardware == "virtio-scsi-pci" &&
      length(proxmox_virtual_environment_vm.this.efi_disk) == 1 &&
      !proxmox_virtual_environment_vm.this.efi_disk[0].pre_enrolled_keys
    )
    error_message = "An explicitly matched UEFI template must retain its firmware contract."
  }

  assert {
    condition = (
      !proxmox_virtual_environment_vm.this.clone[0].full &&
      !proxmox_virtual_environment_vm.this.network_device[0].firewall &&
      proxmox_virtual_environment_vm.this.initialization[0].datastore_id == "vm-storage" &&
      !proxmox_virtual_environment_vm.this.disk[0].iothread
    )
    error_message = "Explicit clone/NIC/media inputs must reach the resource; PCI SCSI does not support IOThread."
  }
}
