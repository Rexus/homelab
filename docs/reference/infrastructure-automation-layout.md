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
| Ansible inventory | hostnames, `ansible_host`, Proxmox display name, service groups, and tags |
| Terraform environment tfvars | Proxmox node, size, storage class, disk size, and network zone |
| Terraform common tfvars | shared storage mappings, network zones, template IDs, and cloud-init SSH keys |

Terraform guest maps are keyed by the matching Ansible inventory host. Keep
hostnames, IP addresses, and Proxmox tags out of the environment tfvars so
Terraform can read shared host identity from inventory while keeping hardware
shape in Terraform.

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
| `terraform/common.tfvars.example` | shared storage, network, template, and SSH-key inputs | [Local setup](../getting-started/local-setup.md) |
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
