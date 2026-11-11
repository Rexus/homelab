"""Template policy and refresh cleanup without live infrastructure."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from proxmox_template_disk_fixture import TemplateDiskApiFixture
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'ansible-doc', 'openssl')),
                     'Requires native Ansible, community.proxmox and OpenSSL')
class TemplatePolicy(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        modules = ['community.proxmox.proxmox_vm_info', 'community.proxmox.proxmox_kvm']
        check = subprocess.run(['ansible-doc', '--json', '-t', 'module', *modules],
                               capture_output=True, text=True)
        if check.returncode or not set(modules).issubset(json.loads(check.stdout)):
            self.skipTest('Install Tier 0 community.proxmox requirements')
        self.root.mkdir(parents=True)
        cert, key = self.root / 'fixture.crt', self.root / 'fixture.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        self.api = TemplateDiskApiFixture(cert, key)
        self.addCleanup(self.api.close)
        self.vars = {'template_disk_sources': {'value': {'rocky-build-1': {
            'vm_id': 110, 'name': self.api.config['name'], 'node_name': 'pve01',
        }}}}
        self.env = dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / 'tier-0/ansible/ansible.cfg'),
                        PROXMOX_CA_FILE=str(cert),
                        PROXMOX_VE_ENDPOINT=f'https://127.0.0.1:{self.api.server.server_port}/',
                        PROXMOX_VE_API_TOKEN='fixture@pve!disk=fixture-not-a-secret')

    def run_policy(self, **overrides):
        inputs = self.root / 'policy.json'
        inputs.write_text(json.dumps(dict(self.vars, **overrides)))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/maintenance/template-policy.yml'),
                                 '--extra-vars', '@' + str(inputs)], env=self.env, capture_output=True, text=True)
        self.assertNotIn('fixture-not-a-secret', result.stdout + result.stderr)
        self.assertNotIn('fixture-cloud-password', result.stdout + result.stderr)
        return result

    def test_apply_clears_identity_and_missing_balloon_then_becomes_noop(self):
        self.api.config.pop('balloon')
        self.api.config.update(cipassword='fixture-cloud-password', sshkeys='ssh-ed25519 fixture-public-key')
        before = dict(self.api.config)
        result = self.run_policy(template_policy_apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.config['balloon'], 0)
        self.assertFalse({'ciuser', 'cipassword', 'sshkeys'} & self.api.config.keys())
        protected = lambda value: {k: v for k, v in value.items()
                                   if k not in ('balloon', 'ciuser', 'cipassword', 'sshkeys')}
        self.assertEqual(protected(self.api.config), protected(before))
        self.assertEqual(len(self.api.writes), 2)
        self.assertEqual(self.api.writes[0][2], {'delete': 'cipassword,ciuser,sshkeys'})
        self.assertEqual(self.api.writes[1][2]['balloon'], '0')
        self.assertIn('digest', self.api.writes[1][2])
        result = self.run_policy(template_policy_apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.api.writes), 2)
        self.assertIn('changed=0', result.stdout)
        result = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"cloud_init_accounts_cleared": true', result.stdout)
        self.assertEqual(len(self.api.writes), 2)

    def test_read_only_verification_reports_enabled_balloon_and_never_writes(self):
        self.api.config.pop('ciuser')
        for balloon in (None, 2048):
            self.api.config.pop('balloon', None)
            if balloon is not None:
                self.api.config['balloon'] = balloon
            result = self.run_policy()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Template policy is not satisfied', result.stdout)
        self.assertEqual(self.api.writes, [])

    def test_selection_identity_and_permission_failures_are_bounded(self):
        self.vars['template_disk_sources']['value']['unselected'] = {
            'vm_id': 999, 'name': 'unrelated', 'node_name': 'elsewhere'}
        result = self.run_policy(template_policy_apply=True, template_policy_key='rocky-build-1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        writes = len(self.api.writes)
        self.api.status = 'running'
        self.assertNotEqual(self.run_policy(template_policy_apply=True,
                                            template_policy_key='rocky-build-1').returncode, 0)
        self.assertEqual(len(self.api.writes), writes)
        self.api.status = 'stopped'
        self.api.config['balloon'] = 2048
        self.api.fail_policy = True
        self.assertNotEqual(self.run_policy(template_policy_apply=True,
                                            template_policy_key='rocky-build-1').returncode, 0)
        self.assertEqual(self.api.config['balloon'], 2048)


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                     'Requires native Ansible on Linux/WSL')
class TemplateRefreshCleanup(TierRepositoryTestCase):
    def test_replacement_preserves_ordinary_vm_configuration_and_disk(self):
        self.root.mkdir(parents=True)
        commands = self.root / 'commands'
        commands.mkdir()
        qm = commands / 'qm'
        qm.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['QM_FIXTURE_ROOT'])
args = sys.argv[1:]
with open(os.environ['QM_FIXTURE_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
config = root / (args[1] + '.conf')
if args[0] == 'config':
    if not config.exists():
        sys.exit(2)
    print(config.read_text(), end='')
elif args[0] == 'destroy':
    config.unlink()
    (root / (args[1] + '.disk')).unlink()
elif args[0] == 'clone':
    (root / (args[2] + '.conf')).write_text('name: selected-image\\n')
    (root / (args[2] + '.disk')).write_bytes(b'new image disk')
elif args[0] == 'template':
    config.write_text(config.read_text() + 'template: 1\\n')
else:
    sys.exit(99)
''')
        qm.chmod(0o755)
        for name, target_config, rejected in (
                ('ordinary', b'name: important-service\n', True),
                ('explicit-false', b'name: important-service\ntemplate: 0\n', True),
                ('template', b'name: selected-image\ntemplate: 1\n', False)):
            with self.subTest(target=name):
                fixture = self.root / name
                fixture.mkdir()
                staged = fixture / '9102.conf'
                staged.write_bytes(b'name: staged-image\ntemplate: 1\n')
                target = fixture / '9101.conf'
                target.write_bytes(target_config)
                disk = fixture / '9101.disk'
                disk.write_bytes(b'irreplaceable original VM disk')
                calls = fixture / 'calls.jsonl'
                play = fixture / 'replacement.yml'
                play.write_text(yaml.safe_dump([{
                    'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                    'environment': {'PATH': f'{commands}:{os.environ["PATH"]}',
                                    'QM_FIXTURE_ROOT': str(fixture), 'QM_FIXTURE_LOG': str(calls)},
                    'vars': {'template_refresh_replace_enabled': True, 'template_refresh_replacements': [
                        {'name': 'selected-image', 'staged_vm_id': 9102, 'target_vm_id': 9101}]},
                    'tasks': [{'ansible.builtin.import_tasks': str(
                        UPSTREAM / 'tier-0/ansible/roles/proxmox_template_replace/tasks/main.yml')}],
                }], sort_keys=False))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                        cwd=fixture, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode != 0, rejected, result.stdout + result.stderr)
                operations = [json.loads(line)[0] for line in calls.read_text().splitlines()]
                self.assertEqual(staged.read_bytes(), b'name: staged-image\ntemplate: 1\n')
                if rejected:
                    self.assertEqual(target.read_bytes(), target_config)
                    self.assertEqual(disk.read_bytes(), b'irreplaceable original VM disk')
                    self.assertEqual(operations, ['config', 'config'])
                else:
                    self.assertEqual(operations, ['config', 'config', 'destroy', 'clone', 'template'])
                    self.assertEqual(disk.read_bytes(), b'new image disk')

    def test_cloud_init_cleanup_failure_stops_subsequent_tasks(self):
        self.root.mkdir(parents=True)
        tasks = yaml.safe_load((UPSTREAM / 'tier-0/ansible/roles/template_refresh/tasks/main.yml').read_text())
        cleanup = next(task for task in tasks
                       if task.get('ansible.builtin.command', {}).get('argv', [])[:2] == ['cloud-init', 'clean'])
        # Run only the real cleanup task: never update packages, reboot or remove host keys.
        fake = self.root / 'cloud-init'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$CLEANUP_CALL"\nexit "$CLEANUP_RC"\n')
        fake.chmod(0o755)
        config = self.root / 'ansible.cfg'
        config.write_text('[defaults]\nstdout_callback = default\n')
        play = self.root / 'cleanup.json'
        play.write_text(json.dumps([{
            'name': 'Offline template cleanup', 'hosts': 'localhost', 'gather_facts': False,
            'environment': {'PATH': f'{self.root}:{os.environ["PATH"]}'},
            'vars': {'template_refresh_prepare_for_template': True, 'template_refresh_clean_cloud_init': True},
            'tasks': [cleanup, {'name': 'Continue after cleanup',
                                'ansible.builtin.debug': {'msg': 'CLEANUP_SUCCEEDED'}}],
        }]))
        for returncode in (42, 0):
            with self.subTest(cloud_init_returncode=returncode):
                call = self.root / f'cleanup-{returncode}.txt'
                env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_STDOUT_CALLBACK='default',
                           CLEANUP_RC=str(returncode), CLEANUP_CALL=str(call), ANSIBLE_NOCOLOR='1')
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(play)],
                                        cwd=self.root, env=env, capture_output=True, text=True)
                self.assertTrue(call.is_file(), result.stdout + result.stderr)
                self.assertEqual(call.read_text().strip(), 'clean --logs --machine-id')
                if returncode:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertNotIn('CLEANUP_SUCCEEDED', result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('CLEANUP_SUCCEEDED', result.stdout)


if __name__ == '__main__':
    unittest.main()
