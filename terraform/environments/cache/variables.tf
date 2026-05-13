variable "platform" {
  description = "Current reference platform implementation. Defaults to proxmox."
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
  description = "Deprecated compatibility value. Do not use for Proxmox tags."
  type        = string
  default     = null
  nullable    = true
}

variable "ansible_inventory_path" {
  description = "Ansible inventory with logical guest keys and groups."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
}

variable "ansible_group_vars_paths" {
  description = "Ansible group vars files merged for hostname decoration and guest IPs."
  type        = list(string)
  default     = ["../../../ansible/group_vars/all.yml"]
}

variable "proxmox_storage_classes" {
  description = "Mapping of logical storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk          = string
    cloud_init_drive = optional(string)
  }))
}

variable "default_linux_vm_template_id" {
  description = "Default Linux cloud-init template VM ID."
  type        = number
}

variable "linux_vm_template_catalog" {
  description = "Template metadata catalog keyed by Proxmox template VM ID."
  type = map(object({
    description = optional(string)
    tags        = list(string)
  }))
  default = {}
}

variable "ssh_public_keys" {
  description = "Shared SSH public keys injected into VM guests."
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

variable "default_platform_node_name" {
  description = "Default platform node used when a guest does not override placement."
  type        = string
  default     = null
  nullable    = true
}

variable "default_proxmox_node_name" {
  description = "Deprecated. Use default_platform_node_name."
  type        = string
  default     = null
  nullable    = true
}

variable "default_vm_network_zone_key" {
  description = "Default network zone key used by VM guests."
  type        = string
  default     = "external_edge"
}

variable "default_lxc_network_zone_key" {
  description = "Default network zone key used by LXC guests."
  type        = string
  default     = "external_edge"
}

variable "vm_instances" {
  description = "VM hardware definitions keyed by logical Ansible inventory hostname."
  type = map(object({
    proxmox_node_name = optional(string)
    vm_id             = optional(number)
    template_vm_id   = optional(number)
    template_catalog_id = optional(number)
    template_tags       = optional(list(string))
    size             = optional(string)
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
