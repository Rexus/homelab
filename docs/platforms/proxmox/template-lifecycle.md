# Proxmox template lifecycle

Tier 0 owns base template creation, updates, candidate testing, and release
approval, including all implementation code. Consuming tiers own their VMs
and select approved template versions. AlmaLinux, Rocky Linux, and Talos use
the same local-image import path. Talos cluster bootstrap remains separate.

**Initial template publication is Day 0-1 work.** Run it from a protected local
execution host before creating managed VMs, including the first control-cluster
nodes. Hosted CI or GitOps scheduling is an optional Day 2 addition to the same
Tier 0-owned automation, not a prerequisite for creating templates.

## Table of contents

- [Prerequisites](#prerequisites)
- [Ownership](#ownership)
- [Local workflow](#local-workflow)
- [Updates and promotion](#updates-and-promotion)
- [GitLab CI example](#gitlab-ci-example)
- [Existing collections](#existing-collections)
- [Offline validation](#offline-validation)
- [References](#references)

## Prerequisites

- A Proxmox host with protected Tier 0 administration, API access, and trusted TLS.
- Proxmox VE 9 with `Import` content enabled on the image datastore. The Tier 0
  module uses API-backed image upload and disk import. [1][2]
- Linux or WSL with Terraform; retain the provider lock file and a local
  provider mirror for recovery. The root constrains the supported provider.
- Approved, unpacked images on the execution host, exact releases, SHA256
  values, unused VMIDs, and approved bridge/storage allocations.
- A local Tier 0 checkout at a reviewed revision; this publisher does not need shared.

Verify vendor provenance before approving images for Tier 0. For an offline
custody deployment, acquire and verify outside the air gap, then transfer through
the approved custody procedure. Matching a locally supplied checksum detects
changed bytes; it is not, by itself, proof of vendor authenticity. No job
downloads from the Internet.
See the [Enterprise Linux image guide](enterprise-linux-template.md) or
[Talos image guide](talos-template.md) for source selection.

## Ownership

| Location | Owner and purpose |
| --- | --- |
| `templates/proxmox.yml` | Tier 0: versioned image catalog, hashes, VMIDs, and placement |
| `terraform/templates/` | Tier 0: native Terraform template publication root |
| `ci/gitlab-templates.yml.example` | Tier 0: developer-owned optional CD pipeline starter |
| `terraform/environments/template-refresh/` | Tier 0: staged mutable Linux package refresh |
| `terraform/environments/immutable-template/` | Tier 0: optional image-based Linux builder |
| `terraform/modules/proxmox_templates/` | Tier 0: file import and unbooted template resources |
| `scripts/proxmox-templates.sh` | Tier 0: local publication entry point |
| `packer/` | Tier 0: optional custom-image build definitions and inputs |
| Tier 0 Ansible playbooks and roles | Linux builder configuration using shared baseline helpers, never Talos guest configuration |
| consuming tier's template mappings | approved versions for that tier's new guests |

Templates are stopped image artifacts, not managed guest hosts. Their catalog
does not replace the shared Terraform/Ansible host inventory within each tier.
Builder VMs still use Tier 0 inventory and group vars.

The image-import publisher does not require a builder VM or an existing clone
template. `template-refresh` and `immutable-template` are later builder paths
that need an existing Linux template; do not use them as the only first-image
or recovery path. All Proxmox VM template automation remains Tier 0-owned,
regardless of which tier will consume the resulting image.

## Local workflow

From `homelab-iac/homelab-tier-0`, initialize the local catalog:

```bash
bash scripts/proxmox-templates.sh init
```

In a private source checkout, start in `tier-0/` and use the same commands.
Edit `templates/proxmox.yml`; remove
unused example entries before the first apply. Record exact releases and the
unpacked image hashes, and use absolute local artifact paths. The initializer
does not overwrite an existing catalog.

Supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through the shell or
protected runner environment. The token format is `user@realm!token=secret`.
This native-provider workflow does not load `.env.local` or the Linux wrapper's
`TF_VAR_proxmox_*` aliases. TLS verification stays enabled. [3]

```bash
bash scripts/proxmox-templates.sh plan
```

Review the plan, then publish exactly that saved plan:

```bash
bash scripts/proxmox-templates.sh apply
```

The default state is `.terraform/state/proxmox-templates/terraform.tfstate`;
working data and the saved plan stay in `.terraform/`. To use another recovery
state location, set `TEMPLATE_STATE_PATH` to its absolute path **before both
plan and apply**. `TEMPLATE_CATALOG_FILE` similarly selects an absolute catalog
path. Back up state independently of the cluster and CI service.

Only new stopped template candidates are published. No guest is booted,
cluster created, existing template deleted, or consumer catalog changed.
The module blocks resource destruction and replacement while its lifecycle
guards remain in configuration. Do not remove those guards during normal updates.

## Updates and promotion

1. Add a new versioned catalog entry with a new VMID and image checksum.
2. Plan and publish it; retain existing entries and artifacts for rollback.
3. Boot disposable clones on approved test networks and test the OS-specific
   first-boot, shutdown, and provisioning path. Never boot the template itself.
4. Record approval in project documentation. Update the consuming tier's
   template mapping only after its destination-side checks pass.
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
[Talos guide](talos-template.md) for the separate machine lifecycle.

Tier 1 and Tier 2 consume approved templates or transferred image artifacts.
Use controlled distribution for connected platforms and offline handoff across
custody boundaries. VMIDs are local to a Proxmox cluster: import into another
cluster under one designated owner and record its destination ID. The kit does
not automate cross-cluster transfer or open a route into offline custody.

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
publish; a stale plan must be regenerated. Test the YAML in your instance's
CI Lint before enabling it. The example publishes new image revisions, not
unattended same-ID replacements or live Talos upgrades.

A general Tier 1 runner must not hold Tier 0 administration credentials. The
code acceptance, approval, runner, and credentials for these jobs need Tier 0
protection; a branch name or runner tag alone is not a boundary. For offline
custody, the execution path must also remain inside the air gap.

Until that path exists, or whenever it is unavailable, use local commands from
an approved Tier 0 workstation with the same state and artifacts. Hosted CI
is a Day 2 convenience, never a bootstrap or recovery prerequisite.

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

See [refresh ownership](../../reference/generated-repository-model.md#refresh-and-local-ownership).
For collections that already keep inputs in Tier 0 but use shared template
code, follow the [automation ownership upgrade](../../reference/generated-repository-model.md#automation-ownership-upgrade).
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
