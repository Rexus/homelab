# Platform inputs and local access

Shared holds references to existing infrastructure, not the infrastructure
resources or host inventory. Network references used across tiers are defined once;
each tier owns its specific networks, guest selections and overrides.

## Table of contents

- [Input ownership](#input-ownership)
- [Loading and overrides](#loading-and-overrides)
- [Local SSH access](#local-ssh-access)
- [OS baseline boundary](#os-baseline-boundary)
- [Existing collections](#existing-collections)

## Input ownership

| Location | Defines |
| --- | --- |
| Shared `config/platform.tfvars` | Project-owned storage, initial placement and common network references in `shared_network_zones` |
| Shared `config/guest-sizes.json` | Reusable size profiles |
| Shared `templates/proxmox-catalog.tfvars` | Approved image references; publication remains Tier 0 |
| Tier `terraform/common.tfvars` | Tier-specific `network_zones`, overrides of shared networks, and optional platform overrides |
| Tier deployment `.tfvars` | Guest hardware and resource selections |
| Tier Ansible inventory/group vars | Host names, groups, IPs, and service configuration |
| Local environment or secret injection | Provider access and local SSH public-key file paths |

The shared profile is a reference catalog, not a Terraform root. It contains
no resources, state, guest assignments, host addresses, credentials, or keys.
For example, the common `application` subnet is recorded here; `identity` and
`cryptography` remain Tier 0-specific references. Merely listing a network does
not connect a guest or authorize access to it.
Tier 0 approves infrastructure references; consumers may override permitted
values. Refresh never replaces or recreates a project-owned profile.

`proxmox_storage_classes` maps VM-disk classes to existing Proxmox datastore IDs;
it does not describe an object-storage API. A datastore may use Ceph RBD or NAS
storage without supplying application buckets. Record the chosen
[storage interfaces](../architecture/compute/runtime.md#storage-interfaces) separately;
object endpoints and scoped credentials belong to the consuming service inputs.

## Loading and overrides

The shared Linux deployment helper passes variable files in this order:

1. Shared platform profile.
2. Shared template catalog.
3. Tier common inputs, then optional environment common inputs.
4. Deployment inputs, then optional environment deployment inputs.

Later assignments win. Terraform replaces a map value rather than deep-merging
it [1]. A storage override must therefore include every class that deployment uses.
Guest-level placement overrides still take precedence inside the tier's modules.

Network references use two variables so tier-specific entries do not erase the
shared catalog. Each Linux deployment passes the following to its tier-local
inventory resolver:

```hcl
network_zones = merge(var.shared_network_zones, var.network_zones)
```

The local entry wins by **network name**, replacing that complete network object [3].
For example, Tier 0 can add `identity` while inheriting `application`; Tier 2 can
replace `application` with a dedicated lab subnet. Include the complete attachment
when overriding it. No per-field or cross-file deep merge is performed.
See [network inputs](network-inputs.md) for the fields and override example.

The independent template-publication and Kubernetes roots keep their existing
input contracts; they do not load unrelated Linux guest settings. Their datastore
choices should follow the same approved project design.

The cluster's `vm_firmware` matches its approved image. Fresh Talos examples use
UEFI and a network-only NoCloud drive: `bootstrap_network` supplies prefix/gateway,
while `platform_host_ips` remains the single tier-owned IP map. Optional `dns_servers`
overrides qualified host defaults. No Linux users, SSH keys or machine-config
snippets are supplied on that drive; the Talos API owns machine configuration.
Omitted firmware and `bootstrap_network = null` preserve the older BIOS/DHCP contract.
See the [cluster inputs](../deployment/stage-4-kubernetes/procedures/talos-terraform.md#configure).

Network keys are guest attachments, not a list of every service a guest can
contact. Tier 1/2 do not need `identity`, `cryptography`, or `ceremony` attachments
just to consume authentication or certificates. See [network inputs](network-inputs.md).

## Local SSH access

Keep both public and private key files outside the repositories, normally under
the execution account's `.ssh/`. In the ignored tier-local `.env.local`, set the
public-key **path**, not its contents:

```dotenv
TF_VAR_ssh_public_key_files='["/home/operator/.ssh/id_ed25519.pub"]'
```

Use the actual execution-host path. Terraform reads existing public files at
plan time [2]; it does not copy them into `.tfvars`. The module rejects files
that do not have single-line OpenSSH public-key syntax. This is a format check,
not cryptographic key verification. Ansible uses the matching private
key through `ssh-agent` or local SSH client configuration. Never pass a private
key to Terraform. Cluster-node APIs such as Talos do not use this Linux SSH path.

Git ignore rules cover local inputs and common SSH-key filenames. Ignore rules
do not protect files already tracked or added with `git add -f`; review the
staged diff and enable the project's secret-scanning policy before pushing.
Public keys can appear in cloud-init and Terraform state; protect state and
plans even though a public key is not a private credential.

## OS baseline boundary

Shared's [baseline role](../../shared/ansible/roles/baseline/tasks/main.yml) manages
repository/shell proxy settings, timezone and the selected IPv6 sysctl policy.
It is not a full security, time-synchronization or service-installation role.

SSH access policy, NTP/chrony, host-firewall rules and audit collection must be
prepared and verified through approved templates/OS configuration and the relevant
service procedures. The separate guarded [Linux host security profile](../deployment/foundation/proxmox/host-security.md)
supplies native SSH, chrony, firewalld and audit controls with tier-owned inputs;
it is not silently enabled by the baseline. Service-specific roles add only their implemented controls;
an installed listener does not imply a permitted or safely restricted network path.

Former `baseline_manage_packages`, `baseline_manage_ssh`,
`baseline_disable_password_auth`, `baseline_permit_root_login`,
`baseline_manage_firewall` and `baseline_ntp_enabled` settings had no implementing
tasks. Removing these unused defaults does not alter an existing machine or harden
it. Existing local copies of those values must not be counted as enforced controls.
Verify effective SSH, time, firewall and audit behavior before accepting a host.

## Existing collections

Refresh preserves local `common.tfvars`, environment files, and state. Their
explicit values continue to override the new profile. Move common storage and
placement values into the shared profile deliberately. To consolidate an existing
network, add its reviewed complete entry under `shared_network_zones` in the
project-owned profile, then remove only the matching duplicate from local
`network_zones`. Compare plans in every consumer before applying changes.
Refresh does not add this entry to an existing owned profile or remove local duplicates;
older tier-local maps continue working because `shared_network_zones` defaults to `{}`.
Existing `ssh_public_keys` inputs remain accepted
for compatibility; move their material to external `.pub` files and remove the
old assignment after verifying that the plan retains the same authorized keys.

## References

1. [Terraform input variables and precedence](https://developer.hashicorp.com/terraform/language/values/variables)
2. [Terraform file function](https://developer.hashicorp.com/terraform/language/functions/file)
3. [Terraform merge function](https://developer.hashicorp.com/terraform/language/functions/merge)
