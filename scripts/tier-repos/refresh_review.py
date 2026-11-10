"""Report preserved differences and retired generator outputs without changing project files."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import sys
from typing import Optional


@dataclass
class PreservedFile:
    relative: str
    data: bytes
    source: Optional[Path]
    reason: str


def needs_operational_review(relative):
    """Filter review noise without changing file ownership or refresh actions."""
    path = Path(relative)
    name = path.name.casefold()
    return not (
        name == "readme" or name.startswith("readme.")
        or path.suffix.casefold() in {".md", ".rst", ".adoc"}
    )


class RefreshReview:
    def __init__(self, root, previous_paths, owned_paths):
        self.root = root
        self.previous_paths = set(previous_paths)
        self.owned_paths = set(owned_paths)
        self.current_paths = set()
        self.removed_paths = {}
        self.replaced_paths = {}
        self.preserved = {}

    def record(self, relative, data, source, reason):
        self.preserved.pop(relative, None)
        self.current_paths.add(relative)
        if reason:
            self.preserved[relative] = PreservedFile(
                relative, data, Path(source).resolve() if source else None, reason,
            )

    def retired_files(self):
        retired = []
        for relative in sorted(self.previous_paths - self.current_paths - self.removed_paths.keys()):
            path = self.root / relative
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                raise ValueError(f"Refusing retired output through symlink: {path}")
            if not path.is_file():
                continue
            if relative in self.owned_paths:
                reason = "retired starter; project-owned content is retained"
            else:
                reason = "previously generated; no current generation target"
            retired.append((path, reason))
        return retired


def use_color(mode, stream):
    if mode != "auto":
        return mode == "always"
    return stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def artifact_path(collection, directory, repository, relative):
    root = collection / directory
    path = root / repository / relative
    if root.is_symlink() or root.resolve() != root or not root.resolve().is_relative_to(collection):
        raise ValueError(f"Refusing review directory through symlink: {root}")
    if path.is_symlink() or path.resolve() != path or not path.resolve().is_relative_to(root):
        raise ValueError(f"Refusing review template through symlink: {path}")
    return root, path


def backup_automation(repository, relative, data, *, dry_run=False):
    digest = hashlib.sha256(data).hexdigest()
    filename = Path(relative)
    filename = filename.with_name(f"{filename.name}.{digest}.bak")
    root, path = artifact_path(repository.parent, ".refresh-backups", repository.name, filename)
    if dry_run:
        return path
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError(f"Backup differs from its content hash; refusing replacement: {path}")
    else:
        with os.fdopen(descriptor, "wb") as backup:
            backup.write(data)
    return path


def write_candidate(collection, review, item):
    root, path = artifact_path(collection, ".refresh-review", review.root.name, item.relative)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(item.data)
    return path


def print_refresh_review(reviews, collection, *, dry_run=False, color="auto", stream=None):
    stream = stream if stream is not None else sys.stdout
    collection = Path(collection).resolve()
    yellow = [(review, item) for review in reviews
              for _, item in sorted(review.preserved.items()) if needs_operational_review(item.relative)]
    red = [(path, reason) for review in reviews for path, reason in review.retired_files()
           if needs_operational_review(path.relative_to(review.root))]
    removed = [(review.root / relative, reason) for review in reviews
               for relative, reason in sorted(review.removed_paths.items())]
    replaced = [(review.root / relative, backup) for review in reviews
                for relative, backup in sorted(review.replaced_paths.items())]
    print("\nRefresh review", file=stream)
    print("  Scope: automation and configuration; README/prose documentation is omitted.", file=stream)
    print(f"  YELLOW: {len(yellow)} preserved differences; RED: {len(red)} retired files.", file=stream)
    if not yellow and not red and not removed and not replaced:
        print("  No preserved differences or retired generated files to review.", file=stream)
        return
    print("  Configuration, project-owned files and unverified existing paths remain protected.", file=stream)
    if removed:
        print(f"  Auto-docs: {len(removed)} {'would be removed' if dry_run else 'removed'}.", file=stream)
    colored = use_color(color, stream)

    def entry(label, path, reason):
        line = f"{label} {path} [{reason}]"
        if colored:
            code = "33" if label == "YELLOW" else "36" if "REPLACE" in label else "31"
            line = f"\033[{code}m{line}\033[0m"
        print(line, file=stream)

    for review, item in yellow:
        entry("YELLOW", review.root / item.relative, item.reason)
        if dry_run:
            source = item.source if item.source else "generated content (no standalone source template)"
            print(f"  Source template: {source}", file=stream)
            print("  Dry run: refresh without --dry-run to write the rendered comparison template.", file=stream)
        else:
            candidate = write_candidate(collection, review, item)
            print(f"  Rendered template: {candidate}", file=stream)
            if item.source:
                print(f"  Source template: {item.source}", file=stream)
    for path, reason in red:
        entry("RED", path, reason)
    for path, reason in removed:
        entry("WOULD REMOVE" if dry_run else "REMOVED", path, reason)
    for path, backup in replaced:
        entry("WOULD REPLACE" if dry_run else "REPLACED", path, "locally edited kit automation")
        print(f"  {'Planned backup' if dry_run else 'Previous version'}: {backup}", file=stream)
