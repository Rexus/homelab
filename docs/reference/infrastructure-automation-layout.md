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
| Ansible inventory | stable logical host keys and service groups |
| Ansible `all` group vars | hostname prefix or suffix, domain, guest IP map, and baseline inputs |
| Ansible setup group vars | service settings and host configuration inputs |
| Terraform environment tfvars | Proxmox tags, size, storage class, disk size, network zone, and optional Proxmox node override |
| Terraform common tfvars | default Proxmox node, shared storage mappings, network zones, template IDs, and cloud-init SSH keys |

Terraform guest maps are keyed by the matching Ansible inventory host key, for
example `idm-1`. Keep that key stable across environments.

Use `platform_hostname_prefix`, `platform_hostname_suffix`,
`platform_domain`, and `platform_host_ips` in Ansible group vars to shape each
environment. The same logical key can become `test-idm-1.example.com`,
`idm-test-1.example.com`, or `idm-1.example.com`.
Use DNS-safe environment names with letters, numbers, and dashes.
Include separators in the prefix or suffix value, for example `test-` or
`-test`. Suffixes are inserted before the numeric suffix, so `ca-root-1`
becomes `ca-root-test-1`.

Terraform reads the same Ansible group vars for the guest IP map and generated
Proxmox name, so IPs and names are not maintained in both tools.
Every Terraform guest key should have a matching `platform_host_ips` entry, or
the value `dhcp` when that guest is intentionally dynamic.

When `--env` is used, the wrapper loads both the environment-wide vars file and
the matching setup vars file when that setup has one. For example,
`--env test` with `foundation` loads `all.test.yml` and
`foundation.test.yml`.

Use `default_proxmox_node_name` for the normal Proxmox placement target.
Only set `proxmox_node_name` on an individual guest when you intentionally
override that default for a clustered Proxmox placement.

Use `default_linux_vm_template_id` in `terraform/common.tfvars` for the shared
Linux cloud-init template. Override it in `terraform.tfvars` or
`terraform.<env>.tfvars` when one deployment tests another supported distro or
template. Use `vm_instances.<key>.template_vm_id` only when one guest should
differ from the deployment default.

## Environment data split

Use the same source code and main inventory for every environment. Split only
the data that changes:

| Layer | Test example | Production default |
| --- | --- | --- |
| Terraform setup vars | `terraform/environments/foundation/terraform.tfvars` | `terraform/environments/foundation/terraform.tfvars` |
| Optional Terraform setup overlay | `terraform/environments/foundation/terraform.test.tfvars` | not used by default |
| Shared Terraform vars | `terraform/common.tfvars` or `--common-var-file` override | `terraform/common.tfvars` or `--common-var-file` override |
| Optional shared Terraform overlay | `terraform/common.test.tfvars` | not used by default |
| Ansible inventory | `ansible/inventory/hosts.yml` | `ansible/inventory/hosts.yml` |
| Ansible environment vars | `ansible/group_vars/all.test.yml` from `all.env.yml.example` | `ansible/group_vars/all.yml` |
| Ansible setup vars | `ansible/group_vars/foundation.test.yml`, loaded by `--env test` | `ansible/group_vars/foundation.yml` |
| Terraform state | `.terraform/state/foundation/test/terraform.tfstate` | `.terraform/state/foundation/prod/terraform.tfstate` |

The repository wrapper keeps Terraform state separate per setup and
environment. Terraform vars are shared by default and only layered per
environment when the optional override files exist. Do not share a Terraform
state file between environments. Omit `--env` for production.

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
| `terraform/environments/foundation/` | identity, DNS, PKI, and optional edge load-balancer guest layout | [Identity foundation path](../foundation/identity-foundation-path.md) |
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
| `ansible/inventory/hosts.yml.example` | stable logical host keys and service groups |
| `ansible/group_vars/all.yml.example` | shared Ansible defaults and default environment data |
| `ansible/group_vars/all.env.yml.example` | environment-specific hostname decoration, domain, and IP map overlay |
| `ansible/playbooks/control-node.yml` | local precheck before each wrapper run |
| `ansible/playbooks/foundation.yml` | staged FreeIPA identity foundation rollout |
| `ansible/playbooks/vault.yml` | Vault host baseline and service installation |
| `ansible/playbooks/site.yml` | broader baseline entry point |
| `ansible/playbooks/ingress.yml` | edge load-balancer backend registration for HSM gateways |
| `ansible/roles/baseline/` | security-first baseline scaffold |
| `ansible/roles/vault/` | Vault service role |
| `ansible/roles/hsm_proxy_ingress/` | HSM gateway backend snippet scaffold |

## Packer

| Path | Contains |
| --- | --- |
| `packer/variables.auto.pkrvars.hcl.example` | safe example input values |
| `packer/templates/proxmox/el10.pkr.hcl` | Enterprise Linux VM image scaffold for the current EL10 reference path |
| `packer/templates/proxmox/debian-12.pkr.hcl` | Debian 12 VM image scaffold |
| `packer/templates/proxmox/talos-linux.pkr.hcl` | Talos Linux VM image scaffold |
