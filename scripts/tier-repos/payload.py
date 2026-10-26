"""Copy visible repository payloads without including operational inputs or state."""

import re

import yaml

TIERS = ("tier-0", "tier-1", "tier-2")
TERRAFORM_ONLY_DEPLOYMENTS = {
    "tier-0": {"kubernetes", "templates", "ci-auth"},
    "tier-1": {"kubernetes"},
    "tier-2": {"kubernetes"},
}
SHARED_TREES = {
    "config": ("*.json", "platform.tfvars"),
    "ansible/roles": ("*.yml", "*.yaml", "*.j2"),
    "ansible/playbooks": ("*.yml",),
    "scripts": ("*.sh", "log-evidence.py", "saved-plan-context.py"),
    "templates": ("proxmox-catalog.tfvars",),
}
TIER_TREES = {
    "terraform": ("*.tf", "*.example", ".terraform.lock.hcl"),
    "ansible": ("ansible.cfg", "requirements.txt", "*.example"),
    "ansible/playbooks": ("*.yml", "*.yaml"),
    "ansible/roles": ("*.yml", "*.yaml", "*.j2", "logging_checkpoint.py", "logging_io.py",
                      "logging_health.py", ".gitkeep"),
    "scripts": ("*.sh",),
    "packer": ("*.example", "*.pkr.hcl"),
    "templates": ("*.example", ".gitkeep"),
    "ci": ("*.example",),
    "bootstrap": ("*.tf", "*.yaml", ".gitkeep"),
    "clusters": ("*.yaml", ".gitkeep"),
    "environments": (".gitkeep",),
    "workloads": (".gitkeep", "*.example"),
}
OWNED_TREES = {"bootstrap", "clusters", "environments", "workloads", "ci"}


def read_file(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError(f"Source must be a regular kit file: {path}")
    return path.read_text(encoding="utf-8")


def tier_setups(upstream, tier):
    root = upstream / tier
    setups = read_file(root / ".deployment-setups").splitlines()
    if not setups or len(set(setups)) != len(setups):
        raise ValueError(f"Expected a nonempty, unique setup list in {tier}/.deployment-setups")
    for setup in setups:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", setup):
            raise ValueError(f"Invalid setup name in {tier}: {setup!r}")
        for relative in (f"terraform/deployments/{setup}/main.tf",
                         f"terraform/deployments/{setup}/terraform.tfvars.example",
                         f"ansible/playbooks/{setup}.yml",
                         f"ansible/group_vars/{setup.replace('-', '_')}.yml.example"):
            if not (root / relative).is_file():
                raise ValueError(f"Missing setup source: {tier}/{relative}")
    roots = {path.parent.name for path in (root / "terraform/deployments").glob("*/main.tf")}
    if roots != set(setups) | TERRAFORM_ONLY_DEPLOYMENTS.get(tier, set()):
        raise ValueError(f"Terraform roots disagree with {tier}/.deployment-setups: {sorted(roots)}")
    return setups


def report_legacy_deployments(writer):
    legacy = [writer.root / "terraform/environments", writer.root / "terraform/talos",
              writer.root / "terraform/deployments/talos",
              writer.root / "terraform/templates"]
    for directory in legacy:
        if any(path.is_file() and (path.suffix in (".tf", ".tfvars")
                                  or path.name.endswith((".tf.json", ".tfvars.json")))
               for path in directory.glob("*" if directory.name != "environments" else "*/*")):
            print(f"Legacy Terraform deployment preserved: {directory}. "
                  "Migrate local inputs and code before running deployment commands; see "
                  "docs/development/generated-repositories.md#terraform-layout-upgrade.")


def validate_layout(upstream):
    """Check ownership where maintainers edit it, before writing any output."""
    shared = upstream / "shared"
    for directory in ("ansible/inventory", "ansible/group_vars", "ansible/host_vars", "terraform"):
        if any(path.is_file() for path in (shared / directory).rglob("*")):
            raise ValueError(f"Shared must not own inventory, deployment inputs, or Terraform: shared/{directory}")
    registered, known_hosts = set(), set()
    for tier in TIERS:
        setups = set(tier_setups(upstream, tier))
        if registered & setups:
            raise ValueError(f"Setups have multiple tier owners: {sorted(registered & setups)}")
        registered.update(setups)
        root = upstream / tier / "ansible"
        inventory = yaml.safe_load(read_file(root / "inventory/hosts.yml.example"))
        groups = inventory["all"]["children"]
        hosts = {host for group in groups.values() for host in (group or {}).get("hosts", {})}
        if known_hosts & hosts:
            raise ValueError(f"Hosts have multiple tier owners: {sorted(known_hosts & hosts)}")
        known_hosts.update(hosts)
        for path in (root / "group_vars").glob("*.example"):
            ips = (yaml.safe_load(read_file(path)) or {}).get("platform_host_ips", {})
            if not set(ips).issubset(hosts):
                raise ValueError(f"Host IPs outside the tier inventory: {path}")


def copy_payload(writer, upstream, name, prefix):
    root = upstream / name

    def copy(path):
        relative = path.relative_to(root)
        content = read_file(path)
        # The source and generated collections have the same sibling layout.
        content = re.sub(r"(?<=\.\./)shared(?=[/\"'\s]|$)", f"{prefix}-shared", content)
        content = content.replace("check out shared beside", f"check out {prefix}-shared beside")
        owned = (relative.parts[0] in OWNED_TREES
                 or relative.as_posix() == "templates/proxmox-catalog.tfvars"
                 or relative.as_posix() == "config/platform.tfvars"
                 or relative.name in (".deployment-setups", ".gitkeep"))
        writer.write(relative.as_posix(), content, executable=path.suffix == ".sh", owned=owned)

    trees = SHARED_TREES if name == "shared" else TIER_TREES
    for directory, patterns in trees.items():
        for path in sorted((root / directory).rglob("*")):
            relative = path.relative_to(root / directory)
            if any(part.startswith(".") or part == "tests" for part in relative.parts[:-1]):
                continue
            if path.name.startswith(".") and path.name not in (".gitkeep", ".terraform.lock.hcl"):
                continue
            if not path.is_file() or not any(path.match(pattern) for pattern in patterns):
                continue
            if path.name == "override.tf" or path.name.endswith("_override.tf"):
                continue
            copy(path)
    for relative in (("ansible/requirements.yml",) if name == "shared"
                     else (".deployment-setups", "env.local.example")):
        copy(root / relative)
    if name != "shared" and (root / "ansible/requirements.yml").is_file():
        copy(root / "ansible/requirements.yml")


def report_legacy_shared(writer, upstream):
    candidates = {"scripts/proxmox-templates.sh", "terraform/modules", "packer/templates",
                  "ansible/inventory", "ansible/group_vars", "ansible/host_vars"}
    for tier in TIERS:
        root = upstream / tier
        for tree in ("ansible/playbooks", "ansible/roles"):
            for path in (root / tree).rglob("*"):
                if path.is_file():
                    relative = path.relative_to(root).as_posix()
                    if not (upstream / "shared" / relative).exists():
                        candidates.add(relative)
    retained = sorted(path for path in candidates if (writer.root / path).exists())
    if retained:
        print("Legacy tier-owned automation preserved in shared. Refresh all repos, review local edits "
              "and owned CI paths before deployment; see docs/development/generated-repositories.md"
              "#automation-ownership-upgrade.")


def report_edge_ownership(writer, tier, registered):
    legacy_roots = ("terraform/deployments/edge", "terraform/deployments/cache")
    old_tier_one = tier == "tier-1" and (
        {"edge", "cache"}.intersection(registered)
        or any((writer.root / path / "main.tf").is_file() for path in legacy_roots)
        or (writer.root / "ansible/playbooks/ingress.yml").is_file()
    )
    missing_tier_two = tier == "tier-2" and not {"edge", "cache"}.issubset(registered)
    if old_tier_one or missing_tier_two:
        print("Edge ownership upgrade: public edge and ordinary cache belong to Tier 2; "
              "private HSM ingress belongs to Tier 0. Existing inventory, registrations, code and state "
              "are preserved. Do not apply the new roots before deliberate migration; see "
              "docs/development/generated-repositories.md#edge-ownership-upgrade.")
