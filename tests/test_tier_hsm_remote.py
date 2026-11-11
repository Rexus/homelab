"""Focused HSM remoting input guards and native SSH/SoftHSM acceptance.

Linux fixture requirements: root on an isolated test host, OS-provided openssh-server
with its existing sshd privilege-separation account, OpenSC, GnuTLS,
SoftHSM2, Jinja2, PyYAML and Ansible with community.crypto. HSM_REMOTE_NATIVE_ROOT
selects an extracted Ubuntu x86_64 native tool tree (including shared libraries).
Run: python -m unittest discover -s tests -p test_tier_hsm_remote.py -v
The fixture creates and cleans temporary software tokens, Linux identities and listeners.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import yaml
import jinja2

from hsm_remote_test_support import ANSIBLE, NATIVE, ROLE, NativeHSMFixture
import hsm_remote_test_support as native_support


class HSMRemoteInputs(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Requires Linux account lookup')
    def test_missing_os_sshd_account_skips_before_any_fixture_mutation(self):
        with mock.patch.object(native_support.pwd, 'getpwnam', side_effect=KeyError('sshd')):
            with mock.patch.object(native_support.subprocess, 'run') as command:
                with mock.patch.object(native_support.tempfile, 'TemporaryDirectory') as directory:
                    with self.assertRaisesRegex(unittest.SkipTest, 'pre-existing openssh-server'):
                        NativeHSMFixture.setUpClass()
                    command.assert_not_called()
                    directory.assert_not_called()

    @unittest.skipUnless(ANSIBLE and NATIVE, 'Requires Ansible and extracted native firewalld Python modules')
    def test_rendered_firewall_rules_pass_native_parser(self):
        with tempfile.TemporaryDirectory(prefix='hsm-firewall-') as directory:
            work = Path(directory)
            rendered = work / 'rules.json'
            tasks = yaml.safe_load((ROLE / 'tasks/firewall.yml').read_text())
            block = next(task['block'] for task in tasks if 'block' in task)
            build = next(task for task in block if task['name'] == 'Build each source-scoped native firewall rule')
            play = work / 'play.yml'
            play.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'gather_facts': False,
                'vars': {'ansible_connection': 'local', 'ansible_become': False,
                         'ansible_python_interpreter': '/usr/bin/python3',
                         'hsm_remote_firewall_rules': [], 'hsm_remote_port': 2222,
                         'hsm_remote_clients': {'one': {'sources': ['192.0.2.10/32']},
                                                'two': {'sources': ['198.51.100.0/24']}}},
                'tasks': [build, {'ansible.builtin.copy': {
                    'content': '{{ hsm_remote_firewall_rules | to_json }}', 'dest': str(rendered)}}],
            }]))
            result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Use the product's parser, without requiring a daemon or touching network policy.
            script = '''
import json, sys
from firewall.core.rich import Rich_Rule
rules = [Rich_Rule(rule_str=rule) for rule in json.load(open(sys.argv[1]))]
assert {rule.source.addr for rule in rules} == {'192.0.2.10/32', '198.51.100.0/24'}
assert all(rule.family == 'ipv4' and rule.element.port == '2222' and
           rule.element.protocol == 'tcp' and type(rule.action).__name__ == 'Rich_Accept' for rule in rules)
'''
            result = subprocess.run(['/usr/bin/python3', '-c', script, str(rendered)],
                                    env=dict(os.environ, PYTHONPATH=str(
                                        Path(NATIVE) / 'usr/lib/python3/dist-packages')),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Requires JavaScript runtime for native Polkit rule semantics')
    def test_pcsc_rule_limits_service_identity_reader_and_action(self):
        template = ROLE.parent / 'hsm_provider/templates/pcsc.rules.j2'
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters['to_json'] = json.dumps
        rule = env.from_string(template.read_text()).render(
            hsm_provider_pcsc_users=['hsmrpc'], hsm_provider_pcsc_readers=['PicoHSM accepted 00 00'])
        script = '''
let callback;
const polkit = {Result: {YES: 'yes', NO: 'no'}, addRule: fn => callback = fn};
''' + rule + '''
const check = (id, user, reader) => callback({id, lookup: () => reader}, {user});
const actual = [check('org.debian.pcsc-lite.access_pcsc', 'hsmrpc', ''),
    check('org.debian.pcsc-lite.access_card', 'hsmrpc', 'PicoHSM accepted 00 00'),
    check('org.debian.pcsc-lite.access_card', 'hsmrpc', 'Other reader 00 00'),
    check('org.debian.pcsc-lite.access_card', 'otheruser', 'PicoHSM accepted 00 00'),
    check('org.example.unrelated', 'hsmrpc', '')];
if (JSON.stringify(actual) !== JSON.stringify(['yes', 'yes', 'no', null, null])) process.exit(1);
'''
        result = subprocess.run([shutil.which('node'), '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(ANSIBLE, 'Requires native Ansible')
    def test_preflight_accepts_explicit_domain_and_rejects_unsafe_inputs(self):
        with tempfile.TemporaryDirectory(prefix='hsm-remote-guard-') as directory:
            work = Path(directory)
            play = work / 'play.yml'
            play.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'gather_facts': False,
                'tasks': [{'ansible.builtin.include_role': {
                    'name': 'hsm_remote', 'tasks_from': 'preflight'}}],
            }]))
            inputs = dict(
                ansible_connection='local', ansible_become=False, ansible_os_family='Debian',
                hsm_remote_enabled=True, hsm_remote_family='picohsm', hsm_remote_pool_id='signing',
                hsm_remote_expected_spki_sha256='ab' * 32, hsm_remote_key_id='01',
                hsm_remote_single_key_custody_confirmed=True, hsm_provider_custody_ready=True,
                hsm_remote_probe_pin='synthetic-test-credential', hsm_remote_p11kit_version='0.25.3',
                hsm_remote_listen_address='127.0.0.1',
                hsm_remote_backends={name: {
                    'host': '127.0.0.1', 'serial': serial,
                    'host_public_keys': ['ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixture'],
                } for name, serial in [('hsm-1', '1234'), ('hsm-2', '5678')]},
                hsm_remote_clients={'consumer': {
                    'public_key': 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixture',
                    'sources': ['127.0.0.1/32']}},
            )
            for override, expected in [({}, 0), ({'hsm_remote_family': 'mixed'}, 2),
                                       ({'hsm_remote_expected_spki_sha256': ''}, 2),
                                       ({'hsm_remote_single_key_custody_confirmed': False}, 2),
                                       ({'hsm_remote_probe_pin': '648219'}, 2),
                                       ({'hsm_remote_probe_pin': '0001password'}, 2),
                                       ({'hsm_remote_probe_login': False}, 2)]:
                with self.subTest(override=override):
                    config = work / 'inputs.json'
                    config.write_text(json.dumps(dict(inputs, **override)))
                    result = subprocess.run(
                        [ANSIBLE, '-i', 'localhost,', str(play), '-e', f'@{config}'],
                        env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent)),
                        capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


@unittest.skipUnless(NATIVE and os.name != 'nt' and os.geteuid() == 0,
                     'Requires isolated Linux root and HSM_REMOTE_NATIVE_ROOT tools')
class NativeHSMRemoting(NativeHSMFixture):
    def test_native_transport_identity_signing_denials_and_reconnect(self):
        shadow = self.native(['getent', 'shadow', self.account]).stdout.split(':')
        self.assertEqual(shadow[1], '*')
        urls = self.native([self.p11tool, '--list-token-urls'],
                           env=self.client_env, client=True).stdout
        slots = self.native([self.native_root / 'usr/bin/pkcs11-tool', '--module', self.proxy,
                             '--list-token-slots'], env=self.client_env, client=True).stdout
        for backend in self.backends.values():
            self.assertIn(backend['serial'], slots, slots)
        self.assertNotIn('unpublished-token', slots)
        for index in range(2):
            public = self.probe(index, '--export-pubkey').stdout
            pem = self.work / f'public-{index}.pem'
            pem.write_text(public)
            der = self.native(['openssl', 'pkey', '-pubin', '-in', pem, '-outform', 'DER'], binary=True)
            self.assertEqual(hashlib.sha256(der.stdout).hexdigest(), self.fingerprint)
            self.probe(index, '--test-sign')
        # Raw PKCS11 consumers dlopen the aggregate library rather than register it again.
        message = self.work / 'message'
        signature = self.work / 'signature'
        signature.touch()
        os.chown(signature, self.user.pw_uid, self.user.pw_gid)
        message.write_text('isolated native remoting acceptance\n')
        self.native([self.native_root / 'usr/bin/pkcs11-tool', '--module', self.proxy,
                     '--token-label', 'hsm-1', '--login', '--pin', self.pin, '--id', '01',
                     '--sign', '--mechanism', 'SHA256-RSA-PKCS', '--input-file', message,
                     '--output-file', signature], env=self.client_env, client=True)
        self.native(['openssl', 'dgst', '-sha256', '-verify', self.work / 'public-0.pem',
                     '-signature', signature, message])
        if ANSIBLE:
            self.run_ansible_probe()
        self.assertNotEqual(self.probe(0, '--test-sign', check=False,
                                      env=dict(self.client_env, GNUTLS_PIN='wrong-test-pin')).returncode, 0)
        # Even an authenticated SSH client cannot execute its requested command.
        sentinel = self.work / 'must-not-exist'
        self.native(['ssh', '-F', self.client_dir / 'ssh_config', 'hsm-signing-hsm-1',
                  f'touch {sentinel}'], client=True, check=False)
        self.assertFalse(sentinel.exists())
        auth = self.work / 'hsm-1/authorized_keys'
        original_auth = auth.read_text()
        auth.write_text(original_auth.replace('127.0.0.1/32', '192.0.2.1/32'))
        self.assertNotEqual(self.probe(0, '--test-sign', check=False).returncode, 0)
        auth.write_text(original_auth)
        pins = self.client_dir / 'known_hosts'
        original_pins = pins.read_text()
        pins.write_text('')
        self.assertNotEqual(self.probe(0, '--test-sign', check=False).returncode, 0)
        pins.write_text(original_pins)
        auth.write_text('')
        self.assertNotEqual(self.probe(0, '--test-sign', check=False).returncode, 0)
        auth.write_text(original_auth)
        self.processes[0].terminate()
        self.processes[0].wait(timeout=5)
        self.assertNotEqual(self.probe(0, '--test-sign', check=False).returncode, 0)
        self.probe(1, '--test-sign')
        self.native([self.native_root / 'usr/bin/pkcs11-tool', '--module', self.proxy,
                     '--token-label', 'hsm-2', '--login', '--pin', self.pin, '--id', '01',
                     '--sign', '--mechanism', 'SHA256-RSA-PKCS', '--input-file', message,
                     '--output-file', signature], env=self.client_env, client=True)
        self.native(['openssl', 'dgst', '-sha256', '-verify', self.work / 'public-0.pem',
                     '-signature', signature, message])
        self.start_server(0)
        self.probe(0, '--test-sign')
