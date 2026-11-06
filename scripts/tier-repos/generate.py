#!/usr/bin/env python3
"""Generate tier-owned automation and inputs plus genuinely shared building blocks."""

import argparse
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required. Activate a Python environment with PyYAML; "
             "see docs/development/generated-repositories.md#purpose-and-prerequisites.")

from generated_files import MARKER, RepositoryWriter
from documentation import copy_documentation, shared_readme, tier_readme
from project_docs import architecture_scaffold
from licensing import copy_attribution
from payload import (TIERS, copy_payload, read_file, report_legacy_deployments,
                     report_edge_ownership, report_legacy_shared, tier_setups, validate_layout)

UPSTREAM = Path(__file__).resolve().parents[2]
REPOSITORIES = ["shared", *TIERS, "architecture"]


def check_directory_case(path):
    if path.parent.is_dir():
        conflicts = [child for child in path.parent.iterdir()
                     if child.name.lower() == path.name and child.name != path.name]
        if conflicts:
            raise ValueError(f"Existing mixed-case path: {conflicts[0]}. "
                             f"Rename it to {path.name} before generation or refresh; "
                             "no automatic directory/state migration is performed. "
                             "See docs/development/generated-repositories.md#prefix-casing.")


def tier_repo(writer, tier, prefix):
    setups = tier_setups(UPSTREAM, tier)
    copy_payload(writer, UPSTREAM, tier, prefix)
    report_legacy_deployments(writer)
    tier_readme(writer, tier, prefix, setups)
    setup_list = writer.root / ".deployment-setups"
    registered = set(setup_list.read_text(encoding="utf-8").splitlines()) if setup_list.is_file() else set(setups)
    report_edge_ownership(writer, tier, registered)
    template_setups = {"immutable-template", "template-refresh"}
    if ((tier == "tier-0" and not template_setups.issubset(registered))
            or (tier == "tier-1" and template_setups.intersection(registered))):
        print("Template lifecycle belongs to Tier 0. Existing collections: review .deployment-setups, "
              "inventory and state migration before applying newly added roots; refresh does not move state.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="homelab",
                        help="Display prefix; folder names use lowercase (default: homelab).")
    parser.add_argument("--root", type=Path, default=UPSTREAM.parent,
                        help="Parent of <prefix>-iac/ (default: beside this kit checkout).")
    parser.add_argument("--repo", action="append", choices=[*REPOSITORIES, "all"], help="Repeat to select repositories.")
    parser.add_argument("--refresh", action="store_true", help="Update unchanged generated files; preserve local edits.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.prefix):
        parser.error("--prefix must start with a letter or number and contain only letters, numbers, and dashes")
    repo_prefix = args.prefix.lower()
    collection = args.root / f"{repo_prefix}-iac"
    check_directory_case(collection)
    if collection.is_symlink() or UPSTREAM.is_relative_to(collection.resolve()):
        parser.error(f"Collection must not contain the upstream or replace a symlink: {collection}")
    print(f"Collection: {collection.resolve()}")
    if (collection / ".git").exists():
        parser.error("The collection directory must not be a Git repository; each child owns its history")
    selected = REPOSITORIES if not args.repo or "all" in args.repo else list(dict.fromkeys(args.repo))
    # Check every sibling's casing: selected repositories may link to any of the others.
    for name in REPOSITORIES:
        check_directory_case(collection / f"{repo_prefix}-{name}")
    destinations = {name: collection / f"{repo_prefix}-{name}" for name in selected}
    for destination in destinations.values():
        if destination.is_symlink() or UPSTREAM.is_relative_to(destination.resolve()):
            parser.error(f"Output must not replace the upstream or a symlink: {destination}")
    validate_layout(UPSTREAM)
    for name in selected:
        writer = RepositoryWriter(destinations[name], args.refresh, args.dry_run)
        writer.write(".gitattributes", f"# {MARKER}\n* text=auto eol=lf\n")
        writer.write(".gitignore", f"# {MARKER}\n" + read_file(UPSTREAM / ".gitignore"))
        copy_attribution(writer, UPSTREAM, name)
        if name == "shared":
            copy_payload(writer, UPSTREAM, name, args.prefix)
            report_legacy_shared(writer, UPSTREAM)
            shared_readme(writer, args.prefix)
        elif name == "architecture":
            copy_documentation(writer, args.prefix, UPSTREAM)
            architecture_scaffold(writer, args.prefix)
        else:
            tier_repo(writer, name, args.prefix)
        writer.finish()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, yaml.YAMLError) as error:
        sys.exit(f"Generation failed: {error}")
