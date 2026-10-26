# VAULT_ADDR, VAULT_TOKEN and VAULT_CACERT come from the protected operator environment.
provider "vault" {
  skip_tls_verify  = false
  skip_child_token = true
}
