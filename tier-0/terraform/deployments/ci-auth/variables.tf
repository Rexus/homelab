variable "accept_trusted_ci" {
  description = "Accept GitLab and hosting administrators as Tier 0 authorities for direct infrastructure execution."
  type        = bool
  default     = false
  validation {
    condition     = var.accept_trusted_ci
    error_message = "Direct CI requires explicit Tier 0 acceptance of the GitLab control-plane trust boundary."
  }
}

variable "gitlab_issuer" {
  type = string
  validation {
    condition     = can(regex("^https://[^/]+$", var.gitlab_issuer))
    error_message = "Use the exact HTTPS GitLab issuer without a trailing slash."
  }
}

variable "gitlab_ca_pem" {
  description = "Public CA chain for Vault's verified GitLab discovery connection; empty uses system trust."
  type        = string
  default     = ""
}

variable "vault_audience" {
  type = string
  validation {
    condition     = can(regex("^https://[^/]+$", var.vault_audience))
    error_message = "Set the exact HTTPS audience used by the CI ID token."
  }
}

variable "projects" {
  description = "Explicit privileged project/namespace IDs and protected branches; no wildcard projects."
  type = map(object({
    project_id   = string
    namespace_id = string
    branch       = string
    secret_path  = string
    runner_cidrs = optional(list(string), [])
  }))
  validation {
    condition = length(var.projects) > 0 && alltrue([for name, project in var.projects :
      can(regex("^[a-z0-9-]+$", name)) &&
      can(regex("^[1-9][0-9]*$", project.project_id)) &&
      can(regex("^[1-9][0-9]*$", project.namespace_id)) &&
      can(regex("^[a-zA-Z0-9_/-]+$", project.branch)) &&
      can(regex("^kv/data/ci/[a-zA-Z0-9_-]+$", project.secret_path))
    ])
    error_message = "Use named roles, numeric project/namespace IDs, exact branches and one non-wildcard KV-v2 secret path."
  }
}
