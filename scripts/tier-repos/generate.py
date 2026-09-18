#!/usr/bin/env python3
"""Generate tier-owned inputs and a shared copy of the deployment automation."""

import argparse
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
from payload import TIERS, copy_payload, read_file, tier_setups, validate_layout

UPSTREAM = Path(__file__).resolve().parents[2]
REPOSITORIES = ["shared", *TIERS, "architecture"]


def tier_repo(writer, tier, prefix):
    setups = tier_setups(UPSTREAM, tier)
    copy_payload(writer, UPSTREAM, tier, prefix)
    tier_readme(writer, tier, prefix, setups)
    setup_list = writer.root / ".deployment-setups"
    registered = set(setup_list.read_text(encoding="utf-8").splitlines()) if setup_list.is_file() else set(setups)
    template_setups = {"immutable-template", "template-refresh"}
    if ((tier == "tier-0" and not template_setups.issubset(registered))
            or (tier == "tier-1" and template_setups.intersection(registered))):
        print("Template lifecycle belongs to Tier 0. Existing collections: review .deployment-setups, "
              "inventory and state migration before applying newly added roots; refresh does not move state.")


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
    validate_layout(UPSTREAM)
    for name in selected:
        destination = collection / f"{args.prefix}-{name}"
        if destination.is_symlink() or UPSTREAM.is_relative_to(destination.resolve()):
            parser.error(f"Output must not replace the upstream or a symlink: {destination}")
        writer = RepositoryWriter(destination, args.refresh, args.dry_run)
        writer.write(".gitattributes", f"# {MARKER}\n* text=auto eol=lf\n")
        writer.write(".gitignore", f"# {MARKER}\n" + read_file(UPSTREAM / ".gitignore"))
        if (UPSTREAM / "LICENSE").is_file():
            writer.write("LICENSE", read_file(UPSTREAM / "LICENSE"))
        if name == "shared":
            copy_payload(writer, UPSTREAM, name, args.prefix)
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
