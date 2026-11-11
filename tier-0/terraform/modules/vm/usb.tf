# Native bpg USB attachment; existing callers retain an empty attachment list.
variable "usb_devices" {
  description = "Approved host USB ports/IDs or existing Proxmox resource mappings; not device replication."
  type = list(object({
    host    = optional(string)
    mapping = optional(string)
    usb3    = optional(bool, false)
  }))
  default  = []
  nullable = false

  validation {
    condition = alltrue([
      for device in var.usb_devices :
      (device.host != null) != (device.mapping != null)
      && (device.host == null ? true : can(regex(
        "^([0-9]+-[0-9]+(\\.[0-9]+)*|[a-fA-F0-9]{4}:[a-fA-F0-9]{4})$", device.host
      )))
      && (device.mapping == null ? true : can(regex("^[a-zA-Z0-9][a-zA-Z0-9_-]*$", device.mapping)))
    ])
    error_message = "Each USB device needs exactly one nonempty host bus-port/vendor:product ID or Proxmox mapping."
  }
}
