variable "platform" {
  description = "Reference virtualization platform."
  type        = string
  default     = "proxmox"
}

variable "proxmox_api_url" {
  description = "Verified Proxmox API URL; prefer TF_VAR_proxmox_api_url."
  type        = string
  default     = null
}

variable "proxmox_api_token_id" {
  description = "Proxmox token ID supplied through protected local environment inputs."
  type        = string
  default     = null
  sensitive   = true
}

variable "proxmox_api_token_secret" {
  description = "Proxmox token secret supplied through protected local environment inputs."
  type        = string
  default     = null
  sensitive   = true
}

variable "ansible_inventory_path" {
  description = "Tier 0 inventory containing the independently hosted cluster_endpoint pair."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
}

variable "ansible_group_vars_paths" {
  description = "Ordered Tier 0 environment and endpoint group vars; no cross-tier inventory."
  type        = list(string)
  default = [
    "../../../ansible/group_vars/all.yml",
    "../../../ansible/group_vars/cluster_endpoint.yml",
  ]
}

variable "proxmox_storage_classes" {
  description = "Shared logical storage classes mapped to approved Proxmox datastores."
  type = map(object({
    vm_disk          = string
    cloud_init_drive = optional(string)
  }))
}

variable "default_linux_vm_template_id" {
  description = "Approved Enterprise Linux template selected from the shared catalog."
  type        = number
  default     = null
}

variable "proxmox_template_catalog" {
  description = "Approved image metadata, type-checked by this tier's environment_guests module."
  type        = any
  default     = {}
}

variable "linux_vm_template_catalog" {
  description = "Legacy local Linux template metadata, resolved by environment_guests."
  type        = any
  default     = {}
}

variable "ssh_public_key_files" {
  description = "External public-key file paths; private keys never enter Terraform."
  type        = list(string)
  default     = []
}

variable "ssh_public_keys" {
  description = "Public SSH keys for the cloud-init automation account."
  type        = list(string)
  default     = []
}

variable "shared_network_zones" {
  description = "Common network references from shared/config/platform.tfvars."
  type = map(object({
    bridge       = string
    vlan_id      = optional(number)
    cidr_ipv4    = optional(string)
    gateway_ipv4 = optional(string)
    sdn_lookup   = optional(bool, false)
  }))
  default  = {}
  nullable = false
}

variable "network_zones" {
  description = "Tier 0 network references and complete per-network overrides."
  type = map(object({
    bridge       = string
    vlan_id      = optional(number)
    cidr_ipv4    = optional(string)
    gateway_ipv4 = optional(string)
    sdn_lookup   = optional(bool, false)
  }))
  default  = {}
  nullable = false
}

variable "default_platform_node_name" {
  description = "Shared placement reference; both gateways require explicit initial host selection."
  type        = string
  default     = null
}

variable "default_vm_network_zone_key" {
  description = "Private gateway attachment in the Tier 0 network catalog."
  type        = string
  default     = "management"
}

variable "vm_instances" {
  description = "VM hardware definitions keyed by logical Ansible inventory hostname."
  type = map(object({
    proxmox_node_name = optional(string)
    vm_id             = optional(number)
    template_vm_id    = optional(number)
    full_clone        = optional(bool, true)
    firmware = optional(object({
      bios                  = optional(string, "seabios")
      machine               = optional(string)
      scsi_hardware         = optional(string, "virtio-scsi-single")
      efi_pre_enrolled_keys = optional(bool, false)
    }))
    initialization_datastore_id = optional(string)
    nic_firewall                = optional(bool, true)
    # Uses catalog tags from another template ID, useful while building templates.
    template_catalog_id = optional(number)
    # Overrides catalog tags when a VM uses a source image not in the catalog.
    template_tags = optional(list(string))
    size          = optional(string)
    cores         = optional(number)
    memory        = optional(number)
    storage_class = optional(string)
    disk_size_gb  = number
    usb_devices = optional(list(object({
      host    = optional(string)
      mapping = optional(string)
      usb3    = optional(bool, false)
    })), [])
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

  validation {
    condition = try(length(var.vm_instances) == 2 && length(toset([
      for vm in values(var.vm_instances) : trimspace(vm.proxmox_node_name)
      ])) == 2 && alltrue([
      for vm in values(var.vm_instances) : trimspace(vm.proxmox_node_name) != ""
    ]), false)
    error_message = "Select exactly two gateway VMs on distinct, explicitly named initial Proxmox hosts."
  }
}
