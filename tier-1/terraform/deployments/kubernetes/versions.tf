terraform {
  required_version = ">= 1.11.0"
  backend "local" {}
  required_providers {
    external = {
      source  = "hashicorp/external"
      version = "~> 2.4.2"
    }
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.112.0"
    }
    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.11.0"
    }
  }
}
