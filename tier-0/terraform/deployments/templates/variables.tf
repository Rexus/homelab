variable "catalog_file" {
  description = "Path to the Tier 0 template image catalog; independent of running-guest inventory."
  type        = string
  default     = "../../../templates/proxmox.yml"
}
