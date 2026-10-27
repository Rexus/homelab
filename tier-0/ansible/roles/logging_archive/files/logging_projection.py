"""Create explicitly approved search copies without granting access to evidence."""

import grp
import json
import os
from pathlib import Path

from logging_io import create_only, digest, directory, encoded, safe_name


FIELDS = {'source', 'source_tier', 'transport', 'received_at', 'reported_at',
          'reported_host', 'message', 'raw', 'peer_ip', 'peer_cn', 'schema'}


def validate(projections, sources):
    for scope, policy in projections.items():
        safe_name(scope)
        safe_name(policy['group'])
        if not policy.get('approval') or not policy.get('sources') or not policy.get('fields'):
            raise ValueError('Search copies need an approval, explicit sources and field allowlist')
        if set(policy['sources']) - sources.keys():
            raise ValueError('Search copy source is not in the receiver-owned catalogue')
        if set(policy['fields']) - FIELDS:
            raise ValueError('Unknown search-copy field')
        if {'raw', 'message'} & set(policy['fields']) and not policy.get('content_approved', False):
            raise ValueError('Message/raw export requires explicit sensitive-content approval')


def publish(config, source, filename, data, offset):
    """Stable IDs survive retries; changing a policy requires a new scope name."""
    for scope, policy in config.get('projections', {}).items():
        if source not in policy['sources']:
            continue
        rows, position = [], offset
        policy_hash = digest(encoded(policy))
        for line in data.splitlines(keepends=True):
            record = json.loads(line)
            selected = {field: record[field] for field in policy['fields'] if field in record}
            identity = encoded([config['collector'], source, filename[:10], position, digest(line)])
            rows.append(encoded({'event_id': digest(identity), 'scope': scope,
                                 'policy_sha256': policy_hash, 'record': selected}))
            position += len(line)
        group = grp.getgrnam(policy['group']).gr_gid
        target = directory(Path(config['projection_root']) / scope)
        os.chown(target, -1, group)
        os.chmod(target, 0o750)
        create_only(target / '.policy.json', encoded({'policy_sha256': policy_hash}), group=group)
        create_only(target / filename, b''.join(rows), group=group)
