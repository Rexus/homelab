"""Keep existing links usable without carrying the old tree into new collections."""

import json
import os
from pathlib import Path
import re

MOVES = json.loads((Path(__file__).with_name("documentation-moves.json")).read_text(encoding="utf-8"))


def redirect_moved_docs(writer, previous_paths):
    for old, new in MOVES.items():
        relative = f"docs/auto-docs/{old}"
        source = writer.root / relative
        target = writer.root / "docs/auto-docs" / new
        if relative not in previous_paths or not source.is_file():
            continue
        if source.is_symlink() or not source.resolve().is_relative_to(writer.root):
            raise ValueError(f"Refusing legacy documentation through symlink: {source}")
        target_relative = f"docs/auto-docs/{new}"
        if not target.exists() and (not writer.dry_run or target_relative in previous_paths):
            continue
        old_content = source.read_text(encoding="utf-8")
        anchors = set(re.findall(r'<a id="([^"]+)"></a>', old_content))
        anchors.add("relocated-reference")
        for heading in re.findall(r"^#{1,6} (.+)$", old_content, re.MULTILINE):
            anchors.add(re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-"))
        link = Path(os.path.relpath(target, source.parent)).as_posix()
        content = ("# Relocated reference\n\n"
                   "> **AUTO-DOCS - DO NOT EDIT**\n"
                   "> Updated by `bash scripts/init-tier-repos.sh --refresh` from the upstream kit.\n\n")
        content += "\n".join(f'<a id="{anchor}"></a>' for anchor in sorted(anchors))
        content += f"\n\nRead the [current guide]({link}) in the reorganized documentation.\n"
        # RepositoryWriter protects edited files, owned files, and recorded deletions.
        writer.write(relative, content)
