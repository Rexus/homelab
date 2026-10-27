mock_provider "proxmox" {}

variables {
  ansible_inventory_path = "../../../ansible/inventory/hosts.yml.example"
  ansible_group_vars_paths = [
    "../../../ansible/group_vars/all.yml.example",
    "../../../ansible/group_vars/cluster_endpoint.yml.example",
  ]
  proxmox_api_url              = "https://pve.invalid:8006/"
  proxmox_api_token_id         = "test@pve!offline"
  proxmox_api_token_secret     = "disposable-fixture"
  default_linux_vm_template_id = 9100
  proxmox_template_catalog = {
    "9100" = { title = "approved-linux", family = "alma", node_name = "pve-image", tags = ["linux"] }
  }
  proxmox_storage_classes = { local = { vm_disk = "local-lvm" } }
  network_zones = {
    management = { bridge = "vmbr0", vlan_id = 10, cidr_ipv4 = "10.10.10.0/24", gateway_ipv4 = "10.10.10.1" }
  }
  vm_instances = {
    api-gw-1 = { proxmox_node_name = "pve01", vm_id = 270, disk_size_gb = 20 }
    api-gw-2 = { proxmox_node_name = "pve02", vm_id = 271, disk_size_gb = 20 }
  }
}

run "independent_gateway_pair" {
  command = plan

  assert {
    condition = (
      length(module.vms) == 2 &&
      module.vms["api-gw-1"].node_name == "pve01" &&
      module.vms["api-gw-2"].node_name == "pve02" &&
      module.environment.vm_instances["api-gw-1"].ipv4_address == "10.10.10.60/24" &&
      module.environment.vm_instances["api-gw-2"].ipv4_address == "10.10.10.61/24" &&
      module.environment.vm_instances["api-gw-1"].template_node_name == "pve-image"
    )
    error_message = "The two native VMs must retain independent placement and tier-owned inventory addresses."
  }
}

run "reject_shared_physical_host" {
  command = plan
  variables {
    vm_instances = {
      api-gw-1 = { proxmox_node_name = "pve01", vm_id = 270, disk_size_gb = 20 }
      api-gw-2 = { proxmox_node_name = "pve01", vm_id = 271, disk_size_gb = 20 }
    }
  }
  expect_failures = [var.vm_instances]
}

run "reject_unowned_inventory_host" {
  command = plan
  variables {
    vm_instances = {
      api-gw-1 = { proxmox_node_name = "pve01", vm_id = 270, disk_size_gb = 20 }
      idm-1    = { proxmox_node_name = "pve02", vm_id = 271, disk_size_gb = 20 }
    }
    ansible_group_vars_paths = [
      "../../../ansible/group_vars/all.yml.example",
      "tests/fixtures/mixed-group-vars.yml",
    ]
  }
  expect_failures = [terraform_data.gateway_contract]
}
