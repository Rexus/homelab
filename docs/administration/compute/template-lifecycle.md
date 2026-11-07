# Proxmox template lifecycle

Tier 0 owns base template creation, updates, candidate testing, and release
approval, including all implementation code. Consuming tiers own their VMs
and select approved template versions. AlmaLinux, Rocky Linux, Debian, and Talos use
the same local-image import path. Kubernetes cluster bootstrap remains separate.

**Initial template publication is a foundation prerequisite.** Run it from a protected local
execution host before creating managed VMs, including the first control-cluster
nodes. Hosted CI or GitOps scheduling is an optional operational addition to the same
Tier 0-owned automation, not a prerequisite for creating templates.

## Table of contents

- [Prerequisites](#prerequisites)
- [Ownership](#ownership)
- [Local workflow](#local-workflow)
- [Adopt existing templates](#adopt-existing-templates)
- [Verify fixed RAM after adoption](#verify-fixed-ram-after-adoption)
- [Interrupted publication](#interrupted-publication)
- [Updates and promotion](#updates-and-promotion)
- [Replace a boot disk](#replace-a-boot-disk)
- [Mutable Linux refresh](#mutable-linux-refresh)
- [GitLab CI example](#gitlab-ci-example)
- [Existing collections](#existing-collections)
- [Offline validation](#offline-validation)
- [References](#references)

## Prerequisites

- A Proxmox host with protected Tier 0 administration, API access, and trusted TLS.
- The publishing token's [effective image-storage permissions](../../deployment/foundation/proxmox/api-access.md#validate-access)
  include `Datastore.AllocateTemplate`, `Datastore.Audit` and `Datastore.AllocateSpace`.
  Verify before the first upload; read-only discovery is not an upload permission check.
- Proxmox VE 9 with `Import` content enabled on the image datastore. The Tier 0
  module uses API-backed image upload and disk import. [1][2]
- Linux or WSL with Terraform 1.7+; retain the provider lock file and a local
  provider mirror for recovery. The root constrains the supported provider.
- Apply and live verification also require the accepted Ansible runtime and Tier 0's
  Python/collection requirements. They complete template settings through native Proxmox modules.
- Approved, unpacked images on the execution host, exact releases, SHA256
  values, unused VMIDs, and approved bridge/storage allocations.
- Free space for upload staging on the execution host and Proxmox, plus the retained
  image files and template disks. See [space checks](#interrupted-publication).
- A local Tier 0 checkout at a reviewed revision. The shared platform profile supplies
  storage-class references when available; explicit catalog datastore IDs also work without Shared.

Verify vendor provenance before approving images for Tier 0. For an offline
custody deployment, acquire and verify outside the air gap, then transfer through
the approved custody procedure. Matching a locally supplied checksum detects
changed bytes; it is not, by itself, proof of vendor authenticity. No job
downloads from the Internet.
Use the [common VM template guide](../../deployment/foundation/proxmox/templates.md)
for image selection and GUI import, including Talos Image Factory, unpacking and firmware.

Fresh publication examples select UEFI (`bios: ovmf`, `machine: q35`) with a 4m
EFI disk and pre-enrolled keys off. The publisher selects VirtIO SCSI Single for
Alma/Rocky/Debian and non-Single `virtio-scsi-pci` for Talos, including the matching
IO-thread setting. The QEMU agent is enabled by default; the image must contain it
(Talos needs the Factory extension). [9]
Set `qemu_agent: false` for an image without that component. All server templates and
VMs use fixed memory with ballooning disabled, regardless of OS family.
Omitted firmware inputs
retain existing BIOS templates. Add a new candidate VMID rather than changing
an existing template's boot contract; consuming clusters must match it explicitly.

## Ownership

| Location | Owner and purpose |
| --- | --- |
| `templates/proxmox.yml` | Tier 0: versioned image catalog, hashes, VMIDs, and placement |
| `terraform/deployments/templates/` | Tier 0: native Terraform template publication root |
| `ci/gitlab-templates.yml.example` | Tier 0: developer-owned optional CD pipeline starter |
| `terraform/deployments/template-refresh/` | Tier 0: staged mutable Linux package refresh |
| `terraform/deployments/immutable-template/` | Tier 0: optional image-based Linux builder |
| `terraform/modules/proxmox_templates/` | Tier 0: file import and unbooted template resources |
| `scripts/proxmox-templates.sh` | Tier 0: local publication entry point |
| `packer/` | Tier 0: optional custom-image build definitions and inputs |
| Tier 0 Ansible playbooks and roles | Template API policy/verification and Linux builder configuration; no Talos guest SSH |
| `ansible/vars/proxmox-api.yml` | Stateless API/TLS defaults for template plays; credentials come from the execution environment |
| shared `templates/proxmox-catalog.tfvars` | one approved consumer catalog, maintained through Tier 0 review |
| consuming tier's template selection | approved VMID for that tier's new guests, not another template recipe |

Templates are stopped image artifacts, not managed guest hosts. Their catalog
does not replace the shared Terraform/Ansible host inventory within each tier.
Builder VMs still use Tier 0 inventory and group vars.

The image-import publisher does not require a builder VM or an existing clone
template. `template-refresh` and `immutable-template` are later builder paths
that need an existing Linux template; do not use them as the only first-image
or recovery path. All Proxmox VM template automation remains Tier 0-owned,
regardless of which tier will consume the resulting image.

## Local workflow

On the prepared bootstrap host, install the apply/verification dependencies from
the **Tier 0 root**. This is the same environment used by disk maintenance:

```bash
python3 -m venv "$HOME/.local/share/homelab/venv"
source "$HOME/.local/share/homelab/venv/bin/activate"
python3 -m pip install --upgrade 'ansible-core>=2.17' -r ansible/requirements.txt
ansible-galaxy collection install 'community.proxmox:>=2.1.0,<3.0.0' --force
```

Activate that environment in each new deployment shell. Use approved pre-staged
wheels/collections for offline installation; see [local tooling](../../development/local-setup.md#ansible-environment).

From `homelab-iac/homelab-tier-0`, initialize the local catalog:

```bash
bash scripts/proxmox-templates.sh init
```

In a private source checkout, start in `tier-0/` and use the same commands.
Access through a symlinked parent directory is supported; default state and working
data remain in the physical Tier 0 checkout, not a second location under the alias.
Edit `templates/proxmox.yml`; remove
unused example entries before the first apply. Record exact releases and the
unpacked image hashes, and use absolute local artifact paths. The initializer
does not overwrite an existing catalog.

Initialization also creates `.env.local` from `env.local.example` if absent, with
owner-only permissions. Edit its endpoint, token ID and secret; it is ignored by Git.
Use **`--env-file .env.local`** on local plan/import/apply commands. The script parses
literal assignments without executing shell expressions and maps `PROXMOX_API_URL`,
`PROXMOX_API_TOKEN_ID` and `PROXMOX_API_TOKEN_SECRET` to the provider's native variables.
Do not run `source`, `set -a` or manual token concatenation.

Runners may instead export `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN`
(`user@realm!token=secret`) or the three aliases and omit `--env-file`.
Conflicting native/alias credentials are rejected. TLS verification stays enabled;
complete the [bootstrap CA trust procedure](proxmox-tls.md#step-1-trust-the-bootstrap-ca)
first, even before platform PKI exists. [3]

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

Review the plan, then publish exactly that saved plan:

```bash
bash scripts/proxmox-templates.sh apply --env-file .env.local
bash scripts/proxmox-templates.sh verify --env-file .env.local
```

`apply` publishes the reviewed Terraform plan, then runs the Tier 0
[template-policy play](../../../tier-0/ansible/playbooks/maintenance/template-policy.yml)
against the applied template identities, using common
[API defaults](../../../tier-0/ansible/vars/proxmox-api.yml). It explicitly disables ballooning and clears
residual `ciuser`, `cipassword` and `sshkeys`, preserving CloudInit media, DHCP,
disks, EFI, NICs and allocated RAM. A second apply makes no further policy writes.
Only after successful raw API verification does the wrapper refresh the original state.
Direct `terraform apply` omits this provider-compatibility phase; use the wrapper. [17]
This clears Proxmox account settings, not files/accounts inside a previously booted
image; use approved unbooted images or the [Linux builder cleanup](#mutable-linux-refresh).

`verify` reads the actual API configuration and exits nonzero if the policy is not
satisfied. It changes neither Proxmox settings nor Terraform state. To inspect one entry,
add `--template rocky-build-1`; the default checks every applied template.
The API token needs `VM.Config.Memory` and `VM.Config.Cloudinit` on the selected templates.

The default state is `.terraform/state/proxmox-templates/terraform.tfstate`;
working data and the saved plan stay in `.terraform/`. To use another recovery
state location, set `TEMPLATE_STATE_PATH` to its absolute path **before both
plan and apply**. `TEMPLATE_CATALOG_FILE` similarly selects an absolute catalog
path. Back up state independently of the cluster and CI service.

For fresh publication, only new stopped template candidates are published. No guest is booted,
cluster created, existing template deleted, or consumer catalog changed.
The module blocks resource destruction and replacement while its lifecycle
guards remain in configuration. Do not remove those guards during normal updates.

### Catalog fields and defaults

The YAML catalog is an input file, not another IaC implementation. The resources live in
Tier 0's `terraform/modules/proxmox_templates/`; `terraform/deployments/templates/main.tf`
merges `all:` into each entry under `templates:`. A build overrides individual fields;
lists such as `tags` replace the common list rather than deep-merging it.
Set common site choices such as bridge, VLAN and storage in `all:` once. Each image
inherits them. Technical defaults stay in the implementation; add optional fields
only when the selected image or site needs a different value.

| Input | Meaning |
| --- | --- |
| `all:` | Common placement, hardware, firmware, agent and additional tags |
| `bridge` | Template NIC bridge; defaults to `vmbr0`, with a per-build override where needed |
| `vlan_id` | Common template VLAN in `all:`; starter uses example VLAN 10; set the site's value or `null` for untagged |
| `nic_firewall` / `nic_mtu` | Optional overrides; omitted values enable the NIC firewall and select MTU 1500 |
| `scsi_hardware` | Optional override; normally omitted so OS family selects Single for Alma/Rocky/Debian or non-Single for Talos |
| `qemu_agent` / `cpu_type` | Optional overrides; defaults are `true` / `x86-64-v3` |
| `memory_mb` | Fixed template RAM; defaults to 2048 MiB with ballooning disabled for every OS; actual service sizing is applied to clones |
| `disk_size_gb` | Template capacity; defaults to 10 GiB, never below the source image's virtual size; cloned service disks are sized separately |
| `storage_class` | Class in Shared `config/platform.tfvars`, selecting its `vm_disk` datastore |
| `datastore_id` | Explicit live disk/EFI storage override; wins over `storage_class` |
| `image_datastore_id` | Tier 0 staging datastore with Import content; independent of live storage |
| `cloud_init_drive` / `cloud_init_datastore_id` | NoCloud media at `ide2` with IPv4 DHCP / override of class `cloud_init_drive` or live disk storage |
| `family` / `distribution` | OS family (`redhat`, `debian`, `talos`) / selected distribution (`alma`, `rocky`, etc.); Fedora uses the `redhat` family |
| `tags` | Extra image/variant tags, such as `[test]`; standard [image tags](../../reference/proxmox-conventions.md#template-tags) are generated automatically |
| `image_path` / `sha256` | Absolute local unpacked artifact path / approved hash of those bytes |
| `image_file_name` | Optional existing Import basename; defaults to `<vm_id>-<sha256>.raw` or `.qcow2` |
| `release` / `schematic_id` | Exact build version, optional `v` prefix / mandatory Talos Factory schematic |

Each build includes `tags: []` for optional extras such as `[test]`. Standard tags
describe the image and CPU profile, not template status or tier ownership. The
`template_candidates` output includes the resolved tags for consumer-catalog review.
Existing local `tags` remain explicit extras: remove old `template`, `tier-0`, `x86_64` or
redundant distribution-version entries there to adopt the current convention.
Updating template tags does not retag already-created clones or rewrite Shared's catalog.

`release` records the approved version/build, not the template name or image filename.
For example, `10.0-20250601` and `v1.14.0` illustrate the accepted format; use the
actual artifact's version. Replace all `REPLACE_WITH_*` values; `latest`/`stable` aliases
are rejected. `vm_id` must be an integer of at least 100 and match the existing VMID
when adopting. Validation errors identify the catalog key, field and rejected value.

The script loads the sibling Shared platform profile if present. Use `--platform-file PATH`
or `TEMPLATE_PLATFORM_FILE` for another profile; catalog `datastore_id` and `node_name`
override shared references. A missing storage class fails validation rather than falling
back silently. Shared owns no template resources, image staging inventory or state.

Existing flat catalogs remain valid; `all:` is optional. Legacy `family: alma`/`rocky`
is accepted. Preserve existing hardware/firmware and explicit `qemu_agent: false` where
required; the new default is true. Changing a revision's inputs can cause drift even
when its VMID is unchanged. Review before applying, never force replacement to fix adoption.
For existing templates, set `bridge` and `memory_mb` to their actual values before
adoption or refresh; omitted memory now defaults to 2048 MiB rather than 4096 MiB.
Omitted NIC settings now use firewall enabled and MTU 1500. Explicit settings still
win. An existing `all.scsi_hardware` overrides automatic selection for every image;
remove it after review to use the OS profiles, or retain an explicit exception.
Fresh examples include DHCP CloudInit media, matching the GUI guide; existing catalogs
without `cloud_init_drive` keep the no-media behavior. All addresses/accounts stay clone-local.
The publisher leaves the optional CloudInit format to Proxmox/provider state:
Linux defaults to NoCloud, and an existing explicit format is retained. Forcing
`nocloud` onto an imported template whose format was implicit can make the pinned
provider propose replacement, despite equivalent Linux behavior. [7][8]

The x86 publication path also leaves CPU architecture implicit. `cpu_type` still
selects the configured CPU model and its tag; an explicit architecture assignment
would request a root-restricted Proxmox operation that API tokens cannot perform. [3]

Ten GiB is a base-image starting capacity, not the recommended disk size for every
service. Check the verified image's virtual size before importing; increase the
template setting when the image requires it. Existing larger disks are not shrunk
by changing this default. Production clones receive their own role-specific disk sizing.
DHCP remains enabled on reusable templates; a clone's explicit network configuration
replaces it. No site-specific account/password is stored in the template. [11]

Discard remains enabled so supported guest filesystems can return unused blocks to
thin-provisioned storage. On adoption, `discard = "ignore" -> "on"` is intentional:
it enables guest TRIM passthrough, not boot-disk replacement or capacity reduction.
Guest-side TRIM still needs to run. The socket-backed serial
port remains available for console diagnostics; visible output depends on the image's
serial-console configuration. The graphical display is retained. [10][11]

## Adopt existing templates

For manually created templates, **adopt instead of creating another copy**. Stop other
writers and back up any existing Terraform state. Confirm that no other root owns the
VMIDs/files. Populate the catalog with the actual VMID, name, node, image datastore,
hardware and original artifact/hash; keep map keys stable afterwards.

1. Find the exact uploaded filename in **Node > storage > Import**, or run
   `pvesm list <image_datastore_id> --content-type import` on the Proxmox host.
   Set `image_file_name` to that basename, for example `nocloud-amd64.raw`; no rename
   to the default hash-based convention is necessary. Independently confirm the remote
   file's SHA256 against the approved artifact; discovery checks identity, **not remote bytes**.
   Upload metadata is write-once: adoption does not re-upload or change existing file
   contents. `image_file_name` is checked against the actual filename. A changed
   artifact/version requires a new catalog key/VMID, not an in-place source edit.
2. From the Tier 0 root, prepare the adoption plan:

   ```bash
   bash scripts/proxmox-templates.sh import --env-file .env.local
   ```

   Terraform reads the catalog, discovers matching files and VMIDs using the provider,
   and adds native `import` blocks to the plan. A matching VM must be a stopped template
   with exactly the configured name and node. Ordinary/running/mismatched VMs fail the
   adoption gate. Unrelated resources are not imported. API visibility must cover every
   selected VMID; an invisible resource cannot be distinguished from an absent one.
3. Review **imports and all proposed changes**. Missing resources are planned as creations;
   an existing VM may need input alignment. Adoption is not a guarantee of a no-change plan.
   Stop on disk/firmware changes, replacement or unexpected deletion; do not remove lifecycle guards.
   After acceptance, run the same `apply --env-file .env.local` command above.

| Plan action | Effect when applied |
| --- | --- |
| Will be imported | Records an existing resource in this state; inspect any accompanying changes |
| `+ create` | Creates a missing catalogued image file or template; expected for new entries |
| `~ update in-place` | Changes the existing template's actual configuration |
| `-/+` replacement | Deletes and recreates a resource; blocked by `prevent_destroy` |

Importing does not automatically copy existing hardware into the catalog. Set common
VLAN, storage and sizing under `all:`; use per-build overrides only for exceptions.
MTU, NIC firewall and controller defaults normally need no entries. For an accepted
template with different settings, record the exception explicitly. Review boot order and CloudInit
account/network changes too; importing state is not approval to change those settings.

The `import` command prepares a plan only: it does not write state or change Proxmox.
Applying that plan records imports and performs any other approved listed actions. [6]
Then run a normal `plan --env-file .env.local` and confirm the expected no-change result.
Already-managed identities are not re-imported. Partial adoption after an interrupted apply
can be reconciled by rerunning `import` with the same catalog/state; never start with a fresh state.
State, provider cache and saved-plan paths are identical for publication and adoption.

### Verify fixed RAM after adoption

The pinned provider reads an **absent** Proxmox `balloon` field as `floating = 0`,
but Proxmox enables the ballooning device when the field is absent. An adopted GUI
template can therefore show a no-change plan while ballooning remains enabled.
The configured `floating = 0` policy alone is not live acceptance evidence. [8][16]

Omitting `initialization.user_account` can also leave residual account fields in the
API even when a plan shows their removal. The wrapper's native policy phase completes
both operations without removing the CloudInit drive or its network configuration. [8][17]
From **Tier 0**, use the normal workflow, including when Terraform itself has no changes:

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
bash scripts/proxmox-templates.sh apply --env-file .env.local
bash scripts/proxmox-templates.sh verify --template rocky-build-1 --env-file .env.local
```

Require `ballooning_disabled: true`, `cloud_init_accounts_cleared: true` and
`other_settings_preserved: true` in the verification output. A Terraform
**Apply complete** line alone does not establish these live settings.
The policy refuses running, locked, ordinary or mismatched VMs. It neither creates
nor replaces guests, and existing clones keep their own configuration.

For an independent read from the hosting Proxmox console:

```bash
read -r -p "Stopped template VMID (example: 110): " TEMPLATE_VMID
qm config "$TEMPLATE_VMID" --current 1 | grep -E '^(name|template|memory|balloon):'
```

Require explicit `balloon: 0`. Inspect **Cloud-Init** in the GUI to confirm the account,
password and SSH-key fields are empty; the CloudInit drive and networking remain present.
The [disk-maintenance preview](template-disk.md#step-4-verify-the-replacement) also
reports live `ballooning_disabled` without changing the memory setting.
Review the compatibility phase when upgrading the pinned provider; retain live verification.

## Interrupted publication

A failed apply can still record successful imports or completed resources. Keep the
same catalog, keys and `.terraform/state/proxmox-templates/terraform.tfstate`; back up
the state before recovery. The wrapper discards the saved plan after any apply attempt.
For older wrappers that leave it behind, prepare a new `import` plan rather than retrying it.

For upload `broken pipe` or `use of closed network connection`, inspect the first
upload error and Proxmox logs. These messages alone do not identify the cause.
Later postcondition errors can follow an unsuccessful creation; retain the filename guard.
In Proxmox's journal, a client IP identifies the connection, not the filesystem that
failed. Preserve the complete error/path; capacity readings after failed temporary
files have been removed do not necessarily describe capacity during the upload.
The bare `problem with client ...; No space left on device` message can also result
from an AnyEvent connection-buffer limit: that library uses `ENOSPC` for buffer
overflow. It does not by itself establish disk exhaustion. Check effective upload
permissions and installed Proxmox HTTP-server packages as well as capacity; a missing
upload privilege has produced misleading connection errors. [12][14][15]

| Check | Location and expected result |
| --- | --- |
| Space | Identify the machine/path in the exact error. Check capacity and inodes on the execution host's temporary filesystem, Proxmox `/var/tmp`, and the image datastore; free Proxmox storage does not establish execution-host capacity. [1][12] |
| Upload permission | Publishing identity has `Datastore.AllocateTemplate` on the image datastore; privilege-separated tokens need their own matching ACLs. [API access](../../deployment/foundation/proxmox/api-access.md#4-grant-storage-permissions-to-the-group) |
| Storage content | Datacenter > Storage permits `Import` on the selected image datastore. Read/list access does not prove upload capability. [1] |
| Connection | Check Proxmox service logs, `/var/log/pveproxy/access.log`, and any intervening proxy/firewall for rejected requests, resets or body/time limits. Do not disable TLS verification. |

On the **target Proxmox host**, inspect the failure time; adjust the time window if needed:

```bash
journalctl -u pveproxy -u pvedaemon --since '-30 min' --no-pager | tail -n 80
df -h / /var/tmp /var/lib/vz
df -i /var/tmp /var/lib/vz
pvesm status
```

On the **execution/bootstrap host**, inspect its own temporary filesystems separately:

```bash
df -h / /tmp /var/tmp
df -i /tmp /var/tmp
findmnt -T /tmp
```

`/var/lib/vz` is the default Proxmox `local` path; check the configured path if different.
Free space on `local-zfs` does not establish free space in Proxmox `/var/tmp` or the
bootstrap VM. The provider stages uploads on the **execution host**, documenting
roughly twice the source size plus overhead. A memory-backed `/tmp` can fill even when
the VM's disk has plenty of space. [1][3][12]
For a different, sufficiently sized temporary filesystem, create a private writable
directory there and set its **literal absolute path** as `PROXMOX_VE_TMPDIR` in Tier 0's
ignored `.env.local`. The template wrapper loads it with `--env-file .env.local`;
this provider-native setting affects execution-host staging, not Proxmox paths. [3]
The wrapper applies with `-parallelism=1` so uploads/imports run sequentially. [13]
This reduces peak temporary use; it does not supply capacity for even one image or
the cumulative retained artifacts. Expand or free the affected filesystem after
identifying its contents; do not delete `base-*` disks or files used by active uploads.

Then inspect the image datastore's **Import** list. If a complete file exists without
a state entry, verify its remote SHA256 and set its exact `image_file_name` before
adopting it. Do not adopt incomplete bytes or delete state to make a retry succeed.
Resolve the cause, then rerun `import --env-file .env.local` from **Tier 0** and review
the new plan. Uploads and guest updates are separate actions; importing a VM does not
mean its planned settings or boot-disk image have been applied.

## Updates and promotion

1. Add a new versioned catalog entry with a new VMID and image checksum.
2. Plan and publish it; retain existing entries and artifacts for rollback.
3. Boot disposable clones on approved test networks and test the OS-specific
   first-boot, shutdown, and provisioning path. Never boot the template itself.
4. Record approval in project documentation. Promote references into the
   [shared consumer catalog](../../reference/template-catalog.md) after destination-side checks pass.
5. Retire old artifacts only through a separate reviewed state/resource change,
   after confirming no clones or recovery procedures still require them.

For AlmaLinux/Rocky package maintenance, the existing `template-refresh`
workflow remains available from Tier 0. Its same-ID replacement is explicitly
opt-in and is not invoked by this publisher. Do not give two Terraform roots
ownership of the same template VMID. For bootc, transfer approved OCI images
into a recoverable Tier 0 image source; a live Tier 1 registry must not be the
only recovery source. Use offline transfer when crossing a custody air gap.

For Talos, publish a fresh raw image for each release/schematic revision;
do not run package updates, SSH provisioners, or Linux cleanup roles on it.
Updating the template does not upgrade running cluster nodes. Follow the
[Talos guide](../../deployment/foundation/proxmox/templates.md) for the separate machine lifecycle.

Tier 1 and Tier 2 consume approved templates or transferred image artifacts.
Use controlled distribution for connected platforms and offline handoff across
custody boundaries. VMIDs are local to a Proxmox cluster: import into another
cluster under one designated owner and record its destination ID. The kit does
not automate cross-cluster transfer or open a route into offline custody.

## Replace a boot disk

To keep an existing template VMID and replace only its OS image, follow the
[boot-disk maintenance path](template-disk.md). It uses the published artifact,
previews the current disk, preserves the previous base volume for rollback and
refreshes the original Terraform state. Normal adoption/apply does not replace
the bytes of an existing boot disk; a changed `import_from` reference is not a reimage.

## Mutable Linux refresh

This optional path is for AlmaLinux/Rocky Linux only, not Talos. The common
[template guide](../../deployment/foundation/proxmox/templates.md) owns the initial
image import. Use a disposable staged clone for packages/cleanup, never boot a
base template that is already being published by another Terraform root.

| Tier 0 input | Purpose |
| --- | --- |
| `terraform/deployments/template-refresh/terraform.tfvars` | Staged VM, source template, size/storage and final template conversion |
| `ansible/group_vars/template_refresh.yml` | Package preparation, cleanup and explicit same-ID replacement |
| `ansible/inventory/hosts.yml` | `template_refresh_builders` and the Proxmox host used for replacement |

1. Review `bash scripts/deploy.sh template-refresh --env test --plan-only`, then
   create/update the staged clone with the same command without `--plan-only`.
   The recipe verifies required guest packages and cloud-init behavior.
2. Set `template_refresh_prepare_for_template: true`; run with `--ansible-only`
   to clean cloud-init state, SSH host keys and caches.
3. Set the staged VM's `template = true`, `started = false`; run with
   `--terraform-only`. Test disposable full clones before promotion.
4. Only for an approved same-ID replacement window, set
   `template_refresh_replace_enabled: true`, `template_refresh_prepare_builders: false`,
   then run with `--ansible-only`.

The last step **deletes the old target template** before replacing it. Quiesce
new clones and check linked-clone dependencies. Prefer new versioned VMIDs when
possible. Keep Shared's catalog aligned after explicit promotion; a builder can
use `template_catalog_id` for the final target's reference tags. Retain independent
artifacts and inputs before any destructive publication change.

## GitLab CI example

The generated Tier 0 `ci/gitlab-templates.yml.example` is seeded once and owned
by that project's developers. Enable it as `.gitlab-ci.yml` only after preparing:

- a Tier 0-protected GitLab job/approval path and dedicated shell runner tagged
  `tier0-templates`, with durable storage outside disposable job checkouts;
- the same reviewed Tier 0 commit and unmodified code for plan and publish;
- protected `TEMPLATE_STATE_PATH` and `TEMPLATE_CATALOG_FILE` values pointing
  to absolute paths available at the same locations in both jobs;
- local images and a provider mirror, plus masked/protected provider credentials;
- a protected default branch and publish environment, restricted CI logs and
  artifacts, and project-member-only CI visibility.

The example uses a resource group to serialize jobs and a blocking manual
publish step that consumes the saved plan. Plans and provider locks are the
only artifacts; state must persist independently. The `maintainer` artifact
access option requires GitLab 18.4 or later. [4][5]

Do not run jobs with the same state on different disks or use ephemeral local
state. Treat saved plans as sensitive. Review the plan job before approving
publish; a stale plan must be regenerated. Test the YAML in the instance's
CI Lint before enabling it. The example publishes new image revisions, not
unattended same-ID replacements or live Talos upgrades.

A general Tier 1 runner must not hold Tier 0 administration credentials. The
code acceptance, approval, runner, and credentials for these jobs need Tier 0
protection; a branch name or runner tag alone is not a boundary. For offline
custody, the execution path must also remain inside the air gap.

Until that path exists, or whenever it is unavailable, use local commands from
an approved Tier 0 workstation with the same state and artifacts. Hosted CI
is an operational convenience, never a bootstrap or recovery prerequisite.

## Existing collections

Refresh adds Tier 0 template files but never moves live configuration or state.
Existing `.deployment-setups`, root READMEs, jobs, and local inventories remain
owned. Before switching `template-refresh` or `immutable-template` from Tier 1:

1. Stop the old jobs and back up their state and live inputs.
2. Review control-network placement and privileges; repo movement does not secure a host.
3. Transfer the authoritative state and matching inputs under a reviewed
   migration, with the same resource identities. Do not apply an empty new
   Tier 0 state against VMs still owned by Tier 1.
4. Update both tiers' `.deployment-setups`, inventory, group vars, job paths,
   and owned READMEs. Review retained old roots and shared Packer vars manually.
5. Verify a no-change plan from the new owner before enabling its jobs.

See [refresh ownership](../../development/generated-repositories.md#refresh-and-local-ownership).
For collections that already keep inputs in Tier 0 but use shared template
code, follow the [automation ownership upgrade](../../development/generated-repositories.md#automation-ownership-upgrade).
That code-path change does not move state.

## Offline validation

From the upstream checkout, use Terraform 1.7 or later for the native mock tests:

```bash
terraform -chdir=tier-0/terraform/modules/proxmox_templates init -backend=false
terraform -chdir=tier-0/terraform/modules/proxmox_templates test
```

These tests inspect plans and validation failures without calling Proxmox.
They do not boot or verify real images; disposable clone tests remain required.

## References

1. [Proxmox provider file upload](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_file), accessed 2026-09-17.
2. [Proxmox provider VM resources](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_vm), accessed 2026-09-17.
3. [Proxmox provider authentication](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/index.md), accessed 2026-09-17.
4. [GitLab CI YAML reference](https://docs.gitlab.com/ci/yaml/), accessed 2026-09-17.
5. [GitLab resource groups](https://docs.gitlab.com/ci/resource_groups/), accessed 2026-09-17.
6. [Terraform configuration-driven imports](https://developer.hashicorp.com/terraform/language/import), checked 2026-11-06.
7. [Proxmox CloudInit format selection](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/QemuServer/Cloudinit.pm), checked 2026-11-06.
8. [Pinned provider CloudInit and memory import refresh](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/vm.go), checked 2026-11-07.
9. [Talos Proxmox controller and guest-agent requirements](https://docs.siderolabs.com/talos/v1.14/platform-specific-installations/virtualized-platforms/proxmox), checked 2026-11-06.
10. [Proxmox disk discard support](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#qm_hard_disk_discard), checked 2026-11-06.
11. [Proxmox CloudInit networking and serial consoles](https://github.com/proxmox/pve-docs/blob/master/qm-cloud-init.adoc), checked 2026-11-06.
12. [Proxmox API temporary upload files](https://github.com/proxmox/pve-http-server/blob/master/src/PVE/APIServer/AnyEvent.pm), checked 2026-11-07.
13. [Terraform apply parallelism](https://developer.hashicorp.com/terraform/cli/commands/apply#parallelism-n), checked 2026-11-07.
14. [AnyEvent connection-buffer limits and ENOSPC](https://metacpan.org/release/MLEHMANN/AnyEvent-7.17/view/lib/AnyEvent/Handle.pm), checked 2026-11-07.
15. [Upload connection errors resolved by Datastore.AllocateTemplate](https://github.com/bpg/terraform-provider-proxmox/issues/2047), checked 2026-11-07.
16. [Proxmox enables ballooning unless explicitly disabled](https://github.com/proxmox/qemu-server/blob/master/src/PVE/QemuServer.pm#L3325), checked 2026-11-07.
17. [Native Proxmox VM updates and selective setting deletion](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_kvm_module.html), checked 2026-11-07.
