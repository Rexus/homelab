"""Health gates for a bounded-loss checkpoint, not a transport acknowledgement."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from logging_io import regular


def received_age(row, now):
    timestamp = datetime.fromisoformat(row['received_at'])
    if timestamp.tzinfo is None:
        raise ValueError('Receiver timestamp lacks timezone')
    return (now - timestamp).total_seconds()


def health(config, sources, positions):
    now = datetime.now(timezone.utc)
    maximum_age = int(config.get('max_lag_seconds', 300))
    minimum_free = int(config.get('min_free_bytes', 0))
    for path in (config['data'], config['mount']):
        if shutil.disk_usage(path).free < minimum_free:
            raise ValueError(f'Logging storage headroom below threshold: {path}')
    for name in config.get('required_sources', []):
        if name not in sources:
            raise ValueError(f'Required source not catalogued: {name}')
        files = sorted((Path(config['data']) / 'records' / name).glob('*.jsonl'))
        if not files:
            raise ValueError(f'Required source has no records: {name}')
        with regular(files[-1]).open('rb') as source:
            source.seek(max(0, files[-1].stat().st_size - 1048576))
            lines = source.read().split(b'\n')
            if len(lines) < 2 or not lines[-2]:
                raise ValueError(f'Required source has no complete recent event: {name}')
            age = received_age(json.loads(lines[-2]), now)
        if age > maximum_age or age < -60:
            raise ValueError(f'Required source stale or receiver clock moved: {name}')
    for name in sources:
        for path in (Path(config['data']) / 'records' / name).glob('*.jsonl'):
            with regular(path).open('rb') as source:
                source.seek(positions.get(f'{name}/{path.name}', {}).get('end', 0))
                line = source.readline(1048576)
            if line.endswith(b'\n') and received_age(json.loads(line), now) > maximum_age:
                raise ValueError(f'NAS checkpoint backlog exceeds the declared window: {name}')
