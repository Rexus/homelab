"""Physical PVE admission and native boot/TPM assertions with only machine I/O doubled."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/proxmox_host'
SHARED = UPSTREAM / 'shared/ansible/roles/guest_boot_security'
RECIPE = Path('ansible/playbooks/maintenance/proxmox-boot-security.yml')
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook')
FACTS = dict(ansible_system='Linux', ansible_os_family='Debian', ansible_distribution='Debian',
             ansible_virtualization_role='host', ansible_virtualization_type='kvm')


def syntax_check(owner):
    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '--syntax-check', str(RECIPE)],
                            cwd=owner, env=dict(os.environ, ANSIBLE_CONFIG=str(owner / 'ansible/ansible.cfg')),
                            capture_output=True, text=True, timeout=35)
    return result.returncode, result.stdout + result.stderr


class ProxmoxHostBootPayload(TierRepositoryTestCase):
    def test_generated_payload_and_source_and_generated_recipe_syntax(self):
        self.generate()
        generated = self.root / 'verify-tier-0'
        for relative in (RECIPE, Path('ansible/roles/proxmox_host/defaults/main.yml'),
                         Path('ansible/roles/proxmox_host/tasks/boot_security.yml')):
            self.assertEqual((generated / relative).read_bytes(), (UPSTREAM / 'tier-0' / relative).read_bytes())
        for source in SHARED.rglob('*.yml'):
            self.assertEqual((self.root / 'verify-shared' / source.relative_to(UPSTREAM / 'shared')).read_bytes(),
                             source.read_bytes())
        if NATIVE:
            for owner in (UPSTREAM / 'tier-0', generated):
                code, output = syntax_check(owner)
                self.assertEqual(code, 0, output)

    def test_public_recipe_and_preparation_are_bounded(self):
        play = yaml.safe_load((UPSTREAM / 'tier-0' / RECIPE).read_text())[0]
        self.assertEqual(play['hosts'], 'hypervisors')
        self.assertEqual(play['serial'], 1)
        self.assertTrue(play['become'])
        self.assertTrue(play['gather_facts'])
        self.assertEqual(play['gather_subset'], ['!all', 'min', 'virtual'])
        self.assertEqual(play['tasks'], [dict(name='Run only the physical host boot-security entry point',
                                             **{'ansible.builtin.import_role': dict(name='proxmox_host',
                                                                                   tasks_from='boot_security')})])
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        public = {key: value for key, value in defaults.items()
                  if key.startswith('proxmox_host_boot_security_') or key.startswith('proxmox_host_require_')}
        self.assertEqual(public, dict(proxmox_host_boot_security_operation='check',
                                      proxmox_host_require_secure_boot=True, proxmox_host_require_tpm=True))
        tasks = yaml.safe_load((ROLE / 'tasks/boot_security.yml').read_text())
        package = next(task for task in tasks if 'ansible.builtin.apt' in task)
        self.assertEqual(package['when'], "proxmox_host_boot_security_operation == 'prepare'")
        self.assertEqual(package['ansible.builtin.apt'], dict(
            name=['mokutil', 'efibootmgr', 'tpm2-tools'], state='present', update_cache=True,
            install_recommends=False, allow_unauthenticated=False, force=False,
            force_apt_get=True, fail_on_autoremove=True))
        block = next(task['block'] for task in tasks if 'block' in task)
        self.assertEqual([task['ansible.builtin.include_role'] for task in block
                          if 'ansible.builtin.include_role' in task],
                         [dict(name='guest_boot_security', tasks_from='secure-boot'),
                          dict(name='guest_boot_security', tasks_from='tpm')])
        # No other mutation modules or unrestricted product CLI commands enter this operation.
        allowed = {'assert', 'stat', 'command', 'debug', 'apt', 'include_role', 'fail'}
        for task in tasks + block + next(task['rescue'] for task in tasks if 'rescue' in task):
            for key in task:
                if key.startswith('ansible.builtin.'):
                    self.assertIn(key.removeprefix('ansible.builtin.'), allowed)
        commands = [task['ansible.builtin.command']['argv'] for task in tasks if 'ansible.builtin.command' in task]
        self.assertEqual(commands, [['/usr/bin/pveversion'], '{{ item }}'])
        inspection = next(task for task in tasks if 'loop' in task and 'ansible.builtin.command' in task)
        self.assertEqual(inspection['loop'], [['/usr/sbin/proxmox-boot-tool', 'status'],
                                             ['/usr/bin/efibootmgr', '-v'], ['/usr/bin/mokutil', '--sb-state']])
        self.assertNotIn('boot_security', (ROLE / 'tasks/main.yml').read_text())
        proxy = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/proxmox-hosts.yml').read_text())[0]
        self.assertFalse(proxy['gather_facts'])
        self.assertEqual(proxy['roles'], ['proxmox_host'])


@unittest.skipUnless(NATIVE, 'Requires native Ansible; no live host or physical TPM required')
class ProxmoxHostBootNative(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='physical-host-boot-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        roles = self.root / 'roles'
        shutil.copytree(ROLE, roles / 'proxmox_host')
        shutil.copytree(SHARED, roles / 'guest_boot_security')
        # Keep the actual admission, control flow, parsing, selection and assertions.
        # Replace fixed machine reads and APT only inside these private fixture copies.
        probes = dict(_proxmox_host_boot_security_pve='fixture_pve',
                      _proxmox_host_boot_security_version='fixture_version',
                      _proxmox_host_boot_security_efi='fixture_efi',
                      _proxmox_host_boot_security_inspection='fixture_inspection',
                      guest_boot_security_mokutil='fixture_mokutil',
                      guest_boot_security_devices='fixture_devices',
                      guest_boot_security_getcap='fixture_getcap')
        for path in (roles / 'proxmox_host/tasks/boot_security.yml',
                     roles / 'guest_boot_security/tasks/secure-boot.yml',
                     roles / 'guest_boot_security/tasks/tpm.yml'):
            tasks = yaml.safe_load(path.read_text())
            for index, task in enumerate(tasks):
                register = task.get('register')
                if register in probes or 'ansible.builtin.apt' in task:
                    facts = ({register: '{{ ' + probes[register] + ' }}'} if register in probes
                             else dict(fixture_packages_prepared=True))
                    tasks[index] = dict(name=task['name'], **{'ansible.builtin.set_fact': facts})
                    if 'when' in task:
                        tasks[index]['when'] = task['when']
            path.write_text(yaml.safe_dump(tasks, sort_keys=False))
        self.env = dict(os.environ, ANSIBLE_ROLES_PATH=str(roles), ANSIBLE_NOCOLOR='1',
                        ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_INVENTORY_UNPARSED_WARNING='False')
        sb = 'SecureBoot enabled\n'
        self.variables = dict(FACTS, ansible_python_interpreter='{{ ansible_playbook_python }}',
                              fixture_pve=dict(stat=dict(isdir=True, islnk=False)),
                              fixture_version=dict(rc=0, stdout='pve-manager/9.1.0/fixture (running kernel: 6.17.2-pve)'),
                              fixture_efi=dict(stat=dict(isdir=True)),
                              fixture_inspection=dict(results=[dict(item=['mokutil', '--sb-state'], rc=0,
                                                                    stdout='SecureBoot disabled')]),
                              fixture_mokutil=dict(rc=0, stdout=sb, stdout_lines=sb.splitlines()),
                              fixture_devices=dict(results=[dict(item='/dev/tpmrm0', stat=dict(ischr=True)),
                                                            dict(item='/dev/tpm0', stat=dict(ischr=True))]),
                              fixture_getcap=dict(rc=0, stdout=yaml.safe_dump(dict(
                                  TPM2_PT_FAMILY_INDICATOR=dict(value='2.0'),
                                  TPM2_PT_MANUFACTURER=dict(value='IFX')))))

    def run_host(self, inputs=None, success=True, check_mode=False):
        variables = dict(self.variables, **(inputs or {}))
        tasks = [{'ansible.builtin.import_role': dict(name='proxmox_host', tasks_from='boot_security')},
                 {'ansible.builtin.assert': {'that':
                  "fixture_packages_prepared | default(false) == (proxmox_host_boot_security_operation == 'prepare')"}}]
        path = self.root / 'host.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, tasks=tasks)], sort_keys=False))
        command = ['ansible-playbook', '-i', 'localhost,', str(path)] + (['--check'] if check_mode else [])
        result = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True, text=True, timeout=35)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        self.assertNotIn('Normalize Proxmox host cache proxy inputs', output)
        self.assertNotIn('Exclude hypervisors, physical machines', output)
        return output

    def test_physical_host_and_na_roles_accept_both_controls_without_packages(self):
        for role in ('host', 'NA'):
            with self.subTest(role=role):
                output = self.run_host(dict(ansible_virtualization_role=role), check_mode=True)
                self.assertIn('pve-manager/9.1.0/fixture', output)
                self.assertIn('Enforced; no shim validation bypass', output)
                self.assertIn('Local TPM 2.0 fixed properties verified', output)
                self.assertIn('does not enroll LUKS', output)
                self.assertIn('attestation', output)

    def test_unsupported_platform_guest_container_and_nested_pve_fail_before_preparation(self):
        for inputs in (dict(ansible_system='Windows'), dict(ansible_os_family='RedHat'),
                       dict(ansible_distribution='Ubuntu'), dict(ansible_virtualization_role='guest'),
                       dict(ansible_virtualization_type='lxc'), dict(ansible_virtualization_type='docker'),
                       dict(ansible_virtualization_roles=['host', 'guest']),
                       dict(fixture_pve=dict(stat=dict(isdir=False))),
                       dict(fixture_pve=dict(stat=dict(isdir=True, islnk=True))),
                       dict(fixture_version=dict(rc=127)), dict(fixture_version=dict(rc=0, stdout='Debian'))):
            with self.subTest(inputs=inputs):
                output = self.run_host(dict(inputs, proxmox_host_boot_security_operation='prepare'), success=False)
                self.assertNotIn('TASK [proxmox_host : Prepare only native inspection tools', output)

    def test_invalid_operations_boolean_strings_and_empty_policy_are_rejected(self):
        for inputs in (dict(proxmox_host_boot_security_operation='apply'),
                       dict(proxmox_host_require_secure_boot='false'), dict(proxmox_host_require_tpm='true'),
                       dict(proxmox_host_require_secure_boot=False, proxmox_host_require_tpm=False)):
            with self.subTest(inputs=inputs):
                self.run_host(inputs, success=False)
        self.run_host(dict(proxmox_host_boot_security_operation='prepare'), success=False, check_mode=True)

    def test_prepare_allows_disabled_secure_boot_and_missing_tpm_without_claiming_acceptance(self):
        output = self.run_host(dict(proxmox_host_boot_security_operation='prepare',
                                    fixture_efi=dict(stat=dict(isdir=False)), fixture_devices=dict(results=[])))
        self.assertIn('SecureBoot disabled', output)
        self.assertIn('Not accepted during prepare', output)
        self.assertIn('proxmox-host-boot-security.md', output)
        self.assertNotIn('TASK [guest_boot_security :', output)

    def test_check_rejects_non_uefi_disabled_secure_boot_setup_mode_and_shim_bypass(self):
        self.run_host(dict(fixture_efi=dict(stat=dict(isdir=False))), success=False)
        for stdout, rc in (('SecureBoot disabled\n', 0),
                           ('SecureBoot disabled\nPlatform is in Setup Mode\n', 0),
                           ('SecureBoot enabled\nSecureBoot validation is disabled in shim\n', 0), ('', 127)):
            with self.subTest(stdout=stdout):
                output = self.run_host(dict(fixture_mokutil=dict(rc=rc, stdout=stdout,
                                                                 stdout_lines=stdout.splitlines())), success=False)
                self.assertIn('Physical Proxmox boot acceptance failed', output)
                self.assertIn('proxmox_host_boot_security_operation=prepare', output)

    def test_check_rejects_missing_tpm_query_failure_and_wrong_family(self):
        for inputs in (dict(fixture_devices=dict(results=[dict(item='/dev/tpm0', stat=dict(exists=False))])),
                       dict(fixture_getcap=dict(rc=1)),
                       dict(fixture_getcap=dict(rc=0, stdout='TPM2_PT_FAMILY_INDICATOR: {value: "1.2"}\n'))):
            with self.subTest(inputs=inputs):
                output = self.run_host(inputs, success=False)
                self.assertIn('Physical Proxmox boot acceptance failed', output)

    def test_each_requirement_can_be_disabled_explicitly(self):
        self.run_host(dict(proxmox_host_require_secure_boot=False, fixture_efi=dict(stat=dict(isdir=False)),
                           fixture_mokutil=dict(rc=127)))
        self.run_host(dict(proxmox_host_require_tpm=False, fixture_devices=dict(results=[])))


if __name__ == '__main__':
    unittest.main()
