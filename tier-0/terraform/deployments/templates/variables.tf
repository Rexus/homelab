variable "catalog_file" {
  description = "Path to the Tier 0 template image catalog; independent of running-guest inventory."
  type        = string
  default     = "../../../templates/proxmox.yml"
}

variable "proxmox_storage_classes" {
  description = "Shared platform references; an explicit catalog datastore_id overrides storage_class."
  type = map(object({
    vm_disk          = string
    cloud_init_drive = optional(string)
  }))
  default = {}
}

variable "default_platform_node_name" {
  description = "Shared initial-placement default; a catalog node_name overrides it."
  type        = string
  default     = null
}

# Accept the existing shared profile without applying guest/network settings to templates.
variable "platform" {
  type    = string
  default = "proxmox"
}

variable "shared_network_zones" {
  type    = any
  default = {}
}

variable "adopt_existing" {
  description = "Discover catalog-matching resources and include native imports in the reviewed plan."
  type        = bool
  default     = false
}
