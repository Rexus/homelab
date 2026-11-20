"""Complete intent inventory as supporting text; it does not add graphical views or pass verdicts."""

REPORT = "architecture/generated/software-intake/intent.md"


def case_target(key, selected):
    return selected.get(key, REPORT + "#" + key.lower())


def intent_report(model):
    lines = ["# Modeled requirements and use cases", "",
        "Generated from the accepted model sources. Links identify specification coverage, not executed results.", "",
        "[Working workflow](../../../docs/04-development/model-change-workflow.md) · "
        "[Verification evidence](../../../docs/01-architecture/07-software-intake/verification.md)", "",
        "## Contents", ""]
    keys = sorted(set(model["requirements"]) | set(model["use_cases"]))
    lines += [f'- [{key}](#{key.lower()})' for key in keys]
    for key in keys:
        element = model["elements"][key]
        lines += ["", '<a id="' + key.lower() + '"></a>', "## " + key + " — " + element["name"], ""]
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
