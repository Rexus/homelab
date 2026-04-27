# Private Cloud IaC Baseline

This repository is a security-first Infrastructure as Code baseline for
building and operating an enterprise-style private cloud on a homelab or small
datacenter scale using Packer, Terraform, and Ansible so you can bring up new
environments quickly, consistently, and without committing secrets into Git.

Proxmox is the current reference foundation for the hypervisor and initial
infrastructure layer, but the repository is organized around the broader
private-cloud lifecycle rather than one product.

This public repository is maintained as a curated upstream reference. Use a
private fork, private mirror, or local copy for actual deployment work and do
not push operational changes back to this upstream.

## Getting started

Use the foundation fast path below for the shortest first run. For a fuller
walkthrough of the same flow, start with
[docs/foundation/foundation-and-domain-path.md](docs/foundation/foundation-and-domain-path.md).
If your local tooling still needs to be prepared, read
[docs/getting-started/local-setup.md](docs/getting-started/local-setup.md).
If you want the broader documentation map, use [docs/README.md](docs/README.md).

Foundation fast path:

1. Review platform prerequisites:
   - [Proxmox reference platform](docs/platforms/proxmox/README.md)
   - [Proxmox API setup](docs/platforms/proxmox/setup-api.md)

2. Initialize local working files:

```bash
bash scripts/init-local-files.sh
```

3. Update the generated local files with your environment values.
   This is a repo-local setup step, not something you rerun for every
   deployment.
   The wrapper automatically loads `.env.local` when it exists. In runners,
   you can provide the same values as environment variables instead.

4. Run the repository deployment wrapper:

```bash
bash scripts/deploy.sh foundation
```

This wrapper runs the local control-node precheck first, then the mapped
Terraform and Ansible steps for that setup. For `foundation`, it prepares the
domain foundation layer first. The current reference shape is `2` identity
hosts plus `1` issuing CA host before Vault.
It also checks that the required local config files exist before the run, such
as the shared `terraform/common.tfvars`, environment `terraform.tfvars`,
inventory, and group vars files copied from the shipped examples.

For a disposable test run before production, initialize the test file set once,
then run and destroy the test environment with the same environment name:

```bash
bash scripts/init-local-files.sh --env test
bash scripts/deploy.sh foundation --env test \
  --inventory ansible/inventory/test.yml \
  --ansible-vars ansible/group_vars/foundation.test.yml
bash scripts/deploy.sh foundation --env test --destroy
```

Use `--env-file path/to/file` when you want to override `.env.local` with
another environment file.
After reviewing files refreshed with `--overwrite`, remove old backups with
`bash scripts/init-local-files.sh --clean-backups`.

5. Continue with:
   - [Vault foundation deployment](docs/foundation/vault-foundation-deployment.md)
   - [Secret strategy](docs/security/secret-strategy.md)
   - [Private cloud maturity path](docs/getting-started/private-cloud-maturity-path.md)
   - [Documentation index](docs/README.md)

Recommended maturity path:

- start with local example files and the smallest possible bootstrap-only secret set
- deploy the identity and PKI foundation first
- establish naming, DNS, and the first issuing-CA path needed by early
  services
- add Windows or AD support later only if the environment needs it
- deploy Vault as the early secret-platform foundation
- move long-lived and shared secrets to Vault before broader deployment
- add backup and recovery before the environment becomes important
- improve resilience and availability as the environment becomes more serious

Read more in:

- [docs/foundation/vault-foundation-deployment.md](docs/foundation/vault-foundation-deployment.md)
- [docs/getting-started/private-cloud-maturity-path.md](docs/getting-started/private-cloud-maturity-path.md)
- [Proxmox backup foundation](docs/platforms/proxmox/backup-foundation.md)
- [docs/reference/environment-variables.md](docs/reference/environment-variables.md)
- [docs/security/secret-strategy.md](docs/security/secret-strategy.md)
- [docs/architecture/overview.md](docs/architecture/overview.md)
- [docs/README.md](docs/README.md)

## Repository structure

- `docs/` overview, foundation, getting started, platform guides, security,
  architecture, reference, and decisions
- `packer/` image build workflow and example variable files
- `terraform/` infrastructure provisioning layout and bootstrap environments
- `ansible/` configuration management layout, inventory examples, and playbooks
- `scripts/` repo-local initialization and deployment wrappers that keep the
  control-node precheck in front of each setup run
- `.ai/` hidden assistant context and session notes

## AI-assisted development

AI may be used to draft documentation, scaffolding, and implementation support.
Human review remains required for architecture, security controls, and any
change that affects secrets, trust boundaries, or production behavior.

## License

MIT License
