variable "template_vm_id_el10" {
  description = "Default template VM ID for the Enterprise Linux 10 baseline image."
  type        = number
}

variable "proxmox_storage_classes" {
  description = "Mapping of logical storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk        = string
    initialization = string
  }))
}

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

variable "ssh_public_keys" {
  description = "SSH public keys injected into VMs."
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Tags applied to every guest in the environment."
  type        = list(string)
  default     = []
}

variable "ansible_inventory_path" {
  description = "Ansible inventory used as the source of truth for host identity and IPs."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
}

variable "vm_instances" {
  description = "VM hardware definitions keyed by Ansible inventory host."
  type = map(object({
    node_name        = string
    template_vm_id   = optional(number)
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
  }))
  default = {}
}

variable "lxc_instances" {
  description = "LXC hardware definitions keyed by Ansible inventory host."
  type = map(object({
    node_name        = string
    template_file_id = string
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
  }))
  default = {}
}
