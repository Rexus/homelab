# Platform inputs and local access

Shared holds references to existing infrastructure, not the infrastructure
resources or host inventory. Network references used across tiers are defined once;
each tier owns its specific networks, guest selections and overrides.

## Table of contents

- [Input ownership](#input-ownership)
- [Find supported settings](#find-supported-settings)
- [VM disk storage](#vm-disk-storage)
- [Initial guest placement](#initial-guest-placement)
- [Loading and overrides](#loading-and-overrides)
- [Local SSH access](#local-ssh-access)
- [OS baseline boundary](#os-baseline-boundary)
- [Existing collections](#existing-collections)

## Input ownership

| Location | Defines |
| --- | --- |
| Shared `config/platform.tfvars` | Project-owned storage, initial placement and common network references in `shared_network_zones` |
| Shared `config/guest-sizes.json` | Reusable size profiles |
| Shared `templates/proxmox-catalog.tfvars` | Published image references synchronized by Tier 0 apply; explicit default selection |
| Tier `terraform/common.tfvars` | Tier-specific `network_zones`, overrides of shared networks, and optional platform overrides |
| Tier deployment `.tfvars` | Guest hardware and resource selections |
| Tier Ansible inventory/group vars | Host names, groups, IPs, and service configuration |
| Local environment or secret injection | Provider access and local SSH public-key file paths |

Guest IDs follow the [VMID allocation convention](../02-conventions/vmid-convention.md),
including the Tier 0 Kubernetes exception and reserved lab/client/template groups. Reservations stay tier-local
and unique across the cluster; Shared is not an allocator.

The shared profile is a reference catalog, not a Terraform root. It contains
no resources, state, guest assignments, host addresses, credentials, or keys.
For example, the common `application` subnet is recorded here; `identity` and
`cryptography` remain Tier 0-specific references. Merely listing a network does
not connect a guest or authorize access to it.
Tier 0 approves infrastructure references; consumers may override permitted
values. Refresh preserves an existing project-owned profile; deleting it restores the current starter,
not the previous local choices. Recover actual site values from their independent backup before deployment.

`proxmox_storage_classes` maps VM-disk classes to existing Proxmox datastore IDs;
it does not describe an object-storage API. A datastore may use Ceph RBD or NAS
storage without supplying application buckets. Record the chosen
[storage interfaces](../01-architecture/06-data/README.md#storage-interfaces) separately;
object endpoints and scoped credentials belong to the consuming service inputs.

## Find supported settings

Configuration headers identify their variable definitions from the named repository root.
Read those definitions for supported fields, types, defaults and validation; edit values in the configuration file.

| Configuration | Variable definitions |
| --- | --- |
| Tier 0 `templates/proxmox.yml` | [Build fields and defaults](../../tier-0/terraform/modules/proxmox_templates/variables.tf), under `images`; [catalog aliases and resolution](../../tier-0/terraform/deployments/templates/main.tf); [root inputs](../../tier-0/terraform/deployments/templates/variables.tf) |
| Tier `terraform/deployments/<setup>/terraform.tfvars` | `variables.tf` in that same deployment directory; [Linux example](../../tier-0/terraform/deployments/foundation/variables.tf), [Kubernetes example](../../tier-0/terraform/deployments/kubernetes/variables.tf) |
| Tier `terraform/common.tfvars` and Shared `config/platform.tfvars` | The consuming deployment's `variables.tf`; [Linux network entry schema](../../tier-0/terraform/modules/environment_guests/variables.tf), under `network_zones` |
| Shared `templates/proxmox-catalog.tfvars` | [Linux reference schema](../../tier-0/terraform/modules/environment_guests/variables.tf), under `proxmox_template_catalog`; [Kubernetes reference schema](../../tier-0/terraform/deployments/kubernetes/variables.tf) |

Shared has no Terraform root: its files supply values to the consuming tier.
A module-only option must be exposed by the root before it can be set in `.tfvars`.
Template YAML builds use the separate catalog mapping linked above.

All Linux guest roots retain the `environment_guests.vm_instances` contract through to their VM module.
Set these per guest in **the owning tier's `terraform/deployments/<setup>/terraform.tfvars`**:

| Field | Behavior |
| --- | --- |
| `full_clone` | `true` by default; explicit linked clones require compatible accepted template/storage |
| `firmware` | Optional explicit match to the source template: BIOS, machine, SCSI controller and EFI enrollment; omission retains existing behavior |
| `initialization_datastore_id` | Optional Cloud-Init media datastore override; omission uses the selected storage-class mapping |
| `nic_firewall` | `true` by default; the NIC flag is separate from installed host/cluster firewall policy |
| `extra_disks` | Additional configured interfaces, capacities and optional datastore/class overrides; service Ansible owns safe initialization and mounts |
| `started`, `template`, `stop_on_destroy` | Explicit lifecycle controls; converting a VM to a template keeps it stopped |

Changing a supplied field now reaches the resource plan. Review existing deployments for intended
changes; firmware/storage moves and template conversion are not implicit migration procedures.

## VM disk storage

The logical class `local` is not the Proxmox datastore ID `local`. In Shared's
`config/platform.tfvars`, map each class to a datastore that accepts **Disk image**
(`images`) content on the eligible node. For a ZFS installation, the existing
`proxmox_storage_classes` map can contain this `local` entry:

Edit in **`<prefix>-shared/`**.

- `config/platform.tfvars`: `proxmox_storage_classes`: actual VM-disk datastore per class

```hcl
local = {
  vm_disk = "local-zfs"
}
```

Preserve the other classes. Use the actual datastore ID; LVM or Ceph installations
can use different names. An omitted `cloud_init_drive` inherits `vm_disk`; an explicit
value must also accept VM disks. Tier 0's `image_datastore_id` is separate: uploaded
raw/qcow2 artifacts can stay on `local` with **Import** content enabled.

For an attached data disk, match the service's device input to Terraform's `extra_disks[].interface`.
The reference `scsi1` disk uses `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`;
do not infer it from `/dev/sda` or `/dev/sdb` ordering. The guarded storage role resolves that device,
preserves existing identity checks and persists the filesystem mount by UUID.
If a local override still uses a disk letter, update that input after verifying the original volume;
refresh preserves existing private configuration and UUID pins.

After preparation, the service prints its actual UUID and the optional configuration key to pin.
The mount is already persistent; saving the guard makes later runs reject a different filesystem.
Each host needs its own UUID. When using `ansible/inventory/host_vars/<host>.yml`, remove the same
key from `-e`/`--ansible-vars` files: extra variables override host variables even when the value is empty.

## Initial guest placement

Before the first Linux deployment, set **Shared's** `config/platform.tfvars` to an
existing Proxmox node name, as shown under **Datacenter**:

Edit in **`<prefix>-shared/`**.

- `config/platform.tfvars`: `default_platform_node_name`: initial destination node

```hcl
default_platform_node_name = "pve01"
```

Use the node name, not an IP address, API URL or cluster name. The template catalog's
`node_name` identifies the clone source; it does not select the destination for new guests.
Each guest can override the default with `proxmox_node_name` in its tier-owned deployment
inputs. The default may stay `null` only when every selected guest supplies an override.

This is initial placement. Later Proxmox-managed VM migration follows the
[HA placement contract](../03-deployment/foundation/proxmox/step-1b-cluster-ha.md#make-guests-movable).

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

The template publisher loads the shared platform profile (or `--platform-file PATH`)
to resolve a catalog `storage_class` into its `vm_disk` datastore. Tier 0's YAML
`all:` supplies common build settings; each template can override them, including
an explicit `datastore_id`. `image_datastore_id` remains a Tier 0 staging reference,
not a shared live-disk class. The
[catalog contract](../05-operations/01-hosting/templates/template-lifecycle.md#catalog-fields-and-defaults)
defines the complete merge and override rules.
Kubernetes roots retain their separate input contract; neither path loads Linux guest inventory/settings.

The cluster's `vm_firmware` matches its approved image. Fresh Talos examples use
UEFI and a network-only NoCloud drive: `bootstrap_network` supplies prefix/gateway,
while `platform_host_ips` remains the single tier-owned IP map. Optional `dns_servers`
overrides qualified host defaults. No Linux users, SSH keys or machine-config
snippets are supplied on that drive; the Talos API owns machine configuration.
Omitted firmware and `bootstrap_network = null` preserve the older BIOS/DHCP contract.
See the [cluster inputs](../03-deployment/stage-4-kubernetes/procedures/talos-terraform.md#configure).
The optional [SDN subnet lookup](network-inputs.md#sdn-subnet-lookup) replaces
explicit prefix/gateway inputs with an existing VNet reference for either path.

Network keys are guest attachments, not a list of every service a guest can
contact. Tier 1/2 do not need `identity`, `cryptography`, or `ceremony` attachments
just to consume authentication or certificates. See [network inputs](network-inputs.md).

## Local SSH access

Linux clone key lists are empty by default. Before deployment, uncomment and configure
`TF_VAR_ssh_public_key_files` in the consuming tier's `.env.local`; Tier 0's setting does
not populate another tier. Reusable templates keep their CloudInit accounts/keys clear.

Keep both public and private key files outside the repositories, normally under
the execution account's `.ssh/`. In the ignored tier-local `.env.local`, set the
public-key **path**, not its contents:

Edit in the consuming **`<prefix>-tier-N/`** repository.

- `.env.local`: `TF_VAR_ssh_public_key_files`: existing public-key file paths on the execution host

```dotenv
TF_VAR_ssh_public_key_files='["/home/operator/.ssh/id_ed25519.pub"]'
```

Use the actual execution-host path. Terraform reads existing public files at
plan time [2]; it does not copy them into `.tfvars`. The module rejects files
that do not have single-line OpenSSH public-key syntax. This is a format check,
not cryptographic key verification. Ansible uses the matching private
key through `ssh-agent` or local SSH client configuration. Never pass a private
key to Terraform. Cluster-node APIs such as Talos do not use this Linux SSH path.

Linux VM clones receive these keys through `initialization.user_account.keys`, for
the `automation` account by default. Rerun the plan after setting the path. If the
plan redacts the enclosing initialization block, inspect the clone's **Cloud-Init >
SSH public key** after apply; template account-policy verification does not check clone keys.

Git ignore rules cover local inputs and common SSH-key filenames. Ignore rules
do not protect files already tracked or added with `git add -f`; review the
staged diff and enable the project's secret-scanning policy before pushing.
Public keys can appear in cloud-init and Terraform state; protect state and
plans even though a public key is not a private credential.

## OS baseline boundary

Additional sources and public trust are explicit local selections:

| Shared baseline input | Owned change |
| --- | --- |
| `baseline_trust_anchors` | Controller-side public CA files installed in the native EL/Debian trust store |
| `baseline_rpm_repositories` | New RPM sources with HTTPS URLs and pinned publisher-key fingerprints |
| `repository_proxy_dnf_sources` | Selected existing vendor stanzas redirected without replacing their keys; `direct: true` bypasses the proxy for that stanza |
| `baseline_apt_repositories` | Native deb822 sources with existing vendor keyrings, suites and components |
| `baseline_apt_retired_files` | Explicitly replaced whole source files, retained as `.save` copies |
| `baseline_apt_direct_hosts` | Exact internal APT publication hosts bypassing a global proxy |

The [Shared defaults](../../shared/ansible/roles/baseline/defaults/main.yml) own these schemas.
[Verified consumer deployment](../03-deployment/stage-3-trust/step-15b-verified-consumers.md)
applies the package/trust subset from the controller without changing guest time, IPv6 or SSH policy.

Shared's [baseline role](../../shared/ansible/roles/baseline/tasks/main.yml) manages
repository/shell proxy settings, explicitly selected existing DNF source URLs,
native package-verification defaults, timezone and the selected IPv6 sysctl policy.
It is not a full security, time-synchronization or service-installation role.
Package policy does not update packages or replace repository definitions/keys; see
[consumer verification](proxy-cache.md#consumer-verification-and-failure-behavior).

SSH access policy, NTP/chrony, host-firewall rules and audit collection must be
prepared and verified through approved templates/OS configuration and the relevant
service procedures. The separate guarded [Linux host security profile](../05-operations/01-hosting/linux-security.md)
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
