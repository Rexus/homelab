"""Report preserved differences and retired generator outputs without changing project files."""

from dataclasses import dataclass
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


class RefreshReview:
    def __init__(self, root, previous_paths, owned_paths):
        self.root = root
        self.previous_paths = set(previous_paths)
        self.owned_paths = set(owned_paths)
        self.current_paths = set()
        self.legacy_paths = set()
        self.preserved = {}

    def record(self, relative, data, source, reason, legacy=False):
        self.preserved.pop(relative, None)
        if legacy:
            self.current_paths.discard(relative)
            self.legacy_paths.add(relative)
            return
        self.current_paths.add(relative)
        if reason:
            self.preserved[relative] = PreservedFile(
                relative, data, Path(source).resolve() if source else None, reason,
            )

    def retired_files(self):
        retired = []
        for relative in sorted((self.previous_paths - self.current_paths) | self.legacy_paths):
            path = self.root / relative
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                raise ValueError(f"Refusing retired output through symlink: {path}")
            if not path.is_file():
                continue
            if relative in self.legacy_paths:
                reason = "legacy documentation redirect; existing links may still use it"
            elif relative in self.owned_paths:
                reason = "retired starter; project-owned content is retained"
            else:
                reason = "previously generated; no current generation target"
            retired.append((path, reason))
        return retired


def use_color(mode, stream):
    if mode != "auto":
        return mode == "always"
    return stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def write_candidate(collection, review, item):
    root = collection / ".refresh-review"
    path = root / review.root.name / item.relative
    if root.is_symlink() or not root.resolve().is_relative_to(collection):
        raise ValueError(f"Refusing review directory through symlink: {root}")
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Refusing review template through symlink: {path}")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(item.data)
    return path


def print_refresh_review(reviews, collection, *, dry_run=False, color="auto", stream=None):
    stream = stream if stream is not None else sys.stdout
    collection = Path(collection).resolve()
    yellow = [(review, item) for review in reviews
              for _, item in sorted(review.preserved.items())]
    red = [item for review in reviews for item in review.retired_files()]
    print("\nRefresh review", file=stream)
    print(f"  YELLOW: {len(yellow)} preserved differences; RED: {len(red)} retired files.", file=stream)
    if not yellow and not red:
        print("  No preserved differences or retired generated files to review.", file=stream)
        return
    print("  Review only: project files and recorded deletions remain unchanged.", file=stream)
    colored = use_color(color, stream)

    def entry(label, path, reason):
        line = f"{label} {path} [{reason}]"
        if colored:
            line = f"\033[{'33' if label == 'YELLOW' else '31'}m{line}\033[0m"
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
