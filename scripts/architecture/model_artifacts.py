"""Validate source-bound generated deliverables without cross-platform font/layout drift."""

import hashlib


def artifact_hash(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def seal_outputs(outputs):
    return {path.as_posix(): artifact_hash(value) for path, value in sorted(outputs.items())}


def verify_outputs(root, snapshot):
    expected = snapshot.get('outputs_sha256')
    if not expected:
        raise ValueError('Model build has no generated-artifact manifest; rebuild and review')
    changed = []
    for relative, digest in expected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            changed.append(relative)
        elif artifact_hash(path.read_text(encoding='utf-8')) != digest:
            changed.append(relative)
    if changed:
        raise ValueError('Changed or missing generated artifacts: ' + ', '.join(changed))
