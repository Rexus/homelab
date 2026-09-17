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
        "tier-0": "the recoverable control foundation, template lifecycle, and custody-local infrastructure",
        "tier-1": "shared platform services and connected infrastructure",
        "tier-2": "application, project, and lab workloads",
    }
    extra_paths = {
        "tier-0": ("- `templates/`, `terraform/templates/`, and `ci/`: image catalog, publication, and jobs\n"
                   "- `bootstrap/` and `clusters/tier0/`: cluster bootstrap and service definitions"),
        "tier-1": "- `clusters/tier1/`: platform cluster definitions",
        "tier-2": "- `environments/` and `workloads/`: project and workload definitions",
    }
    owned_template(writer, "tier-readme.md", "README.md", prefix=prefix,
                   tier_title=tier.replace("-", " ").title(), purpose=descriptions[tier],
                   example=setups[0], extra_paths=extra_paths[tier],
                   docs=f"../{prefix}-architecture/{AUTO_DOCS}")


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


def copy_documentation(writer, prefix, upstream, setup_owners):
    for path in sorted((upstream / "docs").rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        target = f"{AUTO_DOCS}/" + path.relative_to(upstream / "docs").as_posix()
        setup_match = re.search(r"terraform/environments/([a-z-]+)/", content)
        default_owner = setup_owners.get(setup_match[1]) if setup_match else None

        def relocate(match):
            source = (path.parent / match[0]).resolve().relative_to(upstream)
            parts = source.parts
            if parts[:2] in (("ansible", "playbooks"), ("ansible", "roles"), ("terraform", "modules")):
                owner = "shared"
            elif parts[:2] == ("terraform", "templates") or parts[0] in ("templates", "ci"):
                owner = "tier-0"
            elif parts[0] == "packer":
                owner = "shared" if parts[1] == "templates" else "tier-0"
            elif parts[0] == "scripts":
                owner = "shared"
            elif parts[:2] == ("terraform", "environments"):
                owner = setup_owners[parts[2]]
            else:
                owner = default_owner
            if owner is None:
                raise ValueError(f"No tier context for documentation source link: {path}: {source}")
            destination = writer.root.parent / f"{prefix}-{owner}" / source
            return Path(os.path.relpath(destination, (writer.root / target).parent)).as_posix()

        # Preserve Markdown and local doc links; only source-file destinations move between repos.
        content = re.sub(r"(?<=\]\()(?:\.\./)+(?:ansible|terraform|scripts|packer|templates|ci)/[^)#]+",
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
