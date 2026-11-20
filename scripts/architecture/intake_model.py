"""Native SysML JSON projection. No parsing of SysML text or inferred runtime verification."""

from intake_behavior import project_behavior
from intake_use_cases import project_use_cases
from intake_semantics import project_semantics
from intake_execution_model import project_execution
from intake_language import check_language


def normalize(raw):
    objects = {r["payload"]["@id"]: r["payload"] for r in raw}

    def in_scope(element):
        # Unnamed allocations have stable short names but no qualifiedName in the pilot export.
        seen = set()
        while element and element["@id"] not in seen:
            seen.add(element["@id"])
            if element.get("qualifiedName") == "SoftwareIntake":
                return True
            element = objects.get(element.get("owner", {}).get("@id"))
        return False

    names = {
        uid: e["declaredShortName"]
        for uid, e in objects.items()
        if e.get("declaredShortName") and in_scope(e)
    }
    if len(set(names.values())) != len(names):
        raise ValueError("Duplicate stable model identity")
    elements = {
        key: {
            "name": objects[uid].get("declaredName", key),
            "kind": objects[uid]["@type"],
            "docs": [objects[r["@id"]]["body"].strip() for r in objects[uid].get("documentation", [])],
        }
        for uid, key in names.items()
    }
    for uid, key in names.items():
        if objects[uid]['@type'] == 'PartDefinition':
            elements[key]['ports'] = sorted(e['declaredName'] for e in objects.values()
                if e['@type'] == 'PortUsage' and e.get('owner', {}).get('@id') == uid)
    edges = []

    def emit(source, target, kind, key=None):
        if source in names and target in names:
            edges.append(
                {
                    "from": names[source],
                    "to": names[target],
                    "kind": kind,
                    **({"id": key} if key else {}),
                }
            )

    def chain(ref):
        e = objects[ref["@id"]]
        chained = e.get("chainingFeature", [])
        return [uid for r in chained for uid in chain(r)] if chained else [e["@id"]]

    for uid, key in names.items():
        e = objects[uid]
        owner = e.get("owner", {}).get("@id")
        if owner in names:
            emit(owner, uid, "contains")
        if e["@type"] in ("PartUsage", "PortUsage", "ItemUsage", "ReferenceUsage"):
            for t in e.get("type", []):
                emit(uid, t["@id"], "typed-by")
        if e["@type"] == "PartUsage" and not e.get("isComposite", True):
            values = [
                objects[r["@id"]]
                for r in e.get("ownedMembership", [])
                if objects[r["@id"]]["@type"] == "FeatureValue"
            ]
            if values:
                if len(values) != 1 or values[0]["isDefault"]:
                    raise ValueError("Part reference needs one fixed binding: " + key)
                expression = objects[values[0]["value"]["@id"]]
                if expression["@type"] not in ("FeatureChainExpression", "FeatureReferenceExpression"):
                    raise ValueError("Unsupported part reference binding: " + key)
                feature = expression.get("targetFeature", expression.get("referent"))
                targets = [target for target in chain(feature) if target in names]
                if not targets or objects[targets[-1]]["@type"] != "PartUsage":
                    raise ValueError("Unresolved part reference binding: " + key)
                emit(uid, targets[-1], "bound-to")
        if e["@type"] in ("Dependency", "AllocationUsage", "FlowUsage", "ConnectionUsage"):
            for a in e["source"]:
                for b in e["target"]:
                    left = [i for i in chain(a) if i in names]
                    right = [i for i in chain(b) if i in names]
                    if not left or not right:
                        raise ValueError(f"Unsupported relation endpoints: {key}")
                    emit(
                        left[-1],
                        right[-1],
                        {
                            "Dependency": "depends-on",
                            "AllocationUsage": "allocated-to",
                            "FlowUsage": "flow",
                            "ConnectionUsage": "connected-to",
                        }[e["@type"]],
                        key,
                    )
    behaviors, behavior_edges = project_behavior(objects, names)
    edges.extend(behavior_edges)
    model = {
        "behaviors": dict(sorted(behaviors.items())),
        "elements": dict(sorted(elements.items())),
        "edges": sorted(edges, key=lambda e: (e["from"], e["to"], e["kind"], e.get("id", ""))),
    }
    model['language_checks'] = check_language(objects, {uid for uid, e in objects.items() if in_scope(e)})
    project_use_cases(objects, names, model)
    project_semantics(objects, names, model)
    project_execution(objects, names, model)
    model["edges"].sort(key=lambda e: (e["from"], e["to"], e["kind"], e.get("id", "")))
    return model


def impact(model, changed):
    if changed not in model["elements"]:
        raise ValueError(f"Unknown model identity: {changed}")
    affected = {changed}
    while True:
        previous = set(affected)
        for edge in model["edges"]:
            if edge["to"] in affected and edge["kind"] in (
                "typed-by",
                "contains",
                "depends-on",
                "flow",
                "uses-participant",
                "uses-condition",
                "uses-message",
                "allocated-to",
                "bound-to",
                "requires",
                "verifies",
                "satisfies",
            ):
                affected.add(edge["from"])
            if edge["from"] in affected and edge["kind"] == "allocated-to":
                affected.add(edge["to"])
        if affected == previous:
            return sorted(affected)


def validate_trace(model, records):
    unknown = set(records) - set(model["elements"])
    if unknown:
        raise ValueError(f"Trace records reference unknown model identities: {sorted(unknown)}")
    kinds = {"implementation-source", "manual-acceptance", "external-custody", "documented-context"}
    for key, record in records.items():
        if record["state"] not in kinds:
            raise ValueError(f'{key}: unsupported evidence claim {record["state"]}')


def trace_report(model, records, inputs):
    rows = [
        "# Software intake model trace",
        "",
        "Generated from the SysML model and checked repository source links. Runtime acceptance is pending.",
        "",
        "## Selected realization",
        "",
        "| Member | Network key | Cache disk | Cache mount |",
        "| --- | --- | --- | --- |",
    ]
    for name, vm in sorted(inputs["members"].items()):
        rows.append(
            f'| {name} | {vm["network_zone_key"]} | {vm["_cache_disk"]["interface"]} | {inputs["config"]["cache_squid_cache_dir"]} |'
        )
    rows += [
        "",
        "## Obligations and implementation",
        "",
        "| Model identity | Evidence class | Owning sources and checks |",
        "| --- | --- | --- |",
    ]
    for key, record in records.items():
        from intake_case_reports import link

        links = "<br/>".join(link(p) for p in record["sources"] + record.get("checks", []))
        rows.append(f'| {key} | {record["state"]} | {links} |')
    rows += [
        "",
        "Paths are relative to the upstream kit. They are checked for existence; named contract checks",
        "also inspect selected module and role wiring. This does not evaluate every Terraform expression",
        "or establish live firewall, failover, TLS, signature or recovery behavior.",
        "",
        "## Potential impact: proxy contract",
        "",
        "Changing `DEF-proxy` identifies these consumers and owners for review:",
        "",
        ", ".join("`" + k + "`" for k in impact(model, "DEF-proxy")),
        "",
        "The report is conservative and limited to declared relationships; it does not automatically edit IaC.",
        "",
    ]
    return "\n".join(rows)
