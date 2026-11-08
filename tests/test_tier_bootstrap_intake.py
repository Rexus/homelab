"""The manually provisioned bootstrap host consumes intake without becoming a managed guest."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from urllib.request import proxy_bypass_environment

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


PLAY = Path('ansible/playbooks/deployment/bootstrap-software-intake.yml')
INPUTS = Path('ansible/group_vars/bootstrap.yml.example')
NATIVE = os.name != 'nt' and bool(shutil.which('ansible-playbook')) and os.geteuid() == 0


class BootstrapIntake(TierRepositoryTestCase):
    def test_generated_local_recipe_keeps_ownership_and_explicit_internal_bypass(self):
        self.generate()
        for owner in (UPSTREAM / 'tier-0', self.root / 'verify-tier-0'):
            plays = yaml.safe_load((owner / PLAY).read_text())
            self.assertFalse(plays[0]['vars']['control_node_require_terraform'])
            self.assertEqual(plays[1]['hosts'], 'localhost')
            self.assertEqual(plays[1]['connection'], 'local')
            imports = [task['ansible.builtin.import_role'] for task in plays[1]['tasks']
                       if 'ansible.builtin.import_role' in task]
            self.assertEqual([(item['name'], item['tasks_from']) for item in imports],
                             [('baseline', 'repository_proxy'), ('baseline', 'shell_proxy')])
            inputs = yaml.safe_load((owner / INPUTS).read_text())
            self.assertIs(inputs['bootstrap_software_intake_accepted'], False)
            self.assertEqual(inputs['shell_proxy_no_proxy_extra'],
                             ['pve01.example.internal', '10.10.10.11'])
            self.assertNotIn('bootstrap', (owner / '.deployment-setups').read_text())
            self.assertFalse((owner / 'terraform/deployments/bootstrap').exists())
            self.assertNotIn('boot-1', (owner / 'ansible/inventory/hosts.yml.example').read_text())
        generated = self.root / 'verify-tier-0'
        self.assertIn('../../verify-shared/ansible/roles',
                      (generated / 'ansible/ansible.cfg').read_text())
        guide = (self.root / 'verify-architecture/docs/auto-docs/deployment/'
                 'stage-1-software-intake/bootstrap-consumer.md').read_text()
        self.assertIn('# Run from verify-tier-0/', guide)
        self.assertIn('bootstrap-software-intake.yml', guide)
        self.assertIn('verify-tier-0/ansible/group_vars/bootstrap.yml.example', guide)

    def run_recipe(self, owner, directory, values, check_tooling=False):
        """Every mutable task destination is sandboxed; tooling acquisition is skipped."""
        inputs = directory / 'inputs.yml'
        inputs.write_text(yaml.safe_dump(values))
        environment = dict(os.environ, ANSIBLE_CONFIG=str(owner / 'ansible/ansible.cfg'),
                           ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'controller-temp'),
                           CONTROL_NODE_COLLECTIONS_MODE='check')
        environment.pop('ANSIBLE_ROLES_PATH', None)
        command = [
            'ansible-playbook', '-i', 'localhost,', str(owner / PLAY), '-e', '@' + str(inputs),
        ]
        if not check_tooling:
            command.extend(['--skip-tags', 'bootstrap_tooling'])
        return subprocess.run(command, cwd=owner, env=environment, capture_output=True, text=True, timeout=120)

    def fixture(self, name, family):
        directory = Path(self.temp.name) / name
        directory.mkdir()
        dnf = directory / 'dnf.conf'
        dnf.write_text('[main]\ngpgcheck=1\n')
        values = {
            'ansible_become': False, 'ansible_os_family': family,
            'bootstrap_software_intake_mode': 'proxy', 'bootstrap_software_intake_accepted': True,
            'repository_proxy_url': 'http://192.0.2.44:3128',
            'repository_proxy_manage_hosts_entry': False,
            'repository_proxy_dnf_conf_path': str(dnf),
            'repository_proxy_apt_conf_dir': str(directory / 'apt'),
            'repository_proxy_apt_conf_path': str(directory / 'apt/80repositoryproxy'),
            'shell_proxy_profile_dir': str(directory / 'profile.d'),
            'shell_proxy_profile_sh_path': str(directory / 'profile.d/shell-proxy.sh'),
            'shell_proxy_profile_csh_path': str(directory / 'profile.d/shell-proxy.csh'),
            'shell_proxy_no_proxy_extra': ['pve01.example.internal', '10.10.10.11'],
        }
        return directory, values

    @unittest.skipUnless(NATIVE, 'Requires Linux root for native root-owned sandbox files and Ansible')
    def test_native_precheck_accepts_preinstalled_collections_without_acquisition(self):
        directory, values = self.fixture('prepared-collections', 'RedHat')
        result = self.run_recipe(UPSTREAM / 'tier-0', directory, values, check_tooling=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('requires Ansible collections: community.general', result.stdout)
        self.assertIn('Require the effective collection version', result.stdout)

    @unittest.skipUnless(NATIVE, 'Requires Linux root for native root-owned sandbox files and Ansible')
    def test_native_tasks_apply_idempotently_and_preserve_mirror_and_tool_configs(self):
        self.generate()
        for label, owner in (('source', UPSTREAM / 'tier-0'), ('generated', self.root / 'verify-tier-0')):
            for family in ('RedHat', 'Debian'):
                with self.subTest(owner=label, family=family):
                    directory, values = self.fixture(label + '-' + family, family)
                    sentinels = {directory / name: 'accepted native configuration\n' for name in
                                 ('os.repo', 'pip.conf', 'galaxy.cfg', 'terraform.tfrc')}
                    for path, content in sentinels.items():
                        path.write_text(content)
                    applied = self.run_recipe(owner, directory, values)
                    self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
                    proxy_file = Path(values['repository_proxy_dnf_conf_path'] if family == 'RedHat'
                                      else values['repository_proxy_apt_conf_path'])
                    self.assertIn(values['repository_proxy_url'], proxy_file.read_text())
                    profile = Path(values['shell_proxy_profile_sh_path']).read_text()
                    exclusions = re.search(r'^export no_proxy="([^"]+)"', profile, re.MULTILINE).group(1)
                    for endpoint in values['shell_proxy_no_proxy_extra']:
                        self.assertTrue(proxy_bypass_environment(endpoint, {'no': exclusions}), endpoint)
                    repeated = self.run_recipe(owner, directory, values)
                    self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
                    self.assertRegex(repeated.stdout, r'changed=0\s+')
                    values['bootstrap_software_intake_mode'] = 'mirror'
                    mirrored = self.run_recipe(owner, directory, values)
                    self.assertEqual(mirrored.returncode, 0, mirrored.stdout + mirrored.stderr)
                    self.assertNotIn('proxy=', Path(values['repository_proxy_dnf_conf_path']).read_text())
                    self.assertIn('gpgcheck=1', Path(values['repository_proxy_dnf_conf_path']).read_text())
                    self.assertFalse(Path(values['repository_proxy_apt_conf_path']).exists())
                    self.assertFalse(Path(values['shell_proxy_profile_sh_path']).exists())
                    for path, content in sentinels.items():
                        self.assertEqual(path.read_text(), content)

    @unittest.skipUnless(NATIVE, 'Requires Linux root for native root-owned sandbox files and Ansible')
    def test_unaccepted_invalid_or_unscoped_proxy_inputs_fail_before_writes(self):
        for index, override in enumerate((
            {'bootstrap_software_intake_accepted': False},
            {'bootstrap_software_intake_mode': 'direct'},
            {'ansible_os_family': 'Unsupported'},
            {'repository_proxy_url': 'http://operator:secret@192.0.2.44:3128'},
            {'shell_proxy_no_proxy_extra': []},
        )):
            with self.subTest(override=override):
                directory, values = self.fixture('rejected-' + str(index), 'RedHat')
                original = Path(values['repository_proxy_dnf_conf_path']).read_text()
                values.update(override)
                rejected = self.run_recipe(UPSTREAM / 'tier-0', directory, values)
                self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
                self.assertEqual(Path(values['repository_proxy_dnf_conf_path']).read_text(), original)
                self.assertFalse(Path(values['shell_proxy_profile_dir']).exists())


if __name__ == '__main__':
    unittest.main()
