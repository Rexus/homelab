"""Scope-specific engineering context derived from native relationships and existing traces."""

import json
import os
from pathlib import Path
from intake_sources import require, check_native_tree
from intake_platform import dependencies
from intake_use_cases import scenario_functions, CASE_GUIDES

REGISTRY = Path("scripts/architecture/config/views/design-context.json")
INDEX = Path("artifacts/architecture/generated/design-context.json")
BEGIN, END = "<!-- BEGIN DESIGN CONTEXT -->", "<!-- END DESIGN CONTEXT -->"


def scopes(root):
    check_native_tree(root)
    entries = json.loads((root / REGISTRY).read_text(encoding="utf-8"))["scopes"]
    pages = [s["page"] for s in entries]
    actual = {s["page"] for s in entries if (root / s["page"]).is_file()}
    require(
        len(set(pages)) == len(pages) and set(pages) == actual,
        "Every design overview needs exactly one scoped context",
    )
    for scope in entries:
        for name in [scope["page"], *scope["owners"]]:
            require((root / name).is_file(), "Missing design-context owner: " + name)
    return entries


def source_paths(root):
    return {REGISTRY.as_posix()} | {p for s in scopes(root) for p in s["owners"]}


def owned_parts(model, roots):
    require(set(roots) <= set(model["elements"]), "Unknown context model root")
    found = set(roots)
    while True:
        before = set(found)
        for edge in model["edges"]:
            if edge["from"] in found and edge["kind"] in ("contains", "bound-to"):
                if model["elements"][edge["to"]]["kind"] == "PartUsage":
                    found.add(edge["to"])
        if before == found:
            return found


def context(model, scope, records, plan):
    parts = owned_parts(model, scope["roots"])
    edges = model["edges"]
    allocations = {
        f: {e["to"] for e in edges if e["from"] == f and e["kind"] == "allocated-to"}
        for f in model["functions"]
    }
    direct = {f for f, targets in allocations.items() if targets & parts}
    supported = {
        f
        for f, targets in allocations.items()
        if f not in direct and any(set(dependencies(model, t)) & parts for t in targets)
    }
    selected = direct | supported
    scenarios = {key for key in model["scenarios"] if set(scenario_functions(model, key)) & selected}
    cases = {model["scenarios"][key]["use_case"] for key in scenarios}
    types = {e["to"] for e in edges if e["from"] in parts and e["kind"] == "typed-by"}
    requirements = {
        e["to"]
        for e in edges
        if e["from"] in (direct | types)
        and e["kind"] == "depends-on"
        and model["elements"][e["to"]]["kind"] == "RequirementUsage"
    }
    related = {
        e["to"]
        for e in edges
        if e["from"] in supported
        and e["kind"] == "depends-on"
        and model["elements"][e["to"]]["kind"] == "RequirementUsage"
    }
    actors = {
        case["bindings"][actor]
        for key, case in model["use_cases"].items()
        if key in cases
        for actor in case["actors"]
    }
    actor_functions = {f for f, targets in allocations.items() if targets & actors} - selected
    actor_types = {e["to"] for e in edges if e["from"] in actors and e["kind"] == "typed-by"}
    related.update(
        e["to"]
        for e in edges
        if e["from"] in actor_types
        and e["kind"] == "depends-on"
        and model["elements"][e["to"]]["kind"] == "RequirementUsage"
    )
    related -= requirements
    messages = {
        m
        for key in scenarios
        for m in model["scenarios"][key]["messages"]
        if any(e["from"] == m and e["to"] in selected and e["kind"] == "depends-on" for e in edges)
    }
    traced = (types | requirements | related | messages) & set(records)
    implementation = sorted(
        {
            p
            for key in types & set(records)
            if records[key]["state"] == "implementation-source"
            for p in records[key]["sources"]
        }
    )
    checks = sorted({p for key in traced for p in records[key].get("checks", [])})
    manual = sorted(key for key in scenarios if plan[key].get("manual"))
    providers = {
        e["to"]
        for e in edges
        if e["from"] in parts
        and e["kind"] == "depends-on"
        and e["to"] not in parts
        and model["elements"][e["to"]]["kind"] == "PartUsage"
    }
    realization_roots = {e["to"] for e in edges if e["from"] in parts and e["kind"] == "allocated-to"}
    internal_realization = owned_parts(model, realization_roots)
    consumers = {
        e["from"]
        for e in edges
        if e["to"] in parts
        and e["kind"] == "depends-on"
        and e["from"] not in (parts | internal_realization)
        and model["elements"][e["from"]]["kind"] == "PartUsage"
    }
    interactions = set()
    for edge in edges:
        if edge["kind"] in ("flow", "connected-to"):
            if edge["from"] in parts and edge["to"] not in parts:
                interactions.add(edge["to"])
            if edge["to"] in parts and edge["from"] not in parts:
                interactions.add(edge["from"])
    resource_providers = {
        p
        for f in direct
        for t in allocations[f] & parts
        for p in dependencies(model, t)
        if p.startswith("P-") and model["elements"][p]["kind"] == "PartUsage"
    } - parts
    return {
        "scope": scope["key"],
        "use_case_names": [model["elements"][k]["name"] for k in sorted(cases)],
        "function_names": [model["elements"][k]["name"] for k in sorted(direct)],
        "actor_functions": sorted(actor_functions),
        "resource_providers": sorted(resource_providers),
        "parts": sorted(parts),
        "use_cases": sorted(cases),
        "scenarios": sorted(scenarios),
        "functions": sorted(direct),
        "supported_functions": sorted(supported),
        "requirements": sorted(requirements),
        "related_requirements": sorted(related),
        "interacting_parts": sorted(interactions),
        "providers": sorted(providers),
        "consumers": sorted(consumers),
        "implementation": implementation,
        "checks": checks,
        "manual_scenarios": manual,
        "coverage": scope["coverage"],
    }


def relative(page, target):
    name, sep, anchor = str(target).partition("#")
    return Path(os.path.relpath(name, Path(page).parent)).as_posix() + (sep + anchor if sep else "")


def projections(root, model, records, plan):
    result = {}
    for scope in scopes(root):
        data = context(model, scope, records, plan)
        page = (root / scope["page"]).read_text(encoding="utf-8")
        require(bool(page.strip()), "Empty native design owner: " + scope["page"])
        result[scope["key"]] = (
            scope,
            data,
            page,
        )
    return result


def context_outputs(root, model, records, plan):
    """Derived inspection data, not another authored relationship model or diagram."""
    projected = projections(root, model, records, plan)
    return {INDEX: json.dumps({key: data for key, (_, data, _) in projected.items()}, indent=2) + "\n"}
