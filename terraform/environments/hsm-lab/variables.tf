variable "platform" {
  description = "Current reference platform name."
  type        = string
  default     = "proxmox"
}

variable "proxmox_api_url" {
  description = "Proxmox API endpoint. Prefer TF_VAR_proxmox_api_url at runtime."
  type        = string
  default     = null
  nullable    = true
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID. Prefer TF_VAR_proxmox_api_token_id."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API token secret. Prefer TF_VAR_proxmox_api_token_secret."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "cluster_name" {
  description = "Logical name for the environment."
  type        = string
}

variable "lab_variant" {
  description = "Whether the lab is intended for hardware-backed or software-only PKCS#11."
  type        = string
  default     = "hardware"

  validation {
    condition     = contains(["hardware", "software"], var.lab_variant)
    error_message = "lab_variant must be either hardware or software."
  }
}

variable "proxmox_storage_classes" {
  description = "Mapping of logical storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk        = string
    initialization = string
  }))
}

variable "template_vm_id_el10" {
  description = "Template VM ID for the Enterprise Linux 10 baseline image."
  type        = number
}

variable "ssh_public_keys" {
  description = "SSH public keys injected into the lab VMs."
  type        = list(string)
  default     = []
}

variable "network_zones" {
  description = "Shared network zone catalog keyed by the repository reference names."
  type = map(object({
    description  = optional(string)
    bridge       = string
    vlan_id      = optional(number)
    cidr_ipv4    = optional(string)
    gateway_ipv4 = optional(string)
    notes        = optional(string)
  }))
}

variable "default_vm_network_zone_key" {
  description = "Default network zone key used by VM guests."
  type        = string
  default     = "service"
}

variable "default_lxc_network_zone_key" {
  description = "Default network zone key used by LXC guests."
  type        = string
  default     = "service"
}

variable "vm_instances" {
  description = "VM definitions keyed by a local logical name."
  type = map(object({
    name             = string
    node_name        = string
    template_vm_id   = optional(number)
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
    ipv4_address     = optional(string)
    ipv4_gateway     = optional(string)
    role             = optional(string)
    tags             = optional(list(string))
  }))
  default = {}
}

variable "lxc_instances" {
  description = "LXC definitions keyed by a local logical name."
  type = map(object({
    name             = string
    node_name        = string
    template_file_id = string
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
    ipv4_address     = optional(string)
    ipv4_gateway     = optional(string)
    role             = optional(string)
    tags             = optional(list(string))
  }))
  default = {}
}
