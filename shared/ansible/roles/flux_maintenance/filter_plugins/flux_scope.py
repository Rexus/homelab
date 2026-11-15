"""Resolve live Flux ownership and dependency graphs for the maintenance role.

Kubernetes operations stay in native Ansible modules. This filter only transforms
the controller inventory, which cannot be traversed recursively with native filters.
"""

from copy import deepcopy

from ansible.errors import AnsibleFilterError


RECONCILE = "kustomize.toolkit.fluxcd.io/reconcile"
KINDS = {"Kustomization", "HelmRelease"}


def identity(resource):
    metadata = resource["metadata"]
    return "/".join((resource["kind"], metadata.get("namespace", ""), metadata["name"]))


def topological(nodes, edges):
    pending = set(nodes)
    result = []
    while pending:
        ready = sorted(node for node in pending if not (set(edges.get(node, [])) & pending))
        if not ready:
            raise AnsibleFilterError("Flux ownership or dependency graph contains a cycle")
        result.extend(ready)
        pending.difference_update(ready)
    return result


def flux_scope(resources, source, namespace="flux-system"):
    objects = {identity(resource): resource for resource in resources}
    root = "Kustomization/" + namespace + "/" + source
    if root not in objects:
        raise AnsibleFilterError("The selected existing root Kustomization is missing")
    owners = {key: set() for key in objects}
    inventory = {}
    for key, resource in objects.items():
        metadata = resource["metadata"]
        if not metadata.get("uid"):
            raise AnsibleFilterError("Every inventoried resource must have a Kubernetes UID")
        labels = metadata.get("labels", {})
        owner_name = labels.get("kustomize.toolkit.fluxcd.io/name")
        if owner_name:
            owner = "Kustomization/" + labels.get(
                "kustomize.toolkit.fluxcd.io/namespace", metadata.get("namespace", "")
            ) + "/" + owner_name
            if owner in objects and owner != key:
                owners[key].add(owner)
        if resource["kind"] != "Kustomization":
            continue
        entries = resource.get("status", {}).get("inventory", {}).get("entries", [])
        inventory[key] = []
        for entry in entries:
            parts = entry["id"].split("_")
            if len(parts) != 4:
                raise AnsibleFilterError("Unexpected Flux status.inventory entry " + entry["id"])
            child_namespace, name, group, kind = parts
            child = kind + "/" + child_namespace + "/" + name
            inventory[key].append(child)
            if child in owners and child != key:
                owners[child].add(key)

    selected = {root}
    for key, resource in objects.items():
        reference = resource.get("spec", {}).get("sourceRef", {})
        if resource["kind"] == "HelmRelease":
            reference = resource.get("spec", {}).get("chart", {}).get("spec", {}).get("sourceRef", {})
        if (reference.get("kind") == "GitRepository"
                and reference.get("name") == source
                and reference.get("namespace", resource["metadata"].get("namespace")) == namespace):
            selected.add(key)
    expanded = True
    while expanded:
        descendants = {key for key in objects if owners[key] & selected}
        expanded = bool(descendants - selected)
        selected.update(descendants)
    controlled = set(selected)
    expanded = True
    while expanded:
        ancestors = {owner for key in controlled for owner in owners[key]}
        expanded = bool(ancestors - controlled)
        controlled.update(ancestors)

    parent_order = topological(controlled, owners)
    dependencies = {}
    records = {}
    for key in parent_order:
        resource = objects[key]
        metadata = resource["metadata"]
        dependencies[key] = []
        for dependency in resource.get("spec", {}).get("dependsOn", []):
            dependency_key = "/".join((resource["kind"], dependency.get(
                "namespace", metadata.get("namespace", "")), dependency["name"]))
            if dependency_key not in objects:
                raise AnsibleFilterError("A reconciliation dependency is missing " + dependency_key)
            dependencies[key].append(dependency_key)
        records[key] = dict(
            api_version=resource["apiVersion"], kind=resource["kind"], name=metadata["name"],
            namespace=metadata.get("namespace", ""), uid=metadata["uid"],
            previous_suspend=resource.get("spec", {}).get("suspend", False),
            previous_reconcile=metadata.get("annotations", {}).get(RECONCILE),
            control_only=key not in selected, owners=sorted(owners[key]),
            dependencies=dependencies[key], inventory=inventory.get(key, []),
        )
        if resource["kind"] == "HelmRelease":
            history = resource.get("status", {}).get("history", [])
            records[key]["release_name"] = history[0].get("name") if history else None
            records[key]["target_namespace"] = resource.get("spec", {}).get(
                "targetNamespace", metadata.get("namespace", ""))
    resume_order = topological(controlled, dependencies)
    return dict(root=root, source=source, namespace=namespace, resources=records,
                suspend_order=parent_order, resume_order=resume_order)


def flux_scope_receipt(scope, previous, operation_id, source_uid):
    if previous and previous.get("phase") != "resumed":
        if (previous.get("source") != scope["source"] or previous.get("source_uid") != source_uid
                or previous.get("root") != scope["root"]):
            raise AnsibleFilterError("The retained scope belongs to another source or cluster")
        for key, record in previous["resources"].items():
            if key not in scope["resources"] or record["uid"] != scope["resources"][key]["uid"]:
                raise AnsibleFilterError("A retained resource disappeared or changed UID " + key)
        # A retry may discover children created by a parent operation that was draining.
        records = deepcopy(scope["resources"])
        for key, record in previous["resources"].items():
            records[key].update(previous_suspend=record["previous_suspend"],
                                previous_reconcile=record["previous_reconcile"])
        return dict(previous, resources=records, suspend_order=scope["suspend_order"],
                    resume_order=scope["resume_order"], phase="preparing")
    return dict(deepcopy(scope), version=2, phase="preparing", operation_id=operation_id, source_uid=source_uid)


def flux_scope_validate(scope, receipt, source_uid, paused=True):
    if (receipt.get("version") != 2 or receipt.get("source_uid") != source_uid
            or receipt.get("source") != scope["source"] or receipt.get("root") != scope["root"]
            or set(receipt.get("resources", {})) != set(scope["resources"])):
        raise AnsibleFilterError("The retained maintenance scope does not match the live inventory")
    for key, record in receipt["resources"].items():
        if record["uid"] != scope["resources"][key]["uid"]:
            raise AnsibleFilterError("A maintenance resource was replaced " + key)
        if (record["owners"] != scope["resources"][key]["owners"] or
                record["dependencies"] != scope["resources"][key]["dependencies"]):
            raise AnsibleFilterError("Maintenance ownership or dependencies changed " + key)
    if paused and receipt.get("phase") not in ("paused", "staged", "resuming"):
        raise AnsibleFilterError("Complete and verify scoped suspension before staging or resuming")
    return True


def flux_drained(resource):
    if resource.get("metadata", {}).get("deletionTimestamp"):
        return False
    conditions = resource.get("status", {}).get("conditions", [])
    if any(item.get("type") == "Reconciling" and item.get("status") == "True" for item in conditions):
        return False
    history = resource.get("status", {}).get("history", [])
    return not history or not history[0].get("status", "").startswith("pending-")


def flux_suspend_patch(resource, suspend, reconcile="disabled"):
    metadata = resource["metadata"]
    patch = [dict(op="test", path="/metadata/uid", value=metadata["uid"]),
             dict(op="test", path="/metadata/resourceVersion", value=metadata["resourceVersion"]),
             dict(op="add", path="/spec/suspend", value=suspend)]
    if "annotations" not in metadata:
        patch.append(dict(op="add", path="/metadata/annotations", value={}))
    annotation_path = "/metadata/annotations/kustomize.toolkit.fluxcd.io~1reconcile"
    if reconcile is not None:
        patch.append(dict(op="add", path=annotation_path, value=reconcile))
    elif RECONCILE in metadata.get("annotations", {}):
        patch.append(dict(op="remove", path=annotation_path))
    return patch


def flux_writer(resource, scope):
    key = identity(resource)
    metadata = resource["metadata"]
    inventory = {item for record in scope["resources"].values()
                 if not record["control_only"] for item in record["inventory"]}
    annotations = metadata.get("annotations", {})
    helm_owned = any(record.get("release_name") and
                     record["release_name"] == annotations.get("meta.helm.sh/release-name") and
                     record.get("target_namespace") == metadata.get("namespace")
                     for record in scope["resources"].values() if not record["control_only"])
    if key not in inventory and not helm_owned:
        raise AnsibleFilterError("Writer is not owned by the selected live Flux inventory " + key)
    if resource["kind"] not in ("Deployment", "StatefulSet", "CronJob", "Job"):
        raise AnsibleFilterError("Unsupported writer control " + key)
    field = "replicas" if resource["kind"] in ("Deployment", "StatefulSet") else "suspend"
    selector = resource.get("spec", {}).get("selector", {})
    selectors = [key + "=" + value for key, value in selector.get("matchLabels", {}).items()]
    for expression in selector.get("matchExpressions", []):
        operator = expression["operator"]
        key = expression["key"]
        if operator in ("In", "NotIn"):
            selectors.append(key + (" in (" if operator == "In" else " notin (")
                             + ",".join(expression["values"]) + ")")
        else:
            selectors.append(("!" if operator == "DoesNotExist" else "") + key)
    if field == "replicas" and not selectors:
        raise AnsibleFilterError("Writer has no usable native pod selector " + key)
    if resource["kind"] == "Job":
        selectors = ["batch.kubernetes.io/controller-uid=" + metadata["uid"]]
    return dict(api_version=resource["apiVersion"], kind=resource["kind"], name=metadata["name"],
                namespace=metadata["namespace"], uid=metadata["uid"], field=field,
                pod_selectors=selectors,
                previous_value=resource.get("spec", {}).get(field, 1 if field == "replicas" else False),
                previous_reconcile=annotations.get(RECONCILE))


def flux_writer_patch(resource, record, resume=False):
    metadata = resource["metadata"]
    value = record["previous_value"] if resume else (0 if record["field"] == "replicas" else True)
    return [dict(op="test", path="/metadata/uid", value=record["uid"]),
            dict(op="test", path="/metadata/resourceVersion", value=metadata["resourceVersion"]),
            dict(op="add", path="/spec/" + record["field"], value=value)]


def flux_cronjob_children(jobs, owner_uid):
    owned = [job for job in jobs if any(reference.get("uid") == owner_uid
             for reference in job["metadata"].get("ownerReferences", []))]
    drained = all(not job.get("status", {}).get("active", 0) and any(
        condition.get("type") in ("Complete", "Failed") and condition.get("status") == "True"
        for condition in job.get("status", {}).get("conditions", [])) for job in owned)
    return dict(uids=[job["metadata"]["uid"] for job in owned], drained=drained)


def flux_cronjob_pods_drained(pods, job_uids):
    for pod in pods:
        if any(reference.get("uid") in job_uids for reference in pod["metadata"].get("ownerReferences", [])):
            if (pod["metadata"].get("deletionTimestamp") or
                    pod.get("status", {}).get("phase") not in ("Succeeded", "Failed")):
                return False
    return True


def flux_ref_patch(resource, reference):
    metadata = resource["metadata"]
    patch = [dict(op="test", path="/metadata/resourceVersion", value=metadata["resourceVersion"]),
             dict(op="test", path="/metadata/uid", value=metadata["uid"]),
             dict(op="add", path="/spec/ref", value=reference)]
    if "annotations" not in metadata:
        patch.append(dict(op="add", path="/metadata/annotations", value={}))
    patch.append(dict(op="add", path="/metadata/annotations/kustomize.toolkit.fluxcd.io~1reconcile",
                      value="disabled"))
    return patch


class FilterModule:
    def filters(self):
        return dict(flux_scope=flux_scope, flux_scope_receipt=flux_scope_receipt,
                    flux_scope_validate=flux_scope_validate, flux_drained=flux_drained,
                    flux_suspend_patch=flux_suspend_patch, flux_writer=flux_writer,
                    flux_writer_patch=flux_writer_patch, flux_ref_patch=flux_ref_patch,
                    flux_cronjob_children=flux_cronjob_children,
                    flux_cronjob_pods_drained=flux_cronjob_pods_drained)
