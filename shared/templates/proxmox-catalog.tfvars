# Project-owned consumer catalog. Upstream refresh never replaces this file.
# Tier 0 apply refreshes published references here; every tier reads them.
# Clone-test before selecting a default or per-VM template ID. Apply preserves that selection.
# Build inputs, checksums, credentials, and publication state stay in Tier 0.
# Loaded by shared/scripts/deploy.sh before tier-local Terraform inputs.
# Resolved by each tier's Terraform; shared owns no Terraform resources or host inventory.
# Reference: docs/reference/template-catalog.md
# VMID allocation: docs/conventions/vmid-convention.md

# Set this to an approved Linux entry below. Null deliberately selects no image.
default_linux_vm_template_id = null

# Keys are Proxmox VMIDs; title is the human-readable Proxmox template name.
# Keep old approved IDs while consumers use them. Do not repoint an ID at a new image.
# family describes the OS family; distribution-specific consumer metadata stays in title/tags.
# ID, title, node, family and image tags are refreshed from applied template_candidates.
# Earlier entries remain until deliberately retired; template creation stays Tier 0-owned.
proxmox_template_catalog = {
  # "9103" = {
  #   title     = "debian-template-build-1"
  #   node_name = "pve01"
  #   family    = "debian"
  #   tags      = ["debian12", "debian", "x86-64-v3", "cloud-init"]
  # }
  # "9100" = {
  #   title     = "alma-template-build-1"
  #   node_name = "pve01"
  #   family    = "redhat"
  #   tags      = ["el10", "alma", "x86-64-v3", "cloud-init"]
  # }
  # "9101" = {
  #   title     = "rocky-template-build-1"
  #   node_name = "pve01"
  #   family    = "redhat"
  #   tags      = ["el10", "rocky", "x86-64-v3", "cloud-init"]
  # }
  # "9102" = {
  #   title     = "talos-template-build-1"
  #   node_name = "pve01"
  #   family    = "talos"
  #   tags      = ["talos1", "talos", "x86-64-v3", "cloud-init"]
  # }
  # Optional immutable-template target; approve its own metadata after clone testing.
  # "9200" = {
  #   title     = "rhel-10-immu-tmpl"
  #   node_name = "pve01"
  #   family    = "redhat"
  #   tags      = ["el10", "rhel", "x86-64-v3", "cloud-init"]
  # }
}
