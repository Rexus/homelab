#!/usr/bin/env python3
"""Generate tier-owned inputs and a shared copy of the deployment automation."""

import argparse
import configparser
from copy import deepcopy
import io
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: python3 -m pip install -r scripts/tier-repos/requirements.txt")

from generated_files import MARKER, RepositoryWriter
from documentation import architecture_scaffold, copy_documentation, shared_readme, tier_readme
from scaffold import cluster_scaffold

UPSTREAM = Path(__file__).resolve().parents[2]
TIERS = {
    "tier-0": {
        "setups": ["foundation", "vault", "hsm"],
        "groups": ["hypervisors", "foundation", "vault", "hsm_gateways", "crypto_admin"],
    },
    "tier-1": {
        "setups": ["edge", "cache", "development", "observability", "podman-runner",
                   "immutable-template", "template-refresh"],
        "groups": ["edge_load_balancers", "cache", "development_platform", "telemetry_gateways",
                   "security_telemetry", "observability", "archive", "podman_runner",
                   "immutable_template_builders", "template_refresh_builders", "identity_providers"],
    },
    "tier-2": {"setups": ["lab"], "groups": ["lab"]},
}
REPOSITORIES = ["shared", *TIERS, "architecture"]


def copy_file(writer, source, target=None, transform=None):
    source = Path(source)
    path = UPSTREAM / source
    if path.is_symlink():
        raise ValueError(f"Source must be a regular kit file: {path}")
    content = path.read_text(encoding="utf-8")
    writer.write(target or source.as_posix(), transform(content) if transform else content,
                 executable=source.suffix == ".sh")


def copy_tree(writer, directory, patterns, target=None):
    for path in sorted((UPSTREAM / directory).rglob("*")):
        relative = path.relative_to(UPSTREAM / directory)
        if any(part.startswith(".") for part in relative.parts) or not path.is_file():
            continue
        if path.name == "override.tf" or path.name.endswith("_override.tf"):
            continue
        if any(path.match(pattern) for pattern in patterns):
            copy_file(writer, path.relative_to(UPSTREAM), f"{target or directory}/{relative.as_posix()}")


def tier_inventory(tier):
    inventory = yaml.safe_load((UPSTREAM / "ansible/inventory/hosts.yml.example").read_text(encoding="utf-8"))
    groups = inventory["all"]["children"]
    selected = {}

    def include(name):
        if name in selected:
            return
        selected[name] = deepcopy(groups[name])
        for child in (groups[name] or {}).get("children", {}):
            include(child)

    for group in TIERS[tier]["groups"]:
        include(group)
    guest_groups = [name for name in TIERS[tier]["groups"] if name != "hypervisors"]
    selected["guests"] = {"children": {name: None for name in guest_groups}}
    inventory["all"]["children"] = selected
    hosts = {host for group in selected.values() for host in (group or {}).get("hosts", {})}
    return inventory, hosts


def launchers(writer, prefix):
    check = f"""#!/usr/bin/env bash
# {MARKER}
set -euo pipefail
tier_dir="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"
shared_dir="$tier_dir/../{prefix}-shared"
for required in terraform/modules/environment_guests/main.tf terraform/modules/vm/main.tf \\
  terraform/modules/lxc/main.tf ansible/playbooks/control-node.yml ansible/requirements.yml \\
  scripts/deploy.sh scripts/init-local-files.sh scripts/lib/deployment-context.sh; do
  if [[ ! -f "$shared_dir/$required" ]]; then
    echo "Missing shared automation: $shared_dir/$required" >&2
    echo "Generate or check out {prefix}-shared beside this tier repository." >&2
    exit 1
  fi
done
echo "Shared automation found: $shared_dir"
"""
    writer.write("scripts/check-shared.sh", check, executable=True)
    for command in ("deploy", "init-local-files"):
        writer.write(f"scripts/{command}.sh", f"""#!/usr/bin/env bash
# {MARKER}
set -euo pipefail
tier_dir="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"
export DEPLOYMENT_REPO_DIR="$tier_dir"
if [[ ! -f "$tier_dir/../{prefix}-shared/scripts/{command}.sh" ]]; then
  echo "Missing shared automation: $tier_dir/../{prefix}-shared/scripts/{command}.sh" >&2
  exit 1
fi
exec bash "$tier_dir/../{prefix}-shared/scripts/{command}.sh" "$@"
""", executable=True)


def shared_repo(writer, prefix):
    for directory, patterns in (
        ("terraform/modules", ["*.tf"]),
        ("ansible/roles", ["*.yml", "*.yaml", "*.j2"]),
        ("ansible/playbooks", ["*.yml"]),
        ("packer/templates", ["*.pkr.hcl"]),
    ):
        copy_tree(writer, directory, patterns)
    for source in ("ansible/requirements.yml", "packer/variables.auto.pkrvars.hcl.example",
                   "scripts/deploy.sh", "scripts/init-local-files.sh", "scripts/lib/deployment-context.sh"):
        copy_file(writer, source)
    writer.write("templates/.gitkeep", "", owned=True)
    shared_readme(writer, prefix)


def tier_repo(writer, tier, prefix):
    setups = TIERS[tier]["setups"]
    writer.write(".deployment-setups", "\n".join(setups) + "\n", owned=True)
    launchers(writer, prefix)
    inventory, hosts = tier_inventory(tier)
    writer.write("ansible/inventory/hosts.yml.example", f"# {MARKER}\n"
                 "# Tier-owned logical hosts. IPs live in setup group vars.\n"
                 + yaml.safe_dump(inventory, sort_keys=False, width=100))
    for source in ("env.local.example",
                   "ansible/group_vars/all.yml.example", "ansible/group_vars/all.env.yml.example"):
        copy_file(writer, source)
    note = "# Shared across setups in this tier only. Replace reference network values before use.\n"
    if tier == "tier-0":
        note += "# Tier 0: map guest networks to isolated custody bridges; no routed connection to other tiers.\n"
    copy_file(writer, "terraform/common.tfvars.example", transform=lambda content: note + content)
    config = configparser.ConfigParser()
    config.read(UPSTREAM / "ansible/ansible.cfg")
    config["defaults"]["roles_path"] = f"../../{prefix}-shared/ansible/roles"
    content = io.StringIO()
    config.write(content)
    writer.write("ansible/ansible.cfg", f"# {MARKER}\n" + content.getvalue())
    for setup in setups:
        stem = setup.replace("-", "_")
        source = f"ansible/group_vars/{stem}.yml.example"
        if setup == "hsm":
            values = yaml.safe_load((UPSTREAM / source).read_text(encoding="utf-8"))
            values["platform_host_ips"] = {key: value for key, value in values["platform_host_ips"].items()
                                           if key in hosts}
            writer.write(source, f"# {MARKER}\n# Custody hosts only; edge configuration belongs to Tier 1.\n"
                         + yaml.safe_dump(values, sort_keys=False))
        else:
            copy_file(writer, source)
        directory = f"terraform/environments/{setup}"
        for filename in ("main.tf", "variables.tf", "outputs.tf"):
            source_path = UPSTREAM / directory / filename
            if not source_path.is_file():
                continue
            # These kit roots have literal local module sources. Keep the HCL
            # intact and relocate only the known module-source prefix.
            copy_file(writer, source_path.relative_to(UPSTREAM), transform=lambda content: content.replace(
                '"../../modules/', f'"../../../../{prefix}-shared/terraform/modules/'))
        copy_file(writer, f"{directory}/terraform.tfvars.example")
    cluster_scaffold(writer, tier)
    tier_readme(writer, tier, prefix, setups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="homelab", help="Repository name prefix (default: homelab).")
    parser.add_argument("--root", type=Path, default=UPSTREAM.parent,
                        help="Parent of <prefix>-iac/ (default: beside this kit checkout).")
    parser.add_argument("--repo", action="append", choices=[*REPOSITORIES, "all"], help="Repeat to select repositories.")
    parser.add_argument("--refresh", action="store_true", help="Update unchanged generated files; preserve local edits.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.prefix):
        parser.error("--prefix must start with a letter or number and contain only letters, numbers, and dashes")
    collection = args.root / f"{args.prefix}-iac"
    if collection.is_symlink() or UPSTREAM.is_relative_to(collection.resolve()):
        parser.error(f"Collection must not contain the upstream or replace a symlink: {collection}")
    print(f"Collection: {collection.resolve()}")
    if (collection / ".git").exists():
        parser.error("The collection directory must not be a Git repository; each child owns its history")
    selected = REPOSITORIES if not args.repo or "all" in args.repo else list(dict.fromkeys(args.repo))
    for name in selected:
        destination = collection / f"{args.prefix}-{name}"
        if destination.is_symlink() or UPSTREAM.is_relative_to(destination.resolve()):
            parser.error(f"Output must not replace the upstream or a symlink: {destination}")
        writer = RepositoryWriter(destination, args.refresh, args.dry_run)
        writer.write(".gitattributes", f"# {MARKER}\n* text=auto eol=lf\n")
        copy_file(writer, ".gitignore", transform=lambda content: f"# {MARKER}\n" + content
                  + "\n# Cluster credentials\nkubeconfig*\ntalosconfig*\n")
        if (UPSTREAM / "LICENSE").is_file():
            copy_file(writer, "LICENSE")
        if name == "shared":
            shared_repo(writer, args.prefix)
        elif name == "architecture":
            setup_owners = {setup: tier for tier, config in TIERS.items() for setup in config["setups"]}
            copy_documentation(writer, args.prefix, UPSTREAM, setup_owners)
            architecture_scaffold(writer, args.prefix)
        else:
            tier_repo(writer, name, args.prefix)
        writer.finish()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, yaml.YAMLError) as error:
        sys.exit(f"Generation failed: {error}")
