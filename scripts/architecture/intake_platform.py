"""Check the selected resource contract and project both directions of the dependency graph."""

from intake_sources import read_hcl, require
from intake_model import impact


def dependencies(model, selected):
    require(selected in model["elements"], "Unknown model identity: " + selected)
    found = {selected}
    while True:
        previous = set(found)
        for edge in model["edges"]:
            if edge["from"] in found and edge["kind"] in (
                "depends-on",
                "allocated-to",
                "contains",
                "bound-to",
            ):
                found.add(edge["to"])
        if found == previous:
            return sorted(found)


def check_platform(root, model, inputs):
    edges = {(e["from"], e["to"], e["kind"]) for e in model["edges"]}
    for name in inputs["members"]:
        for source, target in (
            (f"VM-{name}", "P-virtualization"),
            (f"VM-{name}", "P-network"),
            (f"DISK-{name}", "P-storage"),
        ):
            require(
                (source, target, "depends-on") in edges,
                f"Missing resource contract: {source} -> {target}",
            )
        require(
            inputs["members"][name]["_cache_disk"].get("storage_class") == "local",
            "Selected cache storage needs an explicit provider model for a non-local class",
        )
    modules = {
        key: value
        for block in read_hcl(root, "tier-2/terraform/deployments/cache/main.tf")["module"]
        for key, value in block.items()
    }
    for field in ("node_name", "bridge", "vlan_id", "storage_class", "extra_disks"):
        require(
            modules["vms"].get(field) == "${each.value." + field + "}",
            "Selected VM resource input is no longer wired: " + field,
        )
    require(
        modules["vms"].get("storage_class_datastores") == "${var.proxmox_storage_classes}",
        "Storage provider map is no longer wired",
    )
    source = root / "tier-2/terraform/modules/vm/main.tf"
    vm = source.read_text(encoding="utf-8")
    for binding in (
        "node_name       = var.node_name",
        "bridge   = var.bridge",
        "vlan_id  = var.vlan_id",
        "datastore_id = disk.value.datastore_id",
    ):
        require(binding in vm, "VM provider binding changed; review: " + binding)
    network = read_hcl(root, "tier-2/terraform/common.tfvars.example")["network_zones"][
        inputs["network"]
    ]
    require(
        network["bridge"] == "vmbr0",
        "Review the platform attachment contract for another bridge or VNet",
    )
    require(
        ("P-servers", "P-switches", "connected-to") in edges, "Missing physical attachment contract"
    )
    require(
        "P-storage-network" not in dependencies(model, "L-Cache"),
        "Local cache storage must not acquire an unselected storage-network dependency",
    )


def resource_report(model):
    lines = [
        "# Software intake resource relationships",
        "",
        "Generated from native model relationships. Platform elements are documented boundary contracts;",
        "host counts, device identities and switch-port placement remain site-owned acceptance inputs.",
        "",
        "| Consumer | Relationship | Provider / related element |",
        "| --- | --- | --- |",
    ]
    for edge in model["edges"]:
        if edge["kind"] not in ("depends-on", "connected-to") or not (
            edge["from"].startswith(("P-", "VM-", "DISK-")) and edge["to"].startswith("P-")
        ):
            continue
        relation = model["elements"][edge["id"]]["name"]
        left = model["elements"][edge["from"]]["name"]
        right = model["elements"][edge["to"]]["name"]
        lines.append(f'| {left} (`{edge["from"]}`) | {relation} | {right} (`{edge["to"]}`) |')
    lines += [
        "",
        "## Follow the same model in both directions",
        "",
        "The provider query follows declared dependencies, allocations and composition. The impact query",
        "walks toward consumers and their scenarios; it is conservative review scope, not a failure simulation.",
        "",
    ]
    for title, keys in (
        ("Providers supporting the proxy contract", dependencies(model, "L-Proxy")),
        ("Potential impact of changing the physical server contract", impact(model, "P-servers")),
        ("Potential impact of changing the guest network attachment", impact(model, "P-network")),
    ):
        lines += ["### " + title, "", ", ".join("`" + key + "`" for key in keys), ""]
    lines += [
        "The optional logical storage network remains outside the selected local-cache dependency path.",
        "A physical connection records attachment, not identical failure behavior in both directions.",
        "",
    ]
    return "\n".join(lines)
