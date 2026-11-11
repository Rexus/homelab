"""Prune retired auto-docs and report their current guide locations."""

import json
import os
from pathlib import Path
import re
import unicodedata
from html import escape
from urllib.parse import quote

MOVES = json.loads((Path(__file__).with_name("documentation-moves.json")).read_text(encoding="utf-8"))


def referenced_manual_aliases(writer, prefix):
    """Retain retired numbered paths only where project-authored records still use them."""
    referenced = set()
    manual = writer.root / "docs/auto-docs"
    for name in ("architecture", "shared", "tier-0", "tier-1", "tier-2"):
        repo = writer.root.parent / f"{prefix.lower()}-{name}"
        if repo.is_symlink():
            continue
        documents = list(repo.glob("*.md"))
        if not (repo / "docs").is_symlink():
            documents.extend((repo / "docs").rglob("*.md"))
        for document in documents:
            if document.is_relative_to(repo / "docs/auto-docs") or document.is_symlink():
                continue
            content = document.read_text(encoding="utf-8")
            for link in re.findall(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)", content):
                if re.match(r"[a-z]+:", link):
                    continue
                target = (document.parent / link).resolve()
                if target.is_relative_to(manual):
                    referenced.add(target.relative_to(manual))
    return referenced


def section_anchors(content):
    """Collect explicit and GitHub-style heading anchors, excluding fenced examples."""
    content = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", content)
    result = set(re.findall(r'<a\s+(?:id|name)=[\'"]([^\'"]+)[\'"][^>]*>', content))
    counts = {}
    for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", content):
        title = re.sub(r"<[^>]*>", "", match[1]).strip().lower()
        base = "".join(char for char in title if char in " -_" or
                       unicodedata.category(char)[0] in "LN").replace(" ", "-")
        count = counts.get(base, 0)
        counts[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


def compatibility_stub(canonical, content, previous=""):
    current = section_anchors(content)
    previous_anchors = section_anchors(previous)
    lines = ["# Compatibility guide", "", "> **Compatibility copy:** "
             f"[Current guide]({canonical}). This page preserves older section links.", ""]
    for anchor in sorted(current | previous_anchors):
        if anchor == "compatibility-guide":
            continue
        target = canonical + ("#" + quote(anchor) if anchor in current else "")
        lines.append(f'<a id="{escape(anchor, quote=True)}"></a> [Continue to guide]({target})')
        lines.append("")
    return "\n".join(lines)


def prune_auto_docs(writer, current_paths):
    if not writer.refresh:
        return
    scope = writer.root / "docs/auto-docs"
    # Validate the entire cleanup scope before deleting any file. Never follow links/junctions.
    for path in (scope.parent, scope):
        if path.is_symlink() or path.resolve() != path:
            raise ValueError(f"Refusing auto-docs cleanup through symlink/junction: {path}")
    files, directories = [], []
    if scope.exists():
        if not scope.is_dir():
            raise ValueError(f"Auto-docs must be a directory: {scope}")

        def walk_error(error):
            raise error

        for directory, children, names in os.walk(scope, followlinks=False, onerror=walk_error):
            for name in children + names:
                path = Path(directory) / name
                if path.is_symlink() or path.resolve() != path or not path.resolve().is_relative_to(scope):
                    raise ValueError(f"Refusing auto-docs cleanup through symlink/junction: {path}")
            files.extend(Path(directory) / name for name in names)
            directories.extend(Path(directory) / name for name in children)
    for path in sorted(files):
        relative = path.relative_to(writer.root).as_posix()
        if relative in current_paths:
            continue
        old = path.relative_to(scope).as_posix()
        replacement = f"docs/auto-docs/{MOVES[old]}" if old in MOVES else None
        writer.review.removed_paths[relative] = (
            f"current guide: {replacement}" if replacement in current_paths else "outside the current generated manual"
        )
        if not writer.dry_run:
            path.unlink()
    if not writer.dry_run:
        for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            if not any(path.iterdir()):
                path.rmdir()
    for relative in set(writer.hashes) | writer.owned_paths:
        if relative.startswith("docs/auto-docs/") and relative not in current_paths:
            writer.hashes.pop(relative, None)
            writer.owned_paths.discard(relative)
