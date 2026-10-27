variable "inventory_path" {
  description = "Tier-local logical hosts; no inventory is read from shared."
  type        = string
  default     = "../../../ansible/inventory/hosts.yml"
}

variable "group_vars_path" {
  description = "Tier-local Talos IP reservations. Values must be plain YAML, not encrypted/Jinja."
  type        = string
  default     = "../../../ansible/group_vars/talos.yml"
}

variable "cluster" {
  description = "Cluster bootstrap contract. Retain these pins and secrets for this cluster's lifetime."
  type = object({
    name                               = string
    endpoint                           = string
    bootstrap_node                     = string
    talos_version                      = string
    kubernetes_version                 = string
    installer_image                    = string
    pod_cidr                           = string
    service_cidr                       = string
    allow_scheduling_on_control_planes = optional(bool, false)
  })
  validation {
    condition = (
      can(regex("^[a-z0-9][a-z0-9-]*$", var.cluster.name)) &&
      can(regex("^https://[^/]+:6443$", var.cluster.endpoint)) &&
      can(regex("^v[0-9]+\\.[0-9]+\\.[0-9]+$", var.cluster.talos_version)) &&
      can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.cluster.kubernetes_version)) &&
      can(regex(":v[0-9]+\\.[0-9]+\\.[0-9]+(@sha256:[a-f0-9]{64})?$", var.cluster.installer_image)) &&
      endswith(split("@", var.cluster.installer_image)[0], ":${var.cluster.talos_version}") &&
      can(cidrnetmask(var.cluster.pod_cidr)) && can(cidrnetmask(var.cluster.service_cidr))
    )
    error_message = "Set a DNS-safe name, HTTPS API endpoint on 6443, exact release pins, installer tag, and IPv4 CIDRs."
  }
}

variable "machine_config_patches" {
  description = "Ordered native Talos YAML/JSON patches applied after the base configuration on every node."
  type        = list(string)
  default     = []
  sensitive   = true
  validation {
    condition     = alltrue([for patch in var.machine_config_patches : length(trimspace(patch)) > 0])
    error_message = "Machine configuration patches must not be empty; use [] for the unmodified base configuration."
  }
}

variable "nodes" {
  description = "Tier-owned VM hardware keyed by Talos inventory hostname; reserve unique MACs and inventory IPs."
  type = map(object({
    vm_id        = number
    node_name    = string
    mac_address  = string
    datastore_id = string
    bridge       = string
    vlan_id      = optional(number)
    size         = optional(string, "medium")
    cores        = optional(number)
    memory       = optional(number)
    disk_size_gb = optional(number, 40)
    # Scheduling metadata only; not a security boundary or an autoscaler.
    pool = optional(string)
  }))
  validation {
    condition = (
      length(var.nodes) > 1 &&
      length(distinct([for node in var.nodes : node.vm_id])) == length(var.nodes) &&
      length(distinct([for node in var.nodes : lower(node.mac_address)])) == length(var.nodes) &&
      alltrue([for name, node in var.nodes :
        can(regex("^[a-z0-9][a-z0-9-]*$", name)) &&
        can(regex("^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", node.mac_address)) &&
        node.vm_id >= 100 && node.vm_id == floor(node.vm_id) && node.disk_size_gb >= 32
      ])
    )
    error_message = "Nodes need unique integer VMIDs and MACs, DNS-safe names, and disks of at least 32 GiB."
  }
  validation {
    condition = alltrue([for node in var.nodes : node.pool == null ? true :
      length(node.pool) <= 63 && can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", node.pool))
    ])
    error_message = "Pool names must be lowercase label values of 1-63 characters, using letters, digits, and internal hyphens."
  }
}

variable "template_vm_id" {
  description = "An approved Talos image from the shared catalog; never a Linux cloud-init image."
  type        = number
}

variable "proxmox_template_catalog" {
  description = "Shared approved image references only; Tier 0 owns templates, this tier owns cluster resources."
  type = map(object({
    title     = string
    family    = string
    node_name = optional(string)
    tags      = optional(list(string), [])
  }))
  default = {}
}

variable "default_linux_vm_template_id" {
  description = "Accepted from the common image catalog; not used by this Talos root."
  type        = number
  default     = null
}

variable "cpu_type" {
  description = "CPU baseline compatible with the approved template and every eligible Proxmox host."
  type        = string
  default     = "x86-64-v3"
}

variable "qemu_agent" {
  description = "Enable only when the approved Talos schematic includes the QEMU guest-agent extension."
  type        = bool
  default     = false
}

variable "bootstrap_network" {
  description = "NoCloud network-only drive for static inventory IPs. Null preserves the existing DHCP bootstrap path."
  type = object({
    prefix_length = number
    gateway       = string
    dns_servers   = optional(list(string), [])
  })
  default = null
  validation {
    condition = var.bootstrap_network == null ? true : (
      var.bootstrap_network.prefix_length >= 1 && var.bootstrap_network.prefix_length <= 30 &&
      floor(var.bootstrap_network.prefix_length) == var.bootstrap_network.prefix_length &&
      can(cidrnetmask("${var.bootstrap_network.gateway}/32")) &&
      alltrue([for server in var.bootstrap_network.dns_servers : can(cidrnetmask("${server}/32"))])
    )
    error_message = "Static bootstrap needs an integer prefix 1-30, an IPv4 gateway and valid optional DNS addresses."
  }
}

variable "vm_firmware" {
  description = "Match the approved template. Omission preserves legacy BIOS clusters; UEFI is explicit for new clusters."
  type = object({
    bios          = optional(string, "seabios")
    machine       = optional(string)
    scsi_hardware = optional(string, "virtio-scsi-single")
  })
  default = {}
  validation {
    condition = (contains(["seabios", "ovmf"], var.vm_firmware.bios) &&
    contains(["virtio-scsi-single", "virtio-scsi-pci"], var.vm_firmware.scsi_hardware))
    error_message = "Select seabios/ovmf and virtio-scsi-single/virtio-scsi-pci to match the template."
  }
}
