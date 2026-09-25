module "templates" {
  source = "../../modules/proxmox_templates"
  images = yamldecode(file(var.catalog_file)).templates
}
