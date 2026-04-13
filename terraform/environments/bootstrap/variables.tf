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

variable "proxmox_node_name" {
  description = "Proxmox node name for instance deployments."
  type        = string
}

variable "proxmox_storage_classes" {
  description = "Mapping of logical storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk        = string
    initialization = string
  }))
}

variable "proxmox_network_bridge" {
  description = "Bridge used by deployed instances."
  type        = string
  default     = "vmbr0"
}

variable "template_vm_id_almalinux_10" {
  description = "Template VM ID for the AlmaLinux 10 baseline image."
  type        = number
}

variable "instance_name" {
  description = "Name of the instance."
  type        = string
  default     = "alma-01"
}

variable "instance_size" {
  description = "Logical size for the instance."
  type        = string
  default     = "tiny"
}

variable "instance_storage_class" {
  description = "Logical storage class for the instance."
  type        = string
  default     = "local"
}

variable "instance_disk_size_gb" {
  description = "Disk size in GB for the instance."
  type        = number
  default     = 20
}

variable "instance_ipv4_address" {
  description = "IPv4 address for the instance in CIDR form or dhcp."
  type        = string
  default     = "dhcp"
}

variable "instance_ipv4_gateway" {
  description = "IPv4 gateway for the instance when using static IP."
  type        = string
  default     = null
  nullable    = true
}

variable "instance_ssh_public_keys" {
  description = "SSH public keys injected into the instance."
  type        = list(string)
  default     = []
}

variable "management_cidr" {
  description = "Management network CIDR."
  type        = string
}

variable "workload_cidr" {
  description = "Primary workload network CIDR."
  type        = string
}

variable "edge_cidr" {
  description = "Edge or DMZ network CIDR."
  type        = string
}

variable "container_name" {
  description = "Name of the container."
  type        = string
  default     = "container-01"
}

variable "container_template_file_id" {
  description = "Proxmox LXC template file ID."
  type        = string
}

variable "container_size" {
  description = "Logical size for the container."
  type        = string
  default     = "tiny"
}

variable "container_storage_class" {
  description = "Logical storage class for the container."
  type        = string
  default     = "local"
}

variable "container_disk_size_gb" {
  description = "Disk size in GB for the container."
  type        = number
  default     = 8
}

variable "container_ipv4_address" {
  description = "IPv4 address for the container in CIDR form or dhcp."
  type        = string
  default     = "dhcp"
}

variable "container_ipv4_gateway" {
  description = "IPv4 gateway for the container when using static IP."
  type        = string
  default     = null
  nullable    = true
}
