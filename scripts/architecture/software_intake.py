"""Build/check connected software-intake structure, behavior and implementation traces."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from intake_sources import (
    MODEL,
    VIEWS,
    GENERATED,
    TRACE,
    TOOLCHAIN,
    selected_inputs,
    check_wiring,
    realization,
    trace_map,
    require,
)
from intake_model import normalize, impact, validate_trace, trace_report
from intake_intent import intent_report
from intake_views import render
from view_catalog import compile_views
from focused_views import outputs as focused_outputs
from model_style import decorate
from view_contracts import contract_outputs
from intake_behavior import mermaid
from intake_use_cases import validate_use_cases
from intake_case_reports import scenario_report, function_report
from intake_case_view import use_case_view
from bootstrap_use_case import outputs as bootstrap_outputs, VIEW as BOOTSTRAP_VIEW
from bootstrap_reference import prepare_reference, VIEW as FOUNDATION_VIEW, RENDERER as FOUNDATION_RENDERER
from intake_resource_view import resource_view
from system_overall import overview_outputs, overview_sources
from design_context import source_paths as context_sources
from design_context_view import context_outputs
from intake_explorer import navigation_outputs
from intake_scenario_views import scenario_views, function_views
from design_context import scopes
from svg_pages import SCENARIOS, FUNCTIONS, validate_links
from intake_reverse_view import reverse_outputs
from intake_reverse_cli import run_file_query
from intake_semantics import case_plan
from intake_engineering_view import outputs as engineering_outputs
from intake_execution_view import execution_outputs
from intake_product import outputs as product_outputs
from intake_platform import check_platform, dependencies, resource_report
from intake_contracts import check_behavior_contracts, behavior_report

DIAGRAMS = Path("docs/08-reference/diagrams")
GUIDE = Path("docs/01-architecture/07-software-intake/README.md")
OUTPUTS = {
    "placement": Path("architecture/views/software-intake/placement.svg"),
    "logical": Path("architecture/views/software-intake/logical.svg"),
}
CASE_PLAN = Path("architecture/test/software-intake/cases.json")
CASE_VIEW = Path("architecture/views/software-intake/use-cases.svg")
SEQUENCES = {"HTTP": "B-HTTP", "HTTPS": "B-HTTPS"}


def fingerprint(root, records):
    files = {p for record in records.values() for p in record["sources"] + record.get("checks", [])}
    for directory in (MODEL, VIEWS, Path("scripts/architecture")):
        files.update(
            p.relative_to(root).as_posix()
            for p in (root / directory).rglob("*")
            if (p.suffix in (".sysml", ".json", ".py", ".java") or p.name.endswith(".layout.svg"))
            and p.name != "catalog.json"
        )
    files.add(BOOTSTRAP_VIEW.with_suffix(".json").as_posix())
    files.update(p.as_posix() for p in (FOUNDATION_VIEW, FOUNDATION_RENDERER))
    files.update(overview_sources(root))
    files.update(context_sources(root))
    # CASE_PLAN is a generated compatibility projection of native verification cases.
    files.update(json.loads((root / MODEL / "model.json").read_text(encoding="utf-8"))["sources"])
    files.update(
        map(
            str, (TRACE, TOOLCHAIN, DIAGRAMS / "palette.json", Path("architecture/views/notation.json"))
        )
    )
    return {
        Path(p).as_posix(): hashlib.sha256((root / p).read_text(encoding="utf-8").encode()).hexdigest()
        for p in sorted(files)
    }


def native_export(root, selected, args):
    require(
        all((args.java, args.kernel, args.library)),
        "build needs --java, --kernel and --library (or SYSML_JAVA/KERNEL/LIBRARY)",
    )
    manifest = json.loads((root / MODEL / "model.json").read_text(encoding="utf-8"))
    sources = []
    for name in manifest["sources"]:
        path = (root / name).resolve()
        require(
            path.is_relative_to((root / "architecture").resolve()) and path.is_file(),
            "Missing or escaping model source: " + name,
        )
        sources.append(path.read_text(encoding="utf-8"))
    build = root / ".tmp/software-intake-model"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "combined.sysml"
    imports = "\n".join("private import " + package + "::*;" for package in manifest["imports"])
    source.write_text(
        "package "
        + manifest["package"]
        + " {\n"
        + imports
        + "\n"
        + "\n".join(sources)
        + selected
        + "\n}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            str(Path(args.java).resolve()),
            "-cp",
            str(Path(args.kernel).resolve()),
            str(root / "scripts/architecture/ExportModel.java"),
            str(Path(args.library).resolve()),
            str(source),
            manifest["package"],
            str(build / "native.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    (build / "validation.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    require(
        result.returncode == 0,
        "Native SysML validation failed; inspect .tmp/software-intake-model/validation.log",
    )
    return normalize(json.loads((build / "native.json").read_text(encoding="utf-8")))


def expected_outputs(root, model, inputs, records, *, execution_report=None):
    outputs = {
        CASE_PLAN: json.dumps(case_plan(model), indent=2) + "\n",
        GENERATED / "realization.sysml": realization(inputs),
        GENERATED
        / "scenarios.md": scenario_report(
            model,
            records,
            case_plan(model),
            json.loads((root / VIEWS / "use-cases.json").read_text(encoding="utf-8")),
        ),
        GENERATED / "functions.md": function_report(model),
        GENERATED / "intent.md": intent_report(model),
        CASE_VIEW: use_case_view(root, model),
        Path("architecture/views/software-intake/resource-dependencies.svg"): resource_view(root, model, inputs),
        GENERATED / "resource-trace.md": resource_report(model),
        GENERATED / "trace.md": trace_report(model, records, inputs),
        GENERATED / "behavior-trace.md": behavior_report(model, records),
        **{path: render(root, model, inputs, kind) for kind, path in OUTPUTS.items()},
        **overview_outputs(root, model),
    }
    view = json.loads((root / VIEWS / "sequence.json").read_text(encoding="utf-8"))
    document = (root / GUIDE).read_text(encoding="utf-8")
    for label, key in SEQUENCES.items():
        code = mermaid(model, key, view)
        outputs[GENERATED / (label.lower() + ".mmd")] = code
        begin, end = "<!-- BEGIN MODEL " + label + " -->", "<!-- END MODEL " + label + " -->"
        require(
            document.count(begin) == document.count(end) == 1,
            "Sequence guide needs unique markers for " + label,
        )
        a, b = document.index(begin) + len(begin), document.index(end)
        document = document[:a] + "\n```mermaid\n" + code + "```\n" + document[b:]
    outputs[GUIDE] = document
    outputs.update(
        context_outputs(
            root, model, records, case_plan(model), outputs
        )
    )
    plan = case_plan(model)
    outputs.update(navigation_outputs(root, model, records, plan, outputs))
    entries = scopes(root)
    outputs[Path(SCENARIOS)] = scenario_views(root, model, entries, records, plan)
    outputs[Path(FUNCTIONS)] = function_views(model, entries, records)
    outputs.update(reverse_outputs(model, records))
    outputs.update(engineering_outputs(root, model, records))
    outputs.update(execution_outputs(root, model, records, fingerprint(root, records), report=execution_report))
    outputs.update(product_outputs(root, model))
    outputs.update(contract_outputs(root, model))
    outputs.update(bootstrap_outputs(root, model))
    outputs.update(focused_outputs(root, model))
    decorate(root, model, outputs)
    selection = json.loads((root / "architecture/views/engineering-views.json").read_text(encoding="utf-8"))["views"]
    compile_views(outputs, model, selection)
    validate_links(root, outputs)
    return outputs


def run(root, command, args):
    if command == "execute":
        from intake_execution import execute
        return execute(root, args)
    if command == "analyze":
        from intake_analysis import evaluate
        return evaluate(root, args)
    if command == "impact" and getattr(args, "file", None):
        return run_file_query(root, args.file)
    inputs = selected_inputs(root)
    check_wiring(root)
    records = trace_map(root)
    index = root / GENERATED / "model-index.json"
    if command == "build":
        prepare_reference(root)
        model = native_export(root, realization(inputs), args)
    else:
        require(index.is_file(), "Build the model once with the native parser before checking")
        snapshot = json.loads(index.read_text(encoding="utf-8"))
        current = fingerprint(root, records)
        changed = sorted(
            p
            for p in set(current) | set(snapshot["sources"])
            if current.get(p) != snapshot["sources"].get(p)
        )
        require(not changed, "Model export needs regeneration after changes to: " + ", ".join(changed))
        model = snapshot["model"]
    validate_trace(model, records)
    check_platform(root, model, inputs)
    check_behavior_contracts(root, inputs, model, records)
    validate_use_cases(model, records, case_plan(model))
    outputs = expected_outputs(root, model, inputs, records)
    if command == "build":
        for path, value in outputs.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(value, encoding="utf-8")
        index.write_text(
            json.dumps(
                {
                    "scope": "upstream example inputs; expected behavior, not live deployment",
                    "model": model,
                    "trace_records": records,
                    "sources": fingerprint(root, records),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f'Native model validated; {len(inputs["members"])} IaC members, use-case/scenario/function views, system/platform overviews, two structural views and two sequences generated.'
        )
    else:
        for path, value in outputs.items():
            require(
                (root / path).is_file() and (root / path).read_text(encoding="utf-8") == value,
                f"Stale generated output: {path}",
            )
        print("PASS: model, behavior, IaC contracts, trace targets and generated views agree.")
        if command == "impact":
            affected = impact(model, args.element)
            print("\nPotentially affected model elements: " + ", ".join(affected))
            owners = {
                e["to"] for e in model["edges"] if e["from"] in affected and e["kind"] == "typed-by"
            }
            for key in sorted(set(affected) | owners):
                if key in records:
                    print("\n" + key + " [" + records[key]["state"] + "]")
                    for path in records[key]["sources"] + records[key].get("checks", []):
                        print("  " + path)
    if command == "dependencies":
        print("\nRequired model elements: " + ", ".join(dependencies(model, args.element)))
    return model


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("build", "check", "impact", "dependencies", "analyze", "execute"))
    p.add_argument("element", nargs="?")
    p.add_argument("--file", help="Upstream file path or path::test method; review the last built trace")
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    for name in ("java", "kernel", "library"):
        p.add_argument("--" + name, default=os.environ.get("SYSML_" + name.upper()))
    p.add_argument("--runtime", default=os.environ.get("SYSML_RUNTIME"), help="Pinned OpenSysML executable")
    p.add_argument("--wsl", default=os.environ.get("SYSML_WSL"), help="WSL distribution for a Linux runtime path")
    args = p.parse_args()
    if args.file and (args.command != "impact" or args.element):
        p.error("--file requires impact and cannot be combined with a model element")
    args.element = args.element or "DEF-proxy"
    try:
        run(args.root.resolve(), args.command, args)
    except (ValueError, KeyError, FileNotFoundError) as error:
        p.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
