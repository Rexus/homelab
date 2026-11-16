#!/usr/bin/env python3
"""Compare reviewed immutable bundles; allow only a PKCS11 key locator/engine change."""

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import tarfile

import yaml


def members(path):
    result = {}
    with tarfile.open(path, 'r:*') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or not (member.isdir() or member.isfile()):
                raise ValueError('Bundle contains an unsafe path or nonregular member')
            key = str(name)
            if key in result:
                raise ValueError('Bundle contains duplicate paths')
            result[key] = (member.mode, None if member.isdir() else archive.extractfile(member).read())
    return result


def validate(old_path, new_path, realm, key, library, engine):
    old, new = members(old_path), members(new_path)
    crypto = f'config.d/realm/{realm}/crypto.yaml'
    if set(old) != set(new) or crypto not in old:
        raise ValueError('Provider migration cannot add or remove bundle paths')
    for name in old:
        if name != crypto and old[name] != new[name]:
            raise ValueError(f'Provider migration cannot change {name}')
    if old[crypto][0] != new[crypto][0]:
        raise ValueError('Provider migration cannot change crypto configuration permissions')
    previous, desired = (yaml.safe_load(tree[crypto][1]) for tree in (old, new))
    old_signer, new_signer = (tree['token']['ca-signer'] for tree in (previous, desired))
    if any(signer.get('engine') != 'PKCS11' or signer.get('key_store') != 'ENGINE'
           for signer in (old_signer, new_signer)):
        raise ValueError('Both configurations must already use PKCS11 custody')
    expected_section = (f'engine_id = pkcs11\ndynamic_path = {engine}\nMODULE_PATH = {library}\n'
                        'PIN = "__PIN__"\ninit = 0')
    if new_signer['key'] != key or new_signer['engine_section'].strip() != expected_section:
        raise ValueError('New signer must contain exactly the selected native key/module/engine')
    for field in ('key', 'engine_section'):
        new_signer[field] = old_signer[field]
    if desired != previous:
        raise ValueError('Provider migration cannot change signer policy or another token/secret')
    # The two connection files are rendered at installation; freeze their installed bytes separately.
    rendered = {'config.d/system/database.yaml', 'client.d/service/webui/default.yaml'}
    return {name: hashlib.sha256(payload).hexdigest() for name, (_, payload) in old.items()
            if payload is not None and name not in rendered}


def build(old_path, output, realm, key, library, engine):
    """Retain all original credentials/policy; create only the requested provider revision."""
    members(old_path)  # Reject links, duplicate names and unsafe members before opening the output.
    crypto = f'config.d/realm/{realm}/crypto.yaml'
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with tarfile.open(old_path, 'r:*') as original, os.fdopen(descriptor, 'wb') as destination:
        with tarfile.open(fileobj=destination, mode='w:gz') as revised:
            for entry in original:
                payload = None if entry.isdir() else original.extractfile(entry).read()
                if str(PurePosixPath(entry.name)) == crypto:
                    policy = yaml.safe_load(payload)
                    signer = policy['token']['ca-signer']
                    if signer.get('engine') != 'PKCS11' or signer.get('key_store') != 'ENGINE':
                        raise ValueError('Only an existing PKCS11 issuer can be relocated')
                    signer['key'] = key
                    signer['engine_section'] = (f'engine_id = pkcs11\ndynamic_path = {engine}\n'
                                                f'MODULE_PATH = {library}\nPIN = "__PIN__"\ninit = 0\n')
                    payload = yaml.safe_dump(policy, sort_keys=False).encode()
                entry = copy.copy(entry)
                if payload is not None:
                    entry.size = len(payload)
                revised.addfile(entry, None if payload is None else io.BytesIO(payload))
    validate(old_path, output, realm, key, library, engine)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('old', 'realm', 'key', 'library', 'engine'):
        parser.add_argument('--' + name, required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument('--new')
    destination.add_argument('--output')
    args = parser.parse_args()
    try:
        if args.output:
            build(args.old, args.output, args.realm, args.key, args.library, args.engine)
            print(json.dumps({'artifact': args.output, 'sha256': hashlib.sha256(open(args.output, 'rb').read()).hexdigest()}))
        else:
            print(json.dumps(validate(args.old, args.new, args.realm, args.key, args.library, args.engine)))
    except (ValueError, KeyError, TypeError, tarfile.TarError, yaml.YAMLError) as error:
        parser.exit(1, str(error) + '\n')
