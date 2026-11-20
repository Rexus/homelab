"""Conservative semantic change boundary and same-engine round-trip comparison."""

import hashlib
import json
import zipfile
from syson_api import objects

ROOT_KINDS = {"RequirementUsage": "REQ-", "UseCaseDefinition": "UC-"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def archive_model(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise ValueError("Damaged SysON archive: " + str(path))
        return [o for name in archive.namelist() if "/documents/" in name
                for o in objects(json.loads(archive.read(name)))]


def stable(obj):
    data = obj.get("data", {})
    return data.get("reqId") or data.get("declaredShortName")


def kind(obj):
    return obj["eClass"].split(":")[-1]


class Graph:
    def __init__(self, model):
        self.objects = {o["id"]: o for o in model}
        self.parents, self.rows, self.keys = {}, {}, {}
        for identity, obj in self.objects.items():
            key = stable(obj)
            if key:
                if key in self.keys:
                    raise ValueError("Duplicate stable identity: " + key)
                self.keys[key] = identity
            def flatten(value):
                if isinstance(value, dict) and "eClass" in value and "id" in value:
                    previous = self.parents.setdefault(value["id"], identity)
                    if previous != identity:
                        raise ValueError("Multiple model owners: " + value["id"])
                    return {"object": value["id"]}
                if isinstance(value, list):
                    return [flatten(v) for v in value]
                if isinstance(value, dict):
                    return {k: flatten(v) for k, v in value.items()}
                return value
            self.rows[identity] = {"kind": kind(obj), "data": flatten(obj.get("data", {}))}

    def ancestors(self, identity):
        seen = set()
        while identity:
            if identity in seen:
                raise ValueError("Cyclic model ownership")
            seen.add(identity)
            yield identity
            identity = self.parents.get(identity)

    def roots(self):
        result = {}
        for key, identity in self.keys.items():
            obj = self.objects[identity]
            if kind(obj) not in ROOT_KINDS:
                continue
            parent = self.parents.get(identity)
            owner = self.parents.get(parent)
            if owner and kind(self.objects[owner]) == "Package":
                result[key] = identity
        return result

    def package(self, identity):
        parts = [self.objects[i]["data"]["declaredName"] for i in self.ancestors(identity)
                 if kind(self.objects[i]) == "Package"]
        return "::".join(reversed(parts))

    def label(self, identity):
        obj = self.objects[identity]
        if stable(obj):
            return "id:" + stable(obj)
        parent = self.parents.get(identity)
        if kind(obj) == "Package":
            return "package:" + self.package(identity)
        if not parent:
            return kind(obj) + ":" + obj.get("data", {}).get("declaredName", "")
        siblings = [i for i, p in self.parents.items() if p == parent and kind(self.objects[i]) == kind(obj)]
        return self.label(parent) + "/" + kind(obj) + ":" + str(siblings.index(identity))

    def canonical(self, key):
        """Compare stored semantics, including anonymous memberships, bindings and literals."""
        def visit(value):
            if isinstance(value, dict):
                if "eClass" in value and "id" in value:
                    return {"kind": kind(value), "data": visit(value.get("data", {}))}
                return {k: (" ".join(v.split()) if k == "body" and isinstance(v, str) else visit(v))
                        for k, v in value.items() if k != "elementId"}
            if isinstance(value, list):
                return [visit(v) for v in value]
            if isinstance(value, str) and value in self.objects:
                return {"reference": self.label(value)}
            # Formatting inside documentation is not model identity or an execution expression.
            return value
        identity = self.keys[key]
        membership = self.parents.get(identity)
        owner = self.parents.get(membership)
        result = visit(self.objects[identity])
        # Package paths and stable identities survive reimport; persistence UUIDs do not.
        result["owner"] = ({"kind": kind(self.objects[owner]), "identity": self.label(owner),
                            "package": self.package(identity)} if owner else None)
        return result


def changed_roots(before, after):
    """Reject every semantic delta outside package-owned requirements/use-case definitions."""
    old, new = Graph(before), Graph(after)
    old_roots, new_roots = old.roots(), new.roots()
    selected, added, conflicts = [], [], []
    for key, identity in old_roots.items():
        if key not in new_roots or new_roots[key] != identity:
            conflicts.append(key + ": deleted or stable identity changed")
            continue
        if kind(old.objects[identity]) != kind(new.objects[identity]):
            conflicts.append(key + ": element kind changed")
        if old.parents[identity] != new.parents[identity] or old.package(identity) != new.package(identity):
            conflicts.append(key + ": ownership changed")
        if old.objects[identity] != new.objects[identity]:
            selected.append(key)
    for key, identity in new_roots.items():
        if key in old_roots:
            continue
        if key in old.keys:
            conflicts.append(key + ": existing identity changed kind or owner")
        elif not key.startswith(ROOT_KINDS[kind(new.objects[identity])]):
            conflicts.append(key + ": use a REQ- or UC- stable identifier")
        else:
            selected.append(key)
            added.append(key)
    allowed_old = {i for i in old.objects if any(a in {old_roots[k] for k in selected if k in old_roots}
                                               for a in old.ancestors(i))}
    allowed_new = {i for i in new.objects if any(a in {new_roots[k] for k in selected}
                                               for a in new.ancestors(i))}
    wrappers = {new.parents[new_roots[k]] for k in added}
    for wrapper in wrappers:
        row = new.rows[wrapper]
        if row["kind"] != "OwningMembership" or set(row["data"]) - {"elementId", "ownedRelatedElement"}:
            conflicts.append("New root has unsupported membership properties")
    for identity in old.rows.keys() | new.rows.keys():
        if identity in allowed_old | allowed_new | wrappers:
            continue
        left, right = old.rows.get(identity), new.rows.get(identity)
        if right and wrappers:
            right = json.loads(json.dumps(right))
            relationships = right["data"].get("ownedRelationship", [])
            right["data"]["ownedRelationship"] = [r for r in relationships
                                                     if r.get("object") not in wrappers]
            if not relationships:
                right["data"].pop("ownedRelationship", None)
        if left != right:
            obj = new.objects.get(identity, old.objects.get(identity))
            conflicts.append((stable(obj) or kind(obj)) + ": unsupported semantic change")
    if conflicts:
        raise ValueError("Change import blocked: " + "; ".join(sorted(set(conflicts))))
    return sorted(selected), sorted(added)


def compare_roots(expected, actual, keys):
    left, right = Graph(expected), Graph(actual)
    for key in keys:
        if key not in right.keys or left.canonical(key) != right.canonical(key):
            raise ValueError("Return-path semantic round trip differs: " + key)
