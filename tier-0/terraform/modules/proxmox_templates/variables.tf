variable "images" {
  description = "Versioned, offline-approved Proxmox template images owned by Tier 0."
  type = map(object({
    family                  = string
    distribution            = optional(string)
    os_type                 = optional(string)
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
    bridge                  = optional(string, "vmbr0")
    vlan_id                 = optional(number)
    nic_firewall            = optional(bool, true)
    nic_mtu                 = optional(number, 1500)
    cpu_type                = optional(string, "x86-64-v3")
    cores                   = optional(number, 2)
    memory_mb               = optional(number, 2048)
    disk_size_gb            = optional(number, 10)
    qemu_agent              = optional(bool, true)
    tags                    = optional(list(string), [])
    cloud_init_drive        = optional(bool, false)
    cloud_init_datastore_id = optional(string)
    # Omitted values retain existing BIOS publications; select UEFI for new image revisions.
    bios                  = optional(string, "seabios")
    machine               = optional(string)
    scsi_hardware         = optional(string)
    efi_pre_enrolled_keys = optional(bool, false)
    tpm_version           = optional(string)
  }))

  validation {
    condition = alltrue([
      for image in var.images : contains(["seabios", "ovmf"], image.bios) &&
      (image.scsi_hardware == null ? true : contains([
        "virtio-scsi-single", "virtio-scsi-pci", "lsi", "lsi53c810", "megasas", "pvscsi"
      ], image.scsi_hardware))
    ])
    error_message = "Select seabios/ovmf and a Proxmox SCSI controller: virtio-scsi-single, virtio-scsi-pci, lsi, lsi53c810, megasas or pvscsi."
  }

  validation {
    condition     = length(var.images) > 0
    error_message = "The template catalog must contain at least one reviewed image."
  }

  validation {
    condition = alltrue([
      for image in var.images : contains([
        "redhat", "rhel", "debian", "suse", "archlinux", "alpine", "gentoo",
        "slackware", "nixos", "void", "linux", "talos", "windows", "other",
        "alma", "rocky"
      ], image.family)
    ])
    error_message = "Use redhat/rhel, debian, suse, archlinux, alpine, gentoo, slackware, nixos, void, linux, talos, windows or other; alma/rocky remain accepted for older catalogs. Use linux for another Linux family, or other for a non-Linux guest."
  }

  validation {
    condition = alltrue([
      for image in var.images : image.distribution == null ? true :
      can(regex("(?i)^[a-z0-9][a-z0-9._-]*$", image.distribution))
    ])
    error_message = "distribution is an open-ended identifier, such as rocky, ubuntu, opensuse, windows-server or other; use letters, digits, dots, underscores and hyphens. Tags normalize it to lowercase."
  }

  validation {
    condition = alltrue([
      for image in var.images : image.os_type == null ? true : contains([
        "l24", "l26", "other", "solaris", "w2k", "w2k3", "w2k8",
        "win7", "win8", "win10", "win11", "wvista", "wxp"
        ], image.os_type) && (image.family == "other" || (
        image.family == "windows" ? can(regex("^w", image.os_type)) :
        contains(["l24", "l26"], image.os_type)
      ))
    ])
    error_message = "os_type must be a supported Proxmox guest type matching the family: l24/l26 for Linux, a Windows type such as win10/win11 for windows, or an explicit guest type for other."
  }

  validation {
    condition = alltrue([
      for image in var.images : (image.tpm_version == null ? true :
      contains(["v1.2", "v2.0"], image.tpm_version)) &&
      (!image.efi_pre_enrolled_keys || image.bios == "ovmf")
    ])
    error_message = "tpm_version must be v1.2 or v2.0 when selected; efi_pre_enrolled_keys requires bios: ovmf."
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
      can(regex("[.](raw|qcow2)$", image.image_path)) &&
      (image.family != "talos" || endswith(image.image_path, ".raw"))
    ])
    error_message = "Use an absolute local path to an unpacked raw or qcow2 image and its SHA256; Talos requires raw."
  }

  validation {
    condition = alltrue([
      for image in var.images : image.family != "talos" || can(regex("^[a-f0-9]{64}$", image.schematic_id))
    ])
    error_message = "Talos images must record the reviewed Image Factory schematic ID."
  }

  validation {
    condition = alltrue([
      for image in var.images : can(regex("^v?[0-9]", image.release)) &&
      !can(regex("(?i)latest|stable", image.release))
    ])
    error_message = format(
      "Invalid release: %s. Use an exact version/build starting with a digit or v followed by a digit; placeholders and latest/stable aliases are not allowed.",
      join(", ", [for key, image in var.images : format("%s.release=%s", key, jsonencode(image.release))
        if !(can(regex("^v?[0-9]", image.release)) && !can(regex("(?i)latest|stable", image.release)))
      ])
    )
  }

  validation {
    condition = alltrue([
      for image in var.images : image.vm_id >= 100 && floor(image.vm_id) == image.vm_id
    ])
    error_message = format(
      "Invalid vm_id: %s. Use an integer VMID >= 100, matching the existing template when adopting it.",
      join(", ", [for key, image in var.images : format("%s.vm_id=%s", key, jsonencode(image.vm_id))
        if !(image.vm_id >= 100 && floor(image.vm_id) == image.vm_id)
      ])
    )
  }

  validation {
    condition     = length(distinct([for image in var.images : image.vm_id])) == length(var.images)
    error_message = "Each catalog entry must have a different VMID in the target Proxmox cluster."
  }

  validation {
    condition = length(distinct([for image in var.images : jsonencode([
      image.node_name, image.image_datastore_id,
      coalesce(image.image_file_name, "${image.vm_id}-${image.sha256}.${endswith(image.image_path, ".raw") ? "raw" : "qcow2"}")
    ])])) == length(var.images)
    error_message = "Each uploaded file must have one resource owner; do not reuse the same node/datastore/image_file_name."
  }
}
