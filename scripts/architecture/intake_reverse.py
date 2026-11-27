"""Reverse file/test trace with bounded model traversal and explainable witness paths."""

from collections import deque
import hashlib
from pathlib import Path
from intake_use_cases import connections

GENERATED = "artifacts/architecture/generated/software-intake/"
REVERSE_REPORT = GENERATED + "reverse-trace.md"
REVERSE_INDEX = GENERATED + "reverse-trace.json"


def asset_id(asset):
    return "asset-" + hashlib.sha256(asset.encode("utf-8")).hexdigest()[:16]


def associations(records):
    found = {}
    for element, record in sorted(records.items()):
        for field, relation in (("sources", "source"), ("checks", "check"), ("test_symbols", "test method")):
            for asset in record.get(field, []):
                found.setdefault(asset, []).append({"element": element, "relation": relation,
                                                    "state": record["state"]})
    return dict(sorted(found.items()))


def asset_links(records):
    return {asset: REVERSE_REPORT + "#" + asset_id(asset) for asset in associations(records)}


def upstream_paths(model, seeds):
    """Walk implementations to their consumers/intent, without fanning out via common guards."""
    incoming = {}
    for edge in model["edges"]:
        kind = edge["kind"]
        if kind == "contains":
            # A containing behavior is not a route into every alternative scenario.
            child = model["elements"][edge["to"]]
            if child["kind"] != "PartUsage" and edge["to"] not in model["scenarios"]:
                continue
        elif kind not in ("typed-by", "allocated-to", "bound-to", "depends-on", "uses-message"):
            continue
        # Scenarios follow their selected messages, never the entire behavior definition.
        if kind == "typed-by" and edge["from"] in model["scenarios"]:
            continue
        incoming.setdefault(edge["to"], []).append(edge)
    paths = {key: [] for key in sorted(seeds)}
    queue = deque(paths)
    while queue:
        key = queue.popleft()
        for edge in sorted(incoming.get(key, []), key=lambda e: (e["from"], e["kind"])):
            other = edge["from"]
            if other not in paths:
                paths[other] = paths[key] + [{"from": key, "to": other,
                    "relation": edge["kind"], "direction": "reverse"}]
                queue.append(other)
    return paths


def review(model, records, asset):
    links = associations(records)
    if asset not in links:
        raise ValueError("No recorded software-intake trace for " + asset +
                         "; missing coverage does not establish no impact")
    direct = links[asset]
    paths = upstream_paths(model, {row["element"] for row in direct})
    # A message identifies its function without turning every other message of that function
    # into an affected scenario. This preserves hit/miss/denial and actor boundaries.
    functions = {key: path for key, path in paths.items() if key in model["functions"]}
    for key, path in list(paths.items()):
        for function in connections(model, key, "depends-on"):
            if function in model["functions"] and function not in functions:
                functions[function] = path + [{"from": key, "to": function,
                    "relation": "depends-on", "direction": "forward"}]
    scenarios = {key: path for key, path in paths.items() if key in model["scenarios"]}
    cases = {key: path for key, path in paths.items() if key in model["use_cases"]}
    for key, path in scenarios.items():
        case = model["scenarios"][key]["use_case"]
        cases.setdefault(case, path + [{"from": key, "to": case, "relation": "scenario-of",
                                        "direction": "owner"}])
    requirements = {key: path for key, path in paths.items()
                    if model["elements"][key]["kind"] == "RequirementUsage"}
    guard_owners = {**functions, **{r["element"]: paths[r["element"]] for r in direct
                   if model["elements"][r["element"]]["kind"] == "PartDefinition"}}
    for key, path in guard_owners.items():
        for target in connections(model, key, "depends-on"):
            if model["elements"][target]["kind"] == "RequirementUsage":
                requirements.setdefault(target, path + [{"from": key, "to": target,
                    "relation": "depends-on", "direction": "forward"}])
    verification = {key:path for key,path in paths.items() if key in model.get("verification", {})}
    for key,path in verification.items():
        if key not in {r["element"] for r in direct}:
            continue
        for target in connections(model, key, "verifies"):
            requirements.setdefault(target, path + [{"from":key,"to":target,"relation":"verifies","direction":"forward"}])
    checks = sorted({value for key in paths if key in records
                     for value in records[key].get("test_symbols", records[key].get("checks", []))})
    return {"asset": asset, "id": asset_id(asset), "direct": direct,
            "mode": "verification" if all(r["relation"] != "source" for r in direct) else "implementation/context",
            "functions": dict(sorted(functions.items())), "scenarios": dict(sorted(scenarios.items())),
            "use_cases": dict(sorted(cases.items())), "requirements": dict(sorted(requirements.items())),
            "verification_cases": dict(sorted(verification.items())),
            "checks": checks, "paths": dict(sorted(paths.items()))}


def path_text(key, hops):
    if not hops:
        return key + " (direct trace)"
    return hops[0]["from"] + "".join(
        " →[" + ("reverse " if h["direction"] == "reverse" else "") + h["relation"] + "] " + h["to"]
        for h in hops)


def select_asset(root, value, records):
    name, separator, symbol = value.partition("::")
    path = Path(name.replace("\\", "/"))
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Asset must belong to this upstream checkout")
    candidate = resolved.relative_to(root.resolve()).as_posix() + (separator + symbol if separator else "")
    if candidate not in associations(records):
        raise ValueError("No recorded software-intake trace for " + candidate +
                         "; missing coverage does not establish no impact")
    return candidate
