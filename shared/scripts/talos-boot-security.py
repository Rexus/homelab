#!/usr/bin/env python3
"""Guard boot-policy changes and verify authenticated Talos boot/encryption state."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def encryption_policy(configuration):
    """Compare the effective native policy, including patches outside the summary selector."""
    import yaml

    if not isinstance(configuration, str) or not configuration.strip():
        raise ValueError('Existing node encryption policy must be known before apply; retain its original secrets and render the complete configuration first.')
    try:
        documents = list(yaml.safe_load_all(configuration))
    except yaml.YAMLError:
        raise ValueError('The native machine configuration could not be decoded; sensitive content withheld.') from None
    result, seen = {'legacy': None, 'STATE': None, 'EPHEMERAL': None}, set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        if document.get('kind') == 'VolumeConfig' and document.get('name') in ('STATE', 'EPHEMERAL'):
            name = document['name']
            if name in seen:
                raise ValueError('Duplicate system VolumeConfig policy; inspect the complete native render before applying.')
            seen.add(name)
            result[name] = document.get('encryption') or None
        if isinstance(document.get('machine'), dict):
            result['legacy'] = document['machine'].get('systemDiskEncryption') or None
    return result


def guard(plan, require_talosctl=False):
    desired = plan.get('planned_values', {}).get('outputs', {}).get('boot_security', {}).get('value')
    previous = plan.get('prior_state', {}).get('values', {}).get('outputs', {}).get('boot_security', {}).get('value')
    existing = any(change.get('type') == 'proxmox_virtual_environment_vm' and
                   change.get('change', {}).get('before') is not None
                   for change in plan.get('resource_changes', []))
    wanted = desired or {'mode': 'template', 'encrypt_system_disks': False}
    original = previous or {'mode': 'template', 'encrypt_system_disks': False}
    if require_talosctl and wanted.get('mode') == 'secureboot' and shutil.which('talosctl') is None:
        raise ValueError('Install the approved talosctl on PATH before applying signed nodes; authenticated guest verification requires it.')
    if existing:
        for field in ('mode', 'encrypt_system_disks'):
            if wanted.get(field) != original.get(field):
                raise ValueError('Existing nodes retain their boot/encryption policy. Use the secured rebuild/recovery path; this is not an in-place conversion.')
    for resource in plan.get('resource_changes', []):
        change = resource.get('change', {})
        before, after = change.get('before'), change.get('after')
        if resource.get('type') == 'proxmox_virtual_environment_vm':
            if before is None:
                if wanted.get('mode') == 'secureboot' and wanted.get('install_media_attached') is False:
                    raise ValueError('New signed nodes require install_media_attached=true. Reattach the approved ISO before scale-out; eject it again after installed-disk verification.')
            elif after is not None:
                for field in ('bios', 'machine', 'scsi_hardware', 'efi_disk', 'tpm_state', 'boot_order'):
                    if before.get(field) != after.get(field):
                        raise ValueError(f'Existing node {field} must remain unchanged; use qualified boot-hardware maintenance or recovery.')
        if resource.get('type') == 'talos_machine_configuration_apply' and before is not None and after is not None:
            if change.get('after_unknown', {}).get('machine_configuration_input'):
                raise ValueError('Existing node encryption policy is unknown in this plan; retain original secrets and render before applying.')
            if encryption_policy(before.get('machine_configuration_input')) != encryption_policy(after.get('machine_configuration_input')):
                raise ValueError('Existing node effective system-disk encryption policy changed in the rendered configuration. Use a fresh installation/recovery design; editing custom patches cannot convert it in place.')


def resources(output):
    """talosctl emits one JSON resource per line; also accept a single resource/list."""
    decoder, remaining, result = json.JSONDecoder(), output.strip(), []
    while remaining:
        value, end = decoder.raw_decode(remaining)
        result.extend(value if isinstance(value, list) else [value])
        remaining = remaining[end:].lstrip()
    return result


def check_security(items):
    if len(items) != 1 or not isinstance(items[0], dict):
        raise ValueError('Expected exactly one SecurityState resource')
    spec = items[0].get('spec', {})
    if spec.get('secureBoot') is not True or spec.get('bootedWithUKI') is not True:
        raise ValueError('Guest must report Secure Boot enabled and a UKI boot')


def check_volume(items, name):
    if len(items) != 1 or items[0].get('metadata', {}).get('id') != name:
        raise ValueError(f'Expected the {name} volume status')
    spec = items[0].get('spec', {})
    keys = spec.get('configuredEncryptionKeys', [])
    if (str(spec.get('phase', '')).lower() != 'ready' or spec.get('encryptionProvider') != 'luks2'
            or spec.get('encryptionSlot') != 0 or spec.get('encryptionFailedSyncs')
            or keys != ['tpm']):
        raise ValueError(f'{name} must be ready and unlocked through its configured TPM LUKS2 slot')


def verify(config, nodes, policy, binary='talosctl'):
    if policy.get('mode') != 'secureboot':
        print('Template boot policy retained; use the guest-security inspection for its selected controls.')
        return
    if not nodes:
        raise ValueError('No managed Talos nodes were exported')
    for name, node in sorted(nodes.items()):
        def query(kind, identity=None):
            command = [binary, '--talosconfig', str(config), '--nodes', node['ip'], '--endpoints', node['ip'], 'get', kind]
            if identity:
                command.append(identity)
            command.extend(['--output', 'json'])
            response = subprocess.run(command, capture_output=True, text=True, timeout=45)
            if response.returncode:
                raise ValueError(f'{name}: authenticated {kind} query failed; inspect the node through its original credentials')
            return resources(response.stdout)

        check_security(query('securitystate'))
        if policy.get('encrypt_system_disks'):
            for volume in ('STATE', 'EPHEMERAL'):
                check_volume(query('volumestatus', volume), volume)
        print(f'{name}: Secure Boot/UKI verified' + ('; STATE and EPHEMERAL TPM encryption verified' if policy.get('encrypt_system_disks') else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    guarded = commands.add_parser('plan-guard')
    guarded.add_argument('--require-talosctl', action='store_true')
    selected = commands.add_parser('verify')
    for name in ('talosconfig', 'nodes', 'policy'):
        selected.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'plan-guard':
            guard(json.load(sys.stdin), require_talosctl=args.require_talosctl)
        else:
            verify(args.talosconfig, json.loads(args.nodes.read_text()), json.loads(args.policy.read_text()))
    except (ValueError, KeyError, TypeError, OSError, ImportError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Boot security: {error}\n')


if __name__ == '__main__':
    main()
