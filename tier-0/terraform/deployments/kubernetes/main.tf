# Resolve this tier's inputs here; machines.tf owns VM and cluster resources.
# Current implementation: Talos on Proxmox. Replacing the OS requires a separate lifecycle design.
# Reference: docs/reference/infrastructure-automation-layout.md#terraform-structure
locals {
  inventory      = yamldecode(file(var.inventory_path)).all.children
  control_planes = toset(keys(try(local.inventory.talos_control_plane.hosts, {})))
  workers        = toset(keys(try(local.inventory.talos_workers.hosts, {})))
  host_ips       = yamldecode(file(var.group_vars_path)).platform_host_ips
  # These are reference data, not shared Terraform modules or shared host inventory.
  sizes    = jsondecode(file("${path.module}/../../../../shared/config/guest-sizes.json")).vm
  template = try(var.proxmox_template_catalog[tostring(var.template_vm_id)], null)
  machines = {
    for name, node in var.nodes : name => merge(node, {
      role   = contains(local.control_planes, name) ? "controlplane" : "worker"
      ip     = try(local.host_ips[name], "")
      cores  = coalesce(node.cores, try(local.sizes[node.size].cores, 0))
      memory = coalesce(node.memory, try(local.sizes[node.size].memory, 0))
    })
  }
}

# Block invalid or incomplete inventory before either provider can create resources.
resource "terraform_data" "configuration" {
  input = var.cluster.name
  lifecycle {
    precondition {
      condition = (
        setunion(local.control_planes, local.workers) == toset(keys(var.nodes)) &&
        length(setintersection(local.control_planes, local.workers)) == 0 &&
        contains([1, 3, 5], length(local.control_planes)) && length(local.workers) > 0 &&
        contains(local.control_planes, var.cluster.bootstrap_node)
      )
      error_message = "Talos inventory must match nodes exactly, with 1/3/5 control planes, workers, and a control-plane bootstrap_node."
    }
    precondition {
      condition = (
        alltrue([for node in local.machines : can(cidrnetmask("${node.ip}/32"))]) &&
        length(distinct([for node in local.machines : node.ip])) == length(var.nodes)
      )
      error_message = "Every Talos node needs a unique IPv4 DHCP reservation in the tier-local platform_host_ips map."
    }
    precondition {
      condition = try(local.template.family == "talos" && length(trimspace(local.template.node_name)) > 0 &&
      length(trimspace(local.template.title)) > 0, false)
      error_message = "Select an approved Talos template with title and source node in the shared consumer catalog."
    }
    precondition {
      condition     = alltrue([for node in var.nodes : node.vm_id != var.template_vm_id])
      error_message = "Cluster VMIDs must not reuse the template VMID."
    }
    precondition {
      condition     = alltrue([for node in local.machines : node.cores >= 2 && node.memory >= 4096])
      error_message = "Talos nodes require a known size profile or explicit sizing of at least 2 cores and 4096 MiB."
    }
  }
}
