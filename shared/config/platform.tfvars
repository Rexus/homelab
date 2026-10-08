# Project-owned references to existing Proxmox infrastructure, not resources.
# Configure once; every Linux deployment loads this before tier-local overrides.
# Only references used across tiers belong here; no hosts, resources, credentials, or keys.
# Guide: docs/reference/platform-inputs.md

platform = "proxmox"

# Set the default initial VM placement or LXC target; deployments can override it.
default_platform_node_name = null

# Existing network shared by multiple tiers. Selection and guest IPs stay tier-local.
# Tier network_zones entries override this map by network name, not by individual field.
shared_network_zones = {
  application = {
    bridge       = "app"
    vlan_id      = null
    cidr_ipv4    = "10.20.20.0/24"
    gateway_ipv4 = "10.20.20.1"
  }
}

proxmox_storage_classes = {
  local = {
    vm_disk = "local-lvm-change-me"
  }
  shared = {
    vm_disk = "shared-change-me"
  }
  fast = {
    vm_disk = "nvme-change-me"
    # Omit cloud_init_drive to use vm_disk for the cloud-init disk as well.
    cloud_init_drive = "local-lvm-change-me"
  }
}
