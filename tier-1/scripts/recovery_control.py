"""Preflight the two Tier 0 native control-product recovery contracts."""

import importlib.util
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit


SHA256 = re.compile(r'[a-f0-9]{64}\Z')


def require_fields(value, fields):
    if not isinstance(value, dict) or any(field not in value or value[field] in ('', None) for field in fields):
        raise ValueError('Complete the native control-product recovery input contract before execution.')


def validate(product, *, verify_custody=True):
    require_fields(product, ('control_backup', 'data_claims', 'claim_uids'))
    if product['tier'] != 0 or not SHA256.fullmatch(product['backup_id']):
        raise ValueError('Control-product recovery requires Tier 0 and a full retained restic snapshot ID.')
    claims = product['data_claims']
    if (not isinstance(claims, list) or not claims or len(set(claims)) != len(claims) or
            not isinstance(product['claim_uids'], dict) or
            set(product['claim_uids']) != set(claims) or
            any(not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,62}', claim) for claim in claims) or
            any(not isinstance(uid, str) or not uid for uid in product['claim_uids'].values())):
        raise ValueError('Bind every selected control-product data claim to its explicit UID or new owned target.')
    backup = product['control_backup']
    require_fields(backup, ('set_path', 'manifest_sha256', 'repository_id'))
    if any(not SHA256.fullmatch(backup[field]) for field in ('manifest_sha256', 'repository_id')):
        raise ValueError('Bind the control backup set and repository to independent checksums.')
    folder = PurePosixPath(backup['set_path'])
    if (not re.fullmatch(r'/[A-Za-z0-9_./-]+', backup['set_path']) or
            not folder.is_absolute() or '..' in folder.parts):
        raise ValueError('Select an exact native control backup subtree.')
    if product['kind'] == 'vault-raft':
        require_fields(product, ('vault',))
        require_fields(product['vault'], ('seal', 'custody', 'statefulset', 'container', 'image', 'members',
            'cluster_id', 'version', 'ca_file', 'ca_sha256', 'tls_secret', 'tls_server_name',
            'leader_api_addr', 'shamir_threshold', 'snapshot_sha256', 'known_secret'))
        require_fields(backup, ('repository', 'password_file', 'password_sha256', 'restic_binary',
                               'restic_version', 'vault_binary'))
        endpoint = urlsplit(product['vault']['leader_api_addr'])
        if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.path not in ('', '/') or endpoint.query or endpoint.fragment:
            raise ValueError('Vault native join requires an independently trusted HTTPS leader endpoint.')
        writers = {(writer['kind'], writer['name']) for writer in product['writers']}
        if ('StatefulSet', product['vault']['statefulset']) not in writers:
            raise ValueError('The exact Vault StatefulSet must be fenced before native recovery.')
        module_path = Path(__file__).resolve().parent.parent / 'ansible/roles/platform_recovery/files/vault_recovery.py'
        spec = importlib.util.spec_from_file_location('native_vault_recovery_preflight', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Reads owner-only external custody files; shares are never copied into Git or returned in the plan.
        if verify_custody:
            module.validate({'product': product})
    else:
        require_fields(product, ('media', 'restic_image', 'restic_secret', 'restic_version'))
        require_fields(backup, ('vault_sha256',))
        media = product['media']
        require_fields(media, ('claim', 'path', 'source_marker', 'known_file', 'known_file_sha256',
                               'run_as_user', 'run_as_group'))
        if claims != [media['claim']] or not SHA256.fullmatch(media['known_file_sha256']) or not SHA256.fullmatch(backup['vault_sha256']):
            raise ValueError('Bind only the selected NetBox media claim and retained media evidence.')
        for path, absolute in ((media['path'], True), (media['known_file'], False)):
            relative = PurePosixPath(path)
            pattern = r'/[A-Za-z0-9_./-]+' if absolute else r'[A-Za-z0-9_./-]+'
            if (not re.fullmatch(pattern, path) or relative.is_absolute() != absolute or
                    '..' in relative.parts or not relative.parts):
                raise ValueError('NetBox media paths must remain within the selected native backup subtree.')
        if (media['known_file'] in ('.control-backup-source', '.platform-recovery-media') or
                product.get('repository_claim') == media['claim']):
            raise ValueError('Known media must be independent of marker files and the backup repository claim.')
        if (not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', media['source_marker']) or
                any(type(media[field]) is not int or media[field] <= 0 for field in ('run_as_user', 'run_as_group'))):
            raise ValueError('Retain the original media marker and native non-root filesystem identity.')
        if not re.search(r'@sha256:[a-f0-9]{64}$', product['restic_image']) or not re.fullmatch(r'\d+\.\d+\.\d+', product['restic_version']):
            raise ValueError('Use the independently retained exact restic image and version.')
