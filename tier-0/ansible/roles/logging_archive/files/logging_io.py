"""Small filesystem primitives for portable, create-only logging checkpoints."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,62}', value):
        raise ValueError('Invalid fixed logging identity')
    return value


def regular(path):
    path = Path(path)
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f'Symlink is not evidence: {parent}')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f'Expected regular evidence file: {path}')
    return path


def directory(path):
    path = Path(path)
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f'Symlink directory refused: {parent}')
    path.mkdir(parents=True, exist_ok=True, mode=0o750)
    if not path.is_dir():
        raise ValueError(f'Expected directory: {path}')
    return path


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_only(path, data, group=None):
    """Existing identical content is a retry; partial/altered content fails closed."""
    path = Path(path)
    directory(path.parent)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640)
    except FileExistsError:
        if regular(path).read_bytes() != data:
            raise ValueError(f'Archive collision; preserve and investigate: {path}') from None
        return
    with os.fdopen(descriptor, 'wb') as output:
        if group is not None:
            os.fchown(output.fileno(), -1, group)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    sync_directory(path.parent)


def require_mount(path, marker):
    path = Path(path)
    if not path.is_absolute() or not os.path.ismount(path):
        raise ValueError(f'Archive mount missing: {path}')
    if regular(path / '.logging-target').read_text().strip() != marker:
        raise ValueError('Wrong independently commissioned archive target')


def catalogue(path):
    value = json.loads(regular(path).read_text())
    sources = value['tls_sources'] + value['legacy_udp_sources']
    names = [safe_name(source['name']) for source in sources]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate catalogue identities')
    for source in sources:
        if source['tier'] not in (0, 1, 2):
            raise ValueError('Invalid source tier')
        if source.get('kind', 'security') not in ('security', 'application'):
            raise ValueError('Unknown source classification')
    return value, {source['name']: source for source in sources}
