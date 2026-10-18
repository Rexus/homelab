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
        health = deepcopy(next(play for play in recipe if play.get('name') == 'Sanity-check the first FreeIPA identity host'))
        health.update(become=False, gather_facts=False, tasks=[{'ansible.builtin.debug': {'msg': 'CA-PRIMARY-HEALTH'}}])
        replica = deepcopy(next(play for play in recipe if play.get('hosts') == 'identity_replicas'))
        replica.pop('roles')
        replica.update(become=False, gather_facts=False, tasks=[{'ansible.builtin.debug': {'msg': 'CA-REPLICA-INSTALL'}}])
        final = deepcopy(recipe[-1])
        self.parent.mkdir(parents=True)
        maintenance = self.parent / 'health.yml'
        maintenance.write_text(yaml.safe_dump([dict(hosts='identity', gather_facts=False, tasks=[
            {'ansible.builtin.debug': {'msg': 'CA-FINAL-HEALTH'}},
        ])]))
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
        for phase in ('csr', 'complete'):
            values = dict(foundation_freeipa_enabled=True, foundation_freeipa_ca_mode='external',
                          foundation_freeipa_external_phase=phase,
                          foundation_freeipa_external_cert_files=['/approved/ipa.pem', '/approved/root.pem'])
            result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(playbook), '-e', json.dumps(values)],
                                    cwd=self.parent, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual('"CA-CSR-HANDOFF"' in result.stdout, phase == 'csr')
            for event in ('CA-PRIMARY-HEALTH', 'CA-REPLICA-INSTALL', 'CA-FINAL-HEALTH'):
                self.assertEqual(f'"{event}"' in result.stdout, phase == 'complete', result.stdout)
