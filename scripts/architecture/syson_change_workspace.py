"""Isolated build inputs and guarded source application for a reviewed change."""

import os
from pathlib import Path
import shutil
from syson_change_source import MANIFEST, sha


def checked_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or Path(name).is_absolute():
        raise ValueError("Escaping change path: " + name)
    return path


def inputs(root):
    from intake_sources import trace_map
    from software_intake import fingerprint
    return {name: sha(checked_path(root, name)) for name in fingerprint(root, trace_map(root))}


def runtime_inputs(args):
    # --root may be another checkout; capture the adapter actually executing as well.
    paths = list(Path(__file__).parent.glob("*.py")) + list(Path(__file__).parent.glob("*.java"))
    for name in ("java", "kernel", "library"):
        value = getattr(args, name, None)
        if not value:
            raise ValueError("Change import needs the pinned SYSML_" + name.upper() + " tool")
        path = Path(value).resolve()
        paths.extend((p for p in path.rglob("*") if p.suffix in (".sysml", ".kerml"))
                     if path.is_dir() else [path])
    return {str(p.resolve()): sha(p) for p in sorted(set(paths))}


def prepare_workspace(root, destination, fingerprints):
    # The build follows documentation/SVG links as well as executable source bindings.
    names = set(fingerprints)
    names.add(MANIFEST)
    for directory in ("architecture", "docs", "scripts/architecture"):
        names.update(p.relative_to(root).as_posix() for p in (root / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts)
    for name in sorted(names):
        source = checked_path(root, name)
        target = checked_path(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # Refuse a changing input set; a copy is not a consistent snapshot merely because it succeeded.
    if inputs(root) != fingerprints or any(sha(destination / n) != h for n, h in fingerprints.items()):
        raise ValueError("Inputs changed while preparing the review workspace; review again")


def replace_sources(root, proposed, before):
    """Stage replacements first; roll back this operation if a replacement fails."""
    pending, replaced, originals = {}, [], {}
    try:
        for name, text in proposed.items():
            path = checked_path(root, name)
            if sha(path) != before[name]:
                raise ValueError("Source changed before application: " + name)
            originals[name] = path.read_bytes()
            temp = path.with_name(path.name + ".syson-return.tmp")
            with temp.open("xb") as stream:
                stream.write(text.encode("utf-8"))
            pending[name] = temp
        for name, temp in pending.items():
            path = checked_path(root, name)
            if sha(path) != before[name]:
                raise ValueError("Source changed during application: " + name)
            os.replace(temp, path)
            replaced.append(name)
    except Exception:
        for name in reversed(replaced):
            path = checked_path(root, name)
            if path.read_text(encoding="utf-8") == proposed[name]:
                path.write_bytes(originals[name])
        raise
    finally:
        for temp in pending.values():
            temp.unlink(missing_ok=True)
