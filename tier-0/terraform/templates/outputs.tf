output "template_candidates" {
  description = "Versioned candidates to test before promoting references into the shared consumer catalog."
  value       = module.templates.catalog
}
