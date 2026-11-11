"""Seed project-owned front doors and refresh clearly marked upstream guidance."""

import os
from pathlib import Path
import re
from documentation_migration import MOVES, compatibility_stub, prune_auto_docs, referenced_manual_aliases
from project_docs import owned_template, repository_guides

AUTO_DOCS = "docs/auto-docs"

# Only these retired software routes need aliases beyond the usual area aliases.
MOVED_SOFTWARE_ROUTES = (
    "README.md", "software-intake.md", "artifact-verification.md", "controllers.md",
    "artifact-supply.md", "development-platform.md", "software-intake/README.md",
)


def compatibility_paths(path):
    areas = {"01-architecture": ("architecture",), "02-conventions": ("conventions",),
             "03-deployment": ("deployment", "02-deployment"),
             "04-development": ("development", "03-development"),
             "05-operations": ("administration", "04-administration"),
             "06-paths": ("paths",), "07-decisions": ("decisions",),
             "08-reference": ("reference",)}
    relative = path.relative_to("docs")
    aliases = [Path(area, *relative.parts[1:]) for area in areas.get(relative.parts[0], ())]
    for route in MOVED_SOFTWARE_ROUTES:
        for area in ("architecture", "01-architecture"):
            old = f"{area}/software/{route}"
            if MOVES[old] == relative.as_posix():
                aliases.append(Path(old))
    # Retired numbered routes are retained only for project records that need them;
    # original area aliases remain available outside the current reading tree.
    for old, current in MOVES.items():
        area = Path(old).parts[0]
        if area in ("01-architecture", "03-deployment", "05-operations") and current == relative.as_posix():
            aliases.append(Path(old))
            aliases.extend(Path(legacy, *Path(old).parts[1:]) for legacy in areas[area])
    return list(dict.fromkeys(aliases))


def tier_readme(writer, tier, prefix, setups):
    descriptions = {
        "tier-0": "hardware-facing infrastructure control, all VM template lifecycles, trust systems, and recovery",
        "tier-1": "shared platform services, authoritative software mirrors, and general build runners",
        "tier-2": "public edge ingress, ordinary outbound caches, and application, project, and lab workloads",
    }
    extra_paths = {
        "tier-0": ("- `templates/`, `terraform/deployments/templates/`, and `ci/`: image catalog, publication, and jobs\n"
                   "- `terraform/deployments/kubernetes/`: control-cluster VMs and bootstrap; currently Talos\n"
                   "- `packer/` and `clusters/tier0/`: custom image builds and cluster-service starters"),
        "tier-1": ("- `terraform/deployments/kubernetes/`: platform cluster VMs and bootstrap\n"
                   "- `clusters/tier1/`: platform manifests; select the delivery controller separately"),
        "tier-2": ("- `terraform/deployments/kubernetes/` and `clusters/tier2/`: workload cluster and manifests\n"
                   "- `environments/` and `workloads/`: project and workload definitions"),
    }
    repo_prefix = prefix.lower()
    docs = f"../{repo_prefix}-architecture/{AUTO_DOCS}"
    deployments = [
        f"| `{setup}` | [main.tf](terraform/deployments/{setup}/main.tf) "
        f"| [playbook](ansible/playbooks/{setup}.yml) |"
        for setup in setups
    ]
    if tier == "tier-0":
        deployments[:0] = [
            "| `ci-auth` | [main.tf](terraform/deployments/ci-auth/main.tf) "
            "| [Vault CI guide](" + docs + "/03-deployment/stage-9-development/procedures/vault-ci.md) |",
            "| `templates` | [main.tf](terraform/deployments/templates/main.tf) "
            "| [image recipes](templates/proxmox.yml.example) |",
        ]
    deployments.insert(0, "| `kubernetes` | [main.tf](terraform/deployments/kubernetes/main.tf) "
                       "| [machine configuration](terraform/deployments/kubernetes/machines.tf) |")
    prerequisites = (
        "Tier 0 supplies approved VM templates and networks. The commands below are\n"
        "operator-run workflows, not a self-service interface for workload users.\n"
        "For a new tier-owned Kubernetes cluster, initialize its local inputs:\n\n"
        f"Run from **`{repo_prefix}-{tier}/`**.\n\n"
        "```bash\n"
        "bash scripts/kubernetes-cluster.sh init\n"
        "```\n\n"
        f"Follow the [cluster procedure]({docs}/03-deployment/stage-4-kubernetes/procedures/talos-terraform.md)\n"
        "to configure, plan, deploy and verify. Cluster manifests are starters, not installed services.\n"
        f"Record the [delivery choice]({docs}/01-architecture/10-delivery/02-controllers.md) separately;\n"
        "Tier 1 does not inherit Tier 0 Flux automatically.\n"
    )
    if tier == "tier-0":
        prerequisites = (
            f"Follow the [capability deployment checklist]({docs}/06-paths/tier-0/README.md#deployment-order).\n"
            f"Verify [foundation prerequisites]({docs}/03-deployment/foundation/README.md) first; "
            "numbered stages add platform capabilities.\n\n"
            f"Prepare [Proxmox hosts]({docs}/03-deployment/foundation/proxmox/README.md#first-deployment-order)\n"
            "first, including optional cluster HA and SDN before important guests.\n\n"
            "For the first installation, create one Linux template manually, then prepare\n"
            f"the [bootstrap execution host]({docs}/03-deployment/foundation/bootstrap/README.md).\n"
            "Its tools, artifact storage, Proxmox CA trust and API credentials must be ready\n"
            "before the publication command below. An accepted privileged workstation is also valid.\n\n"
            "**Templates before VMs.** Initialize the local image catalog:\n\n"
            f"Run from **`{repo_prefix}-tier-0/`**.\n\n"
            "```bash\n"
            "bash scripts/proxmox-templates.sh init\n"
            "```\n\n"
            "Set local images, placement, checksums, and protected API access, then follow\n"
            f"the [template lifecycle]({docs}/05-operations/01-hosting/templates/template-lifecycle.md#local-workflow)\n"
            "to plan, publish, and test templates before deploying guests. For existing manual templates,\n"
            f"use [import and apply]({docs}/05-operations/01-hosting/templates/template-lifecycle.md#adopt-existing-templates).\n"
            f"An intentional OS-disk replacement uses [boot-disk maintenance]({docs}/05-operations/01-hosting/templates/template-disk.md).\n"
            f"Complete [Foundation Step 4]({docs}/03-deployment/foundation/README.md#step-4-publish-and-test-vm-templates)\n"
            "before Stage 1; it lists the commands for both paths. No hosted CI or control cluster is required.\n\n"
            f"Accept [Stage 1: software intake]({docs}/03-deployment/stage-1-software-intake/README.md) first,\n"
            "using existing approved supply or the Tier 2 proxy/cache path.\n\n"
            f"Deploy [Stage 2: protected logging]({docs}/03-deployment/stage-2-logging/README.md), Steps 1-3,\n"
            "outside Kubernetes with this repository's `syslog` setup. The supplied code\n"
            "provisions receiver VMs/disks and installs the isolated receiver after\n"
            "storage/TLS preparation. Separate logging recipes configure producers, NAS checkpoints\n"
            "and independent backups; NAS custody and live acceptance remain explicit gates.\n\n"
            f"After logging, complete [trust]({docs}/03-deployment/stage-3-trust/README.md) before the cluster.\n"
            "**Kubernetes control cluster.** Initialize its Tier 0 inputs:\n\n"
            f"Run from `{repo_prefix}-tier-0/`.\n\n"
            "```bash\n"
            "bash scripts/kubernetes-cluster.sh init\n"
            "```\n\n"
            f"Follow [Stage 4: Kubernetes]({docs}/03-deployment/stage-4-kubernetes/README.md) and its\n"
            f"current [Talos implementation]({docs}/03-deployment/stage-4-kubernetes/procedures/talos-terraform.md) to review\n"
            "inventory, hardware, and cluster settings, then plan and apply. The node OS\n"
            "is an implementation choice; other OS installers are not included.\n"
            "Keycloak is a later service in this cluster.\n"
            "FreeIPA runs on two dedicated VMs through\n"
            "the Linux `foundation` setup, outside Kubernetes. The Linux\n"
            "helper does not create the cluster or install Keycloak.\n"
            f"The [externally signed CA flow]({docs}/03-deployment/stage-5-identity/procedures/freeipa.md#external-ca-integration-gate)\n"
            "uses explicit CSR/pause and signed-certificate completion phases; offline signing remains separate.\n"
        )
    elif tier == "tier-1":
        prerequisites += (
            f"\nAfter [Delivery]({docs}/03-deployment/stage-7-delivery/README.md) and Observability,\n"
            f"follow [Stage 9: Development platform]({docs}/03-deployment/stage-9-development/README.md).\n"
            "Its native Helm recipe installs GitLab and on-demand Kubernetes job runners.\n"
            "Stage 9 provisions the dedicated data-service VMs before installing GitLab.\n"
            "The Linux VM quick start below is an alternative.\n"
        )
    owned_template(writer, "readmes/tier.md", "README.md", prefix=prefix, repo_prefix=repo_prefix,
                   tier_title=tier.replace("-", " ").title(), purpose=descriptions[tier],
                   example={"tier-0": "syslog", "tier-2": "cache"}.get(tier, setups[0]),
                   extra_paths=extra_paths[tier],
                   prerequisites=prerequisites, docs=docs, tier=tier,
                   deployments="\n".join(deployments))
    repository_guides(writer, tier, prefix, descriptions[tier])


def shared_readme(writer, prefix):
    owned_template(writer, "readmes/shared.md", "README.md", prefix=prefix,
                   repo_prefix=prefix.lower(), docs=f"../{prefix.lower()}-architecture/{AUTO_DOCS}")
    repository_guides(writer, "shared", prefix, "reusable automation and common platform references")


def copy_documentation(writer, prefix, upstream):
    documents = sorted((upstream / "docs").rglob("*.md"))
    assets = ("08-reference/diagrams/palette.json", "02-conventions/vmid-convention.svg")
    current_paths = {f"{AUTO_DOCS}/{path.relative_to(upstream / 'docs').as_posix()}" for path in documents}
    referenced = referenced_manual_aliases(writer, prefix)
    aliases = {path: [alias for alias in compatibility_paths(Path("docs") / path.relative_to(upstream / "docs"))
                       if alias.parts[0] not in ("01-architecture", "03-deployment", "05-operations") or alias in referenced]
               for path in documents}
    current_paths.update(f"{AUTO_DOCS}/{alias.as_posix()}" for paths in aliases.values() for alias in paths)
    current_paths.update(f"{AUTO_DOCS}/{asset}" for asset in (*assets, "LICENSE"))
    current_paths.update(f"{AUTO_DOCS}/{alias.as_posix()}" for asset in assets
                         for alias in compatibility_paths(Path("docs") / asset))
    prune_auto_docs(writer, current_paths)
    for path in documents:
        content = path.read_text(encoding="utf-8")
        target = f"{AUTO_DOCS}/" + path.relative_to(upstream / "docs").as_posix()

        def relocate(match):
            source = (path.parent / match[0]).resolve().relative_to(upstream)
            parts = source.parts
            if parts[0] not in ("shared", "tier-0", "tier-1", "tier-2"):
                return match[0]
            destination = writer.root.parent / f"{prefix.lower()}-{parts[0]}" / Path(*parts[1:])
            return Path(os.path.relpath(destination, (writer.root / target).parent)).as_posix()

        # Preserve local doc links; source files and repository roots move between repos.
        content = re.sub(r"(?<=\]\()(?:\.\./)+(?:shared|tier-[012])(?:/[^)#]*)?(?=[)#])",
                         relocate, content)
        # Upstream uses generic repository names; copied run/edit contexts name actual folders.
        # A bare <prefix> can describe DNS or another domain concept, so restrict the suffixes.
        content = re.sub(r"<prefix>-(?=tier-[012]\b|shared\b|architecture\b|iac\b)",
                         f"{prefix.lower()}-", content)
        project_docs = Path(os.path.relpath(writer.root / "docs/README.md",
                                           (writer.root / target).parent)).as_posix()
        notice = (
            "> **AUTO-DOCS - DO NOT EDIT**\n"
            "> Updated by `bash scripts/init-tier-repos.sh --refresh` from the upstream kit checkout.\n"
            "> Reuse this collection's `--prefix` and `--root` flags if customized.\n"
            f"> Keep local decisions in [project documentation]({project_docs}) instead.\n"
        )
        if path.is_relative_to(upstream / "docs/03-deployment"):
            checklist = Path(os.path.relpath(writer.root / "deployments.md",
                                            (writer.root / target).parent)).as_posix()
            notice += (f"> After completing this deployment path, update its entry and selected options in the "
                       f"[deployment checklist]({checklist}).\n")
        heading, _, body = content.partition("\n")
        if heading.startswith("# "):
            body = body.lstrip("\n")
            content = f"{heading}\n\n{notice}\n{body}"
        else:
            content = notice + "\n" + content
        preserved_before = writer.counts["preserve"]
        writer.write(target, content, source=path)
        current_path = writer.root / target
        if writer.counts["preserve"] != preserved_before and current_path.is_file():
            # Aliases must target the headings that readers actually see after refresh.
            content = current_path.read_text(encoding="utf-8")
        for alias in aliases[path]:
            alias_target = f"{AUTO_DOCS}/{alias.as_posix()}"
            canonical = Path(os.path.relpath(writer.root / target,
                                             (writer.root / alias_target).parent)).as_posix()
            previous_path = writer.root / alias_target
            if previous_path.is_symlink() or not previous_path.resolve().is_relative_to(writer.root):
                raise ValueError(f"Refusing generated output through symlink: {previous_path}")
            previous = previous_path.read_text(encoding="utf-8") if previous_path.is_file() else ""
            compatibility = compatibility_stub(canonical, content, previous)
            writer.write(alias_target, compatibility, source=path)

    for asset in assets:
        source = upstream / "docs" / asset
        data = source.read_bytes()
        writer.write(f"{AUTO_DOCS}/{asset}", data, source=source)
        for alias in compatibility_paths(Path("docs") / asset):
            writer.write(f"{AUTO_DOCS}/{alias.as_posix()}", data, source=source)

    legacy = writer.root / "docs/generated/upstream"
    if legacy.exists():
        print(f"Legacy docs preserved at {legacy}; new guidance is in {AUTO_DOCS}/. "
              "Update owned README links and review legacy edits manually.")
