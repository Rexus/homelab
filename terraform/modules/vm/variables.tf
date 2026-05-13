variable "name" {
  description = "VM name."
  type        = string
}

variable "node_name" {
  description = "Proxmox node name."
  type        = string
}

variable "vm_id" {
  description = "Optional target Proxmox VM ID. Null lets Proxmox allocate one."
  type        = number
  default     = null
  nullable    = true
}

variable "template_vm_id" {
  description = "Source template VM ID."
  type        = number
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

variable "datastore_id" {
  description = "Optional datastore override for the VM disk."
  type        = string
  default     = null
  nullable    = true
}

variable "initialization_datastore_id" {
  description = "Optional datastore override for cloud-init initialization media."
  type        = string
  default     = null
  nullable    = true
}

variable "bridge" {
  description = "Network bridge."
  type        = string
}

variable "vlan_id" {
  description = "Optional VLAN ID on the selected bridge."
  type        = number
  default     = null
  nullable    = true
}

variable "storage_class_datastores" {
  description = "Mapping of storage classes to Proxmox datastore IDs."
  type = map(object({
    vm_disk          = string
    cloud_init_drive = optional(string)
  }))
  default = {
    local = {
      vm_disk = "local-lvm"
    }
    shared = {
      vm_disk = "shared"
    }
    fast = {
      vm_disk = "nvme"
    }
  }
}

variable "size" {
  description = "Logical VM size such as tiny, small, medium, large, or xl."
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

variable "sockets" {
  description = "Number of CPU sockets."
  type        = number
  default     = 1
}

variable "memory" {
  description = "Optional memory override in MB. Null uses the selected size profile."
  type        = number
  default     = null
  nullable    = true
}

variable "disk_size_gb" {
  description = "Disk size in GB for this deployment."
  type        = number
}

variable "extra_disks" {
  description = "Optional extra data disks attached to the VM."
  type = list(object({
    interface     = string
    size_gb       = number
    storage_class = optional(string)
    datastore_id  = optional(string)
    iothread      = optional(bool)
    discard       = optional(string)
    ssd           = optional(bool)
  }))
  default = []
}

variable "started" {
  description = "Whether the VM should be started."
  type        = bool
  default     = true
}

variable "template" {
  description = "Whether the VM should be converted to a Proxmox template."
  type        = bool
  default     = false
}

variable "stop_on_destroy" {
  description = "Whether to stop the VM instead of graceful shutdown on destroy."
  type        = bool
  default     = null
  nullable    = true
}

variable "qemu_agent" {
  description = "Enable QEMU guest agent."
  type        = bool
  default     = true
}

variable "ci_username" {
  description = "Cloud-init username."
  type        = string
  default     = "automation"
}

variable "ci_password" {
  description = "Optional cloud-init password. Prefer SSH keys."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "ssh_public_keys" {
  description = "SSH public keys for the cloud-init user."
  type        = list(string)
  default     = []
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

variable "tags" {
  description = "Tags applied to the VM."
  type        = list(string)
  default     = []
}
