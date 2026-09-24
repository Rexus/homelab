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
    condition     = proxmox_virtual_environment_vm.this.node_name == "pve02"
    error_message = "The initial target node must be honored."
  }

  assert {
    condition     = proxmox_virtual_environment_vm.this.clone[0].node_name == "pve01"
    error_message = "The source template node must be independent of target placement."
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
    condition     = proxmox_virtual_environment_vm.this.memory[0].dedicated == 8192
    error_message = "Ignoring placement must not ignore hardware changes."
  }
}
