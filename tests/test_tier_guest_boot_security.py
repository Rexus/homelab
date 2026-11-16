"""Native guest proof admission and actual Secure Boot/TPM result interpretation."""

from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

ROLE = UPSTREAM / 'shared/ansible/roles/guest_boot_security'
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook')
FACTS = dict(ansible_system='Linux', ansible_os_family='Debian', ansible_distribution='Debian',
             ansible_virtualization_role='guest', ansible_virtualization_type='kvm', ansible_kernel='6.12.0-cloud')


class GuestBootSecurityPayload(TierRepositoryTestCase):
    def test_all_tiers_export_the_shared_controller_run_recipe(self):
        self.generate()
        for tier in range(3):
            path = self.root / f'verify-tier-{tier}/ansible/playbooks/deployment/guest-boot-security.yml'
            source = (UPSTREAM / f'tier-{tier}' / path.relative_to(self.root / f'verify-tier-{tier}')).read_text()
            self.assertEqual(path.read_text(), source.replace('../../../../shared/', '../../../../verify-shared/'))
            self.assertIn('../../../../verify-shared/ansible/playbooks/guest-boot-security.yml', path.read_text())
        for source in ROLE.rglob('*.yml'):
            self.assertEqual((self.root / 'verify-shared' / source.relative_to(UPSTREAM / 'shared')).read_bytes(),
                             source.read_bytes())
        packages = yaml.safe_load((ROLE / 'tasks/packages.yml').read_text())
        self.assertFalse(packages[0]['ansible.builtin.dnf']['disable_gpg_check'])
        self.assertFalse(packages[1]['ansible.builtin.apt']['allow_unauthenticated'])
        for task in packages:
            module = next(key for key in task if key.startswith('ansible.builtin.'))
            self.assertEqual(task[module]['state'], 'present')
            self.assertNotIn('enablerepo', task[module])
        sb = yaml.safe_load((ROLE / 'tasks/secure-boot.yml').read_text())[0]
        self.assertEqual(sb['ansible.builtin.command']['argv'], ['/usr/bin/mokutil', '--sb-state'])
        tpm = yaml.safe_load((ROLE / 'tasks/tpm.yml').read_text())[3]
        self.assertEqual(tpm['ansible.builtin.command']['argv'], [
            '/usr/bin/tpm2_getcap', '--tcti=device:{{ guest_boot_security_device }}', 'properties-fixed'])


@unittest.skipUnless(NATIVE, 'Requires native Ansible; no live guest or TPM hardware required')
class GuestBootSecurityNative(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guest-boot-proof-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_NOCOLOR='1',
                        ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_INVENTORY_UNPARSED_WARNING='False')

    def run_tasks(self, tasks, inputs=None, success=True):
        variables = dict(FACTS, ansible_python_interpreter='{{ ansible_playbook_python }}')
        variables.update(inputs or {})
        path = self.root / 'proof.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, tasks=tasks)], sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)], env=self.env,
                                cwd=self.root, capture_output=True, text=True, timeout=35)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_only_managed_linux_guests_and_explicit_operations_are_admitted(self):
        tasks = [{'ansible.builtin.include_role': dict(name='guest_boot_security', tasks_from='validate')}]
        self.run_tasks(tasks)
        for inputs in (dict(ansible_kernel='6.17.2-pve'), dict(ansible_distribution='Talos'),
                       dict(ansible_virtualization_type='lxc'), dict(ansible_virtualization_type='docker'),
                       dict(ansible_virtualization_role='host'), dict(ansible_os_family='Windows'),
                       dict(guest_boot_security_operation='enroll-keys'),
                       dict(guest_boot_security_require_secure_boot=False, guest_boot_security_require_tpm=False)):
            with self.subTest(inputs=inputs):
                self.run_tasks(tasks, inputs, success=False)
        admission = yaml.safe_load((ROLE / 'tasks/validate.yml').read_text())[-1]
        self.run_tasks([admission], dict(guest_boot_security_proxmox=dict(stat=dict(exists=True))), success=False)

    def test_secure_boot_disabled_setup_mode_and_shim_bypass_are_rejected(self):
        tasks = yaml.safe_load((ROLE / 'tasks/secure-boot.yml').read_text())
        for stdout, rc, success in (
                ('SecureBoot enabled\n', 0, True), ('SecureBoot disabled\n', 0, False),
                ('SecureBoot disabled\nPlatform is in Setup Mode\n', 0, False),
                ('SecureBoot enabled\nSecureBoot validation is disabled in shim\n', 0, False),
                ('', 1, False)):
            with self.subTest(stdout=stdout):
                probe = dict(rc=rc, stdout=stdout, stdout_lines=stdout.splitlines())
                self.run_tasks(tasks[1:], dict(guest_boot_security_mokutil=probe), success=success)

    def test_tpm_proof_uses_local_resource_manager_and_verifies_native_properties(self):
        tasks = yaml.safe_load((ROLE / 'tasks/tpm.yml').read_text())
        devices = dict(results=[dict(item='/dev/tpmrm0', stat=dict(ischr=True)),
                                dict(item='/dev/tpm0', stat=dict(ischr=True))])
        valid = yaml.safe_dump(dict(TPM2_PT_FAMILY_INDICATOR=dict(raw='0x322e3000', value='2.0'),
                                    TPM2_PT_MANUFACTURER=dict(raw='0x49424d00', value='IBM')))
        # Double only the physical device read/query. Selection, parsing and assertions stay native.
        fixture = deepcopy(tasks[1:])
        fixture[2] = {'ansible.builtin.set_fact': dict(guest_boot_security_getcap=dict(rc=0, stdout=valid))}
        fixture.append({'ansible.builtin.assert': {'that': "guest_boot_security_device == '/dev/tpmrm0'"}})
        self.run_tasks(fixture, dict(guest_boot_security_devices=devices))
        fallback = deepcopy(devices)
        fallback['results'][0]['stat'] = dict(exists=False)
        fixture[-1] = {'ansible.builtin.assert': {'that': "guest_boot_security_device == '/dev/tpm0'"}}
        self.run_tasks(fixture, dict(guest_boot_security_devices=fallback))
        self.run_tasks(tasks[1:2], dict(guest_boot_security_devices=dict(results=[
            dict(item='/dev/tpm0', stat=dict(exists=False))])), success=False)
        for output in ('TPM2_PT_FAMILY_INDICATOR: {value: "1.2"}\n', '{}\n', '- unexpected\n'):
            self.run_tasks(tasks[4:], dict(guest_boot_security_device='/dev/tpm0',
                                           guest_boot_security_getcap=dict(rc=0, stdout=output)), success=False)
        self.run_tasks(tasks[4:], dict(guest_boot_security_getcap=dict(rc=1)), success=False)

    def test_public_recipes_parse_and_reject_empty_inventory_selection(self):
        for tier in range(3):
            owner = UPSTREAM / f'tier-{tier}'
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '--syntax-check',
                                     'ansible/playbooks/deployment/guest-boot-security.yml'], cwd=owner,
                                    env=dict(self.env, ANSIBLE_CONFIG=str(owner / 'ansible/ansible.cfg')),
                                    capture_output=True, text=True, timeout=35)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        admission = yaml.safe_load((UPSTREAM / 'shared/ansible/playbooks/guest-boot-security.yml').read_text())[0]['tasks']
        for selected in ('', 'all', 'localhost', 'missing-guest'):
            self.run_tasks(admission, dict(guest_boot_security_hosts=selected), success=False)


if __name__ == '__main__':
    unittest.main()
