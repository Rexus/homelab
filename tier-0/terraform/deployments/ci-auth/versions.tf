terraform {
  required_version = ">= 1.11.0"
  backend "local" {}
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "~> 5.0"
    }
  }
}
