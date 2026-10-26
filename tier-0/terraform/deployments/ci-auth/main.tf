# Direct trusted-CI variant only. Human SSO is a separate identity integration.
# Guide: docs/deployment/stage-9-development/procedures/vault-ci.md
resource "vault_jwt_auth_backend" "gitlab" {
  path                  = "gitlab-ci"
  type                  = "jwt"
  oidc_discovery_url    = var.gitlab_issuer
  oidc_discovery_ca_pem = var.gitlab_ca_pem
  bound_issuer          = var.gitlab_issuer
  lifecycle {
    prevent_destroy = true
  }
}

resource "vault_policy" "project" {
  for_each = var.projects
  name     = "ci-${each.key}"
  policy = jsonencode({
    path = {
      (each.value.secret_path) = { capabilities = ["read"] }
      "auth/token/revoke-self" = { capabilities = ["update"] }
      "auth/token/lookup-self" = { capabilities = ["read"] }
    }
  })
}

resource "vault_jwt_auth_backend_role" "project" {
  for_each          = var.projects
  backend           = vault_jwt_auth_backend.gitlab.path
  role_name         = each.key
  role_type         = "jwt"
  user_claim        = "job_id"
  bound_audiences   = [var.vault_audience]
  bound_claims_type = "string"
  bound_claims = {
    job_project_id = each.value.project_id
    namespace_id   = each.value.namespace_id
    ref_type       = "branch"
    ref            = each.value.branch
    ref_protected  = "true"
  }
  token_policies          = [vault_policy.project[each.key].name]
  token_no_default_policy = true
  token_ttl               = 300
  token_explicit_max_ttl  = 900
  token_bound_cidrs       = each.value.runner_cidrs
}
