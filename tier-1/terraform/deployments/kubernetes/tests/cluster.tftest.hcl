mock_provider "proxmox" {}
mock_provider "talos" {}

# Only local secrets/configuration generation uses the real provider below.
# All VM and remote Talos operations remain mocked or explicitly overridden.
provider "talos" {
  alias = "native"
}

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
      datastore_id = "shared", bridge = "control", size = "large", pool = "compute"
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
  assert {
    condition = (
      nonsensitive(yamldecode(data.talos_machine_configuration.node["k8node-1"].config_patches[0]).machine.nodeLabels["node-pool"]) == "compute" &&
      !nonsensitive(yamldecode(data.talos_machine_configuration.node["k8ctl-1"].config_patches[0]).cluster.allowSchedulingOnControlPlanes)
    )
    error_message = "Pool labels must reach node configuration; existing configs must retain disabled control-plane scheduling."
  }
}

run "compact_control_planes" {
  command = plan
  variables {
    inventory_path = "tests/fixtures/missing-worker.yml"
    cluster = {
      name                               = "test-compact", endpoint = "https://kubernetes.example.com:6443", bootstrap_node = "k8ctl-1"
      talos_version                      = "v1.13.0", kubernetes_version = "1.34.0"
      installer_image                    = "factory.talos.dev/installer/test-schematic:v1.13.0"
      pod_cidr                           = "10.244.0.0/16", service_cidr = "10.96.0.0/12"
      allow_scheduling_on_control_planes = true
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
    }
  }
  assert {
    condition = length(proxmox_virtual_environment_vm.node) == 3 && nonsensitive(
      yamldecode(data.talos_machine_configuration.node["k8ctl-1"].config_patches[0]).cluster.allowSchedulingOnControlPlanes
    )
    error_message = "The compact starter must schedule workloads on its three control planes without workers."
  }
}

run "reject_unschedulable_compact_cluster" {
  command = plan
  variables {
    inventory_path = "tests/fixtures/missing-worker.yml"
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
    }
  }
  expect_failures = [terraform_data.configuration]
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

run "native_restricted_network_configuration" {
  command = apply
  providers = {
    proxmox = proxmox
    talos   = talos.native
  }
  # Never contact nodes: only the provider's local key/config generators run.
  override_resource { target = talos_machine_configuration_apply.node }
  override_resource { target = talos_machine_bootstrap.cluster }
  override_resource { target = talos_cluster_kubeconfig.cluster }
  variables {
    machine_config_patches = [yamlencode({
      machine = {
        env = {
          http_proxy  = "http://cache.example.com:3128"
          https_proxy = "http://cache.example.com:3128"
          no_proxy    = "127.0.0.1,localhost,192.0.2.0/24,10.244.0.0/16,10.96.0.0/12,.example.com,.svc,.cluster.local"
        }
        network = { nameservers = ["192.0.2.53"] }
        time    = { servers = ["192.0.2.123"] }
      }
      }), yamlencode({
      apiVersion   = "v1alpha1"
      kind         = "RegistryMirrorConfig"
      name         = "registry.k8s.io"
      endpoints    = [{ url = "https://registry.example.com" }]
      skipFallback = true
    })]
  }
  # tests/test_tier_kubernetes_config.py checks the native multi-document output.
}

run "reject_empty_machine_patch" {
  command = plan
  variables { machine_config_patches = [" "] }
  expect_failures = [var.machine_config_patches]
}
