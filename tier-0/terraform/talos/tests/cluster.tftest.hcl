mock_provider "proxmox" {}
mock_provider "talos" {}

variables {
  inventory_path  = "tests/fixtures/hosts.yml"
  group_vars_path = "tests/fixtures/talos.yml"
  template_vm_id  = 9102
  proxmox_template_catalog = {
    "9102" = { title = "approved-talos", family = "talos", node_name = "pve-image", tags = ["talos"] }
  }
  cluster = {
    name            = "test-control", endpoint = "https://kubernetes.example.com:6443", bootstrap_node = "k8ctl-1"
    talos_version   = "v1.13.0", kubernetes_version = "1.34.0"
    installer_image = "factory.talos.dev/installer/test-schematic:v1.13.0"
    pod_cidr        = "10.244.0.0/16", service_cidr = "10.96.0.0/12"
  }
  nodes = {
    k8ctl-1 = {
      vm_id        = 300, node_name = "pve01", mac_address = "02:00:00:00:03:00"
      datastore_id = "shared", bridge = "control"
    }
    k8ctl-2 = {
      vm_id        = 301, node_name = "pve02", mac_address = "02:00:00:00:03:01"
      datastore_id = "shared", bridge = "control"
    }
    k8ctl-3 = {
      vm_id        = 302, node_name = "pve03", mac_address = "02:00:00:00:03:02"
      datastore_id = "shared", bridge = "control"
    }
    k8node-1 = {
      vm_id        = 310, node_name = "pve01", mac_address = "02:00:00:00:03:10"
      datastore_id = "shared", bridge = "control", size = "large"
    }
  }
}

run "clone_and_bootstrap_contract" {
  command = plan
  assert {
    condition = (
      length(proxmox_virtual_environment_vm.node) == 4 &&
      proxmox_virtual_environment_vm.node["k8ctl-2"].clone[0].node_name == "pve-image" &&
      proxmox_virtual_environment_vm.node["k8ctl-2"].node_name == "pve02" &&
      proxmox_virtual_environment_vm.node["k8ctl-1"].memory[0].dedicated == 4096 &&
      proxmox_virtual_environment_vm.node["k8node-1"].memory[0].dedicated == 8192
    )
    error_message = "Image source, target placement, and shared sizing data must remain distinct."
  }
  assert {
    condition = (
      talos_machine_configuration_apply.node["k8ctl-1"].node == "192.0.2.10" &&
      talos_machine_bootstrap.cluster.node == "192.0.2.10" &&
      data.talos_machine_configuration.node["k8node-1"].machine_type == "worker" &&
      data.talos_machine_configuration.node["k8ctl-2"].machine_type == "controlplane"
    )
    error_message = "Talos roles and endpoints must come from this tier's inventory."
  }
  assert {
    condition = (
      nonsensitive(yamldecode(data.talos_machine_configuration.node["k8ctl-1"].config_patches[0]).machine.install.disk) == "/dev/sda" &&
      length(proxmox_virtual_environment_vm.node["k8ctl-1"].initialization) == 0
    )
    error_message = "Talos must use its native configuration, never Linux cloud-init."
  }
}

run "reject_linux_image" {
  command = plan
  variables {
    proxmox_template_catalog = {
      "9102" = { title = "wrong-linux-image", family = "alma", node_name = "pve-image" }
    }
  }
  expect_failures = [terraform_data.configuration]
}

run "reject_unapproved_image" {
  command = plan
  variables { proxmox_template_catalog = {} }
  expect_failures = [terraform_data.configuration]
}

run "reject_invalid_reservations" {
  command = plan
  variables { group_vars_path = "tests/fixtures/invalid-ips.yml" }
  expect_failures = [terraform_data.configuration]
}

run "reject_incomplete_inventory" {
  command = plan
  variables { inventory_path = "tests/fixtures/missing-worker.yml" }
  expect_failures = [terraform_data.configuration]
}

run "reject_template_without_source" {
  command = plan
  variables {
    proxmox_template_catalog = {
      "9102" = { title = "approved-talos", family = "talos", node_name = " " }
    }
  }
  expect_failures = [terraform_data.configuration]
}
