variable "proxmox_api_url" {
  description = "Proxmox API endpoint; authentication may come from .env.local."
  type        = string
  default     = null
}

variable "proxmox_api_token_id" {
  type      = string
  default   = null
  sensitive = true
}

variable "proxmox_api_token_secret" {
  type      = string
  default   = null
  sensitive = true
}

# The shared deploy wrapper supplies these explicit arguments to every setup.
# Offline sessions deliberately do not consume inventory IPs or SSH configuration.
variable "ansible_inventory_path" {
  type    = string
  default = "../../../ansible/inventory/hosts.yml"
}

variable "ansible_group_vars_paths" {
  type    = list(string)
  default = []
}

variable "ceremony_hypervisor_trust_accepted" {
  description = "Explicitly accept the hypervisor and its administrators for optional VM ceremonies. Physical offline boot remains preferred for root custody."
  type        = bool
  default     = false
}

variable "ceremony_iso_path" {
  description = "Reviewed public live ISO on the controller; relative paths are relative to this Terraform deployment."
  type        = string
  validation {
    condition     = can(regex("\\.iso$", var.ceremony_iso_path)) && fileexists(var.ceremony_iso_path)
    error_message = "Select an existing reviewed local .iso file; build/fetch and accept it before provisioning sessions."
  }
}

variable "ceremony_iso_sha256" {
  description = "Independently accepted SHA256 of the exact public ISO. Never derive approval automatically from the selected file."
  type        = string
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.ceremony_iso_sha256))
    error_message = "Record the accepted 64-digit lowercase ISO SHA256."
  }
}

variable "ceremony_iso_datastore_id" {
  description = "Datastore with ISO content enabled and accessible on every selected session node."
  type        = string
}

variable "ceremony_pool_id" {
  description = "Existing dedicated pool used to scope ceremony provisioning; routine operators receive only per-VM audit/power ACLs."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]*$", var.ceremony_pool_id))
    error_message = "Select the existing dedicated ceremony resource pool."
  }
}

variable "ceremony_sessions" {
  description = "On-demand console-only sessions. USB mappings identify approved exact devices; no disk is created or formatted."
  type = map(object({
    vm_id        = number
    node_name    = string
    cores        = optional(number, 2)
    memory_mb    = optional(number, 4096)
    usb_mappings = optional(set(string), [])
  }))
  default = {}
  validation {
    condition = alltrue([for name, session in var.ceremony_sessions : (
      can(regex("^[a-z][a-z0-9-]{2,7}$", name)) &&
      session.vm_id >= 100 && session.vm_id <= 999999999 && floor(session.vm_id) == session.vm_id &&
      can(regex("^[A-Za-z0-9][A-Za-z0-9.-]*$", session.node_name)) &&
      session.cores >= 1 && session.cores <= 16 && floor(session.cores) == session.cores &&
      session.memory_mb >= 2048 && session.memory_mb <= 65536 && floor(session.memory_mb) == session.memory_mb &&
      length(session.usb_mappings) <= 5 &&
      alltrue([for mapping in session.usb_mappings : can(regex("^[A-Za-z0-9][A-Za-z0-9_-]*$", mapping))])
    )])
    error_message = "Use 3-8 character session names, valid node/VMID, 1-16 cores, 2048-65536 MiB and at most five exact Proxmox USB mappings."
  }
  validation {
    condition     = length(distinct([for session in var.ceremony_sessions : session.vm_id])) == length(var.ceremony_sessions)
    error_message = "Each ceremony session needs its own VMID."
  }
  validation {
    condition = length(flatten([for session in var.ceremony_sessions : tolist(session.usb_mappings)])) == length(
      distinct(flatten([for session in var.ceremony_sessions : tolist(session.usb_mappings)]))
    )
    error_message = "Never assign one USB mapping to multiple ceremony sessions. Detach it from its previous owner first."
  }
}
