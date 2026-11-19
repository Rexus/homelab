"""Bounded ceremony permissions, inherited-access rejection and native lifecycle contracts."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/ceremony_access'
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook')
SESSIONS = {'cadm-1': {'vm_id': 621, 'node_name': 'pve01'},
            'orca-1': {'vm_id': 623, 'node_name': 'pve01'}}


def tasks(name):
    return yaml.safe_load((ROLE / f'tasks/{name}.yml').read_text())


class CeremonyAccessContract(TierRepositoryTestCase):
    def test_generated_roles_and_inputs_have_one_native_owner(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0')
        owner = self.root / 'verify-tier-0'
        for source in ROLE.rglob('*'):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (owner / source.relative_to(UPSTREAM / 'tier-0')).read_bytes())
        for name in ('ceremony-access', 'ceremony-power'):
            play = yaml.safe_load((owner / f'ansible/playbooks/{name}.yml').read_text())
            self.assertEqual(play[0]['vars']['control_node_setup'], name)
            self.assertFalse(play[0]['vars']['control_node_require_terraform'])
        self.assertTrue((owner / 'ansible/group_vars/ceremony_access.yml.example').is_file())
        catalog = yaml.safe_load((owner / 'ansible/playbooks/control-node.yml').read_text())[0]['vars']
        for name in ('ceremony-access', 'ceremony-power'):
            self.assertEqual(catalog['control_node_setup_collection_names'][name], ['community.proxmox'])

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'Requires native Bash')
    def test_initializer_creates_and_preserves_the_generated_access_configuration(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0')
        owner = self.root / 'verify-tier-0'
        for setup in ('ceremony-access', 'ceremony-schedule'):
            command = ['bash', 'scripts/init-local-files.sh', '--setup', setup]
            result = subprocess.run(command, cwd=owner, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            local = owner / f"ansible/group_vars/{setup.replace('-', '_')}.yml"
            self.assertEqual(local.read_bytes(), local.with_suffix('.yml.example').read_bytes())
            local.write_text('retained_local_choice: true\n')
            retained = local.read_bytes()
            result = subprocess.run(command, cwd=owner, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(local.read_bytes(), retained)
            self.assertFalse((owner / f'terraform/deployments/{setup}').exists())

    def test_roles_separate_console_power_and_provisioning(self):
        roles = yaml.safe_load((ROLE / 'vars/main.yml').read_text())['ceremony_access_roles']
        self.assertEqual(roles['CeremonyPower'], ['VM.Audit', 'VM.PowerMgmt'])
        self.assertEqual(roles['CeremonyConsole'], ['VM.Audit', 'VM.Console'])
        self.assertEqual(roles['CeremonyISO'], ['Datastore.Audit', 'Datastore.AllocateTemplate'])
        for name, privileges in roles.items():
            self.assertNotIn('Permissions.Modify', privileges, name)
            self.assertNotIn('Sys.Modify', privileges, name)
            self.assertNotIn('Sys.PowerMgmt', privileges, name)
            self.assertNotIn('VM.GuestAgent.Unrestricted', privileges, name)
            self.assertNotIn('VM.Config.Network', privileges, name)

    def test_native_writes_protect_credentials_and_fixed_lease_has_no_signing_authority(self):
        configure = tasks('configure')
        user = next(t for t in configure if 'community.proxmox.proxmox_user' in t)
        self.assertTrue(user['community.proxmox.proxmox_user']['tokens'][0]['privsep'])
        self.assertTrue(user['no_log'])
        copy = next(t for t in configure if 'ansible.builtin.copy' in t)
        self.assertTrue(copy['no_log'])
        self.assertFalse(copy['diff'])
        self.assertEqual(copy['ansible.builtin.copy']['mode'], '0600')
        service = (ROLE / 'templates/ceremony-provision-lease.service.j2').read_text()
        self.assertIn('ExecStart=/usr/sbin/pveum user modify ceremony-provision@pve --enable 0', service)
        self.assertIn('ExecStart=/usr/sbin/pveum user modify ceremony-power@pve --enable 1', service)
        self.assertLess(service.index('ceremony-provision@pve'), service.index('ceremony-power@pve'))
        self.assertEqual(service.count('ExecStart='), 2)
        self.assertNotIn('SECRET', service)
        timer = (ROLE / 'templates/ceremony-provision-lease.timer.j2').read_text()
        self.assertIn('Persistent=true', timer)
        self.assertIn('OnCalendar=', timer)
        power = (UPSTREAM / 'tier-0/ansible/roles/ceremony_power/tasks/main.yml').read_text()
        self.assertIn("['status', 'start']", power)
        self.assertNotIn('state: stopped', power)
        self.assertNotIn('proxmox_qemu_api', power)

    def test_optional_scheduler_is_one_window_non_root_and_never_catches_up(self):
        schedule = ROLE.parent / 'ceremony_schedule'
        timer = (schedule / 'templates/ceremony-wake.timer.j2').read_text()
        service = (schedule / 'templates/ceremony-wake.service.j2').read_text()
        self.assertIn('Persistent=false', timer)
        self.assertIn('User={{ ceremony_schedule_account.stdout }}', service)
        self.assertIn('EnvironmentFile=/etc/homelab/ceremony/wake-', service)
        self.assertIn('CONTROL_NODE_COLLECTIONS_MODE=check', service)
        self.assertIn('ceremony_power_action=start', service)
        self.assertNotIn('TOKEN_SECRET=', service)
        self.assertNotIn('ExecStop=', service)
        remove = (schedule / 'tasks/remove.yml').read_text()
        self.assertNotIn('community.proxmox.', remove)
        self.assertNotIn('ceremony-provision', remove)


@unittest.skipUnless(NATIVE, 'Requires prepared native Linux Ansible')
class CeremonyAccessNative(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ceremony-access-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_ROLES_PATH=str(ROLE.parent),
                        ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_INVENTORY_UNPARSED_WARNING='False')

    def run_tasks(self, inputs=None, selected=None, success=True):
        variables = dict(ceremony_access_endpoint='https://pve01.example.internal:8006/',
                         ceremony_access_audit_host='pve01', ceremony_access_sessions=deepcopy(SESSIONS),
                         ceremony_access_token_expire=int(time.time()) + 36000,
                         ceremony_access_credentials_directory=str(self.root))
        variables.update(inputs or {})
        selected = selected or [{'ansible.builtin.include_role': dict(name='ceremony_access', tasks_from='validate')}]
        path = self.root / 'check.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                            vars=variables, tasks=selected)], sort_keys=False))
        inventory = self.root / 'inventory.yml'
        inventory.write_text('all:\n  children:\n    hypervisors:\n      hosts:\n        pve01: {}\n')
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-i', str(inventory), str(path)],
                                cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        return output

    def plan_tasks(self):
        return [{'ansible.builtin.include_role': dict(name='ceremony_access', tasks_from=name)}
                for name in ('validate', 'plan')]

    def test_exact_future_vm_paths_and_both_sides_of_separated_tokens(self):
        assertions = ["ceremony_access_vm_paths | sort == ['/vms/621', '/vms/623']",
                      "ceremony_access_expected_acls | selectattr('path', 'equalto', '/') | list | length == 0",
                      "ceremony_access_expected_acls | selectattr('path', 'equalto', '/vms') | list | length == 0",
                      "ceremony_access_expected_acls | selectattr('ugid', 'equalto', 'ceremony-power@pve!maintenance') | list | length == 2",
                      "ceremony_access_expected_acls | selectattr('ugid', 'equalto', 'ceremony-power@pve') | list | length == 2",
                      "ceremony_access_expected_acls | selectattr('ugid', 'equalto', 'automation@pve') | selectattr('roleid', 'equalto', 'NoAccess') | list | length == 5"]
        self.run_tasks(dict(ceremony_access_usb_mappings=['orca-work']),
                       self.plan_tasks() + [{'ansible.builtin.assert': dict(that=assertions)}])

    def test_invalid_scopes_fail_before_any_api_call(self):
        invalid = [dict(ceremony_access_sessions={}),
                   dict(ceremony_access_sessions={'orca-1': {'vm_id': True, 'node_name': 'pve01'}}),
                   dict(ceremony_access_sessions={'orca-1': {'vm_id': 623, 'node_name': 'unknown'}}),
                   dict(ceremony_access_sessions={'orca-1': {'vm_id': 623, 'node_name': 'pve01', 'privs': ['Administrator']}}),
                   dict(ceremony_access_iso_datastore='local'),
                   dict(ceremony_access_endpoint='http://pve01:8006/'),
                   dict(ceremony_access_excluded_users=[]),
                   dict(ceremony_access_excluded_users=['root@pam']),
                   dict(ceremony_access_custodians=['automation@pve']),
                   dict(ceremony_access_token_expire=0),
                   dict(ceremony_access_window_seconds=86400)]
        for inputs in invalid:
            with self.subTest(inputs=inputs):
                self.run_tasks(inputs, success=False)

    def verify_identity(self, name, grants, success=True):
        selected = self.plan_tasks() + [{
            'ansible.builtin.include_role': dict(name='ceremony_access', tasks_from='verify-identity'),
            'vars': {'ceremony_access_identity': dict(item=name, stdout=json.dumps(grants))},
        }]
        return self.run_tasks(selected=selected, success=success)

    def test_effective_power_permissions_reject_console_and_unrelated_or_root_scope(self):
        valid = {'/vms/621': {'VM.Audit': 0, 'VM.PowerMgmt': 0},
                 '/vms/623': {'VM.Audit': 0, 'VM.PowerMgmt': 0}}
        self.verify_identity('ceremony-power@pve!maintenance', valid)
        for extra in ({'/': {'Sys.Audit': 1}}, {'/vms/901': {'VM.PowerMgmt': 1}},
                      {'/vms/621': {'VM.Audit': 0, 'VM.PowerMgmt': 0, 'VM.Console': 1}}):
            self.verify_identity('ceremony-power@pve!maintenance', dict(valid, **extra), success=False)
        self.verify_identity('ceremony-power@pve!maintenance', {'/vms/621': valid['/vms/621']}, success=False)

    def test_ordinary_automation_inherited_vm_or_iso_access_is_rejected(self):
        self.verify_identity('automation@pve', {})
        self.verify_identity('automation@pve', {'/vms/623': {'VM.Config.CDROM': 1}}, success=False)
        self.verify_identity('automation@pve', {'/storage/ceremony-iso': {'Datastore.AllocateTemplate': 1}}, success=False)

    def test_lease_renders_absolute_deadline_and_fixed_revocation_order(self):
        selected = [{'ansible.builtin.include_role': dict(name='ceremony_access', tasks_from='plan')},
                    {'ansible.builtin.template': dict(src=str(ROLE / 'templates/ceremony-provision-lease.timer.j2'),
                                                     dest=str(self.root / 'lease.timer'))}]
        self.run_tasks(dict(ceremony_access_lease_deadline=1800000000), selected)
        rendered = (self.root / 'lease.timer').read_text()
        self.assertIn('OnCalendar=2027-01-15 08:00:00 UTC', rendered)

    def test_expiration_and_lease_epoch_are_correct_outside_utc(self):
        self.env['TZ'] = 'Europe/Stockholm'
        self.run_tasks(dict(ceremony_access_token_expire=int(time.time()) - 60), success=False)
        lease = tasks('lease')[:2]
        lease[0].pop('delegate_to')
        lease[0].pop('become')
        lease.append({'ansible.builtin.assert': {'that': [
            'ceremony_access_lease_deadline | int - ceremony_access_lease_clock.stdout | int == 3600',
            f'ceremony_access_lease_deadline | int >= {int(time.time()) + 3590}',
        ]}})
        self.run_tasks(dict(ceremony_access_action='unlock', ceremony_access_window_seconds=3600), lease)

    @unittest.skipUnless(shutil.which('ansible-doc'), 'Requires the prepared native collection catalog')
    def test_declared_native_modules_accept_all_supplied_arguments(self):
        modules = {}

        def collect(items):
            for task in items:
                for key, arguments in task.items():
                    if key.startswith('community.proxmox.'):
                        modules.setdefault(key, []).append(arguments or {})
                for key in ('block', 'rescue', 'always'):
                    if key in task:
                        collect(task[key])

        for path in ROLE.glob('tasks/*.yml'):
            collect(yaml.safe_load(path.read_text()))
        collect(yaml.safe_load((ROLE.parent / 'ceremony_power/tasks/main.yml').read_text()))
        result = subprocess.run(['ansible-doc', '-t', 'module', '-j', *modules],
                                env=self.env, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        catalog = json.loads(result.stdout)
        for name, calls in modules.items():
            options = catalog[name]['doc']['options']
            for call in calls:
                self.assertFalse(set(call).difference(options), (name, call))

    def schedule_inputs(self):
        for relative in ('ansible/playbooks/ceremony-power.yml', 'ansible/group_vars/ceremony_access.yml'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture: true\n')
        secret = self.root / '.env.ceremony-operator'
        secret.write_text('PROXMOX_API_URL=https://pve01.example.internal:8006/\n'
                          'PROXMOX_API_TOKEN_ID=ceremony-power@pve!maintenance\n'
                          'PROXMOX_API_TOKEN_SECRET=00000000-0000-4000-8000-000000000000\n')
        secret.chmod(0o600)
        return dict(ceremony_schedule_enabled=True, ceremony_schedule_session='orca-1',
                    ceremony_schedule_repository=str(self.root),
                    ceremony_schedule_ansible_playbook=shutil.which('ansible-playbook'),
                    ceremony_access_token_id='maintenance',
                    ceremony_schedule_calendar=datetime.fromtimestamp(time.time() + 3600, timezone.utc)
                    .strftime('%Y-%m-%d %H:%M:%S UTC'))

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'Requires native systemd calendar validation')
    def test_scheduler_preflight_and_rejections_do_not_mutate_the_controller(self):
        schedule = ROLE.parent / 'ceremony_schedule'
        selected = yaml.safe_load((schedule / 'tasks/main.yml').read_text())[:1]
        selected += yaml.safe_load((schedule / 'tasks/install.yml').read_text())[:12]
        inputs = self.schedule_inputs()
        self.run_tasks(inputs, selected)
        output = self.run_tasks(dict(inputs, ceremony_schedule_ansible_playbook=str(self.root / 'missing-ansible-playbook')),
                                selected, success=False)
        self.assertIn('Prepare ceremony-power dependencies', output)
        self.assertNotIn('is undefined', output)
        for relative in ('ansible/group_vars/ceremony_access.yml', '.env.ceremony-operator'):
            missing = self.root / relative
            retained = missing.read_bytes()
            missing.unlink()
            try:
                output = self.run_tasks(inputs, selected, success=False)
                self.assertIn('Prepare ceremony-power dependencies', output)
                self.assertNotIn('is undefined', output)
            finally:
                missing.write_bytes(retained)
                if relative.startswith('.env.'):
                    missing.chmod(0o600)
        self.run_tasks(dict(inputs, ceremony_access_token_expire=int(time.time()) + 60), selected, success=False)
        self.run_tasks(dict(inputs, ceremony_schedule_calendar='*-*-* 09:00:00 UTC'), selected, success=False)
        secret = self.root / '.env.ceremony-operator'
        secret.write_text(secret.read_text().replace('ceremony-power@pve', 'ceremony-provision@pve'))
        secret.chmod(0o600)
        self.run_tasks(inputs, selected, success=False)

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'Requires native systemd unit validation')
    def test_scheduler_units_render_and_pass_native_systemd_verification(self):
        schedule = ROLE.parent / 'ceremony_schedule'
        inputs = self.schedule_inputs()
        inputs['ceremony_schedule_account'] = {'stdout': os.environ.get('USER', 'nobody')}
        selected = [
            {'ansible.builtin.template': dict(src=str(schedule / f'templates/ceremony-wake.{kind}.j2'),
                                             dest=str(self.root / f'ceremony-wake-orca-1.{kind}'))}
            for kind in ('service', 'timer')]
        self.run_tasks(inputs, selected)
        result = subprocess.run(['systemd-analyze', 'verify', str(self.root / 'ceremony-wake-orca-1.service'),
                                 str(self.root / 'ceremony-wake-orca-1.timer')], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_iso_store_binding_and_directory_cannot_be_silently_repointed(self):
        guard = tasks('storage-guard')
        expected = dict(storage='ceremony-iso', type='dir', path='/var/lib/vz/ceremony-iso',
                        content=['iso'], nodes=['pve01'], shared=False)

        def check(storages, symlink=False, success=True):
            selected = deepcopy(guard)
            selected[0] = {'ansible.builtin.set_fact': {'ceremony_access_storage_info': {'proxmox_storages': storages}}}
            selected[4] = {'ansible.builtin.set_fact': {'ceremony_access_storage_paths': {
                'results': [{'stat': {'exists': True, 'isdir': not symlink, 'islnk': symlink}}]}}}
            return self.run_tasks(dict(ceremony_access_iso_datastore='ceremony-iso',
                                       ceremony_access_iso_directory='/var/lib/vz/ceremony-iso'),
                                  selected=self.plan_tasks() + selected, success=success)

        check([])
        check([expected])
        for changes in (dict(path='/var/lib/vz/old'), dict(type='nfs'), dict(content=['iso', 'images']),
                        dict(nodes=['pve02']), dict(shared=True)):
            check([dict(expected, **changes)], success=False)
        check([expected], symlink=True, success=False)
        check([dict(expected, storage='ordinary-template-images')], success=False)

    def test_activation_rejects_nics_guest_agent_and_os_disks_before_any_power_request(self):
        selected = [{'ansible.builtin.include_role': dict(name='ceremony_power', tasks_from='validate-hardware')}]
        live = dict(ide2='ceremony-iso:iso/ceremony-approved.iso,media=cdrom', agent='0')
        self.run_tasks(dict(ceremony_power_configuration=live), selected)
        self.run_tasks(dict(ceremony_power_configuration=dict(live, agent='enabled=0,fstrim_cloned_disks=1')), selected)
        for changes in (dict(net0='virtio=BC:24:11:00:00:01,bridge=dmz'), dict(agent='1'),
                        dict(agent='enabled=1'), dict(scsi0='local-zfs:vm-623-disk-0'),
                        dict(ide2='local-zfs:vm-623-disk-0')):
            self.run_tasks(dict(ceremony_power_configuration=dict(live, **changes)), selected, success=False)


if __name__ == '__main__':
    unittest.main()
