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
        tasks = yaml.safe_load((ROLE / 'tasks/preflight.yml').read_text())
        assertions = [task for task in tasks if 'ansible.builtin.assert' in task]
        valid = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        valid.update(
            ansible_os_family='RedHat', ansible_distribution_major_version='10',
            syslog_ng_data_uuid='data-uuid', syslog_ng_listen_address='10.10.10.30',
            syslog_ng_tls_ca_src='/local/ca', syslog_ng_tls_cert_src='/local/cert', syslog_ng_tls_key_src='/local/key',
            syslog_ng_sources=[dict(name='pve01', address='10.10.10.11', tier=0, tls_dn='CN=pve01')],
            syslog_ng_root_facts=[dict(uuid='root-uuid', device='/dev/vda1')],
            syslog_ng_data_facts=[dict(uuid='data-uuid', device='/dev/vdb1', fstype='xfs', options='rw',
                                      size_available=10 * 1024**3)],
            syslog_ng_directory_stats=dict(results=[dict(item='records', stat=dict(exists=False))]),
            ansible_facts=dict(services={'firewalld.service': dict(state='running')}),
        )
        cases = [('prepared', valid)]
        for name, changes in (
            ('missing UUID', dict(syslog_ng_data_uuid='')),
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


if __name__ == '__main__':
    unittest.main()
