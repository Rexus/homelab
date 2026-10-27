#!/usr/bin/env python3
"""Read NetBox's retained change ledger into create-only local forwarding files."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import ssl
import urllib.parse
import urllib.request


FIELDS = ('id', 'time', 'user_name', 'request_id', 'action', 'changed_object_type',
          'changed_object_id', 'related_object_type', 'related_object_id',
          'object_repr', 'prechange_data', 'postchange_data', 'message')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('NetBox audit endpoint redirects are forbidden')


def action_value(action):
    if isinstance(action, dict):
        action = action.get('value')
    if not isinstance(action, str) or not action:
        raise ValueError('NetBox audit action must have a nonempty stable value')
    return action


def write_once(path, data, *, normalize_action=False):
    if path.is_symlink():
        raise ValueError('Audit file symlink refused')
    if path.exists():
        existing = path.read_bytes()
        if existing != data and normalize_action:
            # Older ledgers kept display labels; compare values without rewriting original evidence.
            previous = json.loads(existing)
            previous['change']['action'] = action_value(previous['change'].get('action'))
            existing = (json.dumps(previous, sort_keys=True, separators=(',', ':')) + '\n').encode()
        if existing != data:
            raise ValueError('Previously exported audit event changed; investigate original history')
        return False
    # Link a fully flushed temporary file: a crash cannot publish a partial event.
    pending = path.with_suffix('.pending')
    with pending.open('wb') as output:
        os.chmod(pending, 0o640)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.link(pending, path)
    pending.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def collect(config, fetch):
    state = Path(config['state'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    events = state / 'events'
    events.mkdir(exist_ok=True, mode=0o750)
    with (state / 'poll.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identity = state / 'instance.json'
        write_once(identity, (json.dumps({'instance': config['instance'], 'endpoint': config['endpoint']},
                                        sort_keys=True) + '\n').encode())
        offset, previous, added = 0, 0, 0
        # Re-read retained history, not an ID high-water mark: IDs may commit out of order.
        while True:
            page = fetch(offset)
            rows = page['results']
            if int(page['count']) > config['max_records'] or offset + len(rows) > config['max_records']:
                raise ValueError('Retained audit history exceeds the reviewed polling budget')
            if not rows and page.get('next'):
                raise ValueError('Empty nonfinal NetBox audit page')
            for row in rows:
                number = row['id']
                if type(number) is not int or number <= previous:
                    raise ValueError('NetBox must honor ordering=id with strictly increasing IDs')
                previous = number
                selected = {field: row[field] for field in FIELDS if field in row}
                selected['action'] = action_value(selected.get('action'))
                event = {'instance': config['instance'], 'event_id': f"{config['instance']}:{number}",
                         'kind': 'netbox-object-change', 'change': selected}
                data = (json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n').encode()
                added += write_once(events / f'{number:020d}.jsonl', data, normalize_action=True)
            if not page.get('next'):
                break
            offset += len(rows)
        return {'exported': added, 'scanned': offset + len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    endpoint = urllib.parse.urlsplit(config['endpoint'])
    if endpoint.scheme != 'https' or endpoint.query or endpoint.fragment or endpoint.username:
        raise ValueError('Use a verified HTTPS NetBox API endpoint without query or credentials')
    credential = Path(os.environ['CREDENTIALS_DIRECTORY']) / 'token'
    token = credential.read_text().strip()
    if not token or '\n' in token or config['auth_scheme'] not in ('Bearer', 'Token'):
        raise ValueError('Invalid separately provisioned NetBox read token')
    context = ssl.create_default_context(cafile=config['ca_file'])
    client = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=context))

    def fetch(offset):
        query = urllib.parse.urlencode({'ordering': 'id', 'limit': 100, 'offset': offset})
        request = urllib.request.Request(config['endpoint'] + '?' + query,
                                         headers={'Authorization': config['auth_scheme'] + ' ' + token,
                                                  'Accept': 'application/json'})
        with client.open(request, timeout=30) as response:
            content = response.read(16777217)
        if len(content) > 16777216:
            raise ValueError('NetBox audit response exceeds 16 MiB per page')
        return json.loads(content)

    print(json.dumps(collect(config, fetch), sort_keys=True))


if __name__ == '__main__':
    main()
