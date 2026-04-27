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

variable "proxmox_node_name" {
  description = "Legacy single-node deployment variable for older bootstrap inputs."
  type        = string
  default     = null
  nullable    = true
}

variable "proxmox_storage_classes" {
  description = "Mapping of logical storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk        = string
    initialization = string
  }))
}

variable "proxmox_network_bridge" {
  description = "Legacy bridge used by deployed guests when shared network_zones are not set."
  type        = string
  default     = "vmbr0"
}

variable "template_vm_id_el10" {
  description = "Template VM ID for the Enterprise Linux 10 baseline image."
  type        = number
  default     = null
  nullable    = true
}

variable "template_vm_id_almalinux_10" {
  description = "Legacy alias for the Enterprise Linux 10 template VM ID."
  type        = number
  default     = null
  nullable    = true
}

variable "instance_name" {
  description = "Legacy single VM name."
  type        = string
  default     = "el10-01"
}

variable "instance_size" {
  description = "Legacy single VM logical size."
  type        = string
  default     = "tiny"
}

variable "instance_storage_class" {
  description = "Legacy single VM storage class."
  type        = string
  default     = "local"
}

variable "instance_disk_size_gb" {
  description = "Legacy single VM disk size in GB."
  type        = number
  default     = 20
}

variable "instance_ipv4_address" {
  description = "Legacy single VM IPv4 address in CIDR form or dhcp."
  type        = string
  default     = "dhcp"
}

variable "instance_ipv4_gateway" {
  description = "Legacy single VM IPv4 gateway when using a static address."
  type        = string
  default     = null
  nullable    = true
}

variable "ssh_public_keys" {
  description = "Shared SSH public keys injected into VM guests."
  type        = list(string)
  default     = []
}

variable "instance_ssh_public_keys" {
  description = "Legacy single VM SSH public keys."
  type        = list(string)
  default     = []
}

variable "management_cidr" {
  description = "Legacy management network CIDR."
  type        = string
  default     = null
  nullable    = true
}

variable "workload_cidr" {
  description = "Legacy primary application network CIDR."
  type        = string
  default     = null
  nullable    = true
}

variable "edge_cidr" {
  description = "Legacy edge or DMZ network CIDR."
  type        = string
  default     = null
  nullable    = true
}

variable "container_name" {
  description = "Legacy single container name."
  type        = string
  default     = "container-01"
}

variable "container_template_file_id" {
  description = "Legacy single container template file ID."
  type        = string
  default     = null
  nullable    = true
}

variable "container_size" {
  description = "Legacy single container logical size."
  type        = string
  default     = "tiny"
}

variable "container_storage_class" {
  description = "Legacy single container storage class."
  type        = string
  default     = "local"
}

variable "container_disk_size_gb" {
  description = "Legacy single container disk size in GB."
  type        = number
  default     = 8
}

variable "container_ipv4_address" {
  description = "Legacy single container IPv4 address in CIDR form or dhcp."
  type        = string
  default     = "dhcp"
}

variable "container_ipv4_gateway" {
  description = "Legacy single container IPv4 gateway when using a static address."
  type        = string
  default     = null
  nullable    = true
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
  default  = null
  nullable = true
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
  description = "Shared VM definitions keyed by a local logical name."
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
  description = "Shared LXC definitions keyed by a local logical name."
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
