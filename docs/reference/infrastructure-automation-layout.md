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
| Ansible `all` group vars | hostname prefix or suffix, domain, and baseline inputs |
| Ansible setup group vars | guest IP map, service settings, and host configuration inputs |
| Terraform environment tfvars | Proxmox VMID, tags, size, storage class, disk size, network zone, and optional Proxmox node override |
| Terraform common tfvars | default platform node, shared storage mappings, guest network attachments, template IDs, and cloud-init SSH keys |

Terraform guest maps are keyed by the matching Ansible inventory host key, for
example `idm-1`. Keep that key stable across environments.
Set `vm_instances.<key>.vm_id` and `lxc_instances.<key>.vm_id` explicitly in
examples so repo-managed guests follow the Proxmox VMID ranges from the platform
conventions. Change the IDs when those ranges are already used in your cluster.

Use `platform_hostname_prefix`, `platform_hostname_suffix`, and
`platform_domain` in `all.yml` or `all.<env>.yml` to shape each environment.
The same logical key can become `test-idm-1.corp.example.com`,
`idm-test-1.corp.example.com`, or `idm-1.corp.example.com`.
Use a private internal subdomain such as `corp.example.com` or
`internal.example.com` instead of the public website apex.
Use DNS-safe environment names with letters, numbers, and dashes.
Do not include separators in the prefix or suffix value; the automation adds
the dash only when the value is not empty. Suffixes are inserted before the
numeric suffix, so `ca-root-1` becomes `ca-root-test-1`.

Setup group vars own `platform_host_ips`, so `foundation.yml`,
`edge.yml`, and the other setup files stay small and focused.
Terraform reads the same setup group vars for the guest IP map and generated
Proxmox name, so IPs and names are not maintained in both tools.
Every Terraform guest key should have a matching `platform_host_ips` entry, or
the value `dhcp` when that guest is intentionally dynamic.
Static guest addressing uses the CIDR prefix and gateway in Terraform
`network_zones`. Keep each zone focused on deployable guest networks:
`bridge`, optional `vlan_id`, `cidr_ipv4`, and optional `gateway_ipv4`.
When you use `<setup>.<env>.yml`, keep the full IP map for that setup in the
environment file. The wrapper layers YAML files predictably, but it does not
try to merge partial maps.

When `--env` is used, the wrapper loads both the environment-wide vars file and
the matching setup vars file when that setup has one. For example,
`--env test` with `foundation` loads `all.test.yml` and
`foundation.test.yml`.

Use `default_platform_node_name` for the normal platform placement target.
Only set `proxmox_node_name` on an individual guest when you intentionally
override that default for a clustered Proxmox placement.
The older `default_proxmox_node_name` key is still accepted as a compatibility
fallback, but new local files should use the platform-generic name.

Use `default_linux_vm_template_id` in `terraform/common.tfvars` for the shared
Linux cloud-init template. Override it in `terraform.tfvars` or
`terraform.<env>.tfvars` when one deployment tests another supported distro or
template. Use `vm_instances.<key>.template_vm_id` only when one guest should
differ from the deployment default.

Use `linux_vm_template_catalog` in `terraform/common.tfvars` for the OS,
distro, architecture, and image-capability tags that should carry from source
templates onto cloned VMs. Terraform looks up catalog tags by the selected
template VM ID, so a per-VM `template_vm_id` override also changes the image
tags when that ID exists in the catalog. Terraform combines catalog tags with
`vm_instances.<key>.tags`, where the latter should stay focused on workload
identity. Template-producing setups can set
`vm_instances.<key>.template_catalog_id` when a builder VM should receive tags
for the target template ID instead of the source clone template ID. Set
`vm_instances.<key>.template_tags` only as an escape hatch for a source image
that is not in the catalog, or set it to `[]` when you intentionally do not
want source-image tags on that deployed VM.

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
| Ansible setup vars | `ansible/group_vars/foundation.yml` plus `foundation.test.yml` | `ansible/group_vars/foundation.yml` |
| Terraform state | `.terraform/state/foundation/test/terraform.tfstate` | `.terraform/state/foundation/prod/terraform.tfstate` |

The repository wrapper keeps Terraform state separate per setup and
environment. Terraform vars are shared by default and only layered per
environment when the optional override files exist. Do not share a Terraform
state file between environments. Omit `--env` for production.

## Main paths

| Path | Purpose | Read first |
| --- | --- | --- |
| `scripts/` | repo-local initialization and deployment wrappers | [Repository scripts](repository-scripts.md) |
| `terraform/` | platform provisioning environments and modules | [Shared services model](../architecture/shared-services.md) |
| `ansible/` | baseline and service configuration playbooks | [Shared services path](../paths/shared-services/README.md) |
| `packer/` | optional custom image builds | [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |

## Terraform

| Path | Contains | Owner guide |
| --- | --- | --- |
| `terraform/common.tfvars.example` | default platform node, storage, network, template, and SSH-key inputs | [Local setup](../getting-started/local-setup.md) |
| `terraform/environments/foundation/` | identity, DNS, PKI, and optional root CA guest layout | [Identity foundation path](../paths/shared-services/identity.md) |
| `terraform/environments/edge/` | edge load-balancer guest layout | [Edge proxy path](../paths/shared-services/edge.md) |
| `terraform/environments/cache/` | cache guest layout | [Cache path](../paths/shared-services/cache.md) |
| `terraform/environments/development/` | GitLab development platform guest layout | [Development platform path](../paths/application-platform/development.md) |
| `terraform/environments/vault/` | dedicated Vault guest layout | [Vault foundation deployment](../paths/shared-services/vault.md) |
| `terraform/environments/observability/` | system-control telemetry, syslog, metrics, logs, and archive guest layout | [Observability path](../paths/system-control/observability.md) |
| `terraform/environments/podman-runner/` | application-platform runner guest layout | [Podman image runner guide](../paths/application-platform/podman-runner.md) |
| `terraform/environments/immutable-template/` | image-based Linux template builder guest layout | [Image-based Linux path](../paths/application-platform/image-based-linux.md) |
| `terraform/environments/template-refresh/` | staged mutable Enterprise Linux template refresh layout | [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |
| `terraform/environments/hsm/` | USB HSM gateway and optional helper guest layout | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md) |
| `terraform/environments/lab/` | general lab guest layout | [Local setup](../getting-started/local-setup.md) |
| `terraform/modules/vm/` | reusable Proxmox VM module | this reference |
| `terraform/modules/lxc/` | reusable Proxmox LXC module | this reference |
| `terraform/modules/environment_guests/` | shared environment guest schema | this reference |

## Ansible

| Path | Contains |
| --- | --- |
| `ansible/requirements.yml` | Galaxy-compatible reference list of required collections |
| `ansible/inventory/hosts.yml.example` | stable logical host keys and service groups |
| `ansible/group_vars/all.yml.example` | shared Ansible defaults and production environment identity |
| `ansible/group_vars/all.env.yml.example` | environment-specific hostname decoration and domain overlay |
| `ansible/group_vars/foundation.yml.example` | foundation IP map and FreeIPA settings |
| `ansible/group_vars/edge.yml.example` | HAProxy and keepalived VIP settings for the edge path |
| `ansible/group_vars/cache.yml.example` | Squid and keepalived VIP settings for the cache path |
| `ansible/group_vars/development.yml.example` | GitLab container setup settings |
| `ansible/group_vars/vault.yml.example` | Vault IP map and service settings |
| `ansible/group_vars/observability.yml.example` | system-control IP map |
| `ansible/group_vars/podman_runner.yml.example` | Podman runner package and registration settings |
| `ansible/group_vars/immutable_template.yml.example` | image-based Linux template conversion settings |
| `ansible/group_vars/template_refresh.yml.example` | mutable Enterprise Linux template refresh and replacement settings |
| `ansible/group_vars/lab.yml.example` | lab IP map |
| `ansible/group_vars/hsm.yml.example` | HSM IP map |
| `ansible/playbooks/control-node.yml` | setup-aware precheck for Terraform and required Ansible collections |
| `ansible/playbooks/foundation.yml` | staged FreeIPA identity foundation rollout |
| `ansible/playbooks/edge.yml` | edge load-balancer baseline plus HAProxy and keepalived |
| `ansible/playbooks/cache.yml` | cache baseline plus Squid and keepalived |
| `ansible/playbooks/development.yml` | GitLab development platform setup |
| `ansible/playbooks/vault.yml` | Vault host baseline and service installation |
| `ansible/playbooks/lab.yml` | lab host baseline |
| `ansible/playbooks/observability.yml` | system-control host baseline |
| `ansible/playbooks/podman-runner.yml` | Podman runner host baseline and runner setup |
| `ansible/playbooks/immutable-template.yml` | image-based Linux template builder setup |
| `ansible/playbooks/template-refresh.yml` | staged Enterprise Linux template refresh and optional same-ID replacement |
| `ansible/playbooks/hsm.yml` | HSM host baseline |
| `ansible/playbooks/site.yml` | broad baseline entry point for manual use |
| `ansible/playbooks/ingress.yml` | edge load-balancer backend registration for HSM gateways |
| `ansible/roles/baseline/` | security-first baseline scaffold |
| `ansible/roles/edge_load_balancer/` | HAProxy and keepalived edge VIP setup |
| `ansible/roles/cache_proxy/` | Squid and keepalived cache VIP setup |
| `ansible/roles/gitlab_container/` | GitLab container host setup role |
| `ansible/roles/vault/` | Vault service role |
| `ansible/roles/podman_runner/` | Podman and GitLab Runner setup role |
| `ansible/roles/immutable_template/` | bootc template conversion preparation role |
| `ansible/roles/template_refresh/` | mutable Enterprise Linux template refresh role |
| `ansible/roles/proxmox_template_replace/` | Proxmox same-ID template replacement role |
| `ansible/roles/hsm_proxy_ingress/` | HSM gateway backend snippet scaffold |

## Packer

| Path | Contains |
| --- | --- |
| `packer/variables.auto.pkrvars.hcl.example` | safe example input values |
| `packer/templates/proxmox/el10.pkr.hcl` | Enterprise Linux VM image scaffold for the current EL10 reference path |
| `packer/templates/proxmox/debian-12.pkr.hcl` | Debian 12 VM image scaffold |
| `packer/templates/proxmox/talos-linux.pkr.hcl` | Talos Linux VM image scaffold |
