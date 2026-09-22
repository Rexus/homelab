# Project-owned consumer catalog. Upstream refresh never replaces this file.
# Tier 0 approves these references after clone testing; every tier reads them.
# Build inputs, checksums, credentials, and publication state stay in Tier 0.
# Loaded by shared/scripts/deploy.sh before tier-local Terraform inputs.
# Resolved by shared/terraform/modules/environment_guests, not by each tier.
# Reference: docs/platforms/proxmox/template-catalog.md

# Set this to an approved Linux entry below. Null deliberately selects no image.
default_linux_vm_template_id = null

# Keys are Proxmox VMIDs; title is the human-readable Proxmox template name.
# Keep old approved IDs while consumers use them. Do not repoint an ID at a new image.
proxmox_template_catalog = {
  # "9100" = {
  #   title     = "alma-template-build-1"
  #   node_name = "pve01"
  #   family    = "alma"
  #   tags      = ["x86_64", "cloud-init", "alma"]
  # }
  # "9101" = {
  #   title     = "rocky-template-build-1"
  #   node_name = "pve01"
  #   family    = "rocky"
  #   tags      = ["x86_64", "cloud-init", "rocky"]
  # }
  # "9102" = {
  #   title     = "talos-template-build-1"
  #   node_name = "pve01"
  #   family    = "talos"
  #   tags      = ["talos"]
  # }
}
