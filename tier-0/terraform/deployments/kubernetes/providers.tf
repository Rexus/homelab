# Provider-native PROXMOX_VE_* credentials stay outside configuration and state inputs.
provider "proxmox" {
  insecure = false
}
provider "talos" {}
