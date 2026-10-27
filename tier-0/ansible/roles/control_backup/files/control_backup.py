#!/usr/bin/env python3
"""Create-only snapshot transport, selected recovery inputs and native restic copies."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import uuid

from control_backup_io import (atomic_json, canonical, digest, job_lock, require_input_sources,
                               require_mount, require_repository, restic_environment, run, selected_inputs)
from vault_snapshot import save


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def backup(config):
    directory = canonical(config['directory'])
    env = restic_environment(config)
    require_repository(config, env)
    mounts = require_input_sources(config['input_sources'])
    sources = selected_inputs(config['inputs'], mounts)
    media = config['media']
    if media['enabled']:
        mount = require_mount(media['mount'], readonly=True)
        if (mount / '.control-backup-source').read_text().strip() != media['marker']:
            raise ValueError('wrong NetBox media source marker')
        sources.append(mount)
    repository = canonical(config['repository'])
    for source in [*sources, *mounts, directory]:
        if source.is_relative_to(repository) or repository.is_relative_to(source):
            raise ValueError('backup source and repository must be disjoint')
    for source in sources:
        if source.is_relative_to(directory) or directory.is_relative_to(source):
            raise ValueError('selected inputs must be disjoint from snapshot staging')

    # An interrupted run stays private and unaccepted; no previous set is overwritten.
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex
    attempt = directory / ('.pending-' + identifier)
    attempt.mkdir(mode=0o700)
    snapshot = attempt / 'vault.snap'
    save(config['vault'], snapshot)
    with snapshot.open('rb+') as stream:
        os.fsync(stream.fileno())
    manifest = {'schema': 1, 'created_at': timestamp(), 'vault_sha256': digest(snapshot),
                'inputs': [str(source) for source in sources], 'media_selected': media['enabled'],
                'input_transports': [{'source': source['source'], 'mount': source['mount']}
                                     for source in config['input_sources']]}
    atomic_json(attempt / 'manifest.json', manifest)
    published = directory / identifier
    attempt.rename(published)
    if digest(published / 'vault.snap') != manifest['vault_sha256']:
        raise ValueError('published snapshot digest mismatch')
    paths = [str(published), *map(str, sources)]
    file_list = published / 'files.txt'
    file_list.write_text('\n'.join(paths) + '\n', encoding='utf-8')
    output = run(['restic', 'backup', '--json', '--tag', 'control-recovery',
                  '--files-from-verbatim', str(file_list)], env, timeout=18000)
    summaries = [item for line in output.splitlines()
                 if (item := json.loads(line)).get('message_type') == 'summary']
    if not summaries or not summaries[-1].get('snapshot_id'):
        raise ValueError('restic did not report a complete snapshot')
    run(['restic', 'check'], env, timeout=18000)
    if digest(published / 'vault.snap') != manifest['vault_sha256']:
        raise ValueError('snapshot changed during encrypted backup')
    run(['curl', '--fail', '--silent', '--show-error', '--max-time', '20',
         '--config', config['health_config']], timeout=30)
    receipt = {'ok': True, 'completed_at': timestamp(), 'set': identifier,
               'vault_sha256': manifest['vault_sha256'],
               'restic_snapshot': summaries[-1]['snapshot_id'],
               'manifest_sha256': digest(published / 'manifest.json')}
    atomic_json(directory / 'last-success.json', receipt)
    atomic_json(directory / 'health.json', receipt)
    return receipt


def execute(config):
    try:
        backup(config)
    except Exception:
        atomic_json(Path(config['directory']) / 'health.json', {'ok': False, 'failed_at': timestamp()})
        # Do not log product errors or local input/credential paths.
        print('Control backup failed; inspect independent custody and native service diagnostics.', file=sys.stderr)
        return 1
    return 0


def main():
    os.umask(0o077)
    config = json.loads(Path(sys.argv[1]).read_text())
    try:
        with job_lock(config['directory']):
            return execute(config)
    except BlockingIOError:
        print('Control backup already running; concurrent invocation rejected.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
