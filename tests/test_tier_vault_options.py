"""Selected seal artifacts and migration boundaries without an initialized Vault."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from test_tier_control_applications import rendered_releases, ROLE, ROOT


class VaultSealRendering(unittest.TestCase):
    def test_transit_uses_scoped_secret_and_verified_provider_without_plaintext_token(self):
        release = next(item for item in rendered_releases({
            'control_applications_components': ['vault'],
            'control_applications_vault_seal_type': 'transit',
            'control_applications_vault_transit': {
                'address': 'https://unseal.lab.test:8200', 'key_name': 'control-unseal',
                'tls_server_name': 'unseal.lab.test'},
        }) if item['name'] == 'vault')
        server = release['values']['server']
        self.assertEqual(server['extraSecretEnvironmentVars'], [{
            'envName': 'VAULT_TRANSIT_SEAL_TOKEN', 'secretName': 'vault-seal',
            'secretKey': 'VAULT_TRANSIT_SEAL_TOKEN'}])
        config = server['ha']['raft']['config']
        self.assertIn('seal "transit"', config)
        self.assertIn('tls_ca_cert = "/vault/seal/ca.crt"', config)
        self.assertNotIn('token =', config)
        self.assertIn({'name': 'vault-seal', 'keys': ['VAULT_TRANSIT_SEAL_TOKEN', 'ca.crt']},
                      release['required_secrets'])
        self.assertIn({'name': 'seal-ca', 'secret': {'secretName': 'vault-seal',
                      'items': [{'key': 'ca.crt', 'path': 'ca.crt'}]}}, server['volumes'])

    def test_pkcs11_uses_selected_provider_artifact_and_pin_secret(self):
        image = {'repository': 'registry.lab.test/vault-provider', 'tag': '2.0.4-ent@sha256:' + '1' * 64}
        release = rendered_releases({
            'control_applications_components': ['vault'],
            'control_applications_vault_seal_type': 'pkcs11',
            'control_applications_vault_provider_image': image,
            'control_applications_vault_seal_hcl': 'seal "pkcs11" { lib = "/opt/provider.so" }',
        })[0]
        self.assertEqual(release['values']['server']['image'], image)
        self.assertEqual(release['values']['server']['extraSecretEnvironmentVars'][0]['secretKey'], 'VAULT_HSM_PIN')
        self.assertNotIn('pin =', release['values']['server']['ha']['raft']['config'])


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
class VaultSealGuards(unittest.TestCase):
    def test_existing_vm_seal_requires_deliberate_migration_and_preserves_file(self):
        with tempfile.TemporaryDirectory(prefix='vault-seal-guard-') as directory:
            base = Path(directory)
            original = 'storage "raft" { path = "/old/data" }\n'
            config = base / 'vault.hcl'
            config.write_text(original)
            play = base / 'play.yml'
            play.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'tasks': [{'ansible.builtin.include_role': {
                    'name': str(ROOT / 'tier-0/ansible/roles/vault'), 'tasks_from': 'seal-guard'}}],
            }]))
            values = {'vault_config_dir': str(base), 'vault_seal_type': 'transit',
                      'vault_transit': {'address': 'https://unseal.lab.test:8200',
                                        'key_name': 'control', 'tls_server_name': 'unseal.lab.test'}}
            for accepted in (False, True):
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play), '-e',
                    json.dumps(values | {'vault_seal_migration_accepted': accepted})],
                    text=True, capture_output=True, timeout=45)
                self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
                self.assertEqual(config.read_text(), original)

    def test_cluster_seal_guard_compares_real_config_and_accepts_unchanged_hcl(self):
        task = yaml.safe_load((ROLE / 'tasks/vault-seal.yml').read_text())[-1]
        task['vars']['new_config'] = task['vars']['new_config'].replace(
            "'vault-values.yml.j2'", repr(str(ROLE / 'templates/vault-values.yml.j2')))
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text()) | {
            'control_applications_action': 'apply',
            'control_applications_components': ['vault'],
            'control_applications_versions': {'vault': '0.31.0'},
            'control_applications_vault_seal_type': 'transit',
            'control_applications_vault_transit': {
                'address': 'https://unseal.lab.test:8200', 'key_name': 'control',
                'tls_server_name': 'unseal.lab.test'},
        }
        release = rendered_releases(values)[0]
        desired = release['values']['server']['ha']['raft']['config']
        for previous, expected in (('ui = true', False), (desired, True)):
            with tempfile.TemporaryDirectory(prefix='vault-k8s-seal-') as directory:
                play = Path(directory) / 'play.yml'
                play.write_text(yaml.safe_dump([{
                    'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                    'vars': values | {'control_applications_vault_previous_config': {
                        'resources': [{'data': {'extraconfig-from-values.hcl': previous}}]}},
                    'tasks': [copy.deepcopy(task)],
                }]))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                    text=True, capture_output=True, timeout=45)
                self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)
