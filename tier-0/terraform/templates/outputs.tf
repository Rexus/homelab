output "template_candidates" {
  description = "Versioned candidates to test before promoting into a consuming tier's template catalog."
  value       = module.templates.catalog
}
