"""Review and apply bounded SysON requirement/use-case changes without committing Git."""

import difflib
import json
from pathlib import Path
import uuid
from syson_api import SysON, checked_url
from syson_change_model import Graph, archive_model, changed_roots, compare_roots, digest
from syson_change_source import (MANIFEST, sha, save, index_source, source_map,
                                 propose, edited_sources)
from syson_change_workspace import inputs, runtime_inputs, checked_path, prepare_workspace, replace_sources


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_for(receipt_path):
    receipt = load(receipt_path)
    checked_url(receipt["server"])
    if receipt.get("url"):
        checked_url(receipt["url"])
    folder = receipt_path.parent
    if receipt.get("status") not in ("verified", "published_with_gaps"):
        raise ValueError("Use a verified publication receipt")
    path = folder / "return-baseline.json"
    if not path.exists() or sha(path) != receipt.get("return_baseline_sha256"):
        raise ValueError("Missing or modified return baseline; publish an unchanged baseline first")
    baseline = load(path)
    if sha(folder / "return-baseline.zip") != baseline["archive_sha256"]:
        raise ValueError("Immutable baseline archive changed")
    if baseline["project_id"] != receipt["project_id"] or baseline["server"] != receipt["server"]:
        raise ValueError("Receipt and return baseline disagree")
    return receipt, baseline, archive_model(folder / "return-baseline.zip")


def probe_round_trip(client, bundle, expected, keys, output):
    name = "Homelab change-check - " + str(uuid.uuid4())
    project = client.create_project(name)
    save(output / "probe.json", {"project_id": project, "name": name, "status": "created"})
    try:
        client.upload(client.context(project), bundle)
        _, actual, _ = client.archive(project, output / "round-trip.zip")
        save(output / "round-trip-expected.json", {k: Graph(expected).canonical(k) for k in keys})
        save(output / "round-trip-actual.json", {k: Graph(actual).canonical(k) for k in keys if k in Graph(actual).keys})
        compare_roots(expected, actual, keys)
    finally:
        # This routine owns only its freshly created, exactly named probe.
        projects = {p["@id"]: p["name"] for p in client.projects()}
        if projects.get(project) != name:
            raise ValueError("Probe ownership changed; retained for inspection: " + project)
        client.archive(project, output / "round-trip.zip")
        result = client.mutate("deleteProject", "DeleteProjectInput", {"projectId": project})
        if result["__typename"] not in ("DeleteProjectSuccessPayload", "SuccessPayload"):
            raise ValueError("Could not retire archived change-check project: " + project)
        if project in {p["@id"] for p in client.projects()}:
            raise ValueError("Change-check project still exists: " + project)
        save(output / "probe.json", {"project_id": project, "name": name, "status": "archived_and_removed"})


def review(args):
    if not args.receipt:
        raise ValueError("review-changes needs --receipt <publication/receipt.json>")
    root, receipt_path = args.root.resolve(), args.receipt.resolve()
    receipt, baseline, before = baseline_for(receipt_path)
    output = root / ".tmp/syson-changes" / uuid.uuid4().hex[:16]
    output.mkdir(parents=True)
    plan = {"schema": 1, "status": "reviewing", "root": str(root), "receipt": str(receipt_path),
            "server": receipt["server"], "project_id": receipt["project_id"],
            "assessment": "Model integration only; requirement fulfillment requires separate implementation/test evidence"}
    save(output / "plan.json", plan)
    try:
        client = SysON(receipt["server"])
        manifest, current_tool, _ = client.archive(receipt["project_id"], output / "edited-project.zip")
        keys, added = changed_roots(before, current_tool)
        plan.update(elements=keys, additions=added, tool_model_sha256=digest(current_tool))
        if not keys:
            plan["status"] = "no_changes"
            save(output / "plan.json", plan)
            print("No supported semantic changes. Evidence: " + str(output))
            return plan
        documents = list(manifest["documentIdsToName"])
        if len(documents) != 1:
            raise ValueError("Return import currently requires one published model document")
        raw_text = client.export_text(receipt["editing_context_id"], documents[0])
        tool_text = raw_text.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        (output / "edited-export.sysml").write_text(tool_text, encoding="utf-8")
        _, check_tool, _ = client.archive(receipt["project_id"], output / "edited-project-check.zip")
        if digest(check_tool) != plan["tool_model_sha256"]:
            raise ValueError("SysON changed during capture; review again")
        plan["inputs"] = inputs(root)
        plan["runtime"] = runtime_inputs(args)
        tool_index = index_source(root, tool_text, output / "tool-index.json", args)
        current_manifest = load(root / MANIFEST)
        if current_manifest != baseline["manifest"]:
            raise ValueError("Compilation manifest changed since publication; reconcile it first")
        sources = {name: checked_path(root, name).read_text(encoding="utf-8") for name in baseline["sources"]}
        package = baseline["manifest"]["package"]
        original = source_map(root, baseline["sources"], package, output / "baseline-index.json", args)
        current = source_map(root, sources, package, output / "current-index.json", args)
        edits = propose(original, current, tool_text, tool_index, Graph(current_tool), keys, added)
        proposed = edited_sources(sources, edits)
        workspace = output / "workspace"
        prepare_workspace(root, workspace, plan["inputs"])
        for name, content in proposed.items():
            (workspace / name).write_text(content, encoding="utf-8", newline="\n")
        patch = []
        for name, content in proposed.items():
            patch.extend(difflib.unified_diff(sources[name].splitlines(True), content.splitlines(True),
                                           fromfile="a/" + name, tofile="b/" + name))
        (output / "changes.diff").write_text("".join(patch), encoding="utf-8")
        print("Validating proposed requirement/use-case changes in an isolated full model...", flush=True)
        from software_intake import run
        from intake_model import impact
        model = run(workspace, "build", args)
        plan["impact"] = {key: impact(model, key) for key in keys if key in model["elements"]}
        plan["verification_gaps"] = [key for key in model["requirements"] if key in keys
            and not any(key in case["requirements"] for case in model["verification"].values())]
        probe_round_trip(client, workspace / ".tmp/software-intake-model/combined.sysml", current_tool, keys, output)
        plan["files"] = {name: {"before": sha(root / name), "after": sha(workspace / name)} for name in proposed}
        if inputs(root) != plan["inputs"] or runtime_inputs(args) != plan["runtime"]:
            raise ValueError("Git inputs or tooling changed during review; review again")
        plan["status"] = "ready" if proposed else "already_integrated"
        save(output / "plan.json", plan)
        print("Validated " + str(len(keys)) + " edited elements; source files: " + str(len(proposed)))
        print("Review diff: " + str(output / "changes.diff"))
        print("Plan: " + str(output / "plan.json"))
        return plan
    except Exception as error:
        plan.update(status="blocked", error=str(error))
        save(output / "plan.json", plan)
        raise ValueError(str(error) + "\nReview evidence: " + str(output)) from error


def apply(args):
    if not args.plan:
        raise ValueError("apply-changes needs --plan <review/plan.json>")
    path, root = args.plan.resolve(), args.root.resolve()
    plan = load(path)
    checked_url(plan["server"])
    if plan.get("schema") != 1 or Path(plan["root"]).resolve() != root:
        raise ValueError("Plan belongs to a different checkout")
    if plan["status"] in ("already_integrated", "no_changes"):
        print("No source changes to apply")
        return plan
    if plan["status"] not in ("ready", "sources_applied", "applied"):
        raise ValueError("Plan is not validated and ready: " + plan["status"])
    if runtime_inputs(args) != plan.get("runtime"):
        raise ValueError("Tooling changed after review; review again")
    client = SysON(plan["server"])
    _, tool, _ = client.archive(plan["project_id"], path.parent / "apply-project.zip")
    if digest(tool) != plan["tool_model_sha256"]:
        raise ValueError("SysON changed after review; review again")
    allowed = set(load(root / MANIFEST)["sources"])
    if not set(plan["files"]) <= allowed:
        raise ValueError("Plan contains files outside the authored model manifest")
    for name, versions in plan["files"].items():
        checked_path(root, name)
        if sha(path.parent / "workspace" / name) != versions["after"]:
            raise ValueError("Reviewed candidate changed: " + name)
    if plan["status"] in ("sources_applied", "applied"):
        if any(sha(root / n) != v["after"] for n, v in plan["files"].items()):
            raise ValueError("Previously integrated sources changed; review their current state")
        if plan["status"] == "applied":
            print("Already applied; no duplicate changes")
            return plan
        expected = dict(plan["inputs"])
        for name, versions in plan["files"].items():
            if expected.get(name) != versions["before"]:
                raise ValueError("Plan source baseline disagrees with reviewed inputs; review again")
            expected[name] = versions["after"]
        if inputs(root) != expected:
            raise ValueError("Git inputs changed since source application; review again")
    else:
        if inputs(root) != plan["inputs"]:
            raise ValueError("Git inputs changed after review; review again")
        proposed = {name: (path.parent / "workspace" / name).read_text(encoding="utf-8") for name in plan["files"]}
        replace_sources(root, proposed, {n: v["before"] for n, v in plan["files"].items()})
        plan["status"] = "sources_applied"
        save(path, plan)
    from software_intake import run
    run(root, "build", args)
    run(root, "check", args)
    plan["status"] = "applied"
    save(path, plan)
    print("Integrated model sources and rebuilt views. Git changes remain uncommitted.")
    print("Review requirement/test obligations, then publish the reconciled model.")
    return plan
