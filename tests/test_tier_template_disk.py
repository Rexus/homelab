"""Explicit same-VMID disk maintenance through native Ansible modules and a local API."""

import hashlib
import json
import os
import shutil
import subprocess
import unittest

from proxmox_template_disk_fixture import TemplateDiskApiFixture, run_with_terminal
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'ansible-doc', 'openssl', 'qemu-img')),
                     'Requires native Ansible, community.proxmox, OpenSSL and qemu-img')
class TemplateDiskMaintenance(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        modules = ['community.proxmox.proxmox_disk', 'community.proxmox.proxmox_vm_info']
        check = subprocess.run(['ansible-doc', '--json', '-t', 'module', *modules],
                               capture_output=True, text=True)
        if check.returncode or not set(modules).issubset(json.loads(check.stdout)):
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
            'template_disk_result_file': str(self.root / 'result.json'),
            'template_disk_plan_file': str(self.root / 'publication.tfplan'),
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
                        ANSIBLE_NOCOLOR='1',
                        PROXMOX_CA_FILE=str(cert),
                        PROXMOX_VE_ENDPOINT=f'https://127.0.0.1:{self.api.server.server_port}/',
                        PROXMOX_VE_API_TOKEN='fixture@pve!disk=fixture-not-a-secret')

    def run_recipe(self, answer=None, on_prompt=None, **overrides):
        variables = dict(self.vars, **overrides)
        path = self.root / 'inputs.json'
        path.write_text(json.dumps(variables))
        arguments = ['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                     str(UPSTREAM / 'tier-0/ansible/playbooks/maintenance/template-disk.yml'),
                     '--extra-vars', '@' + str(path)]
        result = (subprocess.run(arguments, env=self.env, capture_output=True, text=True) if answer is None
                  else run_with_terminal(arguments, self.env, answer, on_prompt))
        self.assertNotIn('fixture-not-a-secret', result.stdout + result.stderr)
        return result

    def test_preview_execute_retention_and_replay_guard(self):
        result = self.run_recipe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.writes, [])
        self.assertFalse((self.root / 'receipts').exists())
        self.assertIn('"ballooning_disabled": true', result.stdout)
        result = self.run_recipe(template_disk_execute=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.config['unused0'], 'local-zfs:base-110-disk-1')
        self.assertTrue(self.api.config['scsi0'].startswith('local-zfs:base-110-disk-2,'))
        self.assertIn('size=10G', self.api.config['scsi0'])
        self.assertEqual({key: value for key, value in self.api.config.items()
                          if key not in ('scsi0', 'unused0')},
                         {key: value for key, value in self.api.original.items() if key != 'scsi0'})
        self.assertEqual(len(self.api.writes), 3)
        self.assertEqual(self.api.writes[-1][1:], ('/api2/json/nodes/pve01/qemu/110/template', {'disk': 'scsi0'}))
        self.assertEqual(len(list((self.root / 'receipts').glob('*.json'))), 2)
        for message in ('"verification": "passed"', '"new_boot_volume": "local-zfs:base-110-disk-2"',
                        '"retained_old_disk": true', 'size=10G'):
            self.assertIn(message, result.stdout)
        receipt = json.loads(next((self.root / 'receipts').glob('*.after.json')).read_text())
        self.assertEqual(receipt['sha256'], self.sha)
        self.assertEqual(receipt['source'], self.vars['template_disk_sources']['value']['rocky-build-1']['image_volume_id'])
        result = self.run_recipe(template_disk_execute=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.api.writes), 3)

    @unittest.skipUnless(shutil.which('script'), 'Requires util-linux script for a controlling terminal')
    def test_interactive_decline_empty_and_yes_use_the_shown_values(self):
        plan = self.root / 'publication.tfplan'
        plan.write_text('existing publication plan')
        for answer in ('no', ''):
            result = self.run_recipe(answer=answer, template_disk_interactive=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.api.writes, [])
            self.assertTrue(plan.exists())
            self.assertFalse(json.loads((self.root / 'result.json').read_text())['changed'])
        result = self.run_recipe(answer='yes', template_disk_interactive=True,
                                 template_disk_expected_disk='', template_disk_expected_sha256='')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"verification": "passed"', result.stdout)
        self.assertTrue(self.api.config['scsi0'].startswith('local-zfs:base-110-disk-2,'))
        self.assertEqual(self.api.config['unused0'], self.api.original['scsi0'].split(',')[0])
        self.assertFalse(plan.exists())
        self.assertTrue(json.loads((self.root / 'result.json').read_text())['changed'])

    @unittest.skipUnless(shutil.which('script'), 'Requires util-linux script for a controlling terminal')
    def test_changed_template_during_confirmation_blocks_all_writes(self):
        result = self.run_recipe(answer='yes', template_disk_interactive=True,
                                 on_prompt=lambda: self.api.config.update(memory=4096))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('template changed after the preview', result.stdout)
        self.assertEqual(self.api.writes, [])

    def test_failed_base_conversion_retains_both_volumes_and_receipts(self):
        self.api.fail_base_task = True
        result = self.run_recipe(template_disk_execute=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.api.config['unused0'], self.api.original['scsi0'].split(',')[0])
        self.assertTrue(self.api.config['scsi0'].startswith('local-zfs:vm-110-disk-2,'))
        self.assertEqual(len(list((self.root / 'receipts').glob('*.json'))), 2)
        self.assertFalse((self.root / 'result.json').exists())

    def test_denied_base_conversion_explains_permissions_and_keeps_rollback(self):
        self.api.fail_base_http = True
        result = self.run_recipe(template_disk_execute=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTP 403', result.stdout)
        self.assertIn('VM.Allocate', result.stdout)
        self.assertEqual(self.api.config['unused0'], self.api.original['scsi0'].split(',')[0])
        self.assertEqual(len(list((self.root / 'receipts').glob('*.json'))), 2)
        self.assertFalse((self.root / 'result.json').exists())

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

    def test_vmid_instead_of_catalog_key_lists_choices_without_api_access(self):
        result = self.run_recipe(template_disk_key='110')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        for message in ("Unknown template catalog key '110'", 'rocky-build-1', 'VMID 110'):
            self.assertIn(message, result.stdout)
        self.assertEqual(self.api.reads, [])
        self.assertEqual(self.api.writes, [])

    def test_preview_reports_implicit_or_enabled_ballooning_without_changing_it(self):
        for balloon in (None, 2048):
            with self.subTest(balloon=balloon):
                self.api.config.pop('balloon', None)
                if balloon is not None:
                    self.api.config['balloon'] = balloon
                result = self.run_recipe()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('"ballooning_disabled": false', result.stdout)
        self.assertEqual(self.api.writes, [])


class TemplateDiskWrapper(TierRepositoryTestCase):
    def test_generated_recipe_and_native_sources_remain_tier_zero_owned(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for relative in ('ansible/playbooks/maintenance/template-disk.yml',
                         'ansible/roles/proxmox_template_disk/tasks/main.yml',
                         'ansible/roles/proxmox_template_disk/tasks/confirm.yml',
                         'ansible/roles/proxmox_template_disk/tasks/base.yml',
                         'ansible/roles/proxmox_template_disk/tasks/replace.yml'):
            self.assertTrue((repo / relative).is_file())
            self.assertFalse((self.root / 'verify-shared' / relative).exists())
        source = (repo / 'ansible/roles/proxmox_template_disk/tasks/replace.yml').read_text()
        self.assertIn('community.proxmox.proxmox_disk:', source)
        self.assertIn('create: forced', source)
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
    output.write(json.dumps({'tool': pathlib.Path(sys.argv[0]).name, 'args': sys.argv[1:],
                             'ansible_config': os.getenv('ANSIBLE_CONFIG'),
                             'version_mismatch': os.getenv('ANSIBLE_COLLECTIONS_ON_ANSIBLE_VERSION_MISMATCH')}) + '\\n')
if 'output' in sys.argv: print('{}')
if pathlib.Path(sys.argv[0]).name == 'ansible-doc':
    print(json.dumps({name: {'doc': {'module': name}} for name in sys.argv[1:]
                      if name.startswith('community.proxmox.') and name != os.getenv('MISSING_MODULE')}))
if pathlib.Path(sys.argv[0]).name == 'ansible-playbook':
    result = next(json.loads(arg)['template_disk_result_file'] for arg in sys.argv[1:]
                  if arg.startswith('{') and 'template_disk_result_file' in arg)
    changed = ('template_disk_execute=true' in sys.argv or
               ('template_disk_interactive=true' in sys.argv and os.getenv('TEST_APPROVE') == 'yes'))
    pathlib.Path(result).write_text(json.dumps({'changed': changed}))
''')
            path.chmod(0o755)
        for tool in ('bash', 'dirname', 'basename', 'mkdir', 'python3'):
            (commands / tool).symlink_to(shutil.which(tool))
        env = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'], TEST_COMMAND_LOG=str(log))

        def run(*args, **overrides):
            return subprocess.run(['bash', 'scripts/proxmox-templates.sh', *args], cwd=repo,
                                  env=dict(env, **overrides), capture_output=True, text=True)

        result = run('replace-disk', '--template', 'rocky', '--execute')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(log.exists())
        result = run('replace-disk', '--template', 'rocky', PATH=str(commands))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('sudo dnf install -y /usr/bin/qemu-img', result.stderr)
        self.assertIn('sudo apt-get install -y qemu-utils', result.stderr)
        self.assertFalse(log.exists(), 'Missing OS tools must stop before Terraform or Ansible runs')
        for missing in ('community.proxmox.proxmox_vm_info', 'community.proxmox.proxmox_disk'):
            before = len(log.read_text().splitlines()) if log.exists() else 0
            result = run('replace-disk', '--template', 'rocky', MISSING_MODULE=missing)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(missing, result.stderr)
            self.assertIn('ansible-galaxy collection install', result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()[before:]]
            self.assertFalse(any(call['tool'] == 'ansible-playbook' for call in calls))
            self.assertFalse(any('apply' in call['args'] for call in calls))
        result = run('replace-disk', '--template', 'rocky', '--preview')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('No disk changed.', result.stdout)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertFalse(any('apply' in call['args'] for call in calls))
        self.assertTrue(all(call['ansible_config'] == str(repo / 'ansible/ansible.cfg')
                            for call in calls if call['tool'] in ('ansible-doc', 'ansible-playbook')))
        self.assertTrue(all(call['version_mismatch'] == 'error'
                            for call in calls if call['tool'] in ('ansible-doc', 'ansible-playbook')))
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
        self.assertNotEqual(run('replace-disk', '--template', 'rocky', '--preview', '--execute').returncode, 0)
        for approved in ('no', 'yes'):
            plan.write_text('reviewed publication plan')
            log.write_text('')
            result = run('replace-disk', '--template', 'rocky', TEST_APPROVE=approved)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            play = next(call for call in calls if call['tool'] == 'ansible-playbook')
            self.assertIn('template_disk_interactive=true', play['args'])
            self.assertEqual(sum('-refresh-only' in call['args'] for call in calls), int(approved == 'yes'))
            self.assertEqual(plan.exists(), approved == 'no')
            self.assertFalse(list((repo / '.terraform/plans').glob('template-disk-result.*')))

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-doc') and shutil.which('qemu-img'),
                         'Requires native Ansible and qemu-img on Linux/WSL')
    def test_incompatible_collection_stops_before_terraform_or_maintenance(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        subprocess.run(['bash', 'scripts/proxmox-templates.sh', 'init'], cwd=repo, check=True, capture_output=True)
        collection_path = self.root / 'collections'
        collection = collection_path / 'ansible_collections/community/proxmox'
        (collection / 'meta').mkdir(parents=True)
        (collection / 'meta/runtime.yml').write_text('requires_ansible: ">=99.0.0"\n')
        (collection / 'plugins/modules').mkdir(parents=True)
        for name in ('proxmox_vm_info', 'proxmox_disk'):
            (collection / f'plugins/modules/{name}.py').write_text('DOCUMENTATION = """\n'
                f'module: {name}\nshort_description: Version-check fixture\n'
                'description: Version-check fixture.\nauthor: Test fixture\n"""\n')
        commands = self.root / 'commands'
        commands.mkdir()
        log = self.root / 'terraform-called'
        terraform = commands / 'terraform'
        terraform.write_text('#!/usr/bin/env python3\nimport os, pathlib\n'
                             'pathlib.Path(os.environ["TEST_COMMAND_LOG"]).touch()\n')
        terraform.chmod(0o755)
        env = dict(os.environ, PATH=str(commands) + ':' + os.environ['PATH'],
                   ANSIBLE_COLLECTIONS_PATH=str(collection_path), TEST_COMMAND_LOG=str(log),
                   ANSIBLE_COLLECTIONS_ON_ANSIBLE_VERSION_MISMATCH='ignore')
        result = subprocess.run(['bash', 'scripts/proxmox-templates.sh', 'replace-disk',
                                 '--template', 'rocky-build-1'], cwd=repo, env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('does not support Ansible version', result.stderr)
        self.assertIn('ansible-core >=2.17', result.stderr)
        self.assertFalse(log.exists())
        self.assertFalse((repo / '.terraform/plans/template-disk-inputs.json').exists())
