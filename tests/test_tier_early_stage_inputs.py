"""Execute early-stage input handoffs without contacting managed infrastructure."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                     'Requires native Ansible')
class EarlyStageInputs(TierRepositoryTestCase):
    def test_documented_hardware_issuer_commands_keep_the_foundation_address(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for relative in ('ansible/inventory/hosts.yml', 'ansible/group_vars/all.yml',
                         'ansible/group_vars/foundation.yml', 'ansible/group_vars/hsm.yml',
                         'ansible/group_vars/issuer.yml'):
            shutil.copyfile(str(repo / relative) + '.example', repo / relative)
        expected = yaml.safe_load((repo / 'ansible/group_vars/foundation.yml').read_text())[
            'platform_host_ips']['ca-1']
        probe = Path(self.temp.name) / 'issuer-input-probe.yml'
        probe.write_text(yaml.safe_dump([{
            'hosts': 'issuing_ca', 'gather_facts': False,
            'tasks': [{'ansible.builtin.assert': {'that': [f"ansible_host == '{expected}'"]}}],
        }]))
        docs = self.root / 'verify-architecture/docs/auto-docs/03-deployment/stage-03-trust'
        checked = 0
        for name in ('step-1c-network-hsm.md', 'step-1d-single-usb.md'):
            for command in re.findall(r'(?ms)^```bash\n(.*?)^```', (docs / name).read_text()):
                playbook = re.search(r'ansible/playbooks/deployment/hsm-(issuer|inspect|token)\.yml', command)
                if playbook is None:
                    continue
                invocation = command.replace(playbook[0], f"'{probe}'")
                result = subprocess.run(['bash', '-c', invocation], cwd=repo, capture_output=True,
                                        text=True, timeout=60,
                                        env=dict(os.environ, ANSIBLE_SSH_EXECUTABLE='/bin/false'))
                self.assertEqual(result.returncode, 0, name + '\n' + result.stdout + result.stderr)
                self.assertIn('ca-1', result.stdout)
                checked += 1
        self.assertEqual(checked, 4)

    def test_direct_monitor_and_backup_stop_at_dependency_check_before_guest_tasks(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        collections = Path(self.temp.name) / 'empty-collections'
        collections.mkdir()
        inventory = Path(self.temp.name) / 'hosts.yml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'infrastructure_monitoring': {'hosts': {'monitor-fixture': {}}},
            'control_recovery': {'hosts': {'recovery-fixture': {}}},
            'identity_primary': {'hosts': {'idm-fixture': {}}},
        }}}))
        environment = dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg'),
                           ANSIBLE_COLLECTIONS_PATH=str(collections),
                           ANSIBLE_COLLECTIONS_SCAN_SYS_PATH='false',
                           CONTROL_NODE_COLLECTIONS_MODE='check',
                           ANSIBLE_SSH_EXECUTABLE='/bin/false', ANSIBLE_NOCOLOR='1')
        for recipe, collection, forbidden in (
            ('deployment/infrastructure-monitoring.yml', 'containers.podman',
             'Render or install independent Tier 0 monitoring'),
            ('maintenance/control-backup.yml', 'ansible.posix',
             'Schedule independently encrypted control recovery copies'),
            ('deployment/netbox-audit-account.yml', 'netbox.netbox',
             'Bootstrap the dedicated read-only NetBox audit credential'),
            ('deployment/freeipa-ldap-reader.yml', 'community.general',
             'Bootstrap the explicitly selected directory reader on the installed primary'),
        ):
            result = subprocess.run([
                'ansible-playbook', '-i', str(inventory),
                str(repo / 'ansible/playbooks' / recipe), '--limit',
                'localhost,monitor-fixture,recovery-fixture,idm-fixture',
            ], cwd=repo, env=environment, capture_output=True, text=True, timeout=90)
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn('Missing collections:', output)
            self.assertIn(collection, output)
            self.assertNotIn(forbidden, output)
            self.assertNotIn('UNREACHABLE', output)
