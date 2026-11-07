"""Raw template-policy enforcement with native Proxmox modules and no live infrastructure."""

import json
import os
import shutil
import subprocess
import unittest

from proxmox_template_disk_fixture import TemplateDiskApiFixture
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'ansible-doc', 'openssl')),
                     'Requires native Ansible, community.proxmox and OpenSSL')
class TemplatePolicy(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        modules = ['community.proxmox.proxmox_vm_info', 'community.proxmox.proxmox_kvm']
        check = subprocess.run(['ansible-doc', '--json', '-t', 'module', *modules],
                               capture_output=True, text=True)
        if check.returncode or not set(modules).issubset(json.loads(check.stdout)):
            self.skipTest('Install Tier 0 community.proxmox requirements')
        self.root.mkdir(parents=True)
        cert, key = self.root / 'fixture.crt', self.root / 'fixture.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        self.api = TemplateDiskApiFixture(cert, key)
        self.addCleanup(self.api.close)
        self.vars = {'template_disk_sources': {'value': {'rocky-build-1': {
            'vm_id': 110, 'name': self.api.config['name'], 'node_name': 'pve01',
        }}}}
        self.env = dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / 'tier-0/ansible/ansible.cfg'),
                        PROXMOX_CA_FILE=str(cert),
                        PROXMOX_VE_ENDPOINT=f'https://127.0.0.1:{self.api.server.server_port}/',
                        PROXMOX_VE_API_TOKEN='fixture@pve!disk=fixture-not-a-secret')

    def run_policy(self, **overrides):
        inputs = self.root / 'policy.json'
        inputs.write_text(json.dumps(dict(self.vars, **overrides)))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local',
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/maintenance/template-policy.yml'),
                                 '--extra-vars', '@' + str(inputs)], env=self.env, capture_output=True, text=True)
        self.assertNotIn('fixture-not-a-secret', result.stdout + result.stderr)
        self.assertNotIn('fixture-cloud-password', result.stdout + result.stderr)
        return result

    def test_apply_clears_identity_and_missing_balloon_then_becomes_noop(self):
        self.api.config.pop('balloon')
        self.api.config.update(cipassword='fixture-cloud-password', sshkeys='ssh-ed25519 fixture-public-key')
        before = dict(self.api.config)
        result = self.run_policy(template_policy_apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.api.config['balloon'], 0)
        self.assertFalse({'ciuser', 'cipassword', 'sshkeys'} & self.api.config.keys())
        protected = lambda value: {k: v for k, v in value.items()
                                   if k not in ('balloon', 'ciuser', 'cipassword', 'sshkeys')}
        self.assertEqual(protected(self.api.config), protected(before))
        self.assertEqual(len(self.api.writes), 2)
        self.assertEqual(self.api.writes[0][2], {'delete': 'cipassword,ciuser,sshkeys'})
        self.assertEqual(self.api.writes[1][2]['balloon'], '0')
        self.assertIn('digest', self.api.writes[1][2])
        result = self.run_policy(template_policy_apply=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.api.writes), 2)
        self.assertIn('changed=0', result.stdout)
        result = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"cloud_init_accounts_cleared": true', result.stdout)
        self.assertEqual(len(self.api.writes), 2)

    def test_read_only_verification_reports_enabled_balloon_and_never_writes(self):
        self.api.config.pop('ciuser')
        for balloon in (None, 2048):
            self.api.config.pop('balloon', None)
            if balloon is not None:
                self.api.config['balloon'] = balloon
            result = self.run_policy()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Template policy is not satisfied', result.stdout)
        self.assertEqual(self.api.writes, [])

    def test_selection_identity_and_permission_failures_are_bounded(self):
        self.vars['template_disk_sources']['value']['unselected'] = {
            'vm_id': 999, 'name': 'unrelated', 'node_name': 'elsewhere'}
        result = self.run_policy(template_policy_apply=True, template_policy_key='rocky-build-1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        writes = len(self.api.writes)
        self.api.status = 'running'
        self.assertNotEqual(self.run_policy(template_policy_apply=True,
                                            template_policy_key='rocky-build-1').returncode, 0)
        self.assertEqual(len(self.api.writes), writes)
        self.api.status = 'stopped'
        self.api.config['balloon'] = 2048
        self.api.fail_policy = True
        self.assertNotEqual(self.run_policy(template_policy_apply=True,
                                            template_policy_key='rocky-build-1').returncode, 0)
        self.assertEqual(self.api.config['balloon'], 2048)


if __name__ == '__main__':
    unittest.main()
