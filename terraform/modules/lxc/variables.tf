variable "name" {
  description = "Container name."
  type        = string
}

variable "description" {
  description = "Optional container description."
  type        = string
  default     = null
  nullable    = true
}

variable "vm_id" {
  description = "Optional target Proxmox container VMID. Null lets Proxmox allocate one."
  type        = number
  default     = null
  nullable    = true
}

variable "node_name" {
  description = "Proxmox node name."
  type        = string
}

variable "template_file_id" {
  description = "Proxmox LXC template file ID."
  type        = string
}

variable "operating_system_type" {
  description = "Operating system type for the container."
  type        = string
  default     = "unmanaged"
}

variable "storage_class" {
  description = "Logical storage class such as local, shared, or fast."
  type        = string
  default     = "local"

  validation {
    condition = contains(["local", "shared", "fast"], var.storage_class)
    error_message = "storage_class must be one of: local, shared, fast."
  }
}

variable "storage_class_datastores" {
  description = "Mapping of storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk          = string
    cloud_init_drive = optional(string)
  }))
}

variable "datastore_id" {
  description = "Optional datastore override for the container rootfs."
  type        = string
  default     = null
  nullable    = true
}

variable "bridge" {
  description = "Network bridge."
  type        = string
}

variable "size" {
  description = "Logical container size such as tiny, small, medium, large, or xl."
  type        = string
  default     = "small"

  validation {
    condition = contains(["tiny", "small", "medium", "large", "xl"], var.size)
    error_message = "size must be one of: tiny, small, medium, large, xl."
  }
}

variable "cores" {
  description = "Optional CPU override. Null uses the selected size profile."
  type        = number
  default     = null
  nullable    = true
}

variable "memory" {
  description = "Optional memory override in MB. Null uses the selected size profile."
  type        = number
  default     = null
  nullable    = true
}

variable "swap" {
  description = "Optional swap override in MB. Null uses the selected size profile."
  type        = number
  default     = null
  nullable    = true
}

variable "disk_size_gb" {
  description = "Disk size in GB for this deployment."
  type        = number
}

variable "ipv4_address" {
  description = "IPv4 address in CIDR form or dhcp."
  type        = string
  default     = "dhcp"
}

variable "ipv4_gateway" {
  description = "IPv4 gateway when using a static address."
  type        = string
  default     = null
  nullable    = true
}

variable "unprivileged" {
  description = "Run the container as unprivileged."
  type        = bool
  default     = true
}

variable "started" {
  description = "Start the container after creation."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to the container."
  type        = list(string)
  default     = []
}
