"""Copy visible repository payloads without including operational inputs or state."""

import re

import yaml

TIERS = ("tier-0", "tier-1", "tier-2")
SHARED_TREES = {
    "terraform/modules": ("*.tf",),
    "ansible/roles": ("*.yml", "*.yaml", "*.j2"),
    "ansible/playbooks": ("*.yml",),
    "packer/templates": ("*.pkr.hcl",),
    "scripts": ("*.sh",),
    "templates": (".gitkeep",),
}
TIER_TREES = {
    "terraform": ("*.tf", "*.example", ".terraform.lock.hcl"),
    "ansible": ("ansible.cfg", "*.example"),
    "scripts": ("*.sh",),
    "packer": ("*.example",),
    "templates": ("*.example", ".gitkeep"),
    "ci": ("*.example",),
    "bootstrap": ("*.tf", "*.yaml", ".gitkeep"),
    "clusters": ("*.yaml", ".gitkeep"),
    "environments": (".gitkeep",),
    "workloads": (".gitkeep",),
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
        for relative in (f"terraform/environments/{setup}/main.tf",
                         f"terraform/environments/{setup}/terraform.tfvars.example",
                         f"ansible/group_vars/{setup.replace('-', '_')}.yml.example"):
            if not (root / relative).is_file():
                raise ValueError(f"Missing setup source: {tier}/{relative}")
    roots = {path.parent.name for path in (root / "terraform/environments").glob("*/main.tf")}
    if roots != set(setups):
        raise ValueError(f"Terraform roots disagree with {tier}/.deployment-setups: {sorted(roots)}")
    return setups


def validate_layout(upstream):
    """Check ownership where maintainers edit it, before writing any output."""
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
