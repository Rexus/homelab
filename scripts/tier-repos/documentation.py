"""Seed project-owned front doors and refresh clearly marked upstream guidance."""

import os
from pathlib import Path
import re
from string import Template

AUTO_DOCS = "docs/auto-docs"
TEMPLATES = Path(__file__).parent / "templates"


def owned_template(writer, template, target, **values):
    content = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
    writer.write(target, content, owned=True)


def tier_readme(writer, tier, prefix, setups):
    descriptions = {
        "tier-0": "hardware-facing infrastructure control, all VM template lifecycles, trust systems, and recovery",
        "tier-1": "shared platform services and connected infrastructure",
        "tier-2": "application, project, and lab workloads",
    }
    extra_paths = {
        "tier-0": ("- `templates/`, `terraform/templates/`, and `ci/`: image catalog, publication, and jobs\n"
                   "- `terraform/modules/` and `packer/`: Tier 0 template implementations and builds\n"
                   "- `bootstrap/` and `clusters/tier0/`: cluster bootstrap and service definitions"),
        "tier-1": "- `clusters/tier1/`: platform cluster definitions",
        "tier-2": "- `environments/` and `workloads/`: project and workload definitions",
    }
    docs = f"../{prefix}-architecture/{AUTO_DOCS}"
    prerequisites = (
        "Tier 0 supplies approved VM templates and networks. The commands below are\n"
        "operator-run workflows, not a self-service interface for workload users.\n"
    )
    if tier == "tier-0":
        prerequisites = (
            f"Use the [Day 0-3 checklist]({docs}/paths/tier-0/README.md#deployment-order):\n"
            "Day 0/1 builds the platform; Day 2 adds identity and service clients;\n"
            "Day 3 proves access handover and recovery.\n\n"
            f"Prepare [Proxmox hosts]({docs}/platforms/proxmox/README.md#first-deployment-order)\n"
            "first, including optional cluster HA and SDN before important guests.\n\n"
            "**Day 0: templates before VMs.** From this repository's root, initialize\n"
            "the local image catalog:\n\n"
            "```bash\n"
            "bash scripts/proxmox-templates.sh init\n"
            "```\n\n"
            "Set local images, placement, checksums, and protected API access, then follow\n"
            f"the [template lifecycle]({docs}/platforms/proxmox/template-lifecycle.md#local-workflow)\n"
            "to plan, publish, and test templates before deploying guests. No hosted CI\n"
            "or control cluster is required. If approved templates already exist, verify\n"
            "their IDs and recovery copies before continuing.\n\n"
            f"Use [Talos bootstrap]({docs}/platforms/talos/bootstrap.md) for the control\n"
            "cluster hosting Keycloak. FreeIPA runs on two dedicated VMs through\n"
            "the Linux `foundation` setup below, outside Kubernetes. The Linux\n"
            "helper does not create the cluster or install Keycloak.\n"
        )
    owned_template(writer, "tier-readme.md", "README.md", prefix=prefix,
                   tier_title=tier.replace("-", " ").title(), purpose=descriptions[tier],
                   example=setups[0], extra_paths=extra_paths[tier],
                   prerequisites=prerequisites, docs=docs, tier=tier)


def shared_readme(writer, prefix):
    owned_template(writer, "shared-readme.md", "README.md", prefix=prefix,
                   docs=f"../{prefix}-architecture/{AUTO_DOCS}")


def architecture_scaffold(writer, prefix):
    for area in ("design", "decisions", "runbooks", "services", "tiers", "network"):
        writer.write(f"docs/owned/{area}/.gitkeep", "", owned=True)
    writer.write("site/.gitkeep", "", owned=True)
    for template, target in (
        ("architecture-readme.md", "README.md"),
        ("project-docs.md", "docs/README.md"),
        ("naming-conventions.md", "docs/naming-conventions.md"),
        ("project-overview.md", "docs/owned/design/overview.md"),
        ("recovery.md", "docs/owned/runbooks/recovery.md"),
    ):
        owned_template(writer, template, target, prefix=prefix)


def copy_documentation(writer, prefix, upstream):
    for path in sorted((upstream / "docs").rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        target = f"{AUTO_DOCS}/" + path.relative_to(upstream / "docs").as_posix()

        def relocate(match):
            source = (path.parent / match[0]).resolve().relative_to(upstream)
            parts = source.parts
            if parts[0] not in ("shared", "tier-0", "tier-1", "tier-2"):
                return match[0]
            destination = writer.root.parent / f"{prefix}-{parts[0]}" / Path(*parts[1:])
            return Path(os.path.relpath(destination, (writer.root / target).parent)).as_posix()

        # Preserve Markdown and local doc links; only source-file destinations move between repos.
        content = re.sub(r"(?<=\]\()(?:\.\./)+(?:shared|tier-[012])/[^)#]+",
                         relocate, content)
        project_docs = Path(os.path.relpath(writer.root / "docs/README.md",
                                           (writer.root / target).parent)).as_posix()
        notice = (
            "> **AUTO-DOCS - DO NOT EDIT**\n"
            "> Updated by `bash scripts/init-tier-repos.sh --refresh` from the upstream kit checkout.\n"
            "> Reuse this collection's `--prefix` and `--root` flags if customized.\n"
            f"> Keep local decisions in [project documentation]({project_docs}) instead.\n"
        )
        heading, _, body = content.partition("\n")
        if heading.startswith("# "):
            body = body.lstrip("\n")
            content = f"{heading}\n\n{notice}\n{body}"
        else:
            content = notice + "\n" + content
        writer.write(target, content)

    legacy = writer.root / "docs/generated/upstream"
    if legacy.exists():
        print(f"Legacy docs preserved at {legacy}; new guidance is in {AUTO_DOCS}/. "
              "Update owned README links and review legacy edits manually.")
