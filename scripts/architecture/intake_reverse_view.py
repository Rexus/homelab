"""Reverse impact is a model-derived review view, with trace paths as a supporting asset."""

import json
from pathlib import Path
from design_context import relative
from intake_use_cases import CASE_VIEWS
from intake_intent import case_target
from svg_pages import SYSTEM, INTAKE, FUNCTIONS, SCENARIOS, card, page, finish, book, grid, text
from intake_reverse import (REVERSE_VIEW, REVERSE_REPORT, REVERSE_INDEX, associations,
                            asset_id, review, path_text)


def category(asset):
    if asset.startswith("tests/"):
        return "Test methods" if "::" in asset else "Tests"
    if "/terraform/" in asset:
        return "Terraform"
    if "/ansible/" in asset:
        return "Ansible"
    return "Design and evidence"


def model_link(key):
    if key.startswith("F-"):
        return FUNCTIONS + "#" + key
    if key.startswith("SC-"):
        return SCENARIOS + "#" + key
    if key.startswith("UC-"):
        return case_target(key, CASE_VIEWS)
    if key.startswith("VC-"):
        return "architecture/generated/software-intake/verification-cases.md#" + key.lower()
    return "architecture/generated/software-intake/intent.md#" + key.lower()


def report(model, reviews):
    rows = ["# Reverse software-intake trace", "", "Generated from the built model and its trace records.",
        "Potential review scope is not a failure prediction, requirement satisfaction or test result.", "",
        "[Visual index](../../views/software-intake/asset-impact.svg) · [How to use this](../../../docs/01-architecture/07-software-intake/03-http-walkthrough.md#follow-a-file-or-test-backwards)",
        "", "## Contents", ""]
    rows += [f'- [{asset}](#{data["id"]})' for asset, data in reviews.items()]
    for asset, data in reviews.items():
        file = asset.split("::")[0]
        rows += ["", f'<a id="{data["id"]}"></a>', "## " + asset, "",
            f'[Impact view]({relative(REVERSE_REPORT, REVERSE_VIEW)}#{data["id"]}) · [Source asset](../../../{file})', "",
            "Association: **" + data["mode"] + "**. Test changes affect the recorded evidence first.", "",
            "Direct links: " + "; ".join(r["element"] + " (" + r["relation"] + "; " + r["state"] + ")" for r in data["direct"]) + ".", "",
            "| Concern | Potential review target | Why it appears |", "| --- | --- | --- |"]
        for label, field in (("Function", "functions"), ("Scenario", "scenarios"),
                             ("Use case", "use_cases"), ("Guardrail to recheck", "requirements"), ("Verification case", "verification_cases")):
            for key, path in data[field].items():
                rows.append(f'| {label} | `{key}` {model["elements"][key]["name"]} | {path_text(key, path)} |')
        rows += ["", "Related checks: " + ("; ".join(
            f'[{p}](../../../{p.split("::")[0]})' for p in data["checks"]) or "None recorded.") + ".", ""]
    return "\n".join(rows)


def impact_page(model, data):
    asset = data["asset"]
    filename, _, symbol = asset.partition("::")
    svg, y, nav = page(REVERSE_VIEW, "Change impact | " + Path(filename).name,
        asset, REVERSE_REPORT + "#" + data["id"], REVERSE_VIEW)
    meaning = ("Test asset: review verification coverage; editing this file does not itself change runtime behavior."
               if data["mode"] == "verification" else
               "Potential review scope from recorded source links; the actual edit determines what must change.")
    y += card(svg, REVERSE_VIEW, 30, y, 900, "Direct trace", meaning + " Direct model links: " +
        ", ".join(sorted({r["element"] for r in data["direct"]})),
        REVERSE_REPORT + "#" + data["id"]) + 28
    # The three columns are related concerns, not runtime components or a causal chain.
    ends = []
    for x, title, field in ((30, "Functions to review", "functions"),
                            (340, "Expected use", "scenarios"),
                            (650, "Guardrails to recheck", "requirements")):
        text(svg, title, x, y, 18, weight="bold")
        yy = y+18
        keys = data[field]
        if field == "scenarios":
            keys = {**data["use_cases"], **keys}
        if not keys:
            yy += card(svg, REVERSE_VIEW, x, yy, 280, "Not linked", "No recorded path in this modeled slice.") + 10
        for key, hops in keys.items():
            yy += card(svg, REVERSE_VIEW, x, yy, 280, key,
                model["elements"][key]["name"], model_link(key), key) + 10
        ends.append(yy)
    y = max(ends) + 12
    if data["verification_cases"]:
        text(svg, "Native verification cases — review evidence coverage", 30, y, 18, weight="bold")
        y = grid(svg, REVERSE_VIEW, y+18, [(k, model["elements"][k]["name"], model_link(k), k) for k in data["verification_cases"]])
    text(svg, "Model-derived review links · Open Trace paths for the relationship behind each result", 480, y, 14, "middle")
    nav = [("System Overall", SYSTEM), ("File / test index", REVERSE_VIEW),
           ("Open source asset", filename), ("Trace paths", REVERSE_REPORT + "#" + data["id"])]
    return finish(svg, REVERSE_VIEW, y+8, nav)


def reverse_outputs(model, records):
    reviews = {asset: review(model, records, asset) for asset in associations(records)}
    groups = {}
    for asset in reviews:
        groups.setdefault(category(asset), []).append(asset)
    pages = []
    svg, y, nav = page(REVERSE_VIEW, "Software intake | Change impact",
        "Start from an IaC file, configuration or test. These are recorded links within the modeled intake slice.",
        "docs/01-architecture/07-software-intake/03-http-walkthrough.md#follow-a-file-or-test-backwards")
    y = grid(svg, REVERSE_VIEW, y, [(name, f"{len(values)} recorded assets", REVERSE_VIEW + "#" + name.replace(" ", "-"), None)
                                 for name, values in groups.items()])
    nav[2] = ("Intake overview", INTAKE)
    pages.append(("index", finish(svg, REVERSE_VIEW, y, nav)))
    for name, values in groups.items():
        count = (len(values)+11)//12
        for number, start in enumerate(range(0, len(values), 12), 1):
            fragment = name.replace(" ", "-") + ("-" + str(number) if number > 1 else "")
            svg, y, nav = page(REVERSE_VIEW, "Change impact | " + name + f" ({number}/{count})",
                "Choose a file or exact test method; unlisted assets need an explicit trace before impact is known.",
                REVERSE_REPORT, REVERSE_VIEW)
            rows = []
            for asset in values[start:start+12]:
                file, _, symbol = asset.partition("::")
                rows.append((symbol or "/".join(Path(file).parts[-3:]), file.split("/")[0],
                             REVERSE_VIEW + "#" + asset_id(asset), asset))
            y = grid(svg, REVERSE_VIEW, y, rows)
            if number < count:
                nav[2] = ("Next files", REVERSE_VIEW + "#" + name.replace(" ", "-") + "-" + str(number+1))
            pages.append((fragment, finish(svg, REVERSE_VIEW, y, nav)))
    pages += [(data["id"], impact_page(model, data)) for data in reviews.values()]
    return {Path(REVERSE_VIEW): book(pages), Path(REVERSE_REPORT): report(model, reviews),
            Path(REVERSE_INDEX): json.dumps({"scope": "Potential review scope of the last built intake model",
                                           "assets": reviews}, indent=2) + "\n"}
