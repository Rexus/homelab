terraform {
  required_version = ">= 1.6.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = ">= 0.66.0"
    }
  }
}

# Prefer environment variables for sensitive provider authentication, for example:
# - TF_VAR_proxmox_api_url
# - TF_VAR_proxmox_api_token_id
# - TF_VAR_proxmox_api_token_secret
# See: ../../../docs/reference/environment-variables.md
provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true
}

locals {
  common_tags = [
    var.cluster_name,
    "terraform",
    "almalinux-10",
  ]
}

module "instance" {
  source = "../../modules/vm"

  name                     = var.instance_name
  node_name                = var.proxmox_node_name
  template_vm_id           = var.template_vm_id_almalinux_10
  storage_class            = var.instance_storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.proxmox_network_bridge
  size                     = var.instance_size
  disk_size_gb             = var.instance_disk_size_gb
  ipv4_address             = var.instance_ipv4_address
  ipv4_gateway             = var.instance_ipv4_gateway
  ssh_public_keys          = var.instance_ssh_public_keys
  tags                     = local.common_tags
}

module "container" {
  source = "../../modules/lxc"

  name                     = var.container_name
  node_name                = var.proxmox_node_name
  template_file_id         = var.container_template_file_id
  storage_class            = var.container_storage_class
  storage_class_datastores = var.proxmox_storage_classes
  bridge                   = var.proxmox_network_bridge
  size                     = var.container_size
  disk_size_gb             = var.container_disk_size_gb
  ipv4_address             = var.container_ipv4_address
  ipv4_gateway             = var.container_ipv4_gateway
  tags                     = local.common_tags
}
