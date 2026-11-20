"""Source-level behavior contracts; native product tests and live acceptance remain separate."""

import ast
import json
import re
from jinja2 import Environment, StrictUndefined
from intake_sources import ROLE, require, read_yaml
from intake_behavior import messages


def check_test_symbols(root, records):
    for record in records.values():
        for selector in record.get("test_symbols", []):
            path, symbol = selector.split("::", 1)
            require(path in record.get("checks", []), "Test selector must name a traced check file")
            node = ast.parse((root / path).read_text(encoding="utf-8"))
            for name in symbol.split("."):
                matches = [
                    child
                    for child in node.body
                    if isinstance(child, (ast.ClassDef, ast.FunctionDef)) and child.name == name
                ]
                require(len(matches) == 1, "Missing behavior test: " + selector)
                node = matches[0]


def check_behavior_contracts(root, inputs, model, records):
    check_test_symbols(root, records)
    config = dict(inputs["config"], inventory_hostname="cache.model.test")
    source = (root / ROLE / "templates/squid.conf.j2").read_text(encoding="utf-8")
    rendered = Environment(undefined=StrictUndefined).from_string(source).render(config)
    lines = [
        line.strip() for line in rendered.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]
    expected = [
        "http_access deny !Safe_ports",
        "http_access deny CONNECT !SSL_ports",
        "http_access allow localhost manager",
        "http_access deny manager",
        "http_access deny !allowed_update_domains",
        "http_access deny to_localhost",
        "http_access deny to_linklocal",
        "http_access allow localhost allowed_update_domains",
        "http_access allow localnet allowed_update_domains",
        "http_access deny all",
    ]
    require(all(line in lines for line in expected), "Admission contract is missing a required Squid rule")
    require(
        [line for line in lines if line.startswith("http_access ")] == expected,
        "Admission rule order or exceptions contradict the selected policy",
    )
    require(
        [line for line in lines if line.startswith("http_access ")][-1] == expected[-1],
        "Admission must end with deny all",
    )
    require(
        "acl SSL_ports port 443" in lines and "acl CONNECT method CONNECT" in lines,
        "CONNECT port contract changed",
    )
    require(
        not any(line.startswith(("ssl_bump ", "https_port ")) for line in lines),
        "TLS interception contradicts the tunnel model",
    )
    require(
        not re.search(
            r"\b(override-expire|override-lastmod|ignore-no-cache|ignore-no-store|ignore-private|ignore-reload|reload-into-ims)\b",
            rendered,
        ),
        "Cache freshness/privacy overrides contradict the HTTP model",
    )
    tasks = read_yaml(root, "shared/ansible/roles/baseline/tasks/package_policy.yml")
    settings = {
        item["option"]: item["value"]
        for task in tasks
        if "community.general.ini_file" in task
        for item in task.get("loop", [])
    }
    require(
        all(
            str(settings.get(key)).lower() == "true"
            for key in ("gpgcheck", "localpkg_gpgcheck", "sslverify", "proxy_sslverify")
        ),
        "Client verification contract no longer enforces DNF verification",
    )
    apt = (root / "shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2").read_text(
        encoding="utf-8"
    )
    for directive in (
        'APT::Get::AllowUnauthenticated "false";',
        'Acquire::AllowInsecureRepositories "false";',
        'Acquire::https::Verify-Peer "true";',
        'Acquire::https::Verify-Host "true";',
    ):
        require(directive in apt, "Client verification contract missing APT setting: " + directive)
    for behavior in model["behaviors"].values():
        for message in messages(behavior["steps"]):
            require(
                message["id"] in records, "Message has no implementation/evidence trace: " + message["id"]
            )


def behavior_report(model, records):
    rows = [
        "# Expected behavior trace",
        "",
        "Generated from native SysML messages and their checked implementation links.",
        "Source checks do not establish a live deployment or execute the model.",
        "",
        "| Message | Expected exchange | Evidence class | Implementation / verification |",
        "| --- | --- | --- | --- |",
    ]
    for behavior in model["behaviors"].values():
        for message in messages(behavior["steps"]):
            record = records[message["id"]]
            sources = record["sources"] + record.get("test_symbols", record.get("checks", []))
            rows.append(
                f'| `{message["id"]}` | {message["label"]} | {record["state"]} | '
                + "<br/>".join("`" + p + "`" for p in sources)
                + " |"
            )
    rows += [
        "",
        "`implementation-source`: selected configuration and code exist; referenced runtime tests may be skipped.",
        "`manual-acceptance`: the expected exchange still requires runtime evidence, including successful CONNECT/TLS.",
        "Package source exceptions and later configuration overrides must also be checked in the deployed environment.",
        "",
    ]
    return "\n".join(rows)
