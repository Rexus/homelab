# Proxmox template lifecycle

Tier 0 owns base template creation, updates, candidate testing, and release
approval. Shared code implements the workflow; consuming tiers own their VMs
and select approved template versions. AlmaLinux, Rocky Linux, and Talos use
the same local-image import path. Talos cluster bootstrap remains separate.

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

- An isolated custody Proxmox host, API access, and locally trusted TLS certificate.
- Proxmox VE 9 with `Import` content enabled on the image datastore. The shared
  module uses API-backed image upload and disk import. [1][2]
- Linux or WSL with Terraform; retain the provider lock file and a local
  provider mirror for recovery. The root constrains the supported provider.
- Approved, unpacked images on the execution host, exact releases, SHA256
  values, unused VMIDs, and custody-local bridge/storage allocations.
- A local checkout of the Tier 0 and shared repositories, with reviewed revisions.

Acquire images outside custody and verify vendor provenance before controlled
transfer. Matching a locally supplied checksum detects changed bytes; it is
not, by itself, proof of vendor authenticity. No job downloads from the Internet.
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
| shared `terraform/modules/proxmox_templates/` | reusable file import and unbooted template resources |
| shared Ansible playbooks and roles | reusable Linux builder configuration, never Talos guest configuration |
| consuming tier's template mappings | approved versions for that tier's new guests |

Templates are stopped image artifacts, not managed guest hosts. Their catalog
does not replace the shared Terraform/Ansible host inventory within each tier.
Builder VMs still use Tier 0 inventory and group vars. Packer definitions remain
optional custom-build scaffolds in shared; build inputs belong to Tier 0.

## Local workflow

From `homelab-iac/homelab-tier-0`, initialize the local catalog:

```bash
bash ../homelab-shared/scripts/proxmox-templates.sh init
```

Use your prefix in the sibling path. Edit `templates/proxmox.yml`; remove
unused example entries before the first apply. Record exact releases and the
unpacked image hashes, and use absolute local artifact paths. The initializer
does not overwrite an existing catalog.

Supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through the shell or
protected runner environment. The token format is `user@realm!token=secret`.
This native-provider workflow does not load `.env.local` or the Linux wrapper's
`TF_VAR_proxmox_*` aliases. TLS verification stays enabled. [3]

```bash
bash ../homelab-shared/scripts/proxmox-templates.sh plan
```

Review the plan, then publish exactly that saved plan:

```bash
bash ../homelab-shared/scripts/proxmox-templates.sh apply
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
3. Boot disposable clones on custody-local networks and test the OS-specific
   first-boot, shutdown, and provisioning path. Never boot the template itself.
4. Record approval in project documentation. Update the consuming tier's
   template mapping only after its destination-side checks pass.
5. Retire old artifacts only through a separate reviewed state/resource change,
   after confirming no clones or recovery procedures still require them.

For AlmaLinux/Rocky package maintenance, the existing `template-refresh`
workflow remains available from Tier 0. Its same-ID replacement is explicitly
opt-in and is not invoked by this publisher. Do not give two Terraform roots
ownership of the same template VMID. For bootc, transfer approved OCI images
into a custody-local source; a Tier 1 registry is not a Tier 0 prerequisite.

For Talos, publish a fresh raw image for each release/schematic revision;
do not run package updates, SSH provisioners, or Linux cleanup roles on it.
Updating the template does not upgrade running cluster nodes. Follow the
[Talos guide](talos-template.md) for the separate machine lifecycle.

Tier 1 and Tier 2 receive approved image artifacts and release metadata by
offline handoff. VMIDs are local to a Proxmox cluster: import into the destination
under one designated owner and record the destination ID. This kit does not
automate cross-cluster transfer or open a route into custody.

## GitLab CI example

The generated Tier 0 `ci/gitlab-templates.yml.example` is seeded once and owned
by that project's developers. Enable it as `.gitlab-ci.yml` only after preparing:

- a custody-local GitLab service and one protected shell runner tagged
  `tier0-templates`, with durable storage outside disposable job checkouts;
- the shared checkout beside `CI_PROJECT_DIR`, at the full commit in `TIER0_SHARED_COMMIT`,
  identical and unmodified for plan and publish;
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

A connected Tier 1 runner must not administer custody. Until custody-local CI
exists, or whenever it is unavailable, run the local commands from an isolated
workstation with the same recovery state and artifacts. A CI server hosted on
the Tier 0 cluster is a Day 2 convenience, never its bootstrap dependency.

## Existing collections

Refresh adds Tier 0 template files but never moves live configuration or state.
Existing `.deployment-setups`, root READMEs, jobs, and local inventories remain
owned. Before switching `template-refresh` or `immutable-template` from Tier 1:

1. Stop the old jobs and back up their state and live inputs.
2. Review physical custody placement; repo movement does not isolate a host.
3. Transfer the authoritative state and matching inputs under a reviewed
   migration, with the same resource identities. Do not apply an empty new
   Tier 0 state against VMs still owned by Tier 1.
4. Update both tiers' `.deployment-setups`, inventory, group vars, job paths,
   and owned READMEs. Review retained old roots and shared Packer vars manually.
5. Verify a no-change plan from the new owner before enabling its jobs.

See [refresh ownership](../../reference/generated-repository-model.md#refresh-and-local-ownership).

## Offline validation

From the upstream checkout, use Terraform 1.7 or later for the native mock tests:

```bash
terraform -chdir=terraform/modules/proxmox_templates init -backend=false
terraform -chdir=terraform/modules/proxmox_templates test
```

These tests inspect plans and validation failures without calling Proxmox.
They do not boot or verify real images; disposable clone tests remain required.

## References

1. [Proxmox provider file upload](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_file), accessed 2026-09-17.
2. [Proxmox provider VM resources](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_vm), accessed 2026-09-17.
3. [Proxmox provider authentication](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/index.md), accessed 2026-09-17.
4. [GitLab CI YAML reference](https://docs.gitlab.com/ci/yaml/), accessed 2026-09-17.
5. [GitLab resource groups](https://docs.gitlab.com/ci/resource_groups/), accessed 2026-09-17.
