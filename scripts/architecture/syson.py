"""Publish validated homelab review snapshots to SysON; see docs/04-development/syson.md."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from software_intake import run
from syson_api import SysON, checked_url
from syson_session import EditingSession
from syson_change_source import record_baseline
from syson_catalog import select_catalog, coverage, unwanted_details, index_objects, verify_representation_set, diagram_nodes, verify_general
from syson_nested import nested_layout, style_nested, verify_nested
from syson_annotations import show_annotations, annotation_boxes, style_annotations
from syson_style import style_palette
from syson_general import verify_view_owners, actor_labels
from syson_model import named_elements, structural_projection, compare
from syson_views import select_views, verify_diagrams, hidden_details, visible_details, detail_boxes, edge_handles


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def publish(args):
    url = checked_url(args.url)
    root = args.root.resolve()
    # The existing build owns source assembly, IaC realization, native validation and projections.
    model = run(root, "build", args)
    build = root / ".tmp/software-intake-model"
    raw = [e["payload"] for e in json.loads((build / "native.json").read_text(encoding="utf-8"))]
    keys = sorted(model["elements"])
    expected = structural_projection(raw, keys)
    curated, _ = select_views(root, raw, model)
    views, view_text = select_catalog(root, raw, model, curated)
    curated = [v for v in curated if v['key'] in {entry['key'] for entry in views}]
    source = (build / "combined.sysml").read_text(encoding="utf-8")
    if not source.endswith("\n}\n"):
        raise ValueError("Unexpected bundle framing from native build")
    bundle = source[:-3] + "\n" + view_text + "}\n"
    source_digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()
    adapter = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.glob("syson*.py"))}
    digest = hashlib.sha256(json.dumps({"source": source_digest, "views": views,
                                       "adapter": adapter}, sort_keys=True).encode()).hexdigest()
    identity = hashlib.sha256((url + "\n" + args.name + "\n" + digest).encode()).hexdigest()[:20]
    output = root / ".tmp/syson" / identity
    output.mkdir(parents=True, exist_ok=True)
    bundle_path = output / "homelab.sysml"
    bundle_path.write_text(bundle, encoding="utf-8")
    client = SysON(url)
    receipt_path = output / "receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        checked_url(receipt["server"])
        if receipt.get("url"):
            checked_url(receipt["url"])
        if receipt["status"] not in ("verified", "published_with_gaps"):
            raise ValueError("Previous publish incomplete; inspect " + str(receipt_path))
        _, stored, diagrams = client.archive(receipt["project_id"], output / "project.zip")
        verify_representation_set(views, diagrams, receipt['representations'])
        verify_view_owners(views, stored)
        model_digest = hashlib.sha256(json.dumps(stored, sort_keys=True).encode()).hexdigest()
        if model_digest != receipt["stored_model_sha256"]:
            raise ValueError("Review snapshot was edited; reconcile it before reuse: " + receipt["url"])
        verify_diagrams(curated, stored, diagrams, receipt["representations"], layout=True)
        verify_nested(views, stored, diagrams, receipt['representations'], model)
        verify_general(views, stored, diagrams, receipt['representations'], model)
        repeated = coverage(views, stored, diagrams, receipt["representations"], model)
        repeated['model_sha256'] = hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
        repeated['catalogue'] = {v['key']:v['content_sha256'] for v in views}
        if repeated != json.loads((output / "view-coverage.json").read_text()):
            raise ValueError("View coverage changed since publication")
        record_baseline(root, output, receipt)
        save(receipt_path, receipt)
        print("Reused snapshot: " + receipt["url"] + "; view gaps: " + str(repeated["gaps"]))
        return receipt
    result = subprocess.run([
        args.java, "-cp", args.kernel, str(root / "scripts/architecture/ExportModel.java"),
        args.library, str(bundle_path), "SoftwareIntake", str(output / "native-with-views.json"),
    ], capture_output=True, text=True, encoding="utf-8", timeout=180)
    (output / "validation.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise ValueError("View bundle failed native validation: " + str(output / "validation.log"))
    project = client.create_project(args.name + " - " + digest[:12])
    context = client.context(project)
    receipt = {"status": "created", "source_sha256": source_digest, "publish_sha256": digest, "server": client.url,
               "profile": "SysON 2026.11.0", "project_id": project, "editing_context_id": context,
               "representations": {}}
    save(receipt_path, receipt)
    with EditingSession(client, context) as live:
        receipt["import"] = client.upload(context, bundle_path)
        print("Imported snapshot; checking model relationships...", flush=True)
        actual_raw = client.elements(project)
        save(output / "syson-elements.json", actual_raw)
        actual = structural_projection(actual_raw, keys)
        save(output / "expected-structure.json", expected)
        save(output / "actual-structure.json", actual)
        compare(expected, actual)
        _, stored, _ = client.archive(project, output / "project.zip")
        by_key = index_objects(stored)
        print("Creating " + str(len(views)) + " shared view entries...", flush=True)
        for view in views:
            receipt["representations"][view["key"]] = client.representation(
                context, by_key[view["key"]]["id"], view["name"], view['representation_description'])
            live.diagram(receipt["representations"][view["key"]]["id"])
        save(receipt_path, receipt)
        _, stored, diagrams = client.archive(project, output / "project.zip")
        verify_diagrams(curated, stored, diagrams, receipt["representations"])
        indexed = index_objects(stored)
        for view in views:
            diagram = diagrams[receipt["representations"][view["key"]]["id"]]
            if view.get('nested_boxes'):
                show_annotations(client, context, diagram, view, indexed)
                _, hidden = nested_layout(view, diagram, stored)
                client.hide_details(context, diagram['id'], hidden + unwanted_details(view, diagram, stored))
                continue
            hidden = hidden_details(view, diagram, stored)
            selected_objects={indexed[k]['id'] for k in view['boxes']}
            hidden += [n['id'] for n in diagram['nodes'] if n['targetObjectId'] not in selected_objects]
            if view['key'] not in {v['key'] for v in curated}:
                # The old impact profile hid every allocation. Other shared views may select allocations.
                edge_ids = {e['id'] for e in diagram['edges']}
                hidden = [identity for identity in hidden if identity not in edge_ids]
            client.hide_details(context, diagram["id"], hidden + unwanted_details(view, diagram, stored))
            client.hide_details(context, diagram["id"], visible_details(view, diagram), hide=False)
        _, stored, diagrams = client.archive(project, output / "project.zip")
        for view in views:
            diagram = diagrams[receipt["representations"][view["key"]]["id"]]
            if view.get('nested_boxes'):
                positions, _ = nested_layout(view, diagram, stored)
                client.layout(context, diagram, annotation_boxes(view, indexed), details=positions)
                style_nested(client, context, diagram)
                style_annotations(client, context, diagram, view, indexed)
                style_palette(client, context, diagram, view, indexed, diagram_nodes(diagram))
                continue
            client.layout(context, diagram, {indexed[k]["id"]: box for k, box in view["boxes"].items()},
                          details=detail_boxes(view, diagram), handles=edge_handles(view, diagram, indexed),
                          labels=actor_labels(view, diagram, {v['id']:k for k,v in indexed.items()}))
        live.check()
        manifest, stored, diagrams = client.archive(project, output / "project.zip")
        verify_representation_set(views, diagrams, receipt['representations'])
        verify_view_owners(views, stored)
        verify_diagrams(curated, stored, diagrams, receipt["representations"], layout=True)
        verify_nested(views, stored, diagrams, receipt['representations'], model)
        verify_general(views, stored, diagrams, receipt['representations'], model)
        for document, name in manifest["documentIdsToName"].items():
            if name == "homelab.sysml":
                (output / "syson-export.sysml").write_bytes(client.export_text(context, document))
        semantic = named_elements(actual_raw)
        object_ids = {o["data"].get("elementId"): o["id"] for o in stored if o.get("data")}
        report = coverage(views, stored, diagrams, receipt["representations"], model)
        report['model_sha256'] = hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
        report['catalogue'] = {v['key']:v['content_sha256'] for v in views}
        save(output / "view-coverage.json", report)
        receipt.update({"status": "verified" if not report["gaps"] else "published_with_gaps",
                        "view_count": len(views), "matched_views": report["matched"], "view_gaps": report["gaps"], "named_elements": len(keys),
                        "stored_model_sha256": hashlib.sha256(json.dumps(stored, sort_keys=True).encode()).hexdigest(),
                        "structural_projection": "matched", "diagram_layout": "matched",
                        "verification_trace": "stored membership/reference and subject-value paths matched",
                        "derived_verification_semantics": "not verified; SysON 2026.11 getters are incomplete",
                        "behavior_execution": "not verified",
                        "text_round_trip": "not lossless; repository remains authoritative",
                        "identities": {k: {"element_id": semantic[k]["@id"],
                                            "object_id": object_ids[semantic[k]["@id"]]} for k in keys},
                        "url": f"{client.url}/projects/{project}/edit/" + receipt["representations"]["VIEW-system-overall"]["id"]})
        record_baseline(root, output, receipt)
        save(receipt_path, receipt)
        print("Published snapshot: " + receipt["url"] + "; matching views: " + str(report["matched"]) + "; gaps: " + str(report["gaps"]))
        for view in views:
            representation = receipt['representations'][view['key']]
            print(representation["label"] + ": " + f"{client.url}/projects/{project}/edit/" + representation["id"])
        rows=['# SysON view coverage', '', 'Git holds the accepted model baseline. Gaps are incomplete native renderings, not equivalent views.', '',
              '| SVG | SysON | Result | Gaps |', '| --- | --- | --- | --- |']
        for result in report['views']:
            view=next(v for v in views if v['key']==result['key'])
            url=f"{client.url}/projects/{project}/edit/"+result['representation']
            issues='; '.join(result.get('issues',[]))
            rows.append(f"| {result['svg']} | [{view['name'].replace('|',' / ')}]({url}) | {result['status']} | {issues} |")
        (output/'view-coverage.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
        portable=list(rows)
        portable[2] += ' Tested with SysON 2026.11.0; results apply to model SHA-256 '+report['model_sha256']+'.'
        for i,row in enumerate(portable):
            if row.startswith('| architecture/generated/'):
                destination=row.split(' | ')[0].removeprefix('| ')
                portable[i]=row.replace(destination,'[SVG]('+destination.replace('architecture/','../',1)+')',1)
        save(root/'artifacts/architecture/evidence/syson-view-coverage.json',report)
        (root/'artifacts/architecture/evidence/syson-view-coverage.md').write_text('\n'.join(portable)+'\n',encoding='utf-8')
        print("Evidence: " + str(output))
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("publish", "review-changes", "apply-changes"))
    parser.add_argument("--receipt", type=Path, help="Verified publication receipt for review-changes")
    parser.add_argument("--plan", type=Path, help="Validated change plan for apply-changes")
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--name", default="Homelab review")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    for name in ("java", "kernel", "library"):
        parser.add_argument("--" + name, default=os.environ.get("SYSML_" + name.upper()))
    args = parser.parse_args()
    try:
        if args.command == "publish":
            publish(args)
        else:
            from syson_changes import review, apply
            (review if args.command == "review-changes" else apply)(args)
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
