"""Boundary checks and durable receipts; native CLIs own backup formats and encryption."""

import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(argv, env=None, timeout=3600, input_data=None):
    result = subprocess.run(argv, env=env, input=input_data, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        # Product output can contain credentials, endpoints or sensitive filenames.
        raise RuntimeError(f'{Path(argv[0]).name} operation failed (exit {result.returncode})')
    return result.stdout


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == 'posix':
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def canonical(path):
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.resolve() != candidate or not candidate.exists():
        raise ValueError('expected an existing absolute path without symlinks or traversal')
    if '\n' in str(candidate) or '\r' in str(candidate):
        raise ValueError('line breaks are not valid backup paths')
    return candidate


def selected_inputs(entries, mounts=None):
    if not entries:
        raise ValueError('explicit local recovery inputs are required')
    selected = []
    for entry in entries:
        repo = canonical(entry['repo'])
        if mounts is not None and not any(repo.is_relative_to(mount) for mount in mounts):
            raise ValueError('input repository is outside the approved read-only transport mounts')
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('select a bounded repo-relative ignored path')
        path = canonical(repo / relative)
        if not path.is_relative_to(repo) or path == repo:
            raise ValueError('input escapes its repository')
        git = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c',
               'core.hooksPath=/dev/null', '-C', str(repo)]
        root = run(git + ['rev-parse', '--show-toplevel']).decode().strip()
        if Path(root).resolve() != repo:
            raise ValueError('repo must be a Git working tree root')
        tracked = run(git + ['ls-files', '--', relative.as_posix()])
        if tracked.strip():
            raise ValueError('recovery selections must contain only ignored local inputs')
        run(git + ['check-ignore', '--quiet', '--', relative.as_posix()])
        selected.append(path)
    return selected


def require_mount(path, readonly=False):
    path = canonical(path)
    result = json.loads(run(['findmnt', '--json', '--mountpoint', str(path),
                             '--output', 'TARGET,OPTIONS']))['filesystems']
    if len(result) != 1 or Path(result[0]['target']) != path:
        raise ValueError('expected the commissioned mountpoint')
    if readonly and 'ro' not in result[0]['options'].split(','):
        raise ValueError('media mount must be read-only')
    return path


def require_input_sources(sources):
    if not sources:
        raise ValueError('original input-custodian transport mounts are required')
    mounts = []
    for source in sources:
        mount = require_mount(source['mount'], readonly=True)
        if (mount / '.control-backup-source').read_text().strip() != source['marker']:
            raise ValueError('wrong original-input source marker')
        mounts.append(mount)
    return mounts


@contextmanager
def job_lock(directory):
    # Kernel-owned flock is released on crash; manual CLI and systemd share this guard.
    import fcntl
    with (canonical(directory) / 'job.lock').open('a') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def restic_environment(config):
    env = {key: value for key, value in os.environ.items() if not key.startswith('RESTIC_')}
    env.update(RESTIC_REPOSITORY=config['repository'], RESTIC_PASSWORD_FILE=config['password_file'],
               RESTIC_CACHE_DIR=str(Path(config['directory']) / 'cache'))
    return env


def require_repository(config, env):
    require_mount(config['repository'])
    found = json.loads(run(['restic', 'cat', 'config'], env))
    if found['id'] != config['repository_id']:
        raise ValueError('mounted restic repository identity differs from commissioned custody')
