mock_provider "proxmox" {}

variables {
  name             = "network-test"
  node_name        = "pve01"
  template_file_id = "local:vztmpl/test.tar.zst"
  bridge           = "vmbr0"
  disk_size_gb     = 8
  storage_class_datastores = {
    local = { vm_disk = "local-lvm" }
  }
}

run "tagged_bridge" {
  command = plan

  variables {
    vlan_id = 420
  }

  assert {
    condition     = proxmox_virtual_environment_container.this.network_interface[0].vlan_id == 420
    error_message = "The selected VLAN must reach the container NIC."
  }
}

run "untagged_vnet" {
  command = plan

  variables {
    bridge = "lab"
  }

  assert {
    condition     = proxmox_virtual_environment_container.this.network_interface[0].bridge == "lab"
    error_message = "The selected VNet must be retained."
  }

  assert {
    condition     = coalesce(proxmox_virtual_environment_container.this.network_interface[0].vlan_id, 0) == 0
    error_message = "An omitted VLAN must not add another tag to an SDN VNet."
  }
}
