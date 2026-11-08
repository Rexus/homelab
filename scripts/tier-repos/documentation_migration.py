"""Prune retired auto-docs and report their current guide locations."""

import json
import os
from pathlib import Path

MOVES = json.loads((Path(__file__).with_name("documentation-moves.json")).read_text(encoding="utf-8"))


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
