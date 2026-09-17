# Generated repository model

## Table of contents

- [Purpose and prerequisites](#purpose-and-prerequisites)
- [Repository ownership](#repository-ownership)
- [Inventory contract](#inventory-contract)
- [Setup ownership](#setup-ownership)
- [Run the generated automation](#run-the-generated-automation)
- [Shared code and recovery](#shared-code-and-recovery)
- [Refresh and local ownership](#refresh-and-local-ownership)
- [Implementation scope](#implementation-scope)
- [References](#references)

## Purpose and prerequisites

From the cloned kit, create the collection with one command:

```bash
bash scripts/init-tier-repos.sh
```

Use `--prefix mylab` to name it `mylab-iac/` with `mylab-*` repos inside.
Use `--root /path/to/parent` to create the collection beneath that directory;
the default parent is beside this kit checkout, independent of your current
working directory. Add `--dry-run` to preview without writing.

The generator requires Python 3.9 or later and PyYAML. An existing Python
environment containing PyYAML needs no additional install. If it is missing:

```bash
python3 -m pip install -r scripts/tier-repos/requirements.txt
```

Native Windows can invoke
`python scripts/tier-repos/generate.py` with the same arguments. Run deployments
from Linux or WSL with the [deployment tooling](../getting-started/local-setup.md).
Generation needs no server, provider credentials, or hosted source control.
It creates directories and files; it does not initialize Git or create remotes.

## Repository ownership

| Repository | Owns |
| --- | --- |
| `<prefix>-tier-0` | custody inventory, recovery inputs, control-service setups, bootstrap and cluster definitions |
| `<prefix>-tier-1` | platform inventory, edge and shared-service setups, platform cluster definitions |
| `<prefix>-tier-2` | workload inventory, lab setups, project and application definitions |
| `<prefix>-shared` | Terraform modules, Ansible playbooks and roles, Packer templates, deployment scripts |
| `<prefix>-architecture` | copied upstream docs and environment-owned design, decisions, service records, runbooks |

The collection directory groups five sibling repositories and is not itself a
Git repository. The prefix defaults to `homelab`:

```text
parent/
  upstream-kit/
  homelab-iac/
    homelab-tier-0/
    homelab-tier-1/
    homelab-tier-2/
    homelab-shared/
    homelab-architecture/
```

Each child can have its own private Git history and remote. Generation does
not nest a collection repository around them or move existing checkouts.
Shared **code** is separate from shared **services**: a platform service still
has an owning tier, inventory, and state.

Each tier has the same operational layout:

```text
<prefix>-tier-N/
  .deployment-setups
  .generated-files.json
  env.local.example
  ansible/
    ansible.cfg
    inventory/hosts.yml.example
    group_vars/all.yml.example
    group_vars/all.env.yml.example
    group_vars/<setup>.yml.example
  terraform/
    common.tfvars.example
    environments/<setup>/
      main.tf
      variables.tf
      terraform.tfvars.example
  scripts/
    check-shared.sh
    init-local-files.sh
    deploy.sh
```

The initializer creates ignored working files from these examples. It creates
only setups listed in that tier's `.deployment-setups`. Actual credentials,
inventory, group vars, state, and local overrides are never copied from upstream.

Every root README is a developer-owned starter, not a refresh target. The
architecture repository includes `docs/naming-conventions.md` and project
templates alongside `docs/auto-docs/`. Start with
[Project documentation](project-documentation.md) for that layout and existing-collection upgrades.

## Inventory contract

There are three independent inventories, one per tier. Within each tier,
Terraform and Ansible consume the **same** inventory and group vars. Terraform
does not generate a second inventory after provisioning.

```mermaid
flowchart LR
  Inputs["Owning tier: inventory and group vars"] --> TF["Terraform guest resolution"]
  Inputs --> Ansible["Ansible configuration"]
  Hardware["Owning tier: hardware and network tfvars"] --> TF
  Shared["Shared: modules, playbooks, roles"] --> TF
  Shared --> Ansible
```

| File in the owning tier | Responsibility |
| --- | --- |
| `ansible/inventory/hosts.yml` | stable logical host keys and service groups |
| `ansible/group_vars/all.yml` | hostname decoration, domain, connection and baseline settings |
| `ansible/group_vars/<setup>.yml` | `platform_host_ips` and service settings |
| `terraform/common.tfvars` | platform placement, guest networks, template and storage mappings |
| `terraform/environments/<setup>/terraform.tfvars` | VM/LXC definitions keyed by those inventory host keys |

The shared `environment_guests` module reads the tier's YAML to resolve names
and IPs. The wrapper supplies the same ordered vars files to both tools:

1. `all.yml`
2. `<setup>.yml`
3. `all.<env>.yml`, when `--env` is used
4. `<setup>.<env>.yml`, when `--env` is used
5. any `--ansible-vars` files, in command-line order

Later top-level values replace earlier ones. Supply the complete
`platform_host_ips` map in an overlay; partial maps are not recursively merged.
Setup stems use underscores for `podman_runner`, `immutable_template`, and
`template_refresh`, matching the upstream conventions.

State and Terraform working data stay under each tier's
`.terraform/state/<setup>/<environment>/` and
`.terraform/data/<setup>/<environment>/`. `--env test` and production therefore
remain separate within each of the three repositories.

NetBox or another inventory application is an early Day 2 documentation service.
Recovery uses local tier inputs and operator-held material without querying it.
An exported inventory snapshot can be reviewed into a tier later; the generator
does not implement a live inventory-application integration.

## Setup ownership

The generator assigns existing setup examples as follows:

| Tier | Setups | Placement condition |
| --- | --- | --- |
| Tier 0 | `foundation`, `vault`, `hsm` | custody-local control instances; map their guest networks to isolated custody infrastructure |
| Tier 1 | `edge`, `cache`, `development`, `observability`, `podman-runner`, `immutable-template`, `template-refresh` | connected platform services, edge and image builders |
| Tier 2 | `lab` | lab and workload instances |

The setup name describes a capability; its tier describes the particular
deployment's ownership. Online identity, issuing, secret, or HSM gateway
instances serving connected networks belong in Tier 1. The Tier 0 copies are
custody-local examples, not permission to connect custody to the DMZ. The
generator preserves reference network values, so operators must replace bridge,
subnet, gateway, template, and VMID values for the actual environment.

Use the [network plan](../architecture/network.md#example-network-plan) and
[firewall policy](../security/firewall-policy.md) to prepare those attachments.
Matching logical network keys across tiers do not imply a shared subnet or
firewall zone; generation does not create or enforce network isolation.

To deploy a capability in another tier, add its Terraform root and example
vars there, register it in `.deployment-setups`, and add only that tier's hosts
and IPs. Point its modules at the shared repo. Give it distinct resource IDs
and state; do not transfer ownership by applying a second state to existing VMs.

The generated Tier 0 `hsm` run targets custody hosts only. The single-tree HSM
wrapper also renders edge snippets, which is intentionally excluded from the
tier run. Connected HSM gateways and their edge configuration must be owned
together in Tier 1; an air-gapped custody HSM is not a live edge backend.

## Run the generated automation

From `homelab-iac/homelab-tier-0`, initialize local working files:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup foundation --env test
```

Replace `homelab` if you used another prefix. Edit the initialized local files
and confirm custody placement, then review a plan from that same directory:

```bash
bash ../homelab-shared/scripts/deploy.sh foundation --env test --plan-only
```

After reviewing the plan, use the same deployment command without `--plan-only`.
The existing [script options](repository-scripts.md) apply in every tier.
For the upstream single-tree workflow, run those wrappers from the upstream
private working copy instead.

## Shared code and recovery

Shared scripts detect the tier root from the current working directory and
check the shared code before running. The tier's `scripts/` entry points remain
shortcuts to that same implementation and also work from other directories.
Run direct shared-script commands from the tier root. Ansible
uses shared playbooks and roles while its config, inventory, and vars stay in
the tier. The generated config uses Ansible's native role path. [1]

Terraform roots use literal relative module sources such as
`../../../../<prefix>-shared/terraform/modules/environment_guests`. Terraform
resolves local module paths relative to the calling module. [2]

Keep the sibling names stable. Arbitrary `SHARED_REPO_DIR` overrides are not
supported because both tools must resolve the same code checkout. Record a
reviewed shared revision in environment decisions and retain that checkout,
required providers, collections, images, and recovery inputs inside custody.
An available local copy is required; a running source-control service is not.
Repository separation scopes automation inputs, but does not enforce permissions
or network policy by itself.

## Refresh and local ownership

After updating the upstream kit, run this from its checkout:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Reuse the same `--prefix` and `--root` flags as creation if customized.
Add `--dry-run` to preview. Refresh does not run the local-file initializer or
deployment scripts.

`.generated-files.json` records hashes for generated code, examples, launchers,
and documentation. Keep it with the downstream repository.
Generated `.gitattributes` keeps text files at LF line endings so checkout on
another operating system does not invalidate those hashes or break Bash scripts.

| File condition | Refresh behavior |
| --- | --- |
| New upstream file, never generated at that path | create it |
| Managed file still matches its recorded generated hash | update from the kit |
| Locally edited or unrecognized existing file | preserve and report it |
| Previously generated file deleted locally | preserve the deletion |
| Live inventory, local vars, credentials, state | never targeted |
| Root READMEs, project docs, bootstrap/cluster skeletons, `.deployment-setups` | seed once; preserve thereafter, even when unchanged |

Source files retain their syntax and use the manifest for provenance. Launchers
carry markers and every auto-doc has a visible do-not-edit notice. A marker alone never
authorizes overwriting a file. Files produced by the older marker-only
generator are preserved when their origin cannot be verified by the manifest.
Refresh does not delete retired files, merge local edits, or commit changes.
Review reported preserved files and upstream removals before adopting an update.
Keep local guides and diagrams in `docs/owned/` and project conventions in
`docs/naming-conventions.md`; upstream guidance updates under `docs/auto-docs/`.
A locally edited example or shared module is also
preserved, so adopting upstream changes to it requires a manual comparison.

Existing READMEs become owned without being rewritten. Earlier
`docs/generated/upstream/` copies remain untouched; follow the
[documentation upgrade steps](project-documentation.md#existing-collections)
to update local links and review legacy docs.

For an older flat layout, move the existing child checkouts together into the
collection directory before refreshing, preserving their manifests, local files,
and Git histories. The generator does not move or import those repositories.

## Implementation scope

Generation includes the existing Linux Terraform/Ansible setups, split inventory
examples, shared automation, and upstream documentation. The Talos bootstrap,
Flux reconciliation, cluster applications, and documentation website remain
skeletons. Kustomization resource lists group files; they do not enforce the
Day 2 deployment sequence. See the [Tier 0 path](../paths/tier-0/README.md).

Offline checks run with:

```bash
python3 -B -m unittest discover -s tests -p 'test_tier*.py' -v
```

## References

1. [Ansible configuration and relative paths](https://docs.ansible.com/projects/ansible/latest/reference_appendices/config.html#relative-paths-for-configuration), accessed 2026-09-15.
2. [Terraform module sources](https://developer.hashicorp.com/terraform/language/modules/configuration), accessed 2026-09-15.
