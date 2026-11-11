# Provider-native PROXMOX_VE_ENDPOINT and PROXMOX_VE_API_TOKEN are supplied at runtime.
# Reference: docs/05-operations/virtual-machines/template-lifecycle.md
provider "proxmox" {
  insecure = false
}
