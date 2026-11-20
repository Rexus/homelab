"""Read the selected upstream Stage 1 examples and verify their implementation entry points."""

import json
from pathlib import Path
import hcl2
import yaml

MODEL = Path("architecture/use-cases/software-intake")
VIEWS = Path("architecture/views/software-intake")
GENERATED = Path("architecture/generated/software-intake")
TRACE = Path("architecture/trace/software-intake.json")
TOOLCHAIN = Path("architecture/toolchain.json")
TF = "tier-2/terraform/deployments/cache/terraform.tfvars.example"
VARS = "tier-2/ansible/group_vars/cache.yml.example"
INVENTORY = "tier-2/ansible/inventory/hosts.yml.example"
ROLE = "tier-2/ansible/roles/cache_proxy"
RECIPE = "tier-2/ansible/playbooks/deployment/outbound-cache.yml"


def read_yaml(root, name):
    return yaml.safe_load((root / name).read_text(encoding="utf-8"))


def read_hcl(root, name):
    with (root / name).open(encoding="utf-8") as stream:
        return hcl2.load(
            stream,
            serialization_options=hcl2.SerializationOptions(
                strip_string_quotes=True, with_comments=False, explicit_blocks=False
            ),
        )


def require(condition, message):
    if not condition:
        raise ValueError(message)


def walk_tasks(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_tasks(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_tasks(child)


def selected_inputs(root):
    tf = read_hcl(root, TF)
    config = {**read_yaml(root, ROLE + "/defaults/main.yml"), **read_yaml(root, VARS)}
    members = tf["vm_instances"]
    hosts = read_yaml(root, INVENTORY)["all"]["children"]["cache"]["hosts"]
    require(set(members) == set(hosts), "Cache Terraform members and Ansible cache hosts disagree")
    require(
        set(members) <= set(config["platform_host_ips"]), "A cache member has no connection address"
    )
    require(
        not tf.get("lxc_instances"),
        "This view supports VM members; add an LXC projection before selecting LXCs",
    )
    require(
        2 <= len(members) <= 4,
        "This failover view supports two to four members; adapt the view for other shapes",
    )
    require(
        config["cache_keepalived_enabled"] is True, "This selected realization requires a failover VIP"
    )
    require(
        config["cache_squid_data_disk_enabled"] is True,
        "Dedicated-cache-disk view needs dedicated storage",
    )
    require(
        config["cache_squid_allowed_cidrs"] and config["cache_squid_allowed_domains"],
        "Source/client policy must be explicit",
    )
    require(
        config["cache_keepalived_group"] == "cache", "The selected VIP and inventory groups disagree"
    )
    zones = {v["network_zone_key"] for v in members.values()}
    require(len(zones) == 1, "Split the view for members on different networks")
    for name, vm in members.items():
        disks = [
            d
            for d in vm["extra_disks"]
            if config["cache_squid_data_device"].endswith("drive-" + d["interface"])
        ]
        require(len(disks) == 1, f"{name}: mounted cache device has no unique Terraform disk")
        require(
            config["cache_squid_cache_mb"] < disks[0]["size_gb"] * 1000,
            f"{name}: cache exceeds its disk",
        )
        vm["_cache_disk"] = disks[0]
    return {"members": members, "config": config, "network": next(iter(zones))}


def check_wiring(root):
    modules = {
        key: value
        for block in read_hcl(root, "tier-2/terraform/deployments/cache/main.tf")["module"]
        for key, value in block.items()
    }
    require(
        modules["environment"]["vm_instances"] == "${var.vm_instances}",
        "Terraform root no longer consumes selected VM inputs",
    )
    require(
        modules["vms"]["source"] == "../../modules/vm"
        and modules["vms"]["for_each"] == "${module.environment.vm_instances}"
        and modules["vms"]["extra_disks"] == "${each.value.extra_disks}",
        "VM resource/module wiring changed; review allocation",
    )
    recipe = read_yaml(root, RECIPE)
    require(
        any(p.get("hosts") == "cache" and "cache_proxy" in p.get("roles", []) for p in recipe),
        "Cache role is not reachable through its deployment recipe",
    )
    compatibility = read_yaml(root, "tier-2/ansible/playbooks/cache.yml")
    require(
        any(
            p.get("ansible.builtin.import_playbook") == "deployment/outbound-cache.yml"
            for p in compatibility
        ),
        "Cache entry point no longer imports the selected deployment recipe",
    )
    imports = {t.get("ansible.builtin.import_tasks") for t in read_yaml(root, ROLE + "/tasks/main.yml")}
    require(
        {"storage.yml", "squid.yml", "keepalived.yml", "services.yml"} <= imports,
        "Cache role wiring changed",
    )
    storage = list(walk_tasks(read_yaml(root, ROLE + "/tasks/storage.yml")))
    calls = {
        t["ansible.builtin.include_role"].get("tasks_from")
        for t in storage
        if isinstance(t.get("ansible.builtin.include_role"), dict)
        and t["ansible.builtin.include_role"].get("name") == "data_volume"
    }
    require({"inspect", "validate", "prepare"} <= calls, "Shared storage safety path is incomplete")
    validation = [t.get("ansible.builtin.include_role", {}) for t in walk_tasks(recipe)]
    require(
        any(
            v.get("name") == "shared" and v.get("tasks_from") == "keepalived_vip_validation"
            for v in validation
        ),
        "VIP ownership/failover validation is no longer connected",
    )


def realization(inputs):
    """Generate actual software/virtual resources; tier/zone frames remain view annotations."""
    quote = lambda s: "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"
    lines = [
        "package Reference {",
        "  doc /* Selected software and virtual resources from IaC. Tiers and zones are explanatory classifications, not containing systems. Physical identities remain site-owned. */",
        "  part <'R-Pair'> services : PolicyProxy {",
    ]
    for name in sorted(inputs["members"]):
        lines += [
            f'    part <{quote("VM-"+name)}> {quote(name)} : ProxyMember {{',
            f'      attribute selectedNetwork : ScalarValues::String = {json.dumps(inputs["network"])};',
            f'      part <{quote("RUN-"+name)}> proxy :>> ProxyMember::proxy;',
            f'      part <{quote("DISK-"+name)}> storage :>> ProxyMember::storage {{',
            f'        item <{quote("CONTENT-"+name)}> {quote("Cached content")} :>> DisposableCache::contents;',
            '      }',
            f'      flow <{quote("IO-"+name)}> cacheIO from proxy.cacheAccess.payload to storage.access.payload;',
            "    }",
        ]
    lines += [
        "  }",
        "  part <'R-VIP'> vip : SharedListener;",
        "  flow <'R-dispatch'> dispatch from vip.dispatch.payload to services.listener.payload;",
        "  ref part <'R-Upstream'> sources : ApprovedSource;",
        "  ref part <'R-Consumers'> clients : UpdateClient;",
        "  flow <'R-request'> request from clients.access.payload to vip.inbound.payload;",
        "  flow <'R-upstream'> upstream from services.outbound.payload to sources.access.payload;",
        "  allocation <'ALLOC-proxy'> allocate context.'Policy proxy / HTTP cache' to services;",
    ]
    for name in sorted(inputs["members"]):
        lines.append(f"  allocation <{quote('ALLOC-'+name)}> allocate context.'Rebuildable cache storage' to services.{quote(name)}.storage;")
        member=f"services::{quote(name)}"
        require(inputs["members"][name]["_cache_disk"].get("storage_class") == "local",
                "The selected platform contract is local cache storage; model a different provider before selecting another class")
        lines += [
            f"  dependency <{quote('HOST-'+name)}> 'Uses virtual execution: {name}' from {member} to platform::'Proxmox virtualization';",
            f"  dependency <{quote('NET-'+name)}> 'Uses guest attachment: {name}' from {member} to platform::'Guest network attachment';",
            f"  dependency <{quote('STORE-'+name)}> 'Uses local storage: {name}' from {member}::storage to platform::'Local guest-disk service';",
        ]
    return "// Generated fragment inserted into SoftwareIntake by the builder; do not edit.\n" + "\n".join(lines+["}", ""])


def trace_map(root):
    records = json.loads((root / TRACE).read_text(encoding="utf-8"))
    for key, record in records.items():
        for path in record["sources"] + record.get("checks", []):
            resolved = (root / path).resolve()
            require(
                resolved.is_relative_to(root.resolve()) and resolved.is_file(),
                f"{key}: missing trace target {path}",
            )
    return records
