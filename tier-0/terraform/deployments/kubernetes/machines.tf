resource "proxmox_virtual_environment_vm" "node" {
  for_each      = local.machines
  depends_on    = [terraform_data.configuration]
  name          = each.key
  vm_id         = each.value.vm_id
  node_name     = each.value.node_name
  tags          = distinct(concat(try(local.template.tags, []), ["tier-0", "talos", each.value.role]))
  started       = true
  on_boot       = true
  bios          = var.vm_firmware.bios
  machine       = var.vm_firmware.machine
  boot_order    = ["scsi0"]
  scsi_hardware = var.vm_firmware.scsi_hardware

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
    floating  = 0
  }
  dynamic "efi_disk" {
    for_each = var.vm_firmware.bios == "ovmf" ? [true] : []
    content {
      datastore_id      = each.value.datastore_id
      type              = "4m"
      pre_enrolled_keys = false
    }
  }
  agent {
    enabled = var.qemu_agent
    # Addresses come from inventory; do not wait for a pre-configuration agent IP lookup.
    wait_for_ip { disabled = true }
  }
  dynamic "initialization" {
    for_each = var.bootstrap_network == null ? [] : [var.bootstrap_network]
    content {
      type         = "nocloud"
      interface    = "ide2"
      datastore_id = each.value.datastore_id
      dynamic "dns" {
        for_each = length(initialization.value.dns_servers) > 0 ? [initialization.value.dns_servers] : []
        content { servers = dns.value }
      }
      ip_config {
        ipv4 {
          address = "${each.value.ip}/${initialization.value.prefix_length}"
          gateway = initialization.value.gateway
        }
      }
    }
  }
  disk {
    datastore_id = each.value.datastore_id
    interface    = "scsi0"
    size         = each.value.disk_size_gb
    iothread     = var.vm_firmware.scsi_hardware == "virtio-scsi-single"
    discard      = "on"
  }
  network_device {
    bridge      = each.value.bridge
    vlan_id     = each.value.vlan_id
    model       = "virtio"
    mac_address = each.value.mac_address
  }

  # NoCloud carries networking only; Talos API owns machine config, not Linux users or Ansible.
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
  # Native patches keep proxy, DNS/time and mirror policy in this cluster's inputs.
  config_patches = concat([yamlencode({
    machine = {
      install    = { disk = "/dev/sda", image = var.cluster.installer_image }
      nodeLabels = each.value.pool == null ? {} : { "node-pool" = each.value.pool }
    }
    cluster = {
      allowSchedulingOnControlPlanes = var.cluster.allow_scheduling_on_control_planes
      network = {
        podSubnets     = [var.cluster.pod_cidr]
        serviceSubnets = [var.cluster.service_cidr]
      }
    }
    }), yamlencode({
    apiVersion = "v1alpha1"
    kind       = "HostnameConfig"
    hostname   = each.key
    # Disable the generated automatic hostname without a conflicting legacy field.
    auto = "off"
  })], var.machine_config_patches)
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
