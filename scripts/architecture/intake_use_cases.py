"""Native use-case membership, scenario selections and functional allocation projection."""

from intake_sources import require

# Navigation owns presentation destinations; native memberships own case meaning.
CASE_VIEWS = {
    "UC-update": "architecture/generated/software-intake/SoftwareIntakeUseCases.svg",
    "UC-clone": "architecture/generated/platform/hosting/Boot1CloneRepository.svg",
}
CASE_GUIDES = {
    "UC-update": "architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml",
    "UC-clone": "architecture/models/platform/hosting/Hosting.sysml",
}


def project_use_cases(objects, names, model):
    cases, scenarios, functions, edges = {}, {}, {}, []

    def identified(ref):
        return names.get(ref.get("@id"))

    def members(element, kind):
        return [
            objects[r["@id"]]
            for r in element.get("ownedMembership", [])
            if objects[r["@id"]]["@type"] == kind
        ]

    def value(element):
        values = members(element, "FeatureValue")
        require(len(values) == 1 and not values[0]["isDefault"], "Scenario/binding needs one fixed value")
        return objects[values[0]["value"]["@id"]]

    def binding(element):
        expression = value(element)
        require(
            expression["@type"] in ("FeatureChainExpression", "FeatureReferenceExpression"),
            "Use-case role must bind directly to a logical part",
        )
        feature = expression.get("targetFeature", expression.get("referent"))
        target = objects[feature["@id"]]
        chain = target.get("chainingFeature", [])
        key = identified(chain[-1] if chain else feature)
        require(key and model["elements"][key]["kind"] == "PartUsage", "Unknown use-case logical binding")
        return key

    for uid, key in names.items():
        element = objects[uid]
        if element["@type"] == "UseCaseDefinition":
            subject = identified(element["subjectParameter"])
            actors = [identified(m["memberElement"]) for m in members(element, "ActorMembership")]
            require(subject and actors and all(actors), "Identify the use-case subject and actors")
            bindings = {
                role: binding(objects[next(u for u, k in names.items() if k == role)])
                for role in [subject, *actors]
            }
            require(bindings[subject] not in {bindings[a] for a in actors}, "Subject cannot be its own actor")
            cases[key] = {"subject": subject, "actors": actors, "bindings": bindings}
            # Preserve native subject/actor memberships as such, not structural composition.
            edges.append({"from": key, "to": subject, "kind": "has-subject"})
            edges.extend({"from": key, "to": actor, "kind": "has-actor"} for actor in actors)
            for role, target in bindings.items():
                edges.append({"from": role, "to": target, "kind": "bound-to"})
        elif element["@type"] == "ActionUsage" and key.startswith("SC-"):
            owner = identified(element["owner"])
            require(
                owner and model["elements"][owner]["kind"] == "UseCaseDefinition",
                "A scenario must belong to its use case",
            )
            types = [identified(t) for t in element["type"] if identified(t) in model["behaviors"]]
            require(len(types) == 1 and not element["isComposite"], "Scenario must reference one behavior")
            docs = {
                objects[d["@id"]].get("declaredName"): objects[d["@id"]]["body"].strip()
                for d in element["documentation"]
            }
            require(
                set(docs) == {"Trigger", "Preconditions", "Outcome"} and all(docs.values()),
                "Scenario needs Trigger, Preconditions and Outcome documentation",
            )
            guards = {}
            for ref in element.get("ownedFeature", []):
                attribute = objects[ref["@id"]]
                redefinitions = [objects[r["@id"]] for r in attribute.get("ownedRedefinition", [])]
                require(len(redefinitions) == 1, "Scenario guard must redefine a native behavior condition")
                guard = identified(redefinitions[0]["redefinedFeature"])
                expression = value(attribute)
                require(
                    guard and expression["@type"] == "LiteralBoolean", "Scenario needs Boolean guard values"
                )
                require(guard not in guards, "Duplicate scenario guard")
                guards[guard] = expression["value"]
            selected, used = [], set()

            def select(steps):
                for step in steps:
                    if step["kind"] == "choice":
                        guard = step["guard"]
                        require(guard in guards, f"{key}: missing scenario condition {guard}")
                        used.add(guard)
                        matches = [b for b in step["branches"] if b["when"] == guards[guard]]
                        require(len(matches) == 1, "Scenario must select one native branch")
                        select(matches[0]["steps"])
                    else:
                        selected.append(step["id"])

            select(model["behaviors"][types[0]]["steps"])
            require(used == set(guards), "Scenario supplies unused or foreign conditions")
            scenarios[key] = {
                "use_case": owner,
                "behavior": types[0],
                "guards": guards,
                "messages": selected,
                "docs": docs,
            }
            edges.append({"from": key, "to": types[0], "kind": "typed-by"})
            edges.extend({"from": key, "to": message, "kind": "uses-message"} for message in selected)
        elif element["@type"] == "ActionUsage" and key.startswith("F-"):
            ports = {direction: [] for direction in ("in", "out")}
            for ref in element.get("ownedFeature", []):
                feature = objects[ref["@id"]]
                if feature.get("direction") in ports:
                    types = [objects[t["@id"]].get("name") for t in feature.get("type", [])]
                    ports[feature["direction"]].append(feature["name"] + " : " + ", ".join(types))
            require(all(ports.values()), "Function needs inputs and outputs: " + key)
            functions[key] = ports
    model.update(
        use_cases=dict(sorted(cases.items())),
        scenarios=dict(sorted(scenarios.items())),
        functions=dict(sorted(functions.items())),
    )
    model["edges"].extend(edges)


def connections(model, source, kind):
    return sorted({e["to"] for e in model["edges"] if e["from"] == source and e["kind"] == kind})


def scenario_functions(model, scenario):
    return sorted(
        {
            target
            for message in model["scenarios"][scenario]["messages"]
            for target in connections(model, message, "depends-on")
            if target in model["functions"]
        }
    )


def validate_use_cases(model, records, plan):
    require(
        model["use_cases"] and model["scenarios"] and model["functions"], "Missing use-case engineering scope"
    )
    require(set(plan) == set(model["scenarios"]), "Test plan must cover exactly the modeled scenarios")
    for function in model["functions"]:
        owners = connections(model, function, "allocated-to")
        require(
            owners and all(model["elements"][o]["kind"] == "PartUsage" for o in owners),
            "Function needs logical part allocation: " + function,
        )
        require(
            any(t.startswith("REQ-") for t in connections(model, function, "depends-on")),
            "Function needs an owning guardrail: " + function,
        )
        for owner in owners:
            types = connections(model, owner, "typed-by")
            require(any(t in records for t in types), "Allocated part has no implementation trace: " + owner)
    covered = set()
    for key, scenario in model["scenarios"].items():
        require(plan[key].get("acceptance"), "Scenario needs an acceptance criterion: " + key)
        for message in scenario["messages"]:
            covered.add(message)
            require(
                any(t in model["functions"] for t in connections(model, message, "depends-on")),
                "Message needs functional ownership: " + message,
            )
            require(
                message in records
                and (
                    records[message].get("test_symbols")
                    or (records[message]["state"] == "manual-acceptance" and plan[key].get("manual"))
                ),
                "Scenario needs executable checks or explicit manual acceptance: " + message,
            )
    from intake_behavior import messages

    expected = {m["id"] for b in model["behaviors"].values() for m in messages(b["steps"])}
    require(covered == expected, "Scenarios must cover all modeled behavior messages")
