"""Immutable publication sources and edits located by the official SysML syntax tree."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
from syson_change_model import Graph, digest
from syson_api import checked_url

MANIFEST = "architecture/use-cases/software-intake/model.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def record_baseline(root, output, receipt):
    checked_url(receipt["server"])
    if receipt.get("url"):
        checked_url(receipt["url"])
    path = output / "return-baseline.json"
    if path.exists():
        if sha(path) != receipt.get("return_baseline_sha256"):
            raise ValueError("Return baseline changed: " + str(path))
        return
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    sources = {name: (root / name).read_text(encoding="utf-8") for name in manifest["sources"]}
    bundle = (output / "homelab.sysml").read_text(encoding="utf-8")
    cursor = 0
    for name, text in sources.items():
        offset = bundle.find(text, cursor)
        if offset < 0:
            raise ValueError("Authored source changed during publication: " + name)
        cursor = offset + len(text)
    archive = output / "return-baseline.zip"
    shutil.copyfile(output / "project.zip", archive)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    save(path, {"schema": 1, "manifest": manifest, "sources": sources,
                "git_revision": result.stdout.strip() if result.returncode == 0 else None,
                "source_fingerprints": {n: sha(root / n) for n in sources},
                "archive_sha256": sha(archive), "project_id": receipt["project_id"],
                "server": receipt["server"], "profile": receipt["profile"]})
    receipt["return_baseline_sha256"] = sha(path)


def index_source(root, source, output, args):
    for field in ("java", "kernel"):
        if not getattr(args, field, None):
            raise ValueError("Change import needs the pinned SYSML_" + field.upper() + " tool")
    output.parent.mkdir(parents=True, exist_ok=True)
    path = output.with_suffix(".sysml")
    path.write_text(source, encoding="utf-8", newline="\n")
    result = subprocess.run([args.java, "-cp", args.kernel,
        str(root / "scripts/architecture/SourceIndex.java"), str(path), str(output)],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    if result.returncode:
        raise ValueError("Native source indexing failed: " + result.stderr[-2000:])
    return json.loads(output.read_text(encoding="utf-8"))


def source_map(root, sources, package, output, args):
    source, regions = "package " + package + " {\n", []
    for name, content in sources.items():
        start = len(source)
        source += content + "\n"
        regions.append((name, start, start + len(content)))
    source += "}\n"
    index = index_source(root, source, output, args)
    if index["errors"]:
        raise ValueError("Authored source has syntax errors: " + str(index["errors"][:3]))
    found = {"keys": {}, "packages": {}}
    packages = [row for row in index["elements"] if row["kind"] == "Package"]
    for row in index["elements"]:
        matches = [(name, start) for name, start, end in regions if start <= row["start"] < row["end"] <= end]
        if not matches:
            continue
        owners = [p for p in packages if p is not row and
                  p["start"] <= row["start"] and row["end"] <= p["end"]]
        package_owner = min(owners, key=lambda p: p["end"] - p["start"]) if owners else None
        name, start = matches[0]
        row = {**row, "file": name, "start": row["start"] - start, "end": row["end"] - start}
        row["package"] = package_owner["qualified_name"] if package_owner else None
        row["text"] = sources[name][row["start"]:row["end"]]
        if row.get("key"):
            if row["key"] in found["keys"]:
                raise ValueError("Duplicate source identity: " + row["key"])
            found["keys"][row["key"]] = row
        if row["kind"] == "Package":
            found["packages"].setdefault(row["qualified_name"], []).append(row)
    return found


def propose(baseline, current, tool, tool_index, graph, keys, added):
    """Whole-element three-way merge: concurrent edits within one element are explicit conflicts."""
    indexed = {}
    for row in tool_index["elements"]:
        if row.get("key"):
            if row["key"] in indexed:
                raise ValueError("Duplicate exported identity: " + row["key"])
            indexed[row["key"]] = row
    edits, conflicts = {}, []
    for key in keys:
        row = indexed.get(key)
        if not row or any(e["start"] < row["end"] and e["end"] > row["start"] for e in tool_index["errors"]):
            conflicts.append(key + ": export has no complete valid syntax node")
            continue
        # Dedent complete statements, not their syntax: the native parser owns the boundaries.
        fragment = dedent_statement(tool[row["start"]:row["end"]])
        package = graph.package(graph.keys[key])
        now = current["keys"].get(key)
        if now and now.get("package") != package:
            conflicts.append(key + ": authored package owner changed")
            continue
        if key in added:
            if key in current["keys"]:
                if dedent_statement(current["keys"][key]["text"]) != fragment:
                    conflicts.append(key + ": new identity already exists in Git")
                continue
            owners = current["packages"].get(package, [])
            if len(owners) != 1 or not owners[0]["text"].endswith("}"):
                conflicts.append(key + ": no unique authored package owner " + package)
                continue
            owner = owners[0]
            edits.setdefault(owner["file"], []).append((owner["end"] - 1, owner["end"] - 1,
                "\n" + textwrap.indent(fragment, "    ") + "\n"))
        else:
            old, now = baseline["keys"].get(key), current["keys"].get(key)
            if not old or not now or old["file"] != now["file"]:
                conflicts.append(key + ": missing or moved authored element")
                continue
            if old.get("package") != now.get("package"):
                conflicts.append(key + ": authored package owner changed")
                continue
            replacement = fragment.replace("\n", "\n    ")
            if dedent_statement(now["text"]) == fragment:
                continue
            if now["text"] != old["text"]:
                conflicts.append(key + ": Git and SysON both changed this element")
                continue
            edits.setdefault(now["file"], []).append((now["start"], now["end"], replacement))
    if conflicts:
        raise ValueError("Change import conflicts: " + "; ".join(conflicts))
    return edits


def dedent_statement(text):
    lines = text.splitlines()
    return lines[0] + ("\n" + textwrap.dedent("\n".join(lines[1:])) if len(lines) > 1 else "")


def edited_sources(sources, edits):
    result = {}
    for name, changes in edits.items():
        content = sources[name]
        previous = len(content) + 1
        for start, end, value in sorted(changes, reverse=True):
            if end > previous:
                raise ValueError("Overlapping proposed source edits: " + name)
            content = content[:start] + value + content[end:]
            previous = start
        result[name] = content
    return result
