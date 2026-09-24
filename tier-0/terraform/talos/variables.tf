variable "inventory_path" {
  description = "Tier 0 logical hosts; no inventory is read from shared."
  type        = string
  default     = "../../ansible/inventory/hosts.yml"
}

variable "group_vars_path" {
  description = "Tier 0 Talos IP reservations. Values must be plain YAML, not encrypted/Jinja."
  type        = string
  default     = "../../ansible/group_vars/talos.yml"
}

variable "cluster" {
  description = "Cluster bootstrap contract. Retain these pins and secrets for this cluster's lifetime."
  type = object({
    name               = string
    endpoint           = string
    bootstrap_node     = string
    talos_version      = string
    kubernetes_version = string
    installer_image    = string
    pod_cidr           = string
    service_cidr       = string
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

variable "nodes" {
  description = "Tier-owned VM hardware keyed by Talos inventory hostname; MACs must have DHCP reservations."
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
}

variable "template_vm_id" {
  description = "An approved Talos image from the shared catalog; never a Linux cloud-init image."
  type        = number
}

variable "proxmox_template_catalog" {
  description = "Shared approved image references only; templates and cluster resources belong to Tier 0."
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
