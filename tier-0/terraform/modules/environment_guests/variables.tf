variable "network_zones" {
  description = "Guest network catalog keyed by repository reference names."
  type = map(object({
    bridge       = string
    vlan_id      = optional(number)
    cidr_ipv4    = string
    gateway_ipv4 = optional(string)
  }))
}

variable "default_platform_node_name" {
  description = "Default initial VM placement or LXC target node when a guest does not override it."
  type        = string
}

variable "default_vm_template_id" {
  description = "Approved Linux template ID supplied by the shared catalog or a tier override."
  type        = number
  default     = null
}

variable "proxmox_template_catalog" {
  description = "Shared approved template references. Tier 0 owns promotion; this module resolves consumer metadata."
  type = map(object({
    title     = string
    node_name = optional(string)
    family    = string
    tags      = optional(list(string), [])
  }))
  default = {}
}

variable "linux_vm_template_catalog" {
  description = "Legacy tier-local metadata overrides. Migrate common entries to the shared proxmox_template_catalog."
  type = map(object({
    description = optional(string)
    node_name   = optional(string)
    tags        = list(string)
  }))
  default = {}
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
    vm_id             = optional(number)
    template_vm_id   = optional(number)
    # Uses catalog tags from another template ID, useful while building templates.
    template_catalog_id = optional(number)
    # Overrides catalog tags when a VM uses a source image not in the catalog.
    template_tags      = optional(list(string))
    size             = optional(string)
    cores            = optional(number)
    memory           = optional(number)
    storage_class    = optional(string)
    disk_size_gb     = number
    extra_disks = optional(list(object({
      interface     = string
      size_gb       = number
      storage_class = optional(string)
      datastore_id  = optional(string)
      iothread      = optional(bool)
      discard       = optional(string)
      ssd           = optional(bool)
    })))
    network_zone_key = optional(string)
    started          = optional(bool)
    template         = optional(bool)
    stop_on_destroy  = optional(bool)
    tags             = optional(list(string))
  }))
  default = {}
}

variable "lxc_instances" {
  description = "LXC hardware definitions keyed by logical Ansible inventory hostname."
  type = map(object({
    proxmox_node_name = optional(string)
    vm_id             = optional(number)
    template_file_id = string
    size             = optional(string)
    storage_class    = optional(string)
    disk_size_gb     = number
    network_zone_key = optional(string)
    tags             = optional(list(string))
  }))
  default = {}
}
