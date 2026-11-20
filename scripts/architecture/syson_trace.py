"""Check stored verification references; SysON 2026.11 derived getters are incomplete."""


def stored_trace(element, objects, field):
    """Return explicit trace endpoints, or None when no explicit structure is present.

    This checks preservation of membership, reference subsetting and value bindings.
    It does not establish SysON's derived verification/satisfaction semantics or execution.
    """
    def owned(parent, kind):
        return [objects[r["@id"]] for r in parent.get("ownedRelationship", [])
                if objects[r["@id"]]["@type"] == kind]

    def members(membership):
        return [objects[r["@id"]] for r in membership.get("ownedRelatedElement", [])]

    if field == "verifiedRequirement":
        objectives = owned(element, "ObjectiveMembership")
        if not objectives:
            return None
        return [relation["referencedFeature"]
                for objective in objectives for requirement in members(objective)
                for verification in owned(requirement, "RequirementVerificationMembership")
                for reference in members(verification)
                for relation in owned(reference, "ReferenceSubsetting")
                if relation.get("referencedFeature")]
    if field == "satisfyingFeature":
        subjects = owned(element, "SubjectMembership")
        if not subjects:
            return None
        targets = []
        for subject in subjects:
            for feature in members(subject):
                for binding in owned(feature, "FeatureValue"):
                    expression = objects[binding["value"]["@id"]]
                    target = expression.get("targetFeature") or expression.get("referent")
                    if target:
                        # A qualified feature expression identifies its final feature.
                        seen = set()
                        while objects[target["@id"]].get("chainingFeature"):
                            if target["@id"] in seen:
                                raise ValueError("Cyclic satisfaction binding")
                            seen.add(target["@id"])
                            target = objects[target["@id"]]["chainingFeature"][-1]
                        targets.append(target)
        return targets
    return None
