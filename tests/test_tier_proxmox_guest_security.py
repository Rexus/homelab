"""Existing-VM TPM maintenance through actual native Ansible/Proxmoxer request semantics."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/proxmox_guest_security'
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('ansible-doc')


class ProxmoxGuestSecurityPayload(TierRepositoryTestCase):
    def test_generated_controller_recipe_and_missing_input_initialization(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0')
        owner = self.root / 'verify-tier-0'
        for source in ROLE.rglob('*.yml'):
            self.assertEqual((owner / source.relative_to(UPSTREAM / 'tier-0')).read_bytes(), source.read_bytes())
        result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'proxmox-guest-security'],
                                cwd=owner, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        local = owner / 'ansible/group_vars/proxmox_guest_security.yml'
        self.assertEqual(local.read_bytes(), local.with_suffix('.yml.example').read_bytes())
        local.write_text('proxmox_guest_security_vmid: 701\n')
        subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'proxmox-guest-security'],
                       cwd=owner, capture_output=True, check=True, timeout=30)
        self.assertEqual(local.read_text(), 'proxmox_guest_security_vmid: 701\n')
        self.assertFalse((owner / 'terraform/deployments/proxmox-guest-security').exists())
        plays = yaml.safe_load((owner / 'ansible/playbooks/deployment/proxmox-guest-security.yml').read_text())
        self.assertEqual(plays[0]['vars'], dict(control_node_setup='proxmox-guest-security',
                                               control_node_require_terraform=False))
        control = yaml.safe_load((owner / 'ansible/playbooks/control-node.yml').read_text())[0]['vars']
        self.assertEqual(control['control_node_setup_collection_names']['proxmox-guest-security'], ['community.proxmox'])
        self.assertEqual(plays[1]['hosts'], 'localhost')
        self.assertFalse(plays[1]['gather_facts'])


@unittest.skipUnless(NATIVE, 'Requires prepared native Ansible, community.proxmox and Proxmoxer')
class ProxmoxGuestSecurityNative(unittest.TestCase):
    def setUp(self):
        from proxmox_guest_security_api import GuestSecurityAPI
        self.temp = tempfile.TemporaryDirectory(prefix='guest-security-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        self.api = GuestSecurityAPI(self.root)
        self.addCleanup(self.api.close)
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_ROLES_PATH=str(ROLE.parent),
                        ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_INVENTORY_UNPARSED_WARNING='False',
                        PROXMOX_API_URL=self.api.endpoint, PROXMOX_API_TOKEN_ID='fixture@pve!maintenance',
                        PROXMOX_API_TOKEN_SECRET='fixture-api-only-value', PROXMOX_CA_FILE=str(self.api.ca),
                        NO_PROXY='localhost,127.0.0.1', no_proxy='localhost,127.0.0.1')
        self.env.pop('PROXMOX_VE_ENDPOINT', None)
        self.env.pop('PROXMOX_VE_API_TOKEN', None)
        self.inputs = dict(proxmox_guest_security_vmid=701, proxmox_guest_security_node='pve01',
                           proxmox_guest_security_name='vm-1', proxmox_guest_security_tpm_storage='local-zfs',
                           proxmox_guest_security_record=str(self.private / 'before.json'),
                           proxmox_guest_security_outage_approved=True, proxmox_guest_security_backup_retained=True,
                           proxmox_guest_security_backup_reference='pbs-independent:vm/701/accepted-snapshot')

    def run_role(self, operation='inspect', inputs=None, success=True, check_mode=False):
        variables = dict(self.inputs, proxmox_guest_security_operation=operation,
                         ansible_python_interpreter='{{ ansible_playbook_python }}')
        variables.update(inputs or {})
        path = self.root / 'play.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, roles=['proxmox_guest_security'])], sort_keys=False))
        command = ['ansible-playbook', '-i', 'localhost,', str(path)]
        if check_mode:
            command.append('--check')
        result = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        self.assertNotIn('private-fixture-cloud-init-value', output)
        self.assertNotIn('fixture-api-only-value', output)
        return output

    def prepare(self):
        self.run_role('prepare')
        record = Path(self.inputs['proxmox_guest_security_record'])
        self.inputs['proxmox_guest_security_record_sha256'] = hashlib.sha256(record.read_bytes()).hexdigest()
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.api.writes, [])
        return record

    def test_missing_tpm_addition_preserves_hardware_power_and_repeat_is_idempotent(self):
        original = deepcopy(self.api.config)
        self.run_role()
        record = self.prepare()
        record_bytes = record.read_bytes()
        self.run_role('check')
        self.assertEqual(self.api.writes, [])
        self.run_role('apply')
        self.assertEqual(self.api.status, 'running')
        self.assertEqual({key: value for key, value in self.api.config.items() if key not in ['tpmstate0', 'digest']},
                         {key: value for key, value in original.items() if key != 'digest'})
        self.assertEqual([(method, path) for method, path, _ in self.api.writes], [
            ('POST', '/nodes/pve01/qemu/701/status/shutdown'),
            ('PUT', '/nodes/pve01/qemu/701/config'), ('POST', '/nodes/pve01/qemu/701/status/start')])
        allocation = self.api.writes[1][2]
        self.assertEqual(allocation, dict(digest=original['digest'], tpmstate0='local-zfs:1,version=v2.0'))
        self.assertEqual(self.api.writes[0][2], dict(forceStop='0', timeout='180'))
        count = len(self.api.writes)
        self.run_role('apply')
        self.assertEqual(len(self.api.writes), count)
        self.assertEqual(record.read_bytes(), record_bytes)

    def test_stopped_vm_stays_stopped_and_existing_tpm_never_has_an_outage(self):
        self.api.status = 'stopped'
        self.prepare()
        self.run_role('apply')
        self.assertEqual(self.api.status, 'stopped')
        self.assertEqual([call[0] for call in self.api.writes], ['PUT'])
        self.api.calls.clear()
        self.inputs['proxmox_guest_security_record'] = str(self.private / 'existing.json')
        original = deepcopy(self.api.config)
        self.prepare()
        self.run_role('apply', dict(proxmox_guest_security_outage_approved=False,
                                    proxmox_guest_security_backup_retained=False))
        self.assertEqual(self.api.writes, [])
        self.assertEqual(self.api.config, original)

    def test_wrong_identity_template_lock_and_pending_edits_are_rejected_without_writes(self):
        for mode in ('identity', 'template', 'lock', 'pending', 'missing'):
            with self.subTest(mode=mode):
                self.api.template = mode == 'template'
                self.api.exists = mode != 'missing'
                self.api.config.pop('lock', None)
                if mode == 'lock':
                    self.api.config['lock'] = 'backup'
                self.api.pending = dict(memory=8192) if mode == 'pending' else {}
                self.api.refresh_digest()
                inputs = dict(proxmox_guest_security_name='wrong') if mode == 'identity' else {}
                self.run_role('inspect', inputs, success=False)
                self.assertEqual(self.api.writes, [])

    def test_missing_backup_outage_and_managed_ha_fail_before_shutdown(self):
        self.prepare()
        for inputs in (dict(proxmox_guest_security_outage_approved=False),
                       dict(proxmox_guest_security_backup_retained=False),
                       dict(proxmox_guest_security_backup_reference='')):
            with self.subTest(inputs=inputs):
                self.run_role('apply', inputs, success=False)
                self.assertEqual(self.api.writes, [])
        self.api.hastate = 'started'
        self.run_role('apply', success=False)
        self.assertEqual(self.api.writes, [])

    def test_changed_disk_and_record_or_tpm12_fail_without_api_mutation(self):
        record = self.prepare()
        original = deepcopy(self.api.config)
        self.api.config['scsi1'] = 'local-zfs:unexpected-data-disk,size=80G'
        self.api.refresh_digest()
        self.run_role('apply', success=False)
        self.api.config = original
        self.run_role('check', dict(proxmox_guest_security_record_sha256='0' * 64), success=False)
        record.chmod(0o644)
        self.run_role('check', success=False)
        record.chmod(0o600)
        self.api.config['tpmstate0'] = 'local-zfs:old-tpm,version=v1.2'
        self.api.refresh_digest()
        self.inputs['proxmox_guest_security_record'] = str(self.private / 'tpm12.json')
        self.prepare()
        self.run_role('apply', success=False)
        self.assertEqual(self.api.writes, [])

    def test_prepared_existing_tpm_cannot_change_identity(self):
        self.api.config['tpmstate0'] = 'local-zfs:original-tpm,version=v2.0'
        self.api.refresh_digest()
        self.prepare()
        self.api.config['tpmstate0'] = 'local-zfs:other-tpm,version=v2.0'
        self.api.refresh_digest()
        self.run_role('apply', success=False)
        self.assertEqual(self.api.writes, [])

    def test_shutdown_and_api_failures_never_force_or_start_an_unverified_vm(self):
        self.prepare()
        original = deepcopy(self.api.config)
        for failure in ('shutdown', 'changed-during-shutdown', 'digest', 'allocation', 'unexpected-after-allocation'):
            with self.subTest(failure=failure):
                self.api.config = deepcopy(original)
                self.api.status = 'running'
                self.api.calls.clear()
                self.api.failure = failure
                self.run_role('apply', success=False)
                self.assertFalse(any(call[1].endswith('/status/start') for call in self.api.writes))
                if failure == 'changed-during-shutdown':
                    self.assertFalse(any(call[0] == 'PUT' for call in self.api.writes))
                self.assertTrue(all(call[2].get('forceStop') == '0' for call in self.api.writes
                                    if call[1].endswith('/status/shutdown')))

    def test_invalid_storage_is_rejected_before_outage(self):
        self.prepare()
        for storage in (dict(storage='local-zfs', content='iso,backup'),
                        dict(storage='local-zfs', content='images', nodes='other-node'),
                        dict(storage='local-zfs', content='images', disable=1)):
            with self.subTest(storage=storage):
                self.api.storage = storage
                self.run_role('apply', success=False)
                self.assertEqual(self.api.writes, [])

    def test_invalid_modes_and_selections_fail_before_contacting_the_api(self):
        for inputs in (dict(proxmox_guest_security_vmid=True), dict(proxmox_guest_security_vmid='701'),
                       dict(proxmox_guest_security_node=''), dict(proxmox_guest_security_operation='replace-tpm'),
                       dict(proxmox_guest_security_shutdown_timeout=0)):
            with self.subTest(inputs=inputs):
                self.run_role('inspect', inputs, success=False)
                self.assertEqual(self.api.calls, [])
        self.run_role('apply', success=False, check_mode=True)
        self.assertEqual(self.api.calls, [])

    def test_native_module_schema_and_public_playbook_syntax(self):
        result = subprocess.run(['ansible-doc', '--json', 'community.proxmox.proxmox_kvm',
                                 'community.proxmox.proxmox_vm_info', 'community.proxmox.proxmox_storage_info'],
                                env=self.env, capture_output=True, text=True, check=True, timeout=45)
        modules = json.loads(result.stdout)
        for path in (ROLE / 'tasks').glob('*.yml'):
            def check(tasks):
                for task in tasks:
                    for key, value in task.items():
                        if key.startswith('community.proxmox.'):
                            self.assertTrue(set(value).issubset(modules[key]['doc']['options']), (path, key))
                        if key in ['block', 'rescue', 'always']:
                            check(value)
            check(yaml.safe_load(path.read_text()))
        tier = UPSTREAM / 'tier-0'
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '--syntax-check',
                                 'ansible/playbooks/deployment/proxmox-guest-security.yml'],
                                cwd=tier, env=dict(self.env, ANSIBLE_CONFIG=str(tier / 'ansible/ansible.cfg')),
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
