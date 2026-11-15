#!/usr/bin/env python3
"""Fence restored GitLab CE through its native v4 API after native backup restore.

Input JSON contains workspace, plan_sha256, namespace_uid and product. Product
contains name, namespace, backup_id and gitlab_recovery with api_url, ca_file,
ca_sha256, admin_headers_file and admin_headers_sha256. Paths are workspace-relative.
Optional timeout_seconds=30, cancel_attempts=30 and poll_seconds=2 bound requests.
The retained headers file is mode 0600 and contains one PRIVATE-TOKEN or Bearer
Authorization header for a trusted instance administrator. The private receipt
retains API-visible original intent. GitLab never returns webhook secret tokens.

The caller starts only the isolated restored webservice. Sidekiq and runner
workloads stay stopped. HTTP 200 on cancellation does not prove completion.
Unsettled pipeline/job states block cutover, including when Sidekiq is required.
This helper never starts workers, plays jobs, retries CI or restores active flags.
Trusted administrators can change the resulting fence. A new accepted source must
explicitly authorize reopening delivery. --operation verify performs only GETs.
--operation pause-triggers verifies trigger settings before a caller-controlled,
network-isolated Sidekiq drain. It never records completed execution fencing.

Native API references (Free / Self-Managed)
https://docs.gitlab.com/api/runners/
https://docs.gitlab.com/api/pipeline_schedules/
https://docs.gitlab.com/api/project_webhooks/
https://docs.gitlab.com/api/pipelines/
https://docs.gitlab.com/api/jobs/
https://github.com/gitlabhq/gitlabhq/blob/v18.6.0/lib/api/ci/pipelines.rb
https://github.com/gitlabhq/gitlabhq/blob/master/app/services/ci/cancel_pipeline_service.rb
"""

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit


TERMINAL = {'success', 'failed', 'canceled', 'skipped'}
HOOK_EVENTS = {
    'push_events', 'tag_push_events', 'issues_events', 'confidential_issues_events',
    'merge_requests_events', 'note_events', 'confidential_note_events', 'job_events',
    'pipeline_events', 'wiki_page_events', 'deployment_events', 'releases_events',
    'feature_flag_events', 'emoji_events', 'resource_access_token_events',
    'resource_deploy_token_events', 'milestone_events', 'duo_flow_callback_enabled',
}


class FenceError(Exception):
    """Safe diagnostics contain no response bodies, URLs or credential values."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()


def checked_file(path, expected=None, private=True):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise FenceError('Select canonical regular custody files without symlinks.')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise FenceError('Recovery input must be a regular file.')
    if private and (stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid()):
        raise FenceError('Private recovery input must be owned by this operator with mode 0600.')
    data = path.read_bytes()
    if expected is not None and (not re.fullmatch('[a-f0-9]{64}', expected) or digest(data) != expected):
        raise FenceError('Retained GitLab custody checksum changed.')
    return data


def local_path(workspace, value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise FenceError('Custody paths must be relative to the recovery workspace.')
    path = workspace / path
    if path.resolve() != path:
        raise FenceError('Custody paths must not traverse symlinks.')
    return path


class GitLab:
    """Direct HTTPS transport deliberately has no proxy or redirect machinery."""

    def __init__(self, url, ca, headers, timeout):
        self.url = urlsplit(url)
        if (self.url.scheme != 'https' or not self.url.hostname or self.url.username is not None or
                self.url.password is not None or self.url.query or self.url.fragment or
                self.url.path not in ('', '/') or not 1 <= (self.url.port or 443) <= 65535):
            raise FenceError('Select the verified HTTPS GitLab origin without URL credentials or a path.')
        self.context = ssl.create_default_context(cafile=str(ca))
        self.headers = headers
        self.timeout = timeout

    def request(self, method, path, data=None):
        connection = http.client.HTTPSConnection(self.url.hostname, self.url.port or 443,
                                               context=self.context, timeout=self.timeout)
        headers = dict(self.headers, Accept='application/json')
        body = None
        if data is not None:
            body = canonical(data)
            headers['Content-Type'] = 'application/json'
        try:
            connection.request(method, '/api/v4' + path, body=body, headers=headers)
            response = connection.getresponse()
            if response.status != 200:
                raise FenceError(f'GitLab native {method} returned HTTP {response.status}. Keep recovery isolated.')
            raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise FenceError('GitLab API response exceeded the bounded JSON page size.')
            return json.loads(raw), response.getheader('X-Next-Page')
        except (OSError, http.client.HTTPException, ValueError):
            raise FenceError('GitLab verified HTTPS request or JSON parsing failed. Keep recovery isolated.') from None
        finally:
            connection.close()

    def get(self, path):
        result, _ = self.request('GET', path)
        if not isinstance(result, dict):
            raise FenceError('GitLab detail response must be a JSON object.')
        return result

    def pages(self, path, **query):
        page, records, seen = 1, [], set()
        while page <= 100000:
            result, next_page = self.request('GET', path + '?' + urlencode(dict(query, page=page, per_page=100)))
            if not isinstance(result, list):
                raise FenceError('GitLab inventory response must be a JSON array.')
            for item in result:
                if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] < 1:
                    raise FenceError('GitLab returned an invalid inventory identity.')
                if item['id'] in seen:
                    raise FenceError('GitLab pagination repeated an identity. Keep recovery isolated.')
                seen.add(item['id'])
                records.append(item)
            if next_page == '' or not result:
                return records
            if next_page is not None and next_page != str(page + 1):
                raise FenceError('GitLab pagination must advance to the next numeric page.')
            # Some GitLab installations omit pagination headers. Read through an empty page.
            page += 1
        raise FenceError('GitLab pagination exceeded its safety bound.')


def inventory(api):
    records = {}
    for runner in api.pages('/runners/all'):
        path = f"/runners/{runner['id']}"
        records[path] = api.get(path)
    projects = api.pages('/projects', order_by='id', sort='asc')
    for project in projects:
        prefix = f"/projects/{project['id']}"
        records[prefix] = project
        for collection in ('pipeline_schedules', 'hooks'):
            for item in api.pages(prefix + '/' + collection):
                path = prefix + '/' + collection + '/' + str(item['id'])
                records[path] = api.get(path)
        pipelines = {item['id']: item for item in api.pages(prefix + '/pipelines', order_by='id', sort='asc')}
        # GitLab excludes child pipelines from the default list.
        pipelines.update({item['id']: item for item in api.pages(prefix + '/pipelines', source='parent_pipeline',
                                                               order_by='id', sort='asc')})
        for identity in pipelines:
            path = prefix + '/pipelines/' + str(identity)
            records[path] = api.get(path)
            for collection in ('jobs', 'bridges'):
                query = {'include_retried': 'true'} if collection == 'jobs' else {}
                for item in api.pages(path + '/' + collection, **query):
                    records[path + '/' + collection + '/' + str(item['id'])] = item
    # System hooks have unconditional lifecycle events and no complete native pause flag.
    # Preserve them for review, then reject that unsupported outbound-trigger scope.
    for item in api.pages('/hooks'):
        records['/hooks/' + str(item['id'])] = item
    return records


def kind(path):
    parts = path.strip('/').split('/')
    if parts[0] == 'runners':
        return 'runner'
    if parts[0] == 'hooks':
        return 'system-hook'
    if len(parts) == 2:
        return 'project'
    return parts[2] if len(parts) == 4 else parts[4]


def hook_flags(value):
    flags = {name: value[name] for name in HOOK_EVENTS if name in value}
    unknown = [name for name, item in value.items() if name.endswith('_events') and name not in HOOK_EVENTS and item]
    if unknown or not flags or any(type(item) is not bool for item in flags.values()):
        raise FenceError('GitLab returned unsupported webhook event flags. Keep recovery isolated.')
    return flags


def validate_inventory(records):
    for path, value in records.items():
        resource = kind(path)
        if resource == 'system-hook':
            raise FenceError('System hooks have unconditional events and no native complete pause flag. '
                             'Keep outbound delivery isolated and resolve system hooks explicitly before cutover.')
        if resource in ('runner', 'pipeline_schedules'):
            flag = 'paused' if resource == 'runner' else 'active'
            if type(value.get(flag)) is not bool:
                raise FenceError('GitLab omitted a native runner or schedule state.')
        if resource == 'hooks':
            hook_flags(value)
            if not isinstance(value.get('url'), str) or not value['url']:
                raise FenceError('Native project webhook update requires its retained URL.')
        if resource in ('pipelines', 'jobs', 'bridges') and not isinstance(value.get('status'), str):
            raise FenceError('GitLab omitted an actual pipeline or job state.')


def paused(records):
    for path, value in records.items():
        resource = kind(path)
        if resource == 'runner' and value['paused'] is not True:
            return False
        if resource == 'pipeline_schedules' and value['active'] is not False:
            return False
        if resource == 'hooks' and any(hook_flags(value).values()):
            return False
    return True


def terminal(records):
    return all(value['status'] in TERMINAL for path, value in records.items()
               if kind(path) in ('pipelines', 'jobs', 'bridges'))


def save_receipt(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix='.gitlab-fence-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(canonical(value) + b'\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fence(api, path, binding, options, operation='fence'):
    """A complete fresh inventory is required even when a receipt already exists."""
    receipt = {'version': 1, 'binding': binding, 'original': {}, 'verified': False}
    if path.exists():
        receipt = json.loads(checked_file(path))
        if receipt.get('version') != 1 or receipt.get('binding') != binding:
            raise FenceError('GitLab recovery target or accepted custody changed. Refuse receipt reuse.')
    elif operation == 'verify':
        raise FenceError('Completed GitLab fencing receipt is required for a read-only audit.')
    actor = api.get('/user')
    if actor.get('is_admin') is not True:
        raise FenceError('GitLab fencing requires the retained trusted instance administrator.')
    version = api.get('/version').get('version', '')
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-ce)?', version)
    if not match or not (17, 0) <= tuple(map(int, match.groups()[:2])) < (19, 6):
        raise FenceError('This instance-wide CE fence supports GitLab 17.0 through 19.5. '
                         '19.6 changes system-hook scope to the current organization.')
    records = inventory(api)
    if operation != 'verify':
        receipt['verified'] = False
        for key, value in records.items():
            receipt['original'].setdefault(key, value)
        save_receipt(path, receipt)  # Persist original intent before the first API write.
    validate_inventory(records)
    if operation == 'verify':
        if not receipt.get('verified') or set(records) != set(receipt['observed']) or not paused(records) or not terminal(records):
            raise FenceError('Live GitLab triggers or executions differ from the completed recovery fence.')
        return {'changed': False, 'verified_resources': len(records)}
    writes = 0
    for key, value in records.items():
        resource = kind(key)
        change = None
        if resource == 'runner' and not value['paused']:
            change = {'paused': True}
        elif resource == 'pipeline_schedules' and value['active']:
            change = {'active': False}
        elif resource == 'hooks' and any(hook_flags(value).values()):
            change = dict.fromkeys(hook_flags(value), False)
            change['url'] = value['url']
        if change is not None:
            api.request('PUT', key, change)
            writes += 1
    stopped = inventory(api)
    validate_inventory(stopped)
    if set(stopped) != set(records) or not paused(stopped):
        raise FenceError('GitLab runner, schedule or webhook fence was not observed. Keep workers stopped.')
    if operation == 'pause-triggers':
        return {'changed': writes > 0, 'verified_trigger_resources': len(stopped), 'executions_verified': False}
    pending_parents = {key.rsplit('/', 2)[0] for key, value in stopped.items()
                       if kind(key) in ('jobs', 'bridges') and value['status'] not in TERMINAL}
    for key, value in stopped.items():
        if kind(key) == 'pipelines' and (value['status'] not in TERMINAL or key in pending_parents):
            api.request('POST', key + '/cancel')
            writes += 1
    # Optional manual/delayed jobs can remain on an otherwise terminal pipeline.
    pending = inventory(api)
    for key, value in pending.items():
        if kind(key) == 'jobs' and value['status'] not in TERMINAL:
            parts = key.strip('/').split('/')
            force = {'force': True} if value['status'] == 'canceling' and tuple(map(int, match.groups()[:2])) >= (17, 11) else None
            api.request('POST', f'/projects/{parts[1]}/jobs/{parts[5]}/cancel', force)
            writes += 1
    for attempt in range(options['cancel_attempts']):
        observed = inventory(api)
        validate_inventory(observed)
        if set(observed) != set(records) or not paused(observed):
            raise FenceError('GitLab inventory or trigger states changed during cancellation.')
        if terminal(observed):
            receipt.update(verified=True, observed={key: value.get('status') for key, value in observed.items()})
            save_receipt(path, receipt)
            return {'changed': writes > 0, 'verified_resources': len(observed)}
        if attempt + 1 < options['cancel_attempts']:
            time.sleep(options['poll_seconds'])
    raise FenceError('GitLab pipelines or jobs remain nonterminal after native cancellation. '
                     'Sidekiq may be required. Keep recovery isolated, workers stopped and the private receipt retained.')


def run(config, operation='fence'):
    workspace = Path(config['workspace'])
    if not workspace.is_absolute() or workspace.resolve() != workspace:
        raise FenceError('Select the canonical recovery workspace.')
    product = config['product']
    if (not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,62}', product['name']) or
            not re.fullmatch('[a-f0-9]{64}', config['plan_sha256']) or
            not config['namespace_uid'] or not product['backup_id']):
        raise FenceError('Bind GitLab fencing to the accepted plan, product, backup and actual namespace UID.')
    options = dict(timeout_seconds=30, cancel_attempts=30, poll_seconds=2)
    options.update(product['gitlab_recovery'])
    for name, minimum, maximum in [('timeout_seconds', 1, 120), ('cancel_attempts', 1, 120), ('poll_seconds', 0, 60)]:
        if type(options[name]) is not int or not minimum <= options[name] <= maximum:
            raise FenceError('GitLab request and polling limits must be bounded integers.')
    ca = local_path(workspace, options['ca_file'])
    checked_file(ca, options['ca_sha256'], private=False)
    headers = json.loads(checked_file(local_path(workspace, options['admin_headers_file']),
                                      options['admin_headers_sha256']))
    if (not isinstance(headers, dict) or len(headers) != 1 or
            not all(isinstance(name, str) and name.lower() in ('private-token', 'authorization') and
                    isinstance(value, str) and value and '\r' not in value and '\n' not in value and
                    (name.lower() != 'authorization' or value.startswith('Bearer '))
                    for name, value in headers.items())):
        raise FenceError('Select one retained administrator PRIVATE-TOKEN or Bearer header without impersonation.')
    api = GitLab(options['api_url'], ca, headers, options['timeout_seconds'])
    directory = workspace / 'receipts'
    info = directory.stat()
    if directory.resolve() != directory or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
        raise FenceError('Private GitLab receipts require an operator-owned canonical directory with mode 0700.')
    path = directory / (product['name'] + '-gitlab-fence.json')
    binding = {'plan_sha256': config['plan_sha256'], 'namespace_uid': config['namespace_uid'],
               'product': product['name'], 'namespace': product['namespace'], 'backup_id': product['backup_id'],
               'inputs_sha256': digest(canonical(product['gitlab_recovery']))}
    import fcntl
    lock_flags = os.O_RDONLY if operation == 'verify' else os.O_CREAT | os.O_RDWR
    lock = os.open(str(path) + '.lock', lock_flags | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fence(api, path, binding, options, operation)
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--operation', choices=('pause-triggers', 'fence', 'verify'), default='fence')
    args = parser.parse_args()
    try:
        result = run(json.loads(checked_file(args.config)), args.operation)
    except FenceError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print('GitLab fencing input or private receipt is invalid. Keep recovery isolated.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
