# Infrastructure automation layout

## Purpose

Use this reference only when you need to find the automation code behind the
guides.

Guides and walkthroughs live under `docs/`. The automation directories stay
focused on source, examples, modules, roles, and playbooks.

For run order, prerequisites, and setup-specific choices, follow the guide
linked for that deployment instead of this reference.

## Ownership rule

Keep shared host identity in Ansible and hardware placement in Terraform.

| Owner | Defines |
| --- | --- |
| Ansible inventory | host keys, `ansible_host`, and service groups |
| Ansible group vars | environment domain, service settings, and host configuration inputs |
| Terraform environment tfvars | Proxmox tags, size, storage class, disk size, network zone, and optional Proxmox node override |
| Terraform common tfvars | default Proxmox node, shared storage mappings, network zones, template IDs, and cloud-init SSH keys |

Terraform guest maps are keyed by the matching Ansible inventory host key. That
key is also the Proxmox VM name and cloud-init hostname, for example
`test-identity-1`.

Use `platform_domain` in Ansible to append the environment domain, so the same
short host key becomes `test-identity-1.example.com` for services that need a
full DNS name.

Use `default_proxmox_node_name` for the normal Proxmox placement target.
Only set `proxmox_node_name` on an individual guest when you intentionally
override that default for a clustered Proxmox placement.

## Environment data split

Use the same source code for every environment and split only the data:

| Layer | Test or staging example | Production example |
| --- | --- | --- |
| Terraform setup vars | `terraform/environments/foundation/terraform.test.tfvars` | `terraform/environments/foundation/terraform.prod.tfvars` |
| Shared Terraform vars | `terraform/common.test.tfvars` or `--common-var-file` override | `terraform/common.prod.tfvars` or `--common-var-file` override |
| Ansible inventory | `ansible/inventory/test.yml` | `ansible/inventory/prod.yml` |
| Ansible setup vars | `ansible/group_vars/foundation.test.yml` | `ansible/group_vars/foundation.prod.yml` |
| Terraform state | `.terraform/state/foundation/test/terraform.tfstate` | `.terraform/state/foundation/prod/terraform.tfstate` |

The repository wrapper keeps Terraform state separate per setup and
environment. Do not share a Terraform state file between test and production.

## Main paths

| Path | Purpose | Read first |
| --- | --- | --- |
| `scripts/` | repo-local initialization and deployment wrappers | [Local setup](../getting-started/local-setup.md) |
| `terraform/` | platform provisioning environments and modules | [Identity foundation path](../foundation/identity-foundation-path.md) |
| `ansible/` | baseline and service configuration playbooks | [Vault foundation deployment](../foundation/vault-foundation-deployment.md) |
| `packer/` | optional custom image builds | [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |

## Terraform

| Path | Contains | Owner guide |
| --- | --- | --- |
| `terraform/common.tfvars.example` | default Proxmox node, storage, network, template, and SSH-key inputs | [Local setup](../getting-started/local-setup.md) |
| `terraform/environments/foundation/` | identity, DNS, PKI, and optional edge-proxy guest layout | [Identity foundation path](../foundation/identity-foundation-path.md) |
| `terraform/environments/vault/` | dedicated Vault guest layout | [Vault foundation deployment](../foundation/vault-foundation-deployment.md) |
| `terraform/environments/hsm-lab/` | USB HSM gateway and optional helper guest layout | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md) |
| `terraform/environments/lab/` | general lab guest layout | [Local setup](../getting-started/local-setup.md) |
| `terraform/modules/vm/` | reusable Proxmox VM module | this reference |
| `terraform/modules/lxc/` | reusable Proxmox LXC module | this reference |
| `terraform/modules/environment_guests/` | shared environment guest schema | this reference |

## Ansible

| Path | Contains |
| --- | --- |
| `ansible/requirements.yml` | required collections for the deployment machine |
| `ansible/playbooks/control-node.yml` | local precheck before each wrapper run |
| `ansible/playbooks/foundation.yml` | staged FreeIPA identity foundation rollout |
| `ansible/playbooks/vault.yml` | Vault host baseline and service installation |
| `ansible/playbooks/site.yml` | broader baseline entry point |
| `ansible/playbooks/ingress.yml` | proxy backend registration for HSM gateways |
| `ansible/roles/baseline/` | security-first baseline scaffold |
| `ansible/roles/vault/` | Vault service role |
| `ansible/roles/hsm_proxy_ingress/` | HSM gateway backend snippet scaffold |

## Packer

| Path | Contains |
| --- | --- |
| `packer/variables.auto.pkrvars.hcl.example` | safe example input values |
| `packer/templates/proxmox/el10.pkr.hcl` | Enterprise Linux 10 VM image scaffold |
| `packer/templates/proxmox/debian-12.pkr.hcl` | Debian 12 VM image scaffold |
| `packer/templates/proxmox/talos-linux.pkr.hcl` | Talos Linux VM image scaffold |
