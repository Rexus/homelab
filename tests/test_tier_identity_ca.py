"""Verify native play boundaries while substituting only external product operations."""

from copy import deepcopy
import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class IdentityCaPhases(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires Ansible on Linux/WSL')
    def test_csr_stops_before_health_and_replicas_and_completion_resumes_them(self):
        source = UPSTREAM / 'tier-0/ansible/playbooks/deployment/identity-freeipa.yml'
        recipe = yaml.safe_load(source.read_text())
        primary = next(play for play in recipe if play.get('name') == 'Configure the first FreeIPA identity host')
        primary = deepcopy(primary)
        primary.update(become=False, gather_facts=False)
        for task in primary['tasks']:
            if 'ansible.builtin.include_role' in task:
                task.pop('ansible.builtin.include_role')
                task['ansible.builtin.assert'] = {'that': [
                    "(ipaserver_external_ca | bool) == (foundation_freeipa_external_phase == 'csr')",
                    "foundation_freeipa_external_phase == 'csr' or "
                    "ipaserver_external_cert_files_from_controller == foundation_freeipa_external_cert_files",
                ]}
            elif 'ansible.builtin.fetch' in task:
                task.pop('ansible.builtin.fetch')
                task['ansible.builtin.debug'] = {'msg': 'CA-CSR-HANDOFF'}
        primary['tasks'].append({'ansible.builtin.debug': {'msg': 'CA-PRIMARY-CONTINUED'}})
        health = deepcopy(next(play for play in recipe
            if play.get('ansible.builtin.import_playbook') == '../maintenance/foundation.yml'
            and play.get('vars', {}).get('foundation_health_hosts') == 'identity_primary'))
        replica = deepcopy(next(play for play in recipe if play.get('hosts') == 'identity_replicas'))
        self.assertLess(recipe.index(next(play for play in recipe if play.get('hosts') == 'identity_primary')),
                        recipe.index(health))
        self.assertLess(recipe.index(health), recipe.index(next(play for play in recipe
                                                              if play.get('hosts') == 'identity_replicas')))
        replica.pop('roles')
        replica.update(become=False, gather_facts=False, tasks=[{'ansible.builtin.debug': {'msg': 'CA-REPLICA-INSTALL'}}])
        final = deepcopy(recipe[-1])
        self.parent.mkdir(parents=True)
        maintenance = self.parent / 'health.yml'
        maintenance_plays = yaml.safe_load((source.parent / '../maintenance/foundation.yml').read_text())
        for play in maintenance_plays:
            play.update(become=False, gather_facts=False, tasks=[
                {'ansible.builtin.assert': {'that': [
                    "not (test_primary_health_fails | default(false) | bool) or "
                    "foundation_health_hosts | default('identity') != 'identity_primary'",
                ]}},
                {'ansible.builtin.debug': {'msg': "{{ 'CA-PRIMARY-HEALTH' if "
                    "foundation_health_hosts | default('identity') == 'identity_primary' "
                    "else 'CA-FINAL-HEALTH' }}:{{ inventory_hostname }}"}},
            ])
        maintenance.write_text(yaml.safe_dump(maintenance_plays))
        health['ansible.builtin.import_playbook'] = maintenance.name
        final['ansible.builtin.import_playbook'] = maintenance.name
        inventory = self.parent / 'inventory.yml'
        inventory.write_text(yaml.safe_dump({'all': {'vars': {'ansible_connection': 'local'}, 'children': {
            'identity': {'children': {
                'identity_primary': {'hosts': {'idm-1': {}}},
                'identity_replicas': {'hosts': {'idm-2': {}}},
            }},
        }}}))
        playbook = self.parent / 'phases.yml'
        playbook.write_text(yaml.safe_dump([primary, health, replica, final], sort_keys=False))
        for phase, health_fails in (('csr', False), ('complete', False), ('complete', True)):
            values = dict(foundation_freeipa_enabled=True, foundation_freeipa_ca_mode='external',
                          foundation_freeipa_external_phase=phase,
                          foundation_freeipa_external_cert_files=['/approved/ipa.pem', '/approved/root.pem'],
                          test_primary_health_fails=health_fails)
            with self.subTest(phase=phase, health_fails=health_fails):
                result = subprocess.run(
                    ['ansible-playbook', '-i', str(inventory), str(playbook), '-e', json.dumps(values)],
                    cwd=self.parent, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode == 0, not health_fails, result.stdout + result.stderr)
                self.assertEqual('"CA-CSR-HANDOFF"' in result.stdout, phase == 'csr')
                self.assertEqual('"CA-PRIMARY-CONTINUED"' in result.stdout, phase == 'complete')
                complete = phase == 'complete' and not health_fails
                for event in ('CA-PRIMARY-HEALTH:idm-1', 'CA-REPLICA-INSTALL',
                              'CA-FINAL-HEALTH:idm-1', 'CA-FINAL-HEALTH:idm-2'):
                    self.assertEqual(f'"{event}"' in result.stdout, complete, result.stdout)
                self.assertNotIn('"CA-PRIMARY-HEALTH:idm-2"', result.stdout)
                if complete:
                    self.assertLess(result.stdout.index('"CA-PRIMARY-HEALTH:idm-1"'),
                                    result.stdout.index('"CA-REPLICA-INSTALL"'))
                    self.assertLess(result.stdout.index('"CA-REPLICA-INSTALL"'),
                                    result.stdout.index('"CA-FINAL-HEALTH:idm-1"'))
