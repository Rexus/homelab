"""Refresh Shared's consumer references from successfully applied Tier 0 outputs.

Reference: docs/08-reference/template-catalog.md
"""

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

try:
    import hcl2
except ImportError:
    sys.exit("Missing python-hcl2. Run scripts/proxmox-templates.sh setup, or install "
             "ansible/runtime-requirements.txt in the prebuilt template runtime.")


def published_references(candidates):
    if not isinstance(candidates, dict) or not candidates:
        raise ValueError("No applied template candidates were returned; Shared was not changed.")
    references = {}
    for key, candidate in candidates.items():
        if not isinstance(candidate, dict):
            raise ValueError(f"Invalid applied candidate {key}; Shared was not changed.")
        vm_id = candidate.get("vm_id")
        if type(vm_id) is not int or vm_id < 100 or str(vm_id) in references:
            raise ValueError(f"Invalid or duplicate applied VMID for {key}; Shared was not changed.")
        entry = {field: candidate.get(field) for field in ("title", "node_name", "family", "tags")}
        if any(not isinstance(entry[field], str) or not entry[field].strip()
               for field in ("title", "node_name", "family")):
            raise ValueError(f"Missing consumer metadata for {key}; Shared was not changed.")
        if entry["family"] not in ("redhat", "debian", "talos", "alma", "rocky"):
            raise ValueError(f"Unsupported template family for {key}; Shared was not changed.")
        if not isinstance(entry["tags"], list) or any(not isinstance(tag, str) for tag in entry["tags"]):
            raise ValueError(f"Invalid image tags for {key}; Shared was not changed.")
        references[str(vm_id)] = entry
    return references


def merged_catalog(original, references):
    try:
        data = hcl2.loads(original, serialization_options=hcl2.SerializationOptions(
            strip_string_quotes=True, with_comments=False,
        ))
    except Exception as error:
        raise ValueError("Shared catalog is not valid HCL; check its syntax before rerunning plan/apply.") from error
    catalog = data.get("proxmox_template_catalog")
    if not isinstance(catalog, dict) or any(not isinstance(entry, dict) for entry in catalog.values()):
        raise ValueError("Shared must contain a literal proxmox_template_catalog map; it was not changed.")
    default = data.get("default_linux_vm_template_id")
    if "default_linux_vm_template_id" not in data or (default is not None and type(default) is not int):
        raise ValueError("Shared must define a literal default_linux_vm_template_id or null.")
    updated = {key: dict(entry) for key, entry in catalog.items()}
    for vm_id, entry in references.items():
        updated[vm_id] = {**updated.get(vm_id, {}), **entry}
    if updated == catalog:
        return original, default

    # Use the HCL parser's source span, not regexes, to leave settings and comments
    # outside the managed reference map intact. Retired entries remain in the map.
    tree = hcl2.parses_to_tree(original)
    attributes = [node for node in tree.children[0].children
                  if getattr(node, "data", None) == "attribute"
                  and str(node.children[0].children[0]) == "proxmox_template_catalog"]
    if len(attributes) != 1:
        raise ValueError("Shared must contain exactly one proxmox_template_catalog attribute.")
    attribute = attributes[0]
    # JSON's literal object syntax is valid inside an HCL expression. Escape HCL
    # template directives so published names/tags cannot become interpolation.
    literal = json.dumps(updated).replace("${", "$${").replace("%{", "%%{")
    rendered = hcl2.dumps(hcl2.loads(f"proxmox_template_catalog = {literal}\n")).rstrip()
    return original[:attribute.meta.start_pos] + rendered + original[attribute.meta.end_pos:], default


def update_catalog(path, candidates):
    references = published_references(candidates)
    original = path.read_text(encoding="utf-8")
    updated, default = merged_catalog(original, references)
    if updated == original:
        return False, default
    # Format and check a temporary HCL file before replacing the tracked catalog.
    # Failed parsing, formatting or concurrent edits leave the original untouched.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tfvars",
                                     prefix=".proxmox-catalog-", dir=path.parent, delete=False) as temporary:
        temporary.write(updated)
        temporary_path = Path(temporary.name)
    try:
        subprocess.run(["terraform", "fmt", "-list=false", str(temporary_path)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if path.read_text(encoding="utf-8") != original:
            raise ValueError("Shared catalog changed during synchronization; rerun plan/apply.")
        os.chmod(temporary_path, stat.S_IMODE(path.stat().st_mode))
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return True, default


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("candidates", type=Path)
    args = parser.parse_args()
    try:
        changed, default = update_catalog(args.catalog, json.loads(args.candidates.read_text(encoding="utf-8")))
    except Exception as error:
        # Catalog contents and parser diagnostics may contain locally added data.
        if isinstance(error, ValueError):
            print(str(error), file=sys.stderr)
        print("Shared catalog update failed; the existing catalog and applied Terraform state were retained.\n"
              "Check the catalog syntax, template output, write permissions and concurrent edits, then rerun plan/apply.",
              file=sys.stderr)
        return 1
    print(f"Shared template references {'updated' if changed else 'already current'}: {args.catalog}")
    if default is None:
        print("No default Linux template selected. Clone-test, then set default_linux_vm_template_id in Shared.")
    else:
        print(f"Preserved default Linux template: {default}. Clone-test new references before selecting them.")
    print("Review and commit the Shared catalog separately; no Git commit or push was performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
