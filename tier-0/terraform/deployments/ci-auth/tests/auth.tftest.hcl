mock_provider "vault" {}
variables {
  accept_trusted_ci = true
  gitlab_issuer     = "https://gitlab.lab.test"
  vault_audience    = "https://vault.lab.test"
  projects = {
    tier0 = {
      project_id  = "123", namespace_id = "12", branch = "main"
      secret_path = "kv/data/ci/tier0", runner_cidrs = ["192.0.2.10/32"]
    }
  }
}
run "bounded_project_authority" {
  command = plan
  assert {
    condition = (
      vault_jwt_auth_backend_role.project["tier0"].bound_claims.job_project_id == "123" &&
      vault_jwt_auth_backend_role.project["tier0"].bound_claims.ref_protected == "true" &&
      vault_jwt_auth_backend_role.project["tier0"].bound_claims.ref == "main" &&
      vault_jwt_auth_backend_role.project["tier0"].token_no_default_policy &&
      vault_jwt_auth_backend_role.project["tier0"].token_explicit_max_ttl == 900 &&
      jsondecode(vault_policy.project["tier0"].policy).path["kv/data/ci/tier0"].capabilities == ["read"]
    )
    error_message = "Only the exact protected project/branch may obtain bounded read-only secret access."
  }
}
run "reject_implicit_trust" {
  command = plan
  variables { accept_trusted_ci = false }
  expect_failures = [var.accept_trusted_ci]
}
run "reject_wildcard_secret_authority" {
  command = plan
  variables {
    projects = { tier0 = { project_id = "123", namespace_id = "12", branch = "main", secret_path = "kv/data/ci/*" } }
  }
  expect_failures = [var.projects]
}
