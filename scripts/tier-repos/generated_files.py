"""Refresh kit automation while protecting project inputs and recoverable local edits."""

import hashlib
import json
from pathlib import Path

from refresh_review import PreservedFile, RefreshReview, backup_automation, needs_operational_review, write_candidate

MARKER = "Generated from the upstream homelab deployment kit."


class RepositoryWriter:
    def __init__(self, root, refresh=False, dry_run=False, code_conflicts="replace"):
        self.root = Path(root).resolve()
        self.refresh = refresh
        self.dry_run = dry_run
        self.code_conflicts = code_conflicts
        self.manifest_path = self.root / ".generated-files.json"
        self.hashes = {}
        self.owned_paths = set()
        if self.manifest_path.exists():
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self.hashes = manifest["files"]
            self.owned_paths = set(manifest.get("owned", []))
        self.review = RefreshReview(self.root, set(self.hashes) | self.owned_paths, self.owned_paths)
        self.counts = dict(create=0, update=0, unchanged=0, preserve=0)

    def replace_edited_automation(self, relative, data, source):
        if self.code_conflicts == "ask":
            if self.dry_run:
                return False
            path = self.root / relative
            candidate = write_candidate(self.root.parent, self.review,
                                        PreservedFile(relative, data, source, "locally edited automation"))
            print(f"Edited kit automation: {path}\nCurrent kit version: {candidate}")
            while True:
                try:
                    answer = input("Preserve or replace with backup? [p/r, default p]: ")
                except EOFError as error:
                    raise ValueError("No conflict decision received; use --code-conflicts replace or preserve") from error
                answer = answer.strip().lower()
                if answer in ("", "p", "preserve"):
                    return False
                if answer in ("r", "replace"):
                    return True
        return self.code_conflicts == "replace"

    def write(self, relative, content, executable=False, owned=False, source=None, automation=False):
        path = self.root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError(f"Refusing generated output through symlink: {path}")
        data = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(data).hexdigest()
        existing = None
        if path.exists():
            existing = hashlib.sha256(path.read_bytes()).hexdigest()
            if not owned and relative not in self.hashes and relative not in self.owned_paths:
                action = "preserve"
            elif existing == digest:
                action = "unchanged"
            elif owned or relative in self.owned_paths or not self.refresh:
                action = "preserve"
            elif self.hashes.get(relative) == existing:
                action = "update"
            elif automation and self.replace_edited_automation(relative, data, source):
                backup = backup_automation(self.root, relative, path.read_bytes(), dry_run=self.dry_run)
                self.review.replaced_paths[relative] = backup
                action = "update"
            else:
                action = "preserve"
        elif not self.refresh and (relative in self.hashes or relative in self.owned_paths):
            action = "preserve"
        else:
            action = "create"
        reason = None
        if action == "preserve" and existing != digest:
            if existing is None:
                reason = "missing file; use --refresh to restore the current template"
            elif owned or relative in self.owned_paths:
                reason = "project-owned; compare the current starter"
            elif relative not in self.hashes:
                reason = "pre-existing file; generation ownership is unverified"
            elif automation and self.refresh:
                reason = f"locally edited automation; --code-conflicts {self.code_conflicts}"
            else:
                reason = "locally edited generated file"
        self.review.record(relative, data, source, reason)
        self.counts[action] += 1
        quiet_document = self.refresh and action == "preserve" and not needs_operational_review(relative)
        if action != "unchanged" and not quiet_document:
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
            self.hashes.pop(relative, None)

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
