"""Refresh only files whose contents still match the last generated version."""

import hashlib
import json
from pathlib import Path

MARKER = "Generated from the upstream homelab deployment kit."


class RepositoryWriter:
    def __init__(self, root, refresh=False, dry_run=False):
        self.root = Path(root).resolve()
        self.refresh = refresh
        self.dry_run = dry_run
        self.manifest_path = self.root / ".generated-files.json"
        self.hashes = {}
        self.owned_paths = set()
        if self.manifest_path.exists():
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self.hashes = manifest["files"]
            self.owned_paths = set(manifest.get("owned", []))
        self.counts = dict(create=0, update=0, unchanged=0, preserve=0)

    def write(self, relative, content, executable=False, owned=False):
        path = self.root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError(f"Refusing generated output through symlink: {path}")
        data = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(data).hexdigest()
        if path.exists():
            existing = hashlib.sha256(path.read_bytes()).hexdigest()
            if not owned and relative not in self.hashes and relative not in self.owned_paths:
                action = "preserve"
            elif existing == digest:
                action = "unchanged"
            elif owned or relative in self.owned_paths or not self.refresh or self.hashes.get(relative) != existing:
                action = "preserve"
            else:
                action = "update"
        elif relative in self.hashes or relative in self.owned_paths:
            action = "preserve"
        else:
            action = "create"
        self.counts[action] += 1
        if action != "unchanged":
            print(f"{action:9} {path}")
        if action in ("create", "update") and not self.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            if executable:
                path.chmod(0o755)
        if not owned and relative not in self.owned_paths and action != "preserve":
            self.hashes[relative] = digest
        if owned:
            self.owned_paths.add(relative)

    def finish(self):
        if not self.dry_run:
            if self.manifest_path.is_symlink():
                raise ValueError(f"Refusing symlink manifest: {self.manifest_path}")
            self.root.mkdir(parents=True, exist_ok=True)
            self.manifest_path.write_text(
                json.dumps({"generator": MARKER, "files": self.hashes, "owned": sorted(self.owned_paths)},
                           indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        prefix = "Would write" if self.dry_run else "Generated"
        print(f"{prefix} {self.root.name}: {self.counts}")
