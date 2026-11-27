"""Derived reverse trace for source/test review; no separate diagram inventory."""

import json
from pathlib import Path
from design_context import relative
from intake_use_cases import CASE_VIEWS
from intake_intent import case_target
from svg_pages import FUNCTIONS, SCENARIOS
from intake_reverse import (REVERSE_REPORT, REVERSE_INDEX, associations,
                            review, path_text)


def model_link(key):
    if key.startswith("F-"):
        return FUNCTIONS + "#" + key
    if key.startswith("SC-"):
        return SCENARIOS + "#" + key
    if key.startswith("UC-"):
        return case_target(key, CASE_VIEWS)
    if key.startswith("VC-"):
        return "architecture/generated/software-intake/SoftwareIntakeVerification.md#" + key.lower()
    return "artifacts/architecture/generated/software-intake/intent.md#" + key.lower()


def report(model, reviews):
    rows = ["# Reverse software-intake trace", "", "Generated from the built model and its trace records.",
        "Potential review scope is not a failure prediction, requirement satisfaction or test result.", "",
        "[How to use this](../../../../docs/01-architecture/07-software-intake/03-http-walkthrough.md#follow-a-file-or-test-backwards)",
        "", "## Contents", ""]
    rows += [f'- [{asset}](#{data["id"]})' for asset, data in reviews.items()]
    for asset, data in reviews.items():
        file = asset.split("::")[0]
        rows += ["", f'<a id="{data["id"]}"></a>', "## " + asset, "",
            f'[Source asset](../../../../{file})', "",
            "Association: **" + data["mode"] + "**. Test changes affect the recorded evidence first.", "",
            "Direct links: " + "; ".join(r["element"] + " (" + r["relation"] + "; " + r["state"] + ")" for r in data["direct"]) + ".", "",
            "| Concern | Potential review target | Why it appears |", "| --- | --- | --- |"]
        for label, field in (("Function", "functions"), ("Scenario", "scenarios"),
                             ("Use case", "use_cases"), ("Guardrail to recheck", "requirements"), ("Verification case", "verification_cases")):
            for key, path in data[field].items():
                rows.append(f'| {label} | `{key}` {model["elements"][key]["name"]} | {path_text(key, path)} |')
        rows += ["", "Related checks: " + ("; ".join(
            f'[{p}](../../../../{p.split("::")[0]})' for p in data["checks"]) or "None recorded.") + ".", ""]
    return "\n".join(rows)


def reverse_outputs(model, records):
    reviews={asset:review(model,records,asset) for asset in associations(records)}
    return {Path(REVERSE_REPORT):report(model,reviews),
            Path(REVERSE_INDEX):json.dumps({'scope':'Potential review scope of the last built intake model',
                                          'assets':reviews},indent=2)+'\n'}
