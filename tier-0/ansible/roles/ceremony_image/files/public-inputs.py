#!/usr/bin/env python3
"""Validate public ceremony bundles and bind one immutable live-build revision."""

import hashlib
import json
from pathlib import Path
import re
import sys


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular_files(root):
    paths = list(root.rglob('*'))
    if root.is_symlink() or any(path.is_symlink() for path in paths):
        raise ValueError('Public input trees must not contain symlinks.')
    if any(not path.is_file() and not path.is_dir() for path in paths):
        raise ValueError('Public input trees must contain only regular files/directories.')
    return sorted((path for path in paths if path.is_file()), key=lambda path: path.as_posix())


def validate_kit(kit, accepted, repository):
    if not re.fullmatch('[a-f0-9]{64}', accepted):
        raise ValueError('Set ceremony_build_orca_kit_sha256 to the accepted manifest SHA256.')
    files = regular_files(kit)
    manifest = kit / 'manifest.sha256'
    if digest(manifest) != accepted:
        raise ValueError('The public ORCA kit manifest differs from its accepted SHA256.')
    listed = {}
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_./-]+)', line)
        if not match or '..' in Path(match[2]).parts or match[2].startswith('/') or match[2] in listed:
            raise ValueError('Unsafe or duplicate kit manifest entry.')
        listed[match[2]] = match[1]
    actual = {path.relative_to(kit).as_posix() for path in files}
    if actual != set(listed) | {'manifest.sha256', 'templates/offline-root/orca.conf'}:
        raise ValueError('Unexpected/unmanifested content: recreate the public kit with offline-root.sh bundle.')
    for name, expected in listed.items():
        if digest(kit / name) != expected:
            raise ValueError('Kit file checksum mismatch: ' + name)
    fixed = {'scripts/offline-root.sh', 'source.txt', 'clca/LICENSE',
             'templates/offline-root/orca.conf.example', 'templates/offline-root/clca.cfg.example',
             'templates/offline-root/openssl.cnf.example'}
    if not fixed.issubset(listed) or any(
        name not in fixed and not name.startswith(('clca/bin/', 'clca/lib/')) for name in listed
    ):
        raise ValueError('Only the native clca bundle and known public policy files may enter the image.')
    for name in fixed - {'source.txt', 'clca/LICENSE'}:
        if digest(kit / name) != digest(repository / name):
            raise ValueError('Kit recipe differs from this reviewed checkout; regenerate the bundle: ' + name)
    source = (repository / 'scripts/offline-root.sh').read_text()
    pinned = re.search(r'CLCA_PAYLOAD_SHA256=([a-f0-9]{64})', source)[1]
    native = sorted((path for path in files if path.relative_to(kit).as_posix().startswith(('clca/bin/', 'clca/lib/'))),
                    key=lambda path: path.relative_to(kit).as_posix())
    native.append(kit / 'clca/LICENSE')
    payload = ''.join(f'{digest(path)}  {path.relative_to(kit / "clca").as_posix()}\n' for path in native)
    if hashlib.sha256(payload.encode()).hexdigest() != pinned:
        raise ValueError('Native clca payload does not match offline-root.sh\'s audited pin.')
    fields = {}
    allowed = {'ORCA_INSTANCE', 'ORCA_TOOLS', 'ORCA_TRANSFER', 'ORCA_BACKUP', 'ORCA_ORGANIZATION',
               'ORCA_COMMON_NAME', 'ORCA_PUBLICATION_URL', 'ORCA_CLCA_REVISION', 'ORCA_BACKUP_RECIPIENT',
               'ORCA_ROOT_DAYS', 'ORCA_ISSUER_DAYS', 'ORCA_CRL_DAYS', 'ORCA_ROOT_FINGERPRINT'}
    for line in (kit / 'templates/offline-root/orca.conf').read_text().splitlines():
        match = re.fullmatch(r'(ORCA_[A-Z_]+)="([^"\n$`\\]*)"', line)
        if not match or match[1] not in allowed or match[1] in fields or len(match[2]) > 2048:
            raise ValueError('Only known literal public ORCA settings are allowed; no secrets or shell input.')
        fields[match[1]] = match[2]
    if fields.keys() != allowed or not re.fullmatch(r'age1[0-9a-z]+', fields['ORCA_BACKUP_RECIPIENT']):
        raise ValueError('Incomplete public ORCA policy or missing age public backup recipient.')
    return {'manifest_sha256': accepted, 'public_policy_sha256': digest(kit / 'templates/offline-root/orca.conf'),
            'files': sorted(actual)}


def seal(workspace):
    paths = [workspace / name for name in ('recipe.json', 'build-image.sh', 'public-inputs.py')]
    for directory in ('includes.chroot', 'hooks/live', 'package-lists', 'packages.chroot'):
        paths += regular_files(workspace / 'build/config' / directory)
    record = {path.relative_to(workspace).as_posix(): digest(path) for path in paths}
    value = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    binding = workspace / 'inputs.sha256'
    if binding.exists() and binding.read_text().strip() != value:
        raise ValueError('This revision already binds different inputs. Select a NEW ceremony_build_revision.')
    if not binding.exists():
        binding.write_text(value + '\n')
    return value


def main():
    if sys.argv[1] == 'kit':
        result = validate_kit(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
    elif sys.argv[1] == 'seal':
        result = {'inputs_sha256': seal(Path(sys.argv[2]))}
    else:
        raise ValueError('Expected kit or seal action.')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, IndexError, KeyError) as error:
        sys.exit(str(error))
