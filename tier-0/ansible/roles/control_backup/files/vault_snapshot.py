"""Acquire and inspect a native Raft snapshot using a bounded snapshot-only token."""

import json
from ipaddress import ip_network
import os
from pathlib import Path

from control_backup_io import run


def environment(config):
    env = {key: value for key, value in os.environ.items() if not key.startswith('VAULT_')}
    if not config['address'].startswith('https://'):
        raise ValueError('Vault requires verified HTTPS')
    env.update(VAULT_ADDR=config['address'], VAULT_CACERT=config['ca_file'],
               VAULT_TLS_SERVER_NAME=config['server_name'], VAULT_CLIENT_TIMEOUT='300s',
               VAULT_TOKEN='unauthenticated-control-backup')
    return env


def validate_token(data, policy, expected_cidrs=None):
    policies = set(data['policies']) | set(data.get('identity_policies') or [])
    if policies != {policy} or policy in {'root', 'default'}:
        raise ValueError('Vault token must have only the snapshot policy')
    if not 60 <= int(data['ttl']) <= 3600:
        raise ValueError('Vault token TTL must be between 60 and 3600 seconds')
    if not 60 <= int(data.get('explicit_max_ttl', 0)) <= 3600:
        raise ValueError('Vault token requires an explicit maximum lifetime of at most one hour')
    if int(data.get('period', 0)) or data.get('type') != 'service':
        raise ValueError('periodic and non-service tokens are not supported')
    if expected_cidrs is not None:
        expected = {ip_network(cidr, strict=False) for cidr in expected_cidrs}
        actual = {ip_network(cidr, strict=False) for cidr in data.get('bound_cidrs', [])}
        if not expected or any(cidr.prefixlen == 0 for cidr in expected) or actual != expected:
            raise ValueError('certificate token must be bound to exactly the approved recovery CIDRs')


def save(config, destination):
    binary = config['binary']
    env = environment(config)
    approle = config['auth'] == 'approle'
    minted = config['auth'] in {'cert', 'approle'}
    if config['auth'] == 'cert':
        env.update(VAULT_CLIENT_CERT=config['client_cert'], VAULT_CLIENT_KEY=config['client_key'])
        run(['openssl', 'x509', '-in', config['client_cert'], '-noout', '-checkend',
             str(config['cert_min_seconds'])], env)
        auth = json.loads(run([binary, 'write', '-format=json', f"auth/{config['cert_mount']}/login",
                               f"name={config['cert_role']}"], env))
        env['VAULT_TOKEN'] = auth['auth']['client_token']
    elif approle:
        login = {field: Path(config[field]).read_text().strip() for field in ['role_id', 'secret_id']}
        auth = json.loads(run([binary, 'write', '-format=json', f"auth/{config['mount']}/login", '-'],
                              env, input_data=json.dumps(login).encode()))
        env['VAULT_TOKEN'] = auth['auth']['client_token']
    elif config['auth'] == 'static-token-local':
        env['VAULT_TOKEN'] = Path(config['token_file']).read_text().strip()
    else:
        raise ValueError('unsupported Vault authentication mode')
    validated = False
    try:
        data = json.loads(run([binary, 'token', 'lookup', '-format=json'], env))['data']
        cidrs = config['bound_cidrs'] if config['auth'] == 'cert' else None
        validate_token(data, config['policy'], cidrs)
        validated = True
        run([binary, 'operator', 'raft', 'snapshot', 'save', str(destination)], env)
        if not Path(destination).is_file() or Path(destination).stat().st_size == 0:
            raise ValueError('empty or missing Vault snapshot')
        run([binary, 'operator', 'raft', 'snapshot', 'inspect', str(destination)], env)
    finally:
        # A rejected root/broad token must never be revoked by this job.
        # Static fallback tokens must survive until the next scheduled run/rotation.
        if minted and validated:
            run([binary, 'token', 'revoke', '-self'], env)
        env.pop('VAULT_TOKEN', None)
