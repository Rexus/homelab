"""The ordinary issuer entry point cannot bypass hardware custody acceptance."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


class HardwareActivation(unittest.TestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_actual_policy_guard_distinguishes_software_inactive_and_accepted_hardware(self):
        policy = UPSTREAM / 'tier-0/ansible/roles/openxpki/tasks/policy.yml'
        guard = next(task for task in yaml.safe_load(policy.read_text())
                     if task['name'].startswith('Require completed hardware custody'))
        for engine, active, accepted, success in (
            ('OpenSSL', True, False, True),
            ('PKCS11', False, False, True),
            ('PKCS11', True, False, False),
            ('PKCS11', True, True, True),
        ):
            with self.subTest(engine=engine, active=active, accepted=accepted), tempfile.TemporaryDirectory() as temporary:
                play = Path(temporary) / 'guard.yml'
                play.write_text(yaml.safe_dump([{
                    'hosts': 'localhost', 'gather_facts': False,
                    'vars': {'openxpki_crypto': {'token': {'ca-signer': {'engine': engine}}},
                             'openxpki_activate_runtime': active, 'hsm_provider_custody_ready': accepted},
                    'tasks': [guard],
                }]))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
