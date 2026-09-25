resource "proxmox_virtual_environment_vm" "node" {
  for_each      = local.machines
  depends_on    = [terraform_data.configuration]
  name          = each.key
  vm_id         = each.value.vm_id
  node_name     = each.value.node_name
  tags          = distinct(concat(try(local.template.tags, []), ["tier-0", "talos", each.value.role]))
  started       = true
  on_boot       = true
  bios          = "seabios"
  boot_order    = ["scsi0"]
  scsi_hardware = "virtio-scsi-single"

  clone {
    vm_id     = var.template_vm_id
    node_name = try(local.template.node_name, null)
    full      = true
  }
  cpu {
    cores = each.value.cores
    type  = var.cpu_type
  }
  memory {
    dedicated = each.value.memory
  }
  agent {
    enabled = var.qemu_agent
  }
  disk {
    datastore_id = each.value.datastore_id
    interface    = "scsi0"
    size         = each.value.disk_size_gb
    iothread     = true
    discard      = "on"
  }
  network_device {
    bridge      = each.value.bridge
    vlan_id     = each.value.vlan_id
    model       = "virtio"
    mac_address = each.value.mac_address
  }

  # No cloud-init, SSH account, or Ansible guest baseline is applied to Talos.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [node_name]
  }
}

resource "talos_machine_secrets" "cluster" {
  depends_on    = [terraform_data.configuration]
  talos_version = var.cluster.talos_version
  lifecycle {
    prevent_destroy = true
  }
}

data "talos_machine_configuration" "node" {
  for_each           = local.machines
  cluster_name       = var.cluster.name
  cluster_endpoint   = var.cluster.endpoint
  machine_type       = each.value.role
  machine_secrets    = talos_machine_secrets.cluster.machine_secrets
  talos_version      = var.cluster.talos_version
  kubernetes_version = var.cluster.kubernetes_version
  config_patches = [yamlencode({
    machine = {
      install = { disk = "/dev/sda", image = var.cluster.installer_image }
      network = { hostname = each.key }
    }
    cluster = {
      network = {
        podSubnets     = [var.cluster.pod_cidr]
        serviceSubnets = [var.cluster.service_cidr]
      }
    }
  })]
}

resource "talos_machine_configuration_apply" "node" {
  for_each                    = local.machines
  depends_on                  = [proxmox_virtual_environment_vm.node]
  node                        = each.value.ip
  endpoint                    = each.value.ip
  client_configuration        = talos_machine_secrets.cluster.client_configuration
  machine_configuration_input = data.talos_machine_configuration.node[each.key].machine_configuration
  # Bootstrap mode; review reboot-requiring updates separately, not as a parallel rollout.
  apply_mode = "auto"
  timeouts   = { create = "20m", update = "20m" }
}

resource "talos_machine_bootstrap" "cluster" {
  depends_on           = [talos_machine_configuration_apply.node]
  node                 = try(local.host_ips[var.cluster.bootstrap_node], "")
  client_configuration = talos_machine_secrets.cluster.client_configuration
  lifecycle {
    prevent_destroy = true
  }
}

data "talos_client_configuration" "cluster" {
  cluster_name         = var.cluster.name
  client_configuration = talos_machine_secrets.cluster.client_configuration
  endpoints            = [for name in sort(tolist(local.control_planes)) : local.host_ips[name]]
  nodes                = [for name in sort(tolist(local.control_planes)) : local.host_ips[name]]
}

resource "talos_cluster_kubeconfig" "cluster" {
  depends_on           = [talos_machine_bootstrap.cluster]
  node                 = local.host_ips[var.cluster.bootstrap_node]
  client_configuration = talos_machine_secrets.cluster.client_configuration
}
