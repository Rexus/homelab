#!/usr/bin/env python3
"""Seal received JSONL prefixes, or verify a restored checkpoint tree offline."""

import argparse
from datetime import datetime, timezone
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from logging_io import catalogue, create_only, digest, directory, encoded, regular, require_mount, safe_name
from logging_health import health
from logging_projection import publish, validate


def prefix(path, previous, limit):
    """Never advance over an incomplete line or silently accept rewritten history."""
    path = regular(path)
    metadata = path.stat()
    if (metadata.st_size == previous['end'] and metadata.st_mtime_ns == previous.get('mtime_ns')
            and metadata.st_ino == previous.get('inode')):
        return b'', previous
    with path.open('rb') as source:
        consumed, history = 0, hashlib.sha256()
        while consumed < previous['end']:
            part = source.read(min(1048576, previous['end'] - consumed))
            if not part:
                break
            history.update(part)
            consumed += len(part)
        if consumed != previous['end'] or history.hexdigest() != previous['sha256']:
            raise ValueError(f'Local evidence was truncated or rewritten: {path}')
        data = source.read(limit + 1)
    end = data.rfind(b'\n', 0, limit + 1) + 1
    if not end and len(data) > limit:
        raise ValueError(f'Record exceeds checkpoint chunk budget: {path}')
    data = data[:end]
    history.update(data)
    return data, {'end': previous['end'] + len(data), 'sha256': history.hexdigest(),
                  'mtime_ns': metadata.st_mtime_ns, 'inode': metadata.st_ino}


def checkpoint(config, check_mount=True):
    mount = Path(config['mount'])
    if check_mount:
        require_mount(mount, config['marker'])
    collector = safe_name(config['collector'])
    target = directory(mount / collector)
    state_path = Path(config['state'])
    directory(state_path.parent)
    with (state_path.parent / 'checkpoint.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(regular(state_path).read_text()) if state_path.exists() else {'files': {}}
        if state.get('manifest'):
            predecessor = regular(target / 'checkpoints' / state['manifest']).read_bytes()
            if digest(predecessor) + '.json' != state['manifest']:
                raise ValueError('Previous NAS checkpoint was altered')
        records = Path(config['data']) / 'records'
        source_catalogue, sources = catalogue(Path(config['data']) / 'source-catalogue.json')
        chunks, changed = [], dict(state['files'])
        budget = int(config['max_bytes'])
        if budget < 65536:
            raise ValueError('Checkpoint budget must be at least 65536 bytes')
        views = config.get('views', {})
        validate(config.get('projections', {}), sources)
        for name, group in views.items():
            safe_name(group)
            if name not in sources or sources[name].get('kind', 'security') != 'application':
                raise ValueError('Only catalogue-approved application streams can have reader views')
        for name, source in sorted(sources.items()):
            source_budget = max(65536, int(config['max_bytes']) // len(sources))
            for path in sorted((records / name).glob('*.jsonl')):
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.jsonl', path.name):
                    raise ValueError('Unexpected record filename')
                relative = f'{name}/{path.name}'
                previous = state['files'].get(relative, {'end': 0, 'sha256': digest(b'')})
                data, position = prefix(path, previous, min(budget, source_budget, 8388608))
                if not data:
                    continue
                for line in data.splitlines():
                    record = json.loads(line)
                    if record['source'] != name or int(record['source_tier']) != source['tier']:
                        raise ValueError('Record identity differs from receiver-owned catalogue')
                filename = f"{path.stem}-{previous['end']}-{position['end']}-{digest(data)}.jsonl"
                chunk = f'chunks/{name}/{filename}'
                create_only(target / chunk, data)
                publish(config, name, filename, data, previous['end'])
                if name in views:
                    group = grp.getgrnam(views[name]).gr_gid
                    view = directory(Path(config['view_root']) / name)
                    os.chown(view, -1, group)
                    os.chmod(view, 0o750)
                    create_only(view / filename, data, group=group)
                chunks.append({'path': chunk, 'sha256': digest(data), 'bytes': len(data),
                               'records': len(data.splitlines())})
                changed[relative] = position
                budget -= len(data)
                source_budget -= len(data)
                if budget < 65536 or source_budget < 65536:
                    break
            if budget < 65536:
                break
        # A quiet source still gets a checkpoint heartbeat; no intake freshness is implied.
        manifest = {'schema': 1, 'collector': collector, 'chunks': chunks, 'files': changed,
                    'previous': state.get('manifest'), 'catalogue': source_catalogue,
                    'created_at': datetime.now(timezone.utc).isoformat()}
        content = encoded(manifest)
        name = digest(content) + '.json'
        create_only(target / 'checkpoints' / name, content)
        replacement = state_path.with_suffix('.pending')
        with replacement.open('wb') as output:
            output.write(encoded({'files': changed, 'manifest': name}))
            output.flush()
            os.fsync(output.fileno())
        os.replace(replacement, state_path)
        from logging_io import sync_directory
        sync_directory(state_path.parent)
        health(config, sources, changed)
        return {'manifest': name, 'chunks': len(chunks), 'bytes': sum(item['bytes'] for item in chunks)}


def verify(root, files_list=None):
    root = Path(root)
    count = 0
    files = set()
    manifests = sorted(root.glob('*/checkpoints/*.json'))
    if not manifests:
        raise ValueError('No complete archive checkpoints found')
    for path in manifests:
        content = regular(path).read_bytes()
        if path.name != digest(content) + '.json':
            raise ValueError(f'Manifest hash mismatch: {path}')
        manifest = json.loads(content)
        files.add(str(path.absolute()))
        if manifest['schema'] != 1 or manifest['collector'] != path.parents[1].name:
            raise ValueError('Manifest owner/schema mismatch')
        previous = manifest['previous']
        if previous and (not re.fullmatch(r'[0-9a-f]{64}\.json', previous)
                         or not (path.parent / previous).is_file()):
            raise ValueError('Checkpoint history missing')
        for chunk in manifest['chunks']:
            relative = Path(chunk['path'])
            if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'chunks':
                raise ValueError('Unsafe chunk reference')
            data = regular(path.parents[1] / relative).read_bytes()
            files.add(str((path.parents[1] / relative).absolute()))
            if digest(data) != chunk['sha256'] or len(data) != chunk['bytes']:
                raise ValueError('Restored chunk integrity mismatch')
            rows = [json.loads(line) for line in data.splitlines()]
            if len(rows) != chunk['records']:
                raise ValueError('Restored record count mismatch')
            count += len(rows)
    if files_list is not None:
        # Only verified, complete, create-only files enter this backup. New files wait for the next run.
        Path(files_list).write_text('\n'.join(sorted(files)) + '\n')
    return {'manifests': len(manifests), 'referenced_records': count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    commands.add_parser('checkpoint').add_argument('--config', required=True)
    verification = commands.add_parser('verify')
    verification.add_argument('--root', required=True)
    verification.add_argument('--files-list')
    args = parser.parse_args()
    try:
        result = verify(args.root, args.files_list) if args.operation == 'verify' else checkpoint(
            json.loads(regular(args.config).read_text()))
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError) as error:
        print(f'Logging checkpoint failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
