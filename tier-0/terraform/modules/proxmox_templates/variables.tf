variable "images" {
  description = "Versioned, offline-approved Proxmox template images owned by Tier 0."
  type = map(object({
    family             = string
    release            = string
    schematic_id       = optional(string)
    vm_id              = number
    name               = string
    node_name          = string
    datastore_id       = string
    image_datastore_id = string
    image_path         = string
    sha256             = string
    bridge             = string
    vlan_id            = optional(number)
    cpu_type           = optional(string, "x86-64-v3")
    cores              = optional(number, 2)
    memory_mb          = optional(number, 4096)
    disk_size_gb       = optional(number, 32)
    qemu_agent         = optional(bool, false)
  }))

  validation {
    condition     = length(var.images) > 0
    error_message = "The template catalog must contain at least one reviewed image."
  }

  validation {
    condition = alltrue([
      for image in var.images : contains(["alma", "rocky", "talos"], image.family)
    ])
    error_message = "Supported image families are alma, rocky, and talos."
  }

  validation {
    condition = alltrue([
      for image in var.images : can(regex("^[a-f0-9]{64}$", image.sha256)) &&
      startswith(image.image_path, "/") &&
      endswith(image.image_path, image.family == "talos" ? ".raw" : ".qcow2")
    ])
    error_message = "Use an absolute local path to an unpacked raw (Talos) or qcow2 image and its SHA256."
  }

  validation {
    condition = alltrue([
      for image in var.images : image.family != "talos" || can(regex("^[a-f0-9]{64}$", image.schematic_id))
    ])
    error_message = "Talos images must record the reviewed Image Factory schematic ID."
  }

  validation {
    condition = alltrue([
      for image in var.images : can(regex("^[0-9]", image.release)) &&
      !can(regex("(?i)latest|stable", image.release)) &&
      image.vm_id >= 100 && floor(image.vm_id) == image.vm_id
    ])
    error_message = "Record an explicit release/build (starting with a digit) and an integer VMID >= 100."
  }

  validation {
    condition     = length(distinct([for image in var.images : image.vm_id])) == length(var.images)
    error_message = "Each catalog entry must have a different VMID in the target Proxmox cluster."
  }
}
