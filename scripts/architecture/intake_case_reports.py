"""Reader views follow the same scenario, behavior, allocation and evidence identities."""

from pathlib import Path
from intake_use_cases import connections, scenario_functions
from intake_sources import require


def link(path, label=None):
    file, _, selector = path.partition("::")
    # Reports live under artifacts/architecture/generated/software-intake.
    return f"[{label or "/".join(Path(file).parts[-3:])}](../../../../{file})" + (
        f" `{selector}`" if selector else ""
    )


def scenario_report(model, records, plan, view):
    order = view["scenarios"]
    require(
        len(order) == len(set(order)) and set(order) == set(model["scenarios"]),
        "Scenario view must include every scenario exactly once",
    )
    rows = [
        "# Software intake scenarios",
        "",
        "Generated from the owning use case, native branch selections and test plan.",
        "These are expected paths through the model, not simulated or observed executions.",
        "",
        "[Use-case view](../../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg) Â· "
        "[Functions](functions.md) Â· [Test and evidence](../../evidence/software-intake/README.md)",
        "",
        "## Contents",
        "",
    ]
    for key in order:
        rows.append(f'- [{model["elements"][key]["name"]}](#{key.lower()})')
    for key in order:
        scenario = model["scenarios"][key]
        rows += [
            "",
            f'<a id="{key.lower()}"></a>',
            f"## {key}",
            "",
            f'**{model["elements"][key]["name"]}**',
            "",
        ]
        rows += [f"**{field}:** {text}" + "\n" for field, text in ((field, scenario["docs"][field]) for field in ("Trigger", "Preconditions", "Outcome"))]
        rows += [
            f'Behavior: `{scenario["behavior"]}`. Functions: '
            + ", ".join(f"`{f}`" for f in scenario_functions(model, key))
            + ".",
            "",
            "| Step | Expected interaction | Function | Logical owner |",
            "| --- | --- | --- | --- |",
        ]
        for index, message in enumerate(scenario["messages"], 1):
            functions = [t for t in connections(model, message, "depends-on") if t in model["functions"]]
            owners = sorted({p for f in functions for p in connections(model, f, "allocated-to")})
            rows.append(
                f'| {index} Â· `{message}` | {model["elements"][message]["name"]} | '
                + ", ".join(f"`{f}`" for f in functions)
                + " | "
                + ", ".join(model["elements"][p]["name"] for p in owners)
                + " |"
            )
        checks = sorted({t for m in scenario["messages"] for t in records[m].get("test_symbols", [])})
        sources = sorted({s for m in scenario["messages"] for s in records[m]["sources"]})
        rows += [
            "",
            "**Acceptance:** " + plan[key]["acceptance"],
            "",
            "**Implementation:** " + "; ".join(link(s) for s in sources),
            "",
            "**Linked checks:** " + "; ".join(link(t) for t in checks),
            "",
        ]
        if plan[key].get("manual"):
            rows += ["**Additional manual acceptance:** " + plan[key]["manual"], ""]
    rows += [
        "All named checks must be run in their declared environment. Links do not mean a test passed.",
        "The test/evidence entry records actual executions and remaining site acceptance.",
        "",
    ]
    return "\n".join(rows)


def function_report(model):
    rows = [
        "# Software intake functions",
        "",
        "Generated from native function contracts and allocations. Product choices remain in "
        "[Solution design](../../../../architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml).",
        "",
        "| Function | Inputs â†’ outputs | Responsibility | Allocated logical parts | Guardrails |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in sorted(model["functions"]):
        ports = model["functions"][key]
        element = model["elements"][key]
        owners = connections(model, key, "allocated-to")
        guards = [t for t in connections(model, key, "depends-on") if t.startswith("REQ-")]
        rows.append(
            f'| `{key}` {element["name"]} | '
            + ", ".join(ports["in"])
            + " â†’ "
            + ", ".join(ports["out"])
            + " | "
            + " ".join(element["docs"])
            + " | "
            + ", ".join(f'`{p}` {model["elements"][p]["name"]}' for p in owners)
            + " | "
            + ", ".join(f"`{g}`" for g in guards)
            + " |"
        )
    rows += [
        "",
        "`F-verify` is allocated to the external consumer. It is an interaction obligation, not a proxy feature.",
        "Allocation can be many-to-many; it neither creates a service nor establishes implementation conformance.",
        "",
        "Follow [scenarios](scenarios.md) for ordered paths and "
        "[implementation trace](trace.md) for code, IaC and checks.",
        "",
    ]
    return "\n".join(rows)
