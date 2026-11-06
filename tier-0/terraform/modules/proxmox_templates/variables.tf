variable "images" {
  description = "Versioned, offline-approved Proxmox template images owned by Tier 0."
  type = map(object({
    family                  = string
    distribution            = optional(string)
    release                 = string
    schematic_id            = optional(string)
    vm_id                   = number
    name                    = string
    node_name               = string
    datastore_id            = string
    image_datastore_id      = string
    image_path              = string
    image_file_name         = optional(string)
    sha256                  = string
    bridge                  = string
    vlan_id                 = optional(number)
    cpu_type                = optional(string, "x86-64-v3")
    cores                   = optional(number, 2)
    memory_mb               = optional(number, 4096)
    disk_size_gb            = optional(number, 32)
    qemu_agent              = optional(bool, true)
    tags                    = optional(list(string), [])
    cloud_init_drive        = optional(bool, false)
    cloud_init_datastore_id = optional(string)
    # Omitted values retain existing BIOS publications; select UEFI for new image revisions.
    bios          = optional(string, "seabios")
    machine       = optional(string)
    scsi_hardware = optional(string, "virtio-scsi-single")
  }))

  validation {
    condition = alltrue([
      for image in var.images : contains(["seabios", "ovmf"], image.bios) &&
      contains(["virtio-scsi-single", "virtio-scsi-pci"], image.scsi_hardware)
    ])
    error_message = "Select seabios/ovmf and virtio-scsi-single/virtio-scsi-pci for the approved image."
  }

  validation {
    condition     = length(var.images) > 0
    error_message = "The template catalog must contain at least one reviewed image."
  }

  validation {
    condition = alltrue([
      for image in var.images : contains(["redhat", "debian", "talos", "alma", "rocky"], image.family)
    ])
    error_message = "Use redhat, debian or talos as OS family; alma/rocky remain accepted for older catalogs."
  }

  validation {
    condition = alltrue([for image in var.images :
      image.datastore_id != null && image.node_name != null &&
      (image.image_file_name == null ? true : can(regex("^[A-Za-z0-9][A-Za-z0-9._-]*\\.(raw|qcow2)$", image.image_file_name)))
    ])
    error_message = "Resolve live storage_class/datastore_id and node_name; image_file_name must be a raw/qcow2 basename without paths."
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

  validation {
    condition = length(distinct([for image in var.images : jsonencode([
      image.node_name, image.image_datastore_id,
      coalesce(image.image_file_name, "${image.vm_id}-${image.sha256}.${image.family == "talos" ? "raw" : "qcow2"}")
    ])])) == length(var.images)
    error_message = "Each uploaded file must have one resource owner; do not reuse the same node/datastore/image_file_name."
  }
}
