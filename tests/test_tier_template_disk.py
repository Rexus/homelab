"""Explicit same-VMID disk maintenance through native Ansible modules and a local API."""

import hashlib
import json
import os
import shutil
import subprocess
import unittest

from proxmox_template_disk_fixture import TemplateDiskApiFixture
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'ansible-doc', 'openssl', 'qemu-img')),
                     'Requires native Ansible, community.proxmox, OpenSSL and qemu-img')
class TemplateDiskMaintenance(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        check = subprocess.run(['ansible-doc', '-t', 'module', 'community.proxmox.proxmox_disk'],
                               capture_output=True, text=True)
        if check.returncode or 'was not found' in check.stderr:
            self.skipTest('Install Tier 0 community.proxmox requirements')
        self.root.mkdir(parents=True)
        image = self.root / 'approved.raw'
        image.write_bytes(b'approved fixture'.ljust(512, b'\0'))
        self.sha = hashlib.sha256(image.read_bytes()).hexdigest()
        cert, key = self.root / 'fixture.crt', self.root / 'fixture.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        self.api = TemplateDiskApiFixture(cert, key)
        self.addCleanup(self.api.close)
        self.vars = {
            'template_disk_key': 'rocky-build-1', 'template_disk_execute': False,
            'template_disk_receipt_dir': str(self.root / 'receipts'),
            'template_disk_expected_disk': 'local-zfs:base-110-disk-1',
            'template_disk_expected_sha256': self.sha,
            'template_disk_sources': {'value': {'rocky-build-1': {
                'vm_id': 110, 'name': 'rocky-template', 'node_name': 'pve01',
                'image_path': str(image), 'sha256': self.sha,
                'image_volume_id': 'local:import/approved.raw', 'datastore_id': 'local-zfs',
                'disk_size_gb': 10, 'iothread': True, 'discard': 'on', 'cache': 'none',
            }}},
        }
        self.env = dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / 'tier-0/ansible/ansible.cfg'),
                        PROXMOX_CA_FILE=str(cert),
                        PROXMOX_VE_ENDPOINT=f'https://127.0.0.1:{self.api.server.server_port}/',
                        PROXMOX_VE_API_TOKEN='fixture@pve!disk=fixture-not-a-secret')

    def run_recipe(self, **overrides):
        variables = dict(self.vars, **overrides)
        path = self.root / 'inputs.json'
        path.write_text(json.dumps(variables))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/maintenance/template-disk.yml'),
                                 '--extra-vars', '@' + str(path)], env=self.env, capture_output=True, text=True)
        self.assertNotIn('fixture-not-a-secret', result.stdout + result.stderr)
        return result

    def test_preview_execute_retention_and_replay_guard(self):
        result = self.run_recipe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.writes, [])
        self.assertFalse((self.root / 'receipts').exists())
        result = self.run_recipe(template_disk_execute=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.config['unused0'], 'local-zfs:base-110-disk-1')
        self.assertTrue(self.api.config['scsi0'].startswith('local-zfs:base-110-disk-2,'))
        self.assertIn('size=10G', self.api.config['scsi0'])
        self.assertEqual({key: value for key, value in self.api.config.items()
                          if key not in ('scsi0', 'unused0')},
                         {key: value for key, value in self.api.original.items() if key != 'scsi0'})
        self.assertEqual(len(self.api.writes), 2)
        self.assertEqual(len(list((self.root / 'receipts').glob('*.json'))), 2)
        result = self.run_recipe(template_disk_execute=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.api.writes), 2)

    def test_wrong_disk_hash_running_vm_and_oversized_image_are_read_only(self):
        for overrides in ({'template_disk_expected_disk': 'local-zfs:wrong'},
                          {'template_disk_expected_sha256': '0' * 64}):
            result = self.run_recipe(template_disk_execute=True, **overrides)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.api.status = 'running'
        self.assertNotEqual(self.run_recipe(template_disk_execute=True).returncode, 0)
        self.api.status = 'stopped'
        self.vars['template_disk_sources']['value']['rocky-build-1']['disk_size_gb'] = 0
        self.assertNotEqual(self.run_recipe(template_disk_execute=True).returncode, 0)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(self.api.config, self.api.original)

    def test_failed_import_preserves_original_disk_and_records_receipt(self):
        self.api.fail_import = True
        result = self.run_recipe(template_disk_execute=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.config, self.api.original)
        self.assertEqual(len(self.api.writes), 1)
        self.assertEqual(len(list((self.root / 'receipts').glob('*.json'))), 2)


class TemplateDiskWrapper(TierRepositoryTestCase):
    def test_generated_recipe_and_native_sources_remain_tier_zero_owned(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for relative in ('ansible/playbooks/maintenance/template-disk.yml',
                         'ansible/roles/proxmox_template_disk/tasks/main.yml',
                         'ansible/roles/proxmox_template_disk/tasks/replace.yml'):
            self.assertTrue((repo / relative).is_file())
            self.assertFalse((self.root / 'verify-shared' / relative).exists())
        source = (repo / 'ansible/roles/proxmox_template_disk/tasks/replace.yml').read_text()
        self.assertIn('community.proxmox.proxmox_disk:', source)
        self.assertIn('create: forced', source)
        self.assertNotIn('state: absent', source)
        self.assertIn('community.proxmox', (repo / 'ansible/requirements.yml').read_text())
        self.assertIn('template-disk:', (repo / 'ansible/playbooks/control-node.yml').read_text())

    @unittest.skipIf(os.name == 'nt', 'Requires Linux/WSL Bash')
    def test_execution_requires_pinned_intent_and_only_refreshes_state(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        subprocess.run(['bash', 'scripts/proxmox-templates.sh', 'init'], cwd=repo, check=True, capture_output=True)
        commands = self.root / 'commands'
        commands.mkdir()
        log = self.root / 'calls.jsonl'
        for tool in ('terraform', 'ansible-doc', 'ansible-playbook'):
            path = commands / tool
            path.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['TEST_COMMAND_LOG'], 'a') as output:
    output.write(json.dumps({'tool': pathlib.Path(sys.argv[0]).name, 'args': sys.argv[1:]}) + '\\n')
if 'output' in sys.argv: print('{}')
''')
            path.chmod(0o755)
        env = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'], TEST_COMMAND_LOG=str(log))

        def run(*args):
            return subprocess.run(['bash', 'scripts/proxmox-templates.sh', *args], cwd=repo,
                                  env=env, capture_output=True, text=True)

        result = run('replace-disk', '--template', 'rocky', '--execute')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(log.exists())
        result = run('replace-disk', '--template', 'rocky')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertFalse(any('apply' in call['args'] for call in calls))
        plan = repo / '.terraform/plans/proxmox-templates.tfplan'
        plan.write_text('obsolete plan')
        result = run('replace-disk', '--template', 'rocky', '--execute',
                     '--expected-disk', 'local-zfs:base-110-disk-1', '--expected-sha256', 'a' * 64)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        apply = [call for call in calls if 'apply' in call['args']]
        self.assertEqual(len(apply), 1)
        self.assertIn('-refresh-only', apply[0]['args'])
        self.assertFalse(plan.exists())
        self.assertNotEqual(run('init', '--execute').returncode, 0)
