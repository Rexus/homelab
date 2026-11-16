resource "proxmox_virtual_environment_vm" "node" {
  for_each      = local.machines
  depends_on    = [terraform_data.configuration]
  name          = each.key
  vm_id         = each.value.vm_id
  node_name     = each.value.node_name
  tags          = distinct(concat(try(local.template.tags, []), ["tier-1", "talos", each.value.role]))
  started       = true
  on_boot       = true
  bios          = var.vm_firmware.bios
  machine       = var.vm_firmware.machine
  # Keep the drive and boot order stable so media changes stay hot-swappable.
  boot_order    = var.secure_boot == null ? ["scsi0"] : ["scsi0", "ide0"]
  scsi_hardware = var.vm_firmware.scsi_hardware

  dynamic "clone" {
    for_each = var.secure_boot == null ? [true] : []
    content {
      vm_id     = var.template_vm_id
      node_name = try(local.template.node_name, null)
      full      = true
    }
  }
  dynamic "cdrom" {
    for_each = var.secure_boot == null ? [] : [true]
    content {
      interface = "ide0"
      file_id = !var.secure_boot.install_media_attached ? "none" : proxmox_virtual_environment_file.secure_boot_iso[
        local.secure_boot_shared ? sort(tolist(local.secure_boot_nodes))[0] : each.value.node_name
      ].id
    }
  }
  dynamic "tpm_state" {
    for_each = var.secure_boot == null ? [] : [true]
    content {
      datastore_id = each.value.datastore_id
      version      = "v2.0"
    }
  }
  dynamic "operating_system" {
    for_each = var.secure_boot == null ? [] : [true]
    content { type = "l26" }
  }
  dynamic "serial_device" {
    for_each = var.secure_boot == null ? [] : [true]
    content { device = "socket" }
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
    for_each = local.effective_bootstrap_network == null ? [] : [local.effective_bootstrap_network]
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
    firewall    = true
  }

  # NoCloud carries networking only; Talos API owns machine config, not Linux users or Ansible.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [node_name, efi_disk, tpm_state]
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
  })], var.machine_config_patches, local.secure_boot_installer_patches, local.secure_boot_volume_patches)
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
