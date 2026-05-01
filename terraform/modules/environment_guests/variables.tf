variable "network_zones" {
  description = "Network zone catalog keyed by the repository reference names."
  type = map(object({
    description  = optional(string)
    bridge       = string
    vlan_id      = optional(number)
    cidr_ipv4    = optional(string)
    gateway_ipv4 = optional(string)
    notes        = optional(string)
  }))
}

variable "default_platform_node_name" {
  description = "Default platform node used when a guest does not override placement."
  type        = string
}

variable "default_vm_network_zone_key" {
  description = "Default network zone key used by VM instances when they do not override it."
  type        = string
  default     = "application"
}

variable "default_lxc_network_zone_key" {
  description = "Default network zone key used by LXC instances when they do not override it."
  type        = string
  default     = "application"
}

variable "ansible_inventory_path" {
  description = "Ansible inventory used as the source of truth for logical guest keys and groups."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
}

variable "ansible_group_vars_paths" {
  description = "Ansible group vars files merged for hostname decoration and guest IPs."
  type        = list(string)
  default     = ["../../../ansible/group_vars/all.yml"]
}

variable "vm_instances" {
  description = "VM hardware definitions keyed by logical Ansible inventory hostname."
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
  description = "LXC hardware definitions keyed by logical Ansible inventory hostname."
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
