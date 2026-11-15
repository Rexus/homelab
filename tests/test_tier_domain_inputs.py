"""Native host selection and initializer compatibility without contacting any guest."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
class DomainInputs(TierRepositoryTestCase):
    def test_identity_recipe_requires_authority_namespace_before_any_host_operation(self):
        self.generate()
        source = yaml.safe_load((UPSTREAM/'tier-0/ansible/playbooks/deployment/identity-freeipa.yml').read_text())
        guard = next(task for task in source[0]['tasks'] if task['name'].startswith("Require each authority"))
        play = self.root/'authority-check.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'all', 'gather_facts': False, 'tasks': [guard]}]))
        inventory = self.root/'authority-host.yml'
        values = {'foundation_freeipa_enabled': True, 'foundation_freeipa_domain': 'corp.example.com'}
        for role, success in (('authority', True), ('standalone', False)):
            inventory.write_text(yaml.safe_dump({'all': {'hosts': {'idm-1': {'platform_domain_role': role}}}}))
            override = self.root/'authority-inputs.yml'
            override.write_text(yaml.safe_dump(values))
            result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play),
                '-e', '@'+str(self.root/'verify-tier-0/ansible/group_vars/all.yml.example'),
                '-e', '@'+str(override)], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_host_roles_override_global_derived_names_and_services_stay_internal(self):
        self.generate()
        inventory = self.root / 'domain-hosts.yml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'standalone': {'hosts': {'guest-1': {'expected_domain': 'example.internal'}}},
            'members': {'vars': {'platform_domain_role': 'member'},
                        'hosts': {'member-1': {'expected_domain': 'corp.example.com'}}},
            'authorities': {'vars': {'platform_domain_role': 'authority'},
                           'hosts': {'idm-1': {'expected_domain': 'corp.example.com'}}},
        }}}))
        play = self.root / 'domain-check.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'all', 'gather_facts': False, 'tasks': [{
            'ansible.builtin.assert': {'that': [
                'platform_host_domain == expected_domain',
                'platform_fqdn == inventory_hostname ~ "." ~ expected_domain',
                'platform_internal_domain == "example.internal"',
            ]},
        }]}]))
        for tier, service_file, field, endpoint in (
            ('tier-0', 'issuer', 'openxpki_portal_fqdn', 'ca.example.internal'),
            ('tier-1', 'development', 'gitlab_hostname', 'git.example.internal'),
            ('tier-2', 'cache', 'cache_proxy_fqdn', 'cache.example.internal'),
        ):
            with self.subTest(tier=tier):
                repo = self.root / f'verify-{tier}'
                service_check = {'ansible.builtin.assert': {'that': f"{field} == '{endpoint}'"}}
                service_play = yaml.safe_load(play.read_text())
                service_play[0]['tasks'].append(service_check)
                scoped_play = self.root / f'{tier}-service-check.yml'
                scoped_play.write_text(yaml.safe_dump(service_play))
                result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(scoped_play),
                    '-e', '@' + str(repo/'ansible/group_vars/all.yml.example'),
                    '-e', '@' + str(repo/f'ansible/group_vars/{service_file}.yml.example'),
                    '-e', 'platform_internal_domain=example.internal'],
                    capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_initializer_creates_both_environment_domains_and_preserves_existing_values(self):
        self.generate()
        for tier, setup in (('tier-0', 'syslog'), ('tier-1', 'development'), ('tier-2', 'cache')):
            with self.subTest(tier=tier):
                repo = self.root / f'verify-{tier}'
                command = ['bash', 'scripts/init-local-files.sh', '--setup', setup, '--env', 'lab1']
                result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                overlay = repo/'ansible/group_vars/all.lab1.yml'
                values = yaml.safe_load(overlay.read_text())
                self.assertEqual(values['platform_internal_domain'], 'lab1.internal.example.com')
                self.assertEqual(values['platform_domain'], 'lab1.corp.example.com')
                overlay.write_text('platform_internal_domain: accepted.internal\nplatform_domain: corp.accepted.example\n')
                before = overlay.read_bytes()
                result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(overlay.read_bytes(), before)

    def test_legacy_missing_internal_domain_keeps_directory_suffix(self):
        self.generate()
        values = yaml.safe_load((UPSTREAM/'tier-0/ansible/group_vars/all.yml.example').read_text())
        del values['platform_internal_domain']
        values.pop('baseline_manage_hostname', None)
        values['platform_domain'] = 'legacy.example'
        variables = self.root/'legacy-inputs.yml'
        variables.write_text(yaml.safe_dump(values))
        inventory = self.root/'legacy-host.yml'
        inventory.write_text('all:\n  hosts:\n    guest-1: {}\n')
        play = self.root/'legacy-check.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'all', 'gather_facts': False,
            'tasks': [{'ansible.builtin.assert': {'that': 'platform_fqdn == "guest-1.legacy.example"'}}]}]))
        result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play), '-e', '@'+str(variables)],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
