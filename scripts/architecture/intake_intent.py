"""Complete intent inventory as supporting text; it does not add graphical views or pass verdicts."""

from pathlib import Path

REPORT = "artifacts/architecture/generated/software-intake/intent.md"


def case_target(key, selected):
    return selected.get(key, REPORT + "#" + key.lower())


def intent_report(model):
    lines = ["# Modeled requirements and use cases", "",
        "Generated from the accepted model sources. Links identify specification coverage, not executed results.", "",
        "[Working workflow](../../../../docs/04-development/model-change-workflow.md) Â· "
        "[Verification evidence](../../../../docs/01-architecture/07-software-intake/verification.md)", "",
        "## Contents", ""]
    keys = sorted(set(model["requirements"]) | set(model["use_cases"]))
    lines += [f'- [{key}](#{key.lower()})' for key in keys]
    for key in keys:
        element = model["elements"][key]
        lines += ["", '<a id="' + key.lower() + '"></a>', "## " + key + " â€” " + element["name"], ""]
        if key in model["requirements"]:
            lines += model["requirements"][key]["constraints"] + [""]
            cases = sorted(k for k, v in model["verification"].items() if key in v["requirements"])
            lines += ["Verification cases: " + (", ".join(cases) if cases else "None recorded; verification is uncovered.")]
        else:
            case = model["use_cases"][key]
            requirements = sorted(e["to"] for e in model["edges"] if e["from"] == key and e["kind"] == "requires")
            scenarios = sorted(k for k, v in model["scenarios"].items() if v["use_case"] == key)
            lines += ["Subject: " + case["bindings"][case["subject"]] + ".",
                      "Actors: " + ", ".join(case["actors"]) + ".",
                      "Required obligations: " + (", ".join(requirements) or "None recorded") + ".",
                      "Scenarios: " + (", ".join(scenarios) or "None recorded; scenario detail is pending") + "."]
    return "\n".join(lines) + "\n"


def guardrail_table(model, outputs):
    path = Path("architecture/README.md")
    document = outputs[path]
    start, end = "<!-- BEGIN MODEL GUARDRAILS -->", "<!-- END MODEL GUARDRAILS -->"
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError("Intake needs unique native guardrail table markers")
    lines = ["", "| Guardrail | Subject | Native acceptance constraint | Verification intent |",
             "| --- | --- | --- | --- |"]
    for key, requirement in sorted(model["requirements"].items()):
        criteria = " ".join(requirement["constraints"]).replace("|", " / ").replace("\n", " ")
        cases = sorted(k for k, v in model["verification"].items() if key in v["requirements"])
        target = "views/software-intake/SoftwareIntakeVerification.md#" + key
        subject = ", ".join(model["elements"][s]["name"] for s in requirement["subject_types"])
        lines.append(f"| `{key}` | {subject} | {criteria} | [{', '.join(cases) or 'Uncovered'}]({target}) |")
    outputs[path] = document[:document.index(start)+len(start)] + "\n".join(lines) + "\n" + document[document.index(end):]
