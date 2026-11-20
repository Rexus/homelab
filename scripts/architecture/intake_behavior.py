"""Project native messages, guarded actions and succession into readable sequence views."""

import json
from intake_sources import require

MESSAGE_KINDS = {"MSG-request": "request", "MSG-response": "response", "MSG-process": "process"}


def project_behavior(objects, names):
    behaviors, edges = {}, []

    def named(ref):
        return names.get(ref.get("@id"))

    def endpoint(message, direction):
        ends = [objects[r["@id"]] for r in message["ownedFeature"]]
        matches = [e for e in ends if e.get("name") == direction + "Event"]
        require(len(matches) == 1, "Message needs a unique " + direction + " event")
        event = objects[matches[0]["eventOccurrence"]["@id"]]
        participant = named(event.get("owner", {}))
        require(participant, "Message event must belong to an identified participant")
        return participant

    def steps(container):
        children = [objects[r["@id"]] for r in container.get("ownedFeature", [])]
        actions = {
            e["@id"]: e for e in children if e["@type"] in ("FlowUsage", "IfActionUsage", "ActionUsage")
        }
        require(all(uid in names for uid in actions), "Every behavior step needs a stable identity")
        if not actions:
            raise ValueError("Empty or unsupported behavior: " + str(container.get("declaredName")))
        links = []
        for e in children:
            if e["@type"] == "SuccessionAsUsage":
                left, right = e["source"], e["target"]
                require(len(left) == len(right) == 1, "Only linear succession is supported within a branch")
                a, b = left[0]["@id"], right[0]["@id"]
                require(a in actions and b in actions, "Unsupported succession endpoint")
                links.append((a, b))
                edges.append({"from": names[a], "to": names[b], "kind": "before"})
        # Derive order from native succession, never textual declaration order.
        require(len(links) == len(actions) - 1, "Behavior steps need a complete succession chain")
        heads = set(actions) - {b for _, b in links}
        require(len(heads) == 1, "Behavior has ambiguous start or a cycle")
        ordered, cursor = [], heads.pop()
        while cursor is not None and cursor not in ordered:
            ordered.append(cursor)
            followers = [b for a, b in links if a == cursor]
            require(len(followers) <= 1, "Use a guarded action for alternatives")
            cursor = followers[0] if followers else None
        require(len(ordered) == len(actions) and cursor is None, "Incomplete or cyclic sequence")
        result = []
        for uid in ordered:
            e = actions[uid]
            key = names[uid]
            if e["@type"] == "FlowUsage":
                kinds = [MESSAGE_KINDS[named(t)] for t in e.get("type", []) if named(t) in MESSAGE_KINDS]
                require(len(kinds) == 1, "Message needs one declared request/response/process kind")
                source, target = endpoint(e, "source"), endpoint(e, "target")
                require(
                    kinds[0] != "process" or source == target,
                    "Internal processing must stay on its participant",
                )
                result.append(
                    {
                        "id": key,
                        "kind": kinds[0],
                        "from": source,
                        "to": target,
                        "label": e["declaredName"],
                        "notes": [objects[d["@id"]]["body"].strip() for d in e.get("documentation", [])],
                    }
                )
                for participant in {source, target}:
                    edges.append({"from": key, "to": participant, "kind": "uses-participant"})
            elif e["@type"] == "IfActionUsage":
                condition = objects[e["ifArgument"]["@id"]]
                require(
                    condition["@type"] == "FeatureReferenceExpression",
                    "Use an identified Boolean outcome as the guard",
                )
                guard = named(condition["referent"])
                require(guard, "Behavior guard needs a stable identity")
                branches = []
                for field, value in (("thenAction", True), ("elseAction", False)):
                    require(field in e, "Show both outcomes of the decision")
                    branch = objects[e[field]["@id"]]
                    branches.append(
                        {
                            "id": names[branch["@id"]],
                            "label": branch["declaredName"],
                            "when": value,
                            "steps": steps(branch),
                        }
                    )
                result.append({"id": key, "kind": "choice", "guard": guard, "branches": branches})
                edges.append({"from": key, "to": guard, "kind": "uses-condition"})
            else:
                raise ValueError("Unsupported behavior step: " + key)
        return result

    for uid, key in names.items():
        e = objects[uid]
        if e["@type"] == "ActionDefinition" and key.startswith("B-"):
            participants = [named(r) for r in e["ownedFeature"] if objects[r["@id"]]["@type"] == "PartUsage"]
            require(all(participants), "Every sequence participant needs a stable identity")
            bindings = {}
            for ref in e["ownedFeature"]:
                relation = objects[ref["@id"]]
                if relation["@type"] != "BindingConnectorAsUsage":
                    continue

                def bound(ref):
                    feature = objects[ref["@id"]]
                    chain = feature.get("chainingFeature", [])
                    return named(chain[-1]) if chain else named(ref)

                left = bound(relation["source"][0])
                right = bound(relation["target"][0])
                require(left in participants and right, "Bind each participant to an identified logical part")
                bindings[left] = right
                edges.append({"from": left, "to": right, "kind": "bound-to"})
            require(
                set(bindings) == set(participants), "Sequence participants must bind to the logical structure"
            )
            behaviors[key] = {"participants": participants, "bindings": bindings, "steps": steps(e)}
    return behaviors, edges


def messages(steps):
    for step in steps:
        if step["kind"] == "choice":
            for branch in step["branches"]:
                yield from messages(branch["steps"])
        else:
            yield step


def mermaid(model, key, view):
    behavior = model["behaviors"][key]
    order = view["participants"][key]
    require(
        len(order) == len(set(order)) and set(order) == set(behavior["participants"]),
        "Sequence view must include every model participant exactly once",
    )
    aliases = {participant: "P" + str(i) for i, participant in enumerate(order)}

    def label(value):
        return value.replace("\n", " ").replace(";", "#59;").replace("<", "&lt;").replace(">", "&gt;")

    rows = [
        "%%{init: " + json.dumps(view["mermaid"], separators=(",", ":")) + "}%%",
        "sequenceDiagram",
        "  autonumber",
    ]
    rows += [
        f'  participant {alias} as {label(model["elements"][key]["name"])}' for key, alias in aliases.items()
    ]

    def emit(steps, indent):
        for step in steps:
            rows.append(indent + "%% model: " + step["id"])
            if step["kind"] == "choice":
                for i, branch in enumerate(step["branches"]):
                    rows.append(indent + ("alt " if i == 0 else "else ") + label(branch["label"]))
                    emit(branch["steps"], indent + "  ")
                rows.append(indent + "end")
            else:
                a, b = aliases[step["from"]], aliases[step["to"]]
                for note in step["notes"]:
                    rows.append(f"{indent}Note over {a},{b}: {label(note)}")
                arrow = "-->>" if step["kind"] == "response" else "->>"
                rows.append(f'{indent}{a}{arrow}{b}: {label(step["label"])}')

    emit(behavior["steps"], "  ")
    return "\n".join(rows) + "\n"
