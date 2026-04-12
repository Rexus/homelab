# Homelab IaC Baseline

This repository is a security-first Infrastructure as Code baseline for building
and operating a private cloud homelab or small datacenter using Packer,
Terraform, and Ansible so new environments can be brought up quickly,
consistently, and without committing secrets into Git.

Proxmox is the current reference foundation for the hypervisor and initial
infrastructure layer, but the repository is organized around the broader
private-cloud lifecycle rather than one product.

This public repository is maintained as a curated upstream reference. Use a
private fork, private mirror, or local copy for actual deployment work and do
not push operational changes back to this upstream.

## Getting started

1. Copy these files:
   - `packer/variables.auto.pkrvars.hcl.example`
     -> `packer/variables.auto.pkrvars.hcl`
   - `terraform/environments/lab/terraform.tfvars.example`
     -> `terraform/environments/lab/terraform.tfvars`
   - `ansible/inventory/hosts.yml.example`
     -> `ansible/inventory/hosts.yml`
   - `ansible/group_vars/all.yml.example`
     -> `ansible/group_vars/all.yml`
2. Replace the placeholder values with your own.
3. Set required secrets as environment variables.
4. Follow the current platform guide in [platforms/proxmox](platforms/proxmox/README.md).
5. Run Packer, then Terraform, then Ansible.

Recommended maturity path:

- start with the local example files and bootstrap secrets
- add backup and recovery before the environment becomes important
- move long-lived secrets to Vault when the platform is stable enough to host it
- improve resilience and availability as the environment becomes more serious

Read more in:

- [docs/getting-started/private-cloud-maturity-path.md](docs/getting-started/private-cloud-maturity-path.md)
- [platforms/proxmox/backup-foundation.md](platforms/proxmox/backup-foundation.md)
- [docs/reference/environment-variables.md](docs/reference/environment-variables.md)
- [docs/security/secret-strategy.md](docs/security/secret-strategy.md)
- [docs/architecture/overview.md](docs/architecture/overview.md)

## Repository structure

- `docs/` overview, architecture, security, and decision records
- `platforms/` provider-specific guidance and implementation notes
- `packer/` image build workflow and example variable files
- `terraform/` infrastructure provisioning layout and environment examples
- `ansible/` configuration management layout, inventory examples, and defaults
- `.ai/` hidden assistant context and session notes

## AI-assisted development

AI may be used to draft documentation, scaffolding, and implementation support.
Human review remains required for architecture, security controls, and any
change that affects secrets, trust boundaries, or production behavior.

## License

MIT License
