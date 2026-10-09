"""Seed project-owned design records and workflow directories, never replace them."""

import os
from pathlib import Path
from string import Template

TEMPLATES = Path(__file__).parent / "templates"


def owned_template(writer, template, target, legacy=None, **values):
    content = Template((TEMPLATES / template).read_text(encoding="utf-8")).substitute(values)
    if legacy and (writer.root / legacy).is_file():
        link = Path(os.path.relpath(writer.root / legacy, (writer.root / target).parent)).as_posix()
        content += (f"\nPrevious project record: [retained local document]({link}). "
                    "Review and transfer its decisions before adopting this record.\n")
        print(f"Project documentation retained at {legacy}; review the new {target} manually.")
    writer.write(target, content, owned=True)


def workflow_guides(writer, repo, docs):
    title = repo.replace("-", " ").title()
    owned_template(writer, "project/deployment.md", "docs/deployment/README.md", title=title, docs=docs)
    workflows = {
        "development": (
            "Change, review and validation procedures for this repository.",
            [("Change IaC or documentation", "Record ownership, review and test commands", "development/code-layout.md"),
             ("Adopt upstream changes", "Record refresh and compatibility checks", "development/generated-repositories.md")],
        ),
        "administration": (
            "Supported maintenance and recovery procedures for the deployed services.",
            [("Maintain services", "Record supported operations, scheduling and rollback", "administration/README.md"),
             ("Recover and verify", "Record backup custodians and restore evidence", "administration/recovery.md")],
        ),
    }
    for area, (purpose, tasks) in workflows.items():
        rows = "\n".join(f"| {task} | {procedure} | [Guide]({docs}/{reference}) |"
                         for task, procedure, reference in tasks)
        owned_template(writer, "project/workflow.md", f"docs/{area}/README.md",
                       title=title, area_title=area,
                       purpose=purpose, rows=rows)


def repository_guides(writer, repo, prefix, scope):
    selections = {
        "tier-0": (
            "| Compute | Draft: Proxmox; select single host or HA, bridge or SDN | Templates and Kubernetes roots; host readiness checks |\n"
            "| Identity | Draft: dedicated FreeIPA pair and cluster identity broker | Foundation root; directory health and OIDC checks |\n"
            "| Cryptography | Select offline custody, issuer and optional HSM variant | HSM host root is baseline only; record signing integration separately |"
        ),
        "tier-1": (
            "| Traffic | Select edge and outbound cache requirements | Edge/cache roots and deployment recipes |\n"
            "| Compute | Draft: independent three-control-plane cluster; optional worker pools | Kubernetes root and tier-local inventory |\n"
            "| Delivery | Unselected: Argo CD application GitOps or Spinnaker release pipelines | Select sources, targets, RBAC, secrets and recovery before installation |"
        ),
        "tier-2": ("| Compute | Draft: independent workload cluster; development, testing and lab pools when needed | Kubernetes root and tier-local inventory |\n"
                   "| Workloads | Select Linux VMs or application delivery targets | Lab root or cluster manifests; record acceptance checks |"),
        "shared": "| Common automation | Review platform references, sizes and image catalog | Scripts and baseline roles; no inventory or state |",
    }
    docs = f"../../{prefix}-architecture/docs/auto-docs"
    title = repo.replace("-", " ").title()
    owned_template(writer, "project/repository-index.md", "docs/README.md",
                   title=title, prefix=prefix, docs=docs)
    owned_template(writer, "project/repository-design.md", "docs/architecture/README.md",
                   legacy="docs/architecture.md", title=title, prefix=prefix,
                   scope=f"This repository owns {scope}.", selections=selections[repo], docs=f"../{docs}")
    workflow_guides(writer, repo, f"../{docs}")


def architecture_scaffold(writer, prefix):
    previous_design = next((path for path in ("docs/architecture/system-design/README.md", "docs/owned/design/overview.md")
                            if (writer.root / path).is_file()), None)
    writer.write("docs/architecture/decisions/.gitkeep", "", owned=True)
    writer.write("site/.gitkeep", "", owned=True)
    for template, target, legacy in (
        ("readmes/architecture.md", "README.md", None),
        ("project/index.md", "docs/README.md", None),
        ("project/naming-conventions.md", "docs/naming-conventions.md", None),
        ("project/platform-design.md", "docs/architecture/README.md", previous_design),
        ("project/recovery.md", "docs/administration/recovery.md", "docs/owned/runbooks/recovery.md"),
    ):
        owned_template(writer, template, target, legacy=legacy, prefix=prefix)
    for domain, title in (("networking", "Networking"), ("compute", "Compute"),
                          ("identity", "Identity"), ("cryptography", "Cryptography"),
                          ("delivery", "Delivery"), ("operations", "Operations")):
        owned_template(writer, "project/domain-design.md", f"docs/architecture/{domain}/README.md",
                       legacy="docs/architecture/subsystem-design/README.md",
                       prefix=prefix, domain=domain, title=title)
    workflow_guides(writer, "architecture", "../auto-docs")
