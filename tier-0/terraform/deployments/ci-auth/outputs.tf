output "ci_roles" {
  description = "Non-secret login roles, policies and the existing KV paths they may read."
  value = {
    for name, role in vault_jwt_auth_backend_role.project : name => {
      backend     = vault_jwt_auth_backend.gitlab.path
      role        = role.role_name
      policy      = vault_policy.project[name].name
      secret_path = var.projects[name].secret_path
    }
  }
}
