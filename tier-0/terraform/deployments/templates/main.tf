locals {
  catalog = yamldecode(file(var.catalog_file))
  # A build replaces only the common fields it supplies; nested values are not deep-merged.
  builds = { for key, image in local.catalog.templates : key => merge(try(local.catalog.all, {}), image) }
  images = { for key, image in local.builds : key => merge(image, {
    datastore_id = try(coalesce(
      try(image.datastore_id, null),
      try(var.proxmox_storage_classes[image.storage_class].vm_disk, null)
    ), null)
    node_name = try(coalesce(try(image.node_name, null), var.default_platform_node_name), null)
    cloud_init_datastore_id = try(coalesce(
      try(image.cloud_init_datastore_id, null),
      try(var.proxmox_storage_classes[image.storage_class].cloud_init_drive, null)
    ), null)
    image_file_name = try(coalesce(
      try(image.image_file_name, null),
      "${image.vm_id}-${image.sha256}.${image.family == "talos" ? "raw" : "qcow2"}"
    ), null)
  }) }
}

module "templates" {
  source = "../../modules/proxmox_templates"
  images = local.images
}
