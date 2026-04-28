variable "platform" {
  description = "Current reference platform name."
  type        = string
  default     = "proxmox"
}

variable "proxmox_api_url" {
  description = "Proxmox endpoint for bpg/proxmox, such as https://pve.example.com:8006/."
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

variable "ansible_inventory_path" {
  description = "Ansible inventory used as the source of truth for guest IPs."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
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

variable "default_proxmox_node_name" {
  description = "Default Proxmox node used when a guest does not override placement."
  type        = string
}

variable "default_vm_network_zone_key" {
  description = "Default network zone key used by VM guests."
  type        = string
  default     = "application"
}

variable "default_lxc_network_zone_key" {
  description = "Default network zone key used by LXC guests."
  type        = string
  default     = "application"
}

variable "vm_instances" {
  description = "VM hardware definitions keyed by hostname and Proxmox VM name."
  type = map(object({
    proxmox_node_name = optional(string)
    template_vm_id   = optional(number)
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
    tags             = optional(list(string))
  }))
  default = {}
}

variable "lxc_instances" {
  description = "LXC hardware definitions keyed by hostname and Proxmox VM name."
  type = map(object({
    proxmox_node_name = optional(string)
    template_file_id = string
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
    tags             = optional(list(string))
  }))
  default = {}
}
