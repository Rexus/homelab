"""Exercise the receiver's real Ansible assertions without touching hosts or storage."""

from copy import deepcopy
import os
import shutil
import subprocess
import unittest

import yaml

from syslog_receiver_test_support import ROLE
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ReceiverPreflight(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                         'Requires Ansible on Linux/WSL')
    def test_native_assertions_accept_prepared_inputs_and_reject_unsafe_variants(self):
        tasks = yaml.safe_load((ROLE / 'tasks/inputs.yml').read_text())
        tasks += yaml.safe_load((ROLE / 'tasks/preflight.yml').read_text())
        assertions = [task for task in tasks if 'ansible.builtin.assert' in task]
        runtime = yaml.safe_load((ROLE / 'tasks/runtime.yml').read_text())
        assertions += [task for task in runtime if 'ansible.builtin.assert' in task]
        valid = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        valid.update(
            ansible_os_family='RedHat', ansible_distribution_major_version='10',
            syslog_ng_data_uuid='data-uuid', syslog_ng_effective_data_uuid='data-uuid',
            syslog_ng_listen_address='10.10.10.30',
            syslog_ng_tls_ca_src='/local/ca', syslog_ng_tls_cert_src='/local/cert', syslog_ng_tls_key_src='/local/key',
            syslog_ng_sources=[dict(name='pve01', address='10.10.10.11', tier=0, tls_dn='CN=pve01')],
            syslog_ng_root_facts=[dict(uuid='root-uuid', device='/dev/vda1')],
            syslog_ng_data_facts=[dict(uuid='data-uuid', device='/dev/vdb1', fstype='xfs', options='rw',
                                      size_available=10 * 1024**3)],
            syslog_ng_directory_stats=dict(results=[dict(item='records', stat=dict(exists=False))]),
            ansible_facts=dict(services={'firewalld.service': dict(state='running')}),
            syslog_ng_version=dict(stdout='syslog-ng 4 (4.11.0)'),
        )
        cases = [('prepared', valid)]
        for name, changes in (
            ('missing verified UUID', dict(syslog_ng_effective_data_uuid='')),
            ('missing mount', dict(syslog_ng_data_facts=[])),
            ('wrong volume', dict(syslog_ng_data_uuid='other-uuid')),
            ('root volume', dict(syslog_ng_root_facts=[dict(uuid='data-uuid', device='/dev/vdb1')])),
            ('read only', dict(syslog_ng_data_facts=[dict(valid['syslog_ng_data_facts'][0], options='ro')])),
            ('missing trust', dict(syslog_ng_tls_key_src='')),
            ('no sources', dict(syslog_ng_sources=[])),
            ('wildcard subject', dict(syslog_ng_sources=[dict(valid['syslog_ng_sources'][0], tls_dn='CN=*')])),
            ('wrong CN', dict(syslog_ng_sources=[dict(valid['syslog_ng_sources'][0], tls_dn='CN=other')])),
            ('duplicate namespace', dict(syslog_ng_legacy_sources=[dict(name='pve01', address='10.10.10.12', tier=2)])),
            ('linked records', dict(syslog_ng_directory_stats=dict(results=[
                dict(item='records', stat=dict(exists=True, isdir=False, islnk=True))]))),
            ('missing firewall', dict(ansible_facts=dict(services={}))),
            ('existing logger', dict(ansible_facts=dict(services={
                'syslog-ng.service': dict(state='running'), 'firewalld.service': dict(state='running')}))),
            ('unsupported OS', dict(ansible_distribution_major_version='9')),
            ('old TLS metadata runtime', dict(syslog_ng_version=dict(stdout='syslog-ng 4 (4.10.2)'))),
        ):
            case = deepcopy(valid)
            case.update(changes)
            cases.append((name, case))
        plays = []
        for name, variables in cases:
            checks = deepcopy(assertions)
            if name != 'prepared':
                checks = [
                    {'ansible.builtin.set_fact': dict(receiver_rejected=False)},
                    {'block': checks, 'rescue': [{'ansible.builtin.set_fact': dict(receiver_rejected=True)}]},
                    {'ansible.builtin.assert': {'that': ['receiver_rejected'],
                                               'fail_msg': f'Unsafe case accepted: {name}'}},
                ]
            plays.append(dict(name=name, hosts='localhost', connection='local', gather_facts=False,
                              vars=variables, tasks=checks))
        playbook = self.parent / 'preflight.yml'
        playbook.parent.mkdir(parents=True)
        playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                cwd=UPSTREAM, capture_output=True, text=True, timeout=90,
                                env=dict(os.environ, ANSIBLE_NOCOLOR='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                         'Requires Ansible on Linux/WSL')
    def test_storage_handoff_keeps_explicit_pins_and_uses_verified_uuid_for_new_disks(self):
        fixture = self.parent / 'volume-handoff'
        shared = fixture / 'roles/data_volume/tasks'
        shared.mkdir(parents=True)
        prepare = yaml.safe_load((UPSTREAM / 'shared/ansible/roles/data_volume/tasks/prepare.yml').read_text())
        uuid_guard = next(task for task in prepare
                          if task['name'] == 'Require the expected UUID before changing mount configuration')
        result_fact = next(task for task in prepare
                           if 'data_volume_result' in task.get('ansible.builtin.set_fact', {}))
        # Execute the actual adapter, shared UUID guard and output task without device/mount mutations.
        bridge = [
            {'ansible.builtin.assert': {'that': [
                "data_volume_device == '/dev/sdb'",
                "data_volume_path == '/srv/security-logging'",
                'data_volume_fstype == expected_fstype',
                "data_volume_label == 'security-log'",
                'data_volume_expected_uuid == expected_pin',
                'data_volume_min_free_bytes | int == 2147483648',
                "data_volume_environment == {'https_proxy': 'http://approved.invalid:3128'}",
                'data_volume_allowed_bind_mounts == []',
            ]}},
            {'ansible.builtin.set_fact': {
                'data_volume_uuid_probe': {'stdout': '{{ fixture_uuid }}'},
                'data_volume_realpaths': {'results': [{'stdout': '/dev/sdb'}]},
            }},
            uuid_guard, result_fact,
        ]
        (shared / 'main.yml').write_text(yaml.safe_dump(bridge, sort_keys=False))
        actual_uuid = 'f38b0f72-6281-44c0-8d8e-d8a5278d9bf6'
        wrong_uuid = '93ce1176-a192-4b4b-a4e2-ed3fb60d1ef3'
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        plays = []
        for label, pin, fstype, rejected in (
            ('fresh disk', '', 'xfs', False),
            ('pinned XFS', actual_uuid, 'xfs', False),
            ('pinned ext4', actual_uuid, 'ext4', False),
            ('wrong pin', wrong_uuid, 'xfs', True),
        ):
            variables = dict(defaults, fixture_uuid=actual_uuid, expected_pin=pin, expected_fstype=fstype,
                             syslog_ng_data_uuid=pin, syslog_ng_data_fstype=fstype,
                             syslog_ng_data_environment={'https_proxy': 'http://approved.invalid:3128'})
            tasks = [
                {'ansible.builtin.set_fact': {'handoff_rejected': False, 'data_volume_result': None,
                                              'syslog_ng_effective_data_uuid': None}},
                {'block': [{'ansible.builtin.include_tasks': str(ROLE / 'tasks/storage.yml')}],
                 'rescue': [{'ansible.builtin.set_fact': {'handoff_rejected': True}}]},
                {'ansible.builtin.assert': {'that': [
                    'handoff_rejected == expected_rejection',
                    'syslog_ng_data_uuid == expected_pin',
                ]}},
            ]
            if rejected:
                tasks.append({'ansible.builtin.assert': {'that': [
                    'data_volume_result == None', 'syslog_ng_effective_data_uuid == None',
                ]}})
            else:
                tasks.append({'ansible.builtin.assert': {'that': [
                    'syslog_ng_effective_data_uuid == fixture_uuid',
                    'data_volume_result.path == syslog_ng_data_mount',
                    'data_volume_result.fstype == expected_fstype',
                ]}})
            variables['expected_rejection'] = rejected
            plays.append(dict(name=label, hosts='localhost', connection='local', gather_facts=False,
                              vars=variables, tasks=tasks))
        playbook = fixture / 'handoff.yml'
        playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                cwd=fixture, capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, ANSIBLE_NOCOLOR='1',
                                         ANSIBLE_ROLES_PATH=str(fixture / 'roles')))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
