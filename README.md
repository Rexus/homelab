# Homelab IaC Baseline

This repository is a security-first Infrastructure as Code baseline for
building and operating a private cloud homelab or small datacenter using
Packer, Terraform, and Ansible so you can bring up new environments quickly,
consistently, and without committing secrets into Git.

Proxmox is the current reference foundation for the hypervisor and initial
infrastructure layer, but the repository is organized around the broader
private-cloud lifecycle rather than one product.

This public repository is maintained as a curated upstream reference. Use a
private fork, private mirror, or local copy for actual deployment work and do
not push operational changes back to this upstream.

## Getting started

Use the bootstrap fast path below for the shortest first run. For a fuller
walkthrough of the same flow, start with
[docs/getting-started/bootstrap-path.md](docs/getting-started/bootstrap-path.md).
If your local tooling still needs to be prepared, read
[docs/getting-started/local-setup.md](docs/getting-started/local-setup.md).
If you want the broader documentation map, use [docs/README.md](docs/README.md).

Bootstrap fast path:

1. Review platform prerequisites:
   - [Proxmox reference platform](docs/platforms/proxmox/README.md)
   - [Proxmox API setup](docs/platforms/proxmox/setup-api.md)

2. Prepare local working files:

```bash
cp packer/variables.auto.pkrvars.hcl.example packer/variables.auto.pkrvars.hcl
cp terraform/environments/bootstrap/terraform.tfvars.example terraform/environments/bootstrap/terraform.tfvars
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
cp ansible/group_vars/all.yml.example ansible/group_vars/all.yml
cp ansible/group_vars/vault.yml.example ansible/group_vars/vault.yml
```

3. Update the copied files with your local values.

4. Set platform API access for the current shell:

```bash
export TF_VAR_proxmox_api_url="https://proxmox.example.com:8006/api2/json"
export TF_VAR_proxmox_api_token_id="terraform@pve!change-me"
export TF_VAR_proxmox_api_token_secret="change-me"
```

5. Run the bootstrap deployment:

```bash
cd terraform/environments/bootstrap
terraform init
terraform plan
terraform apply
cd ../../..
```

6. Apply bootstrap configuration after provisioning:

```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap.yml
cd ..
```

Hosts placed in the `vault` inventory group receive the Vault bootstrap role as
part of this run.

7. Continue with:
   - [Vault bootstrap](docs/getting-started/vault-bootstrap.md)
   - [Secret strategy](docs/security/secret-strategy.md)
   - [Private cloud maturity path](docs/getting-started/private-cloud-maturity-path.md)
   - [Documentation index](docs/README.md)

Recommended maturity path:

- start with local example files and the smallest possible bootstrap secret set
- turn the first managed VM into a dedicated Vault node before broader deployment
- add backup and recovery before the environment becomes important
- move long-lived and shared secrets to Vault immediately after bootstrap
- improve resilience and availability as the environment becomes more serious

Read more in:

- [docs/getting-started/vault-bootstrap.md](docs/getting-started/vault-bootstrap.md)
- [docs/getting-started/private-cloud-maturity-path.md](docs/getting-started/private-cloud-maturity-path.md)
- [Proxmox backup foundation](docs/platforms/proxmox/backup-foundation.md)
- [docs/reference/environment-variables.md](docs/reference/environment-variables.md)
- [docs/security/secret-strategy.md](docs/security/secret-strategy.md)
- [docs/architecture/overview.md](docs/architecture/overview.md)
- [docs/README.md](docs/README.md)

## Repository structure

- `docs/` overview, getting started, platform guides, security, and decisions
- `packer/` image build workflow and example variable files
- `terraform/` infrastructure provisioning layout and bootstrap environments
- `ansible/` configuration management layout, inventory examples, and playbooks
- `.ai/` hidden assistant context and session notes

## AI-assisted development

AI may be used to draft documentation, scaffolding, and implementation support.
Human review remains required for architecture, security controls, and any
change that affects secrets, trust boundaries, or production behavior.

## License

MIT License
