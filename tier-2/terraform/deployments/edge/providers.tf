# Prefer environment variables for sensitive provider authentication, for example:
# - TF_VAR_proxmox_api_url
# - TF_VAR_proxmox_api_token_id
# - TF_VAR_proxmox_api_token_secret
# Reference: docs/reference/environment-variables.md
provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token_secret}"
  insecure  = true
}
