#!/usr/bin/env python3
"""Restore Shamir Raft through native Vault APIs and retained control_backup files.

Adapter contract (product.kind = vault-raft, tier = 0)
  data_claims lists every data/audit PVC, claim_uids maps each name to its UID or new.
  vault contains version, image, statefulset, container, tls_secret, tls_server_name,
  ca_file/ca_sha256, cluster_id, shamir_threshold, leader_api_addr, and members.
  Each member contains pod, node_id and data_claim. Ordinals start at zero.
  known_secret contains path (a complete v1-relative KV read API path), pointer
  (keys below the JSON response), and sha256 of the canonical JSON selected value.
  control_backup contains repository, repository_id, password_file/password_sha256,
  restic_binary/restic_version, vault_binary, set_path and manifest_sha256.
  backup_id is the full restic snapshot ID. vault.snapshot_sha256 is the accepted
  control_backup manifest vault_sha256. The exact original Vault version is used.
  custody contains mode=ephemeral-file, file, sha256 and directory. Files are local,
  owner-only and outside Git. The original file is {token, unseal_keys_b64}.

The controller keeps shares off Kubernetes and calls verified HTTPS through native
kubectl port-forward. Only temporary bootstrap credentials use a private session file.
An uncertain snapshot submission is observed, never replayed. A failed native restore
keeps its evidence and requires an explicitly selected clean target.

Native API references
https://developer.hashicorp.com/vault/docs/sysadmin/snapshots/restore
https://developer.hashicorp.com/vault/api-docs/system/storage/raft
https://developer.hashicorp.com/vault/api-docs/system/unseal
"""

import argparse
from contextlib import contextmanager
import getpass
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit


def checksum(value):
    return hashlib.sha256(value).hexdigest()


def checked_file(path, expected=None, *, private=True):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('Custody requires an absolute canonical file without symlinks.')
    details = path.stat()
    if not stat.S_ISREG(details.st_mode):
        raise ValueError('Recovery inputs must be regular files.')
    if private and stat.S_IMODE(details.st_mode) != 0o600:
        raise ValueError('Custody files require mode 0600.')
    if private and hasattr(os, 'getuid') and details.st_uid != os.getuid():
        raise ValueError('Custody file belongs to a different operator.')
    data = path.read_bytes()
    if expected is not None and checksum(data) != expected:
        raise ValueError('Private custody input checksum changed.')
    return data


def private_directory(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or not path.is_dir():
        raise ValueError('An existing canonical ephemeral custody directory is required.')
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ValueError('Ephemeral custody directory requires mode 0700.')
    if hasattr(os, 'getuid') and path.stat().st_uid != os.getuid():
        raise ValueError('Ephemeral custody directory belongs to a different operator.')
    if any((parent / '.git').exists() for parent in [path, *path.parents]):
        raise ValueError('Shamir custody must be outside Git working trees.')
    return path


def validate(config):
    product = config['product']
    vault = product['vault']
    if not re.fullmatch(r'[a-z0-9]([a-z0-9-]{0,28}[a-z0-9])?', product['name']):
        raise ValueError('Select a bounded DNS product name for native recovery receipts.')
    if vault['seal'] != 'shamir':
        raise ValueError('This adapter supports Shamir. Transit/PKCS11 require the original working seal and a separate adapter.')
    if product.get('tier') != 0 or not re.fullmatch(r'[a-f0-9]{64}', product['backup_id']):
        raise ValueError('Select Tier 0 and an exact completed restic snapshot.')
    if not re.fullmatch(r'\d+\.\d+\.\d+', vault['version']):
        raise ValueError('The exact original community Vault version is required.')
    if any(check.get('authenticated', False) or check.get('headers_file') for check in product.get('checks', [])):
        raise ValueError('Vault general verification uses unauthenticated status and denial checks. Original custody tokens stay in the controller helper.')
    if '@sha256:' not in vault['image'] or not re.fullmatch(r'[a-f0-9]{64}', vault['snapshot_sha256']):
        raise ValueError('Select the retained Vault image digest and native snapshot checksum.')
    hostname = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*'
    if len(vault['tls_server_name']) > 253 or not re.fullmatch(hostname, vault['tls_server_name']):
        raise ValueError('Vault TLS server name must be an explicit safe hostname or IPv4 address.')
    leader = urlsplit(vault['leader_api_addr'])
    if (leader.scheme != 'https' or not leader.hostname or not re.fullmatch(hostname, leader.hostname) or
            leader.username is not None or leader.password is not None or leader.path not in ['', '/'] or
            leader.query or leader.fragment or not 1 <= (leader.port or 443) <= 65535):
        raise ValueError('Select an explicit verified HTTPS leader API address without credentials or URL parameters.')
    if vault['custody']['mode'] != 'ephemeral-file':
        raise ValueError('Physical custodians must furnish approved ephemeral inputs before the unattended run. Use --collect-custody first.')
    custody = vault['custody']
    directory = private_directory(custody['directory'])
    if Path(custody['file']).parent != directory:
        raise ValueError('Original shares must be in the selected ephemeral custody directory.')
    keys = json.loads(checked_file(custody['file'], custody['sha256']))
    shares = keys['unseal_keys_b64']
    if (not isinstance(shares, list) or
            not all(isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9+/=_-]+', key) for key in shares) or
            len(set(shares)) != len(shares) or type(vault['shamir_threshold']) is not int or
            not 1 <= vault['shamir_threshold'] <= len(shares) or
            not isinstance(keys['token'], str) or not re.fullmatch(r'[A-Za-z0-9._/-]+', keys['token'])):
        raise ValueError('Original distinct Shamir quorum and an original authorized token are required.')
    checked_file(vault['ca_file'], vault['ca_sha256'], private=False)
    try:
        ssl.create_default_context(cafile=vault['ca_file'])
    except ssl.SSLError:
        raise ValueError('Vault trust bundle must contain valid retained CA certificates.') from None
    backup = product['control_backup']
    checked_file(backup['password_file'], backup['password_sha256'])
    folder = PurePosixPath(backup['set_path'])
    if not folder.is_absolute() or '..' in folder.parts or ':' in str(folder):
        raise ValueError('Select the exact absolute control_backup set path.')
    members = vault['members']
    if not members or len({item['node_id'] for item in members}) != len(members):
        raise ValueError('Select distinct original Raft node identities.')
    for ordinal, member in enumerate(members):
        if member['pod'] != f"{vault['statefulset']}-{ordinal}" or member['data_claim'] not in product['data_claims']:
            raise ValueError('Member ordinals and explicit data claims must match the retained StatefulSet.')
    secret = vault['known_secret']
    if not re.fullmatch(r'[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}', vault['cluster_id']):
        raise ValueError('Retain the original Vault cluster UUID.')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', secret['path']) or '..' in secret['path'].split('/'):
        raise ValueError('Select an explicit retained KV read path.')
    if (not isinstance(secret['pointer'], list) or not secret['pointer'] or
            not all(isinstance(key, str) for key in secret['pointer']) or
            not re.fullmatch(r'[a-f0-9]{64}', secret['sha256'])):
        raise ValueError('A retained secret value checksum and JSON pointer keys are required.')
    return keys


def prepare_snapshot(config, io, restore):
    """Use the existing native restic restore guard and control_backup manifest."""
    product, directory = config['product'], Path(config['workspace']) / 'receipts'
    backup, vault = product['control_backup'], product['vault']
    env = io.restic_environment(dict(backup, directory=str(directory)))
    version = io.run([backup['restic_binary'], 'version'], env).decode().split()
    if len(version) < 2 or version[1] != backup['restic_version']:
        raise ValueError('Restore with the retained original restic version.')
    native_version = json.loads(io.run([backup['vault_binary'], 'version', '-format=json']))
    if native_version['version'] != vault['version']:
        raise ValueError('Restore with the exact original Vault CLI version.')
    # restore_files owns the native CLI name. Pin PATH to the selected restic binary.
    if Path(backup['restic_binary']).name != 'restic':
        raise ValueError('The retained native restic executable must be named restic.')
    env['PATH'] = str(Path(backup['restic_binary']).parent) + os.pathsep + os.environ.get('PATH', '')
    if json.loads(io.run([backup['restic_binary'], 'cat', 'config'], env))['id'] != backup['repository_id']:
        raise ValueError('Independent restic repository identity changed.')
    target = directory / (product['name'] + '-native-backup')
    if not target.exists():
        # The shared restore helper creates a fresh directory and verifies every byte.
        attempt = Path(tempfile.mkdtemp(prefix='.vault-download-', dir=directory)) / 'files'
        previous = dict(os.environ)
        try:
            os.environ.update(env)
            restore.restore(product['backup_id'], attempt, backup['set_path'])
        finally:
            os.environ.clear()
            os.environ.update(previous)
        attempt.rename(target)
    manifest_file, snapshot = target / 'manifest.json', target / 'vault.snap'
    if io.digest(manifest_file) != backup['manifest_sha256']:
        raise ValueError('Retained control_backup manifest checksum differs.')
    manifest = json.loads(manifest_file.read_text())
    if (manifest['schema'] != 1 or manifest['vault_sha256'] != vault['snapshot_sha256'] or
            io.digest(snapshot) != vault['snapshot_sha256']):
        raise ValueError('Native Vault snapshot does not match its retained backup set.')
    io.run([backup['vault_binary'], 'operator', 'raft', 'snapshot', 'inspect', str(snapshot)])
    return snapshot


class VaultRecovery:
    def __init__(self, config, request, save, record, credentials, sleep=time.sleep):
        self.config, self.vault = config, config['product']['vault']
        self.request, self.save, self.record = request, save, record
        self.credentials, self.sleep = credentials, sleep

    def status(self, member):
        result = self.request(member, 'GET', 'sys/seal-status')
        if result['type'] != 'shamir' or result.get('recovery_seal', False):
            raise ValueError('Observed Vault seal differs from the accepted Shamir recovery.')
        if result.get('version') != self.vault['version']:
            raise ValueError('Observed Vault version differs from the original snapshot version.')
        return result

    def unseal(self, member, keys):
        status = self.status(member)
        if not status['sealed']:
            return status
        self.request(member, 'PUT', 'sys/unseal', {'reset': True})
        for key in keys:
            status = self.request(member, 'PUT', 'sys/unseal', {'key': key})
            if not status['sealed']:
                return self.status(member)
        raise ValueError('Original Shamir quorum did not unseal the selected member.')

    def verify_member(self, member):
        status = self.status(member)
        if (status['sealed'] or status.get('cluster_id') != self.vault['cluster_id'] or
                status.get('t') != self.vault['shamir_threshold']):
            raise ValueError('Recovered member has a different original cluster identity or is sealed.')

    def verify_content(self, member):
        self.verify_member(member)
        proof = self.vault['known_secret']
        value = self.request(member, 'GET', proof['path'], token=self.credentials['token'])
        for key in proof['pointer']:
            value = value[key]
        if checksum(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()) != proof['sha256']:
            raise ValueError('Original known secret content differs from retained evidence.')

    def leader(self, snapshot, session, write_session):
        leader = self.vault['members'][0]
        phase = self.record.get('phase', 'planned')
        if phase == 'planned':
            if self.status(leader)['initialized']:
                raise ValueError('Unjournaled initialized Vault target requires a new clean data claim.')
            self.record['phase'] = 'initialization-submitted'
            self.save(self.record)
            temporary = self.request(leader, 'PUT', 'sys/init', {'secret_shares': 1, 'secret_threshold': 1})
            write_session(temporary)
            session = temporary
            self.record['phase'] = 'temporary-initialized'
            self.save(self.record)
            phase = self.record['phase']
        if phase == 'initialization-submitted':
            # Losing the init response loses the temporary root. Never initialize again.
            if not session:
                raise ValueError('Interrupted initialization has no private temporary credentials. Preserve this target and select a new clean claim.')
            phase = 'temporary-initialized'
        if phase == 'temporary-initialized':
            if not session:
                raise ValueError('Temporary initialization credentials are missing.')
            self.unseal(leader, session['keys_base64'])
            if self.status(leader).get('cluster_id') == self.vault['cluster_id']:
                raise ValueError('Original data appeared before the recorded snapshot submission.')
            self.record['phase'] = 'snapshot-submitted'
            self.save(self.record)
            self.request(leader, 'POST', 'sys/storage/raft/snapshot-force', snapshot, token=session['root_token'])
        # Vault accepts restore asynchronously. Wait for the original barrier before proof.
        for _ in range(180):
            status = self.status(leader)
            if status['sealed']:
                self.unseal(leader, self.credentials['unseal_keys_b64'])
            elif status.get('cluster_id') == self.vault['cluster_id']:
                self.verify_content(leader)
                self.record['phase'] = 'leader-verified'
                self.save(self.record)
                return
            self.sleep(2)
        raise ValueError('Snapshot submission remains uncertain. Preserve the target and journal. Snapshot overwrite will not be replayed.')

    def members(self):
        leader = self.vault['members'][0]
        self.verify_content(leader)
        ca = Path(self.vault['ca_file']).read_text()
        for member in self.vault['members'][1:]:
            current = self.status(member)
            if not current['initialized']:
                self.request(member, 'POST', 'sys/storage/raft/join', {
                    'leader_api_addr': self.vault['leader_api_addr'], 'leader_ca_cert': ca,
                    'leader_tls_servername': self.vault['tls_server_name'], 'retry': True})
            self.unseal(member, self.credentials['unseal_keys_b64'])
            self.verify_member(member)
        expected = {member['node_id'] for member in self.vault['members']}
        for _ in range(180):
            servers = self.request(leader, 'GET', 'sys/storage/raft/configuration', token=self.credentials['token'])['data']['config']['servers']
            if {item['node_id'] for item in servers} == expected and all(item['voter'] for item in servers):
                self.record['phase'] = 'verified'
                self.record['cluster_id'] = self.vault['cluster_id']
                self.save(self.record)
                return
            self.sleep(2)
        raise ValueError('Native Raft membership has not converged to the accepted voters.')


@contextmanager
def port_forward(config, member):
    pod = ['kubectl', '--kubeconfig', config['kubeconfig'], '--context', config['context'],
           '-n', config['product']['namespace'], 'wait']
    # OrderedReady StatefulSets create the next follower only after its predecessor
    # is unsealed. Joining one member at a time also supports that native policy.
    for condition in ['create', 'jsonpath={.status.phase}=Running']:
        result = subprocess.run(pod + ['--for=' + condition, '--timeout=900s', 'pod/' + member['pod']],
                                capture_output=True, timeout=920)
        if result.returncode:
            raise RuntimeError('Native Vault member Pod did not become available.')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    command = ['kubectl', '--kubeconfig', config['kubeconfig'], '--context', config['context'],
               '-n', config['product']['namespace'], 'port-forward', '--address', '127.0.0.1',
               'pod/' + member['pod'], f'{port}:8200']
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError('Native Vault pod port-forward failed.')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError('Native Vault pod port-forward did not become available.')
        yield port
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def native_request(config, member, method, path, body=None, token=None):
    vault = config['product']['vault']
    context = ssl.create_default_context(cafile=vault['ca_file'])
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    with port_forward(config, member) as port:
        connection = http.client.HTTPSConnection(vault['tls_server_name'], timeout=300, context=context)
        raw = socket.create_connection(('127.0.0.1', port), timeout=300)
        connection.sock = context.wrap_socket(raw, server_hostname=vault['tls_server_name'])
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Vault-Token'] = token
        try:
            if isinstance(body, Path):
                headers['Content-Type'] = 'application/octet-stream'
                headers['Content-Length'] = str(body.stat().st_size)
                with body.open('rb') as stream:
                    connection.request(method, '/v1/' + path, body=stream, headers=headers)
            else:
                connection.request(method, '/v1/' + path, body=json.dumps(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            data = response.read()
            if not 200 <= response.status < 300:
                raise RuntimeError(f'Native Vault recovery API failed with HTTP {response.status}.')
            return json.loads(data) if data else {}
        finally:
            connection.close()


def execute(config, operation, io, restore):
    credentials = validate(config)
    if not re.fullmatch(r'[a-f0-9]{64}', config['plan_sha256']):
        raise ValueError('The accepted recovery plan checksum is required.')
    product, vault = config['product'], config['product']['vault']
    snapshot = prepare_snapshot(config, io, restore)
    if operation == 'prepare':
        return
    # Bind every target UID in addition to immutable plan and snapshot evidence.
    binding = {key: config[key] for key in ['plan_sha256', 'namespace_uid', 'statefulset_uid', 'claim_uids']}
    path = Path(config['workspace']) / 'receipts' / (product['name'] + '-vault.json')
    record = json.loads(checked_file(path)) if path.exists() else dict(binding, phase='planned')
    if any(record.get(key) != value for key, value in binding.items()):
        raise ValueError('Vault recovery target or accepted plan changed on retry.')
    if record['phase'] not in ['planned', 'initialization-submitted', 'temporary-initialized',
                               'snapshot-submitted', 'leader-verified', 'verified']:
        raise ValueError('Vault native operation journal has an unknown phase.')
    session_file = private_directory(vault['custody']['directory']) / (product['name'] + '-' + config['plan_sha256'] + '-temporary.json')
    session = json.loads(checked_file(session_file)) if session_file.exists() else None
    recovery = VaultRecovery(config, lambda *args, **kwargs: native_request(config, *args, **kwargs),
                             lambda value: io.atomic_json(path, value), record, credentials)
    with io.job_lock(vault['custody']['directory']):
        if operation == 'leader':
            recovery.leader(snapshot, session, lambda value: io.atomic_json(session_file, value))
        elif operation == 'members':
            recovery.members()
        else:
            for member in vault['members']:
                recovery.verify_member(member)
            recovery.verify_content(vault['members'][0])
            recovery.members()
        if recovery.record['phase'] in ['leader-verified', 'verified']:
            session_file.unlink(missing_ok=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config')
    parser.add_argument('--control-tools')
    parser.add_argument('--operation', choices=['prepare', 'leader', 'members', 'verify'])
    parser.add_argument('--collect-custody', help='New file in a private directory outside Git. Run interactively before accepting the plan.')
    parser.add_argument('--shares', type=int)
    args = parser.parse_args()
    try:
        if args.collect_custody:
            path = Path(args.collect_custody)
            private_directory(path.parent)
            if not sys.stdin.isatty() or not args.shares or not 1 <= args.shares <= 255:
                raise ValueError('Attending custodians and the original quorum size are required.')
            value = {'token': getpass.getpass('Original authorized recovery token: '),
                     'unseal_keys_b64': [getpass.getpass('Original Shamir share: ') for _ in range(args.shares)]}
            data = (json.dumps(value) + '\n').encode()
            with path.open('xb') as stream:
                stream.write(data)
            print(checksum(data))
            return 0
        if not args.config or not args.control_tools or not args.operation:
            raise ValueError('Select the accepted private config, retained control_backup tooling and native operation.')
        sys.path.insert(0, str(Path(args.control_tools).resolve()))
        import control_backup_io as io
        import restore_files
        execute(json.loads(checked_file(args.config)), args.operation, io, restore_files)
        return 0
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (KeyError, OSError, subprocess.SubprocessError):
        # Exceptions from products may include sensitive paths, bodies or credentials.
        print('Vault recovery failed. Preserve the plan-bound journal and inspect private native diagnostics.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
