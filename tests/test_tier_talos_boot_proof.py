"""The completion gate must prove the guest's selected controls over its authenticated API."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from tier_repo_test_support import UPSTREAM

spec = importlib.util.spec_from_file_location('talos_boot_proof', UPSTREAM / 'shared/scripts/talos-boot-security.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class TalosGuestProof(unittest.TestCase):
    def test_signed_apply_requires_verification_tool_before_provisioning(self):
        plan = {'planned_values': {'outputs': {'boot_security': {'value': {
            'mode': 'secureboot', 'encrypt_system_disks': True}}}}}
        with patch.object(proof.shutil, 'which', return_value=None) as available:
            proof.guard(plan)
            available.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'talosctl on PATH before applying'):
                proof.guard(plan, require_talosctl=True)
            available.assert_called_once_with('talosctl')
            proof.guard({}, require_talosctl=True)
        with patch.object(proof.shutil, 'which', return_value='/approved/bin/talosctl'):
            proof.guard(plan, require_talosctl=True)

    def test_existing_policy_is_compared_from_effective_vm_and_machine_configuration(self):
        policy = {'mode': 'secureboot', 'encrypt_system_disks': True, 'install_media_attached': True}
        encrypted = 'kind: VolumeConfig\nname: STATE\nencryption:\n  provider: luks2\n  keys: [{slot: 0, tpm: {checkSecurebootStatusOnEnroll: true}}]\n'
        plain = 'machine:\n  install: {image: signed-installer:v1.13.0}\n'
        original = {'machine_configuration_input': encrypted}

        def plan(kind, before, after, unknown=None):
            return {'planned_values': {'outputs': {'boot_security': {'value': policy}}},
                    'prior_state': {'values': {'outputs': {'boot_security': {'value': policy}}}},
                    'resource_changes': [{'type': kind, 'change': {
                        'before': before, 'after': after, 'after_unknown': unknown or {}}}]}

        config_type = 'talos_machine_configuration_apply'
        proof.guard(plan(config_type, original, {'machine_configuration_input': encrypted}))
        for changed in (plain, encrypted.replace('tpm:', 'static:')):
            with self.assertRaisesRegex(ValueError, 'effective system-disk encryption policy'):
                proof.guard(plan(config_type, original, {'machine_configuration_input': changed}))
        with self.assertRaisesRegex(ValueError, 'unknown'):
            proof.guard(plan(config_type, original, {'machine_configuration_input': None}, {'machine_configuration_input': True}))
        for key in ('bios', 'machine', 'scsi_hardware', 'efi_disk', 'tpm_state', 'boot_order'):
            with self.assertRaisesRegex(ValueError, 'must remain unchanged'):
                proof.guard(plan('proxmox_virtual_environment_vm', {key: 'retained'}, {key: 'changed'}))
        # A new empty VolumeConfig is still the same plaintext policy; YAML formatting is irrelevant.
        self.assertEqual(proof.encryption_policy(plain), proof.encryption_policy(plain + '---\nkind: VolumeConfig\nname: STATE\n'))
        with self.assertRaisesRegex(ValueError, 'sensitive content withheld'):
            proof.encryption_policy('machine: [private broken configuration')

    def test_scale_out_requires_bootable_installation_media_before_any_mutation(self):
        policy = {'mode': 'secureboot', 'encrypt_system_disks': True, 'install_media_attached': False}
        plan = {'planned_values': {'outputs': {'boot_security': {'value': policy}}},
                'prior_state': {'values': {'outputs': {'boot_security': {'value': policy}}}},
                'resource_changes': [{'type': 'proxmox_virtual_environment_vm', 'change': {'before': None, 'after': {}}}]}
        with self.assertRaisesRegex(ValueError, 'Reattach the approved ISO before scale-out'):
            proof.guard(plan)
        policy['install_media_attached'] = True
        proof.guard(plan)

    def test_media_changes_preserve_existing_boot_order(self):
        policy = {'mode': 'secureboot', 'encrypt_system_disks': True, 'install_media_attached': True}
        before = {'boot_order': ['scsi0', 'ide0'],
                  'cdrom': [{'interface': 'ide0', 'file_id': 'iso-store:iso/approved.iso'}]}
        after = {'boot_order': ['scsi0', 'ide0'],
                 'cdrom': [{'interface': 'ide0', 'file_id': 'none'}]}
        plan = {'planned_values': {'outputs': {'boot_security': {'value': dict(policy, install_media_attached=False)}}},
                'prior_state': {'values': {'outputs': {'boot_security': {'value': policy}}}},
                'resource_changes': [{'type': 'proxmox_virtual_environment_vm',
                                      'change': {'before': before, 'after': after}}]}
        proof.guard(plan)
        after['boot_order'] = ['scsi0']
        with self.assertRaisesRegex(ValueError, 'boot_order must remain unchanged'):
            proof.guard(plan)
        # Earlier ejected installations also require explicit serial boot-hardware maintenance.
        before['boot_order'], after['boot_order'] = ['scsi0'], ['scsi0', 'ide0']
        with self.assertRaisesRegex(ValueError, 'boot_order must remain unchanged'):
            proof.guard(plan)

    def test_all_selected_nodes_and_both_volumes_use_authenticated_native_api(self):
        calls = []

        def native(command, **options):
            calls.append(command)
            self.assertTrue(options['capture_output'])
            self.assertLessEqual(options['timeout'], 60)
            if 'securitystate' in command:
                data = {'spec': {'secureBoot': True, 'bootedWithUKI': True}}
            else:
                name = command[command.index('volumestatus') + 1]
                data = {'metadata': {'id': name}, 'spec': {
                    'phase': 'ready', 'encryptionProvider': 'luks2', 'encryptionSlot': 0,
                    'configuredEncryptionKeys': ['tpm']}}
            return subprocess.CompletedProcess(command, 0, json.dumps(data), '')

        selected = {'one': {'ip': '192.0.2.11'}, 'two': {'ip': '192.0.2.12'}}
        with patch.object(proof.subprocess, 'run', side_effect=native), contextlib.redirect_stdout(io.StringIO()) as output:
            proof.verify(Path('private/original-talosconfig'), selected,
                         {'mode': 'secureboot', 'encrypt_system_disks': True})
        self.assertEqual(len(calls), 6)
        for command in calls:
            self.assertEqual(command[0], 'talosctl')
            self.assertEqual(command[command.index('--talosconfig') + 1], 'private/original-talosconfig')
            self.assertEqual(command[command.index('--nodes') + 1], command[command.index('--endpoints') + 1])
            self.assertNotIn('--insecure', command)
        self.assertEqual(output.getvalue().count('TPM encryption verified'), 2)

    def test_failed_api_and_disabled_boot_are_never_accepted(self):
        selected = {'one': {'ip': '192.0.2.11'}}
        policy = {'mode': 'secureboot', 'encrypt_system_disks': True}
        for result in (subprocess.CompletedProcess([], 1, 'private server output', 'private error'),
                       subprocess.CompletedProcess([], 0, json.dumps({'spec': {'secureBoot': False, 'bootedWithUKI': True}}), '')):
            with patch.object(proof.subprocess, 'run', return_value=result), self.assertRaises(ValueError) as error:
                proof.verify('original-config', selected, policy)
            self.assertNotIn('private', str(error.exception))

    def test_template_policy_does_not_claim_secure_boot_or_contact_nodes(self):
        with patch.object(proof.subprocess, 'run') as native, contextlib.redirect_stdout(io.StringIO()) as output:
            proof.verify('original-config', {}, {'mode': 'template', 'encrypt_system_disks': False})
        native.assert_not_called()
        self.assertIn('Template boot policy retained', output.getvalue())
        with self.assertRaisesRegex(ValueError, 'No managed Talos nodes'):
            proof.verify('original-config', {}, {'mode': 'secureboot'})
