"""Bounded native-model compatibility checks."""

from syson_trace import stored_trace


def named_elements(elements):
    result = {}
    for element in elements:
        key = element.get("declaredShortName")
        if key:
            if key in result:
                raise ValueError("Duplicate stable model identity: " + key)
            result[key] = element
    return result


def structural_projection(elements, keys):
    """Compare named structure, typing, documentation and relation endpoints, not execution."""
    objects = {e["@id"]: e for e in elements}
    named = named_elements(elements)
    missing = set(keys) - set(named)
    if missing:
        raise ValueError("Missing model identities: " + ", ".join(sorted(missing)))
    names = {named[k]["@id"]: k for k in keys}

    def references(element, field):
        values = element.get(field) or []
        if isinstance(values, dict):
            values = [values]
        return sorted(names[v["@id"]] for v in values if v["@id"] in names)

    def chain(identity, visited=frozenset()):
        if identity in visited:
            raise ValueError("Cyclic feature chain: " + identity)
        element = objects.get(identity)
        if element is None:
            raise ValueError("Unresolved relationship endpoint: " + identity)
        parts = element.get("chainingFeature", [])
        return [r for p in parts for r in chain(p["@id"], visited | {identity})] if parts else [identity]

    result = {}
    for key in sorted(keys):
        element = named[key]
        row = {"kind": element["@type"], "name": element.get("declaredName"),
               "owner": references(element, "owner"), "type": references(element, "type"),
               "docs": [" ".join(objects[r["@id"]]["body"].split())
                        for r in element.get("documentation", [])]}
        if element["@type"] == "Documentation":
            row["body"] = " ".join(element["body"].split())
        if element["@type"] == "PartDefinition":
            row["ports"] = sorted((e.get("declaredName"), references(e, "type"))
                                  for e in elements if e["@type"] == "PortUsage"
                                  and (e.get("owner") or {}).get("@id") == element["@id"])
        if element["@type"] == "PartUsage":
            owner = objects.get((element.get("owner") or {}).get("@id"), {})
            # The engines differ on this derived default for package-level parts and actors.
            # Compare it where it expresses actual composition inside another part.
            if owner.get("@type") in ("PartUsage", "PartDefinition"):
                row["composite"] = element.get("isComposite")
            values = [objects[r["@id"]] for r in element.get("ownedMembership", [])
                      if objects[r["@id"]]["@type"] == "FeatureValue"]
            row["bound_to"] = []
            for value in values:
                expression = objects[value["value"]["@id"]]
                target = expression.get("targetFeature") or expression.get("referent")
                if target:
                    row["bound_to"].extend(names[t] for t in chain(target["@id"]) if t in names)
        if element["@type"] in ("Dependency", "AllocationUsage", "FlowUsage", "ConnectionUsage"):
            for field in ("source", "target"):
                row[field] = sorted(names[t] for r in element.get(field, [])
                                    for t in chain(r["@id"]) if t in names)
        if element["@type"] in ("RequirementUsage", "VerificationCaseDefinition", "SatisfyRequirementUsage"):
            for field in ("verifiedRequirement", "satisfiedRequirement", "satisfyingFeature"):
                trace = stored_trace(element, objects, field)
                row[field] = references(element if trace is None else {field: trace}, field)
            row["required_text"] = [" ".join(objects[d["@id"]]["body"].split())
                for c in element.get("requiredConstraint", [])
                for d in objects[c["@id"]].get("documentation", [])]
        result[key] = row
    return result


def compare(expected, actual):
    changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
    if changed:
        raise ValueError("SysON structural compatibility mismatch: " + ", ".join(changed))
