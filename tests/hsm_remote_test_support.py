"""Native restricted SSH/p11-kit transport, identity and negative-path checks.

Set HSM_REMOTE_NATIVE_ROOT to an extracted Debian/Ubuntu native tool tree and run
as root on an isolated Linux test host. Only temporary keys/tokens/listeners are
created, including a temporary password-disabled Linux identity. The OS must already
provide OpenSSH's sshd privilege-separation account; this fixture never changes it.
No hardware is provisioned.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import uuid

if os.name != 'nt':
    import pwd

import jinja2
import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-0/ansible/roles/hsm_remote'
NATIVE = os.environ.get('HSM_REMOTE_NATIVE_ROOT')
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None


class NativeHSMFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            pwd.getpwnam('sshd')
        except KeyError as error:
            raise unittest.SkipTest(
                "Native SSH fixture requires the pre-existing openssh-server privilege-separation "
                "account 'sshd'; prepare the OS package on the isolated test host."
            ) from error
        cls.temp = tempfile.TemporaryDirectory(prefix='hsm-remote-native-', dir='/run')
        cls.work = Path(cls.temp.name)
        cls.work.chmod(0o755)
        cls.native_root = Path(NATIVE)
        cls.account = 'hsmt' + uuid.uuid4().hex[:8]
        subprocess.run(['useradd', '--system', '--user-group', '--no-create-home',
                        '--home-dir', '/nonexistent', '--shell', '/bin/sh', '--password', '*',
                        cls.account], check=True, capture_output=True)
        cls.user = pwd.getpwnam(cls.account)
        cls.processes = []
        cls.logs = []
        cls.created_privsep = False
        cls.addClassCleanup(cls.cleanup_native)
        cls.env = dict(os.environ, LD_LIBRARY_PATH=str(cls.native_root / 'usr/lib/x86_64-linux-gnu'))
        cls.p11tool = cls.native_root / 'usr/bin/p11tool'
        cls.module = cls.native_root / 'usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so'
        cls.proxy = cls.native_root / 'usr/lib/x86_64-linux-gnu/p11-kit-proxy.so'
        cls.sshd = cls.native_root / 'usr/sbin/sshd'
        cls.pin = '794629'
        cls.jinja = jinja2.Environment(loader=jinja2.FileSystemLoader(ROLE / 'templates'),
                                       undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
        cls.key = cls.work / 'client.key'
        cls.native(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', cls.key])
        os.chown(cls.key, cls.user.pw_uid, cls.user.pw_gid)
        cls.public = cls.key.with_suffix('.key.pub').read_text().strip()
        cls.original = cls.work / 'original.pem'
        cls.native(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
                 '-out', cls.original])
        der = cls.native(['openssl', 'pkey', '-in', cls.original, '-pubout', '-outform', 'DER'], binary=True)
        cls.fingerprint = hashlib.sha256(der.stdout).hexdigest()
        cls.backends = {}
        cls.server_inputs = []
        # The native privilege-separation directory is normally provided by openssh-server.
        cls.created_privsep = not Path('/run/sshd').exists()
        Path('/run/sshd').mkdir(mode=0o755, exist_ok=True)
        for index in range(2):
            cls.create_backend(index)
        cls.client_dir = cls.work / 'client'
        cls.client_dir.mkdir()
        cls.modules = cls.client_dir / 'pkcs11/modules'
        cls.modules.mkdir(parents=True)
        cls.client_inputs = {
            'hsm_remote_backends': cls.backends, 'hsm_remote_pool_id': 'signing',
            'hsm_remote_port': 0, 'hsm_remote_account': cls.user.pw_name,
            'hsm_remote_config_dir': str(cls.client_dir), 'hsm_remote_ssh_binary': '/usr/bin/ssh',
        }
        shutil.copyfile(cls.key, cls.client_dir / 'client.key')
        os.chmod(cls.client_dir / 'client.key', 0o600)
        os.chown(cls.client_dir / 'client.key', cls.user.pw_uid, cls.user.pw_gid)
        cls.render('known_hosts.j2', cls.client_dir / 'known_hosts', cls.client_inputs)
        # Ports differ only in this isolated test; production uses the declared common service port.
        config = ''
        for name, backend in cls.backends.items():
            config += cls.jinja.get_template('ssh_config.j2').render(
                **dict(cls.client_inputs, hsm_remote_backends={name: backend},
                       hsm_remote_port=backend['port']))
            cls.render('remote.module.j2', cls.modules / f'{name}.module',
                       dict(cls.client_inputs, item={'key': name}))
            probe_dir = cls.client_dir / 'probes' / name / 'pkcs11'
            (probe_dir / 'modules').mkdir(parents=True)
            cls.render('probe.conf.j2', probe_dir / 'pkcs11.conf', cls.client_inputs)
            cls.render('remote.module.j2', probe_dir / 'modules/remote.module',
                       dict(cls.client_inputs, item={'key': name}))
        (cls.client_dir / 'ssh_config').write_text(config)
        cls.client_env = dict(cls.env, XDG_CONFIG_HOME=str(cls.client_dir), GNUTLS_PIN=cls.pin)

    @classmethod
    def native(cls, args, *, env=None, check=True, client=False, binary=False):
        command = [str(value) for value in args]
        selected_env = env or cls.env
        if client:
            command = ['runuser', '-u', cls.user.pw_name, '--', 'env'] + [
                f'{key}={value}' for key, value in selected_env.items()
                if key in ['LD_LIBRARY_PATH', 'XDG_CONFIG_HOME', 'GNUTLS_PIN', 'P11_KIT_DEBUG']] + command
        result = subprocess.run(command, env=selected_env, input=b'' if binary else '',
                                capture_output=True, text=not binary, timeout=30)
        if check and result.returncode:
            logs = ''
            for log in cls.logs:
                log.flush()
                log.seek(0)
                logs += log.read()
            raise AssertionError(f'{command[:3]} rc={result.returncode}: {result.stdout}\n{result.stderr}\n{logs}')
        return result

    @classmethod
    def render(cls, name, dest, inputs):
        dest.write_text(cls.jinja.get_template(name).render(**inputs))

    @classmethod
    def create_backend(cls, index):
        name = f'hsm-{index + 1}'
        directory = cls.work / name
        directory.mkdir()
        store = directory / 'tokens'
        store.mkdir()
        config = directory / 'softhsm.conf'
        config.write_text(f'directories.tokendir = {store}\nobjectstore.backend = file\n')
        env = dict(cls.env, SOFTHSM2_CONF=str(config))
        utility = cls.native_root / 'usr/bin/softhsm2-util'
        cls.native([utility, '--module', cls.module, '--init-token', '--free', '--label', name,
                 '--so-pin', '937462', '--pin', cls.pin], env=env)
        cls.native([utility, '--module', cls.module, '--import', cls.original, '--token', name, '--id', '01',
                 '--label', 'original-signing-key', '--pin', cls.pin], env=env)
        urls = cls.native([cls.p11tool, '--provider', cls.module, '--list-token-urls'], env=env).stdout
        serial = re.search(r'serial=([^;\s]+)', urls).group(1)
        if index == 0:
            # A second token on this provider must remain hidden by the fixed serial filter.
            cls.native([utility, '--module', cls.module, '--init-token', '--free', '--label',
                        'unpublished-token', '--so-pin', '937462', '--pin', cls.pin], env=env)
        for path in [store, *store.rglob('*')]:
            os.chown(path, cls.user.pw_uid, cls.user.pw_gid)
        hostkey = directory / 'host.key'
        cls.native(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', hostkey])
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        inputs = {
            'hsm_remote_port': port, 'hsm_remote_pool_id': name,
            'hsm_remote_listen_address': '127.0.0.1', 'hsm_remote_host_key_files': [str(hostkey)],
            'hsm_remote_config_dir': str(directory), 'hsm_remote_account': cls.user.pw_name,
            'hsm_remote_p11kit_binary': str(cls.native_root / 'usr/bin/p11-kit'),
            'hsm_provider_library': str(cls.module), 'hsm_provider_driver': 'opensc',
            'hsm_provider_expected_serial': serial,
            'hsm_remote_environment': dict(
                SOFTHSM2_CONF=str(config), LD_LIBRARY_PATH=cls.env['LD_LIBRARY_PATH'],
                P11_KIT_PRIVATEDIR=str(cls.native_root / 'usr/libexec/p11-kit')),
            'hsm_remote_clients': {'test': {'public_key': cls.public, 'sources': ['127.0.0.1/32']}},
        }
        cls.render('authorized_keys.j2', directory / 'authorized_keys', inputs)
        cls.render('sshd_config.j2', directory / 'sshd_config', inputs)
        cls.native([cls.sshd, '-t', '-f', directory / 'sshd_config'])
        cls.server_inputs.append(inputs)
        cls.backends[name] = dict(host='127.0.0.1', port=port, serial=serial,
                                  host_public_keys=[hostkey.with_suffix('.key.pub').read_text().strip()])
        cls.start_server(index)

    @classmethod
    def start_server(cls, index):
        config = Path(cls.server_inputs[index]['hsm_remote_config_dir']) / 'sshd_config'
        log = open(config.parent / f'log-{len(cls.logs)}', 'w+')
        process = subprocess.Popen([str(cls.sshd), '-D', '-e', '-f', str(config)],
                                   env=cls.env, stdout=log, stderr=log, start_new_session=True)
        cls.logs.append(log)
        if index < len(cls.processes):
            cls.processes[index] = process
        else:
            cls.processes.append(process)
        for _ in range(50):
            try:
                with socket.create_connection(('127.0.0.1', cls.server_inputs[index]['hsm_remote_port']), .1):
                    return
            except OSError:
                time.sleep(.02)
        log.seek(0)
        raise AssertionError(log.read())

    def probe(self, index, *options, check=True, env=None):
        serial = self.backends[f'hsm-{index + 1}']['serial']
        return self.native([self.p11tool, '--batch', '--login', *options,
                         f'pkcs11:serial={serial};id=%01;type=private'],
                        env=dict(env or self.client_env,
                                 XDG_CONFIG_HOME=str(self.client_dir / 'probes' / f'hsm-{index + 1}')),
                        check=check, client=True)

    @classmethod
    def cleanup_native(cls):
        for process in cls.processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        for log in cls.logs:
            log.close()
        subprocess.run(['pkill', '-TERM', '-u', str(cls.user.pw_uid)], check=False, capture_output=True)
        for _ in range(20):
            result = subprocess.run(['pgrep', '-u', str(cls.user.pw_uid)], capture_output=True)
            if result.returncode:
                break
            time.sleep(.05)
        if cls.created_privsep:
            Path('/run/sshd').rmdir()
        subprocess.run(['userdel', cls.account], check=True, capture_output=True)
        cls.temp.cleanup()

    def run_ansible_probe(self):
        """Exercise the production inventory regex and canonical crypto-module SPKI hash."""
        play = self.work / 'probe.yml'
        play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'gather_facts': False,
            'tasks': [{'ansible.builtin.include_role': {
                'name': 'hsm_remote', 'tasks_from': 'probe'}}],
        }]))
        inputs = dict(self.client_inputs,
                      ansible_connection='local', ansible_become_method='su',
                      ansible_python_interpreter='/usr/bin/python3',
                      hsm_remote_backend={'key': 'hsm-1', 'value': self.backends['hsm-1']},
                      hsm_remote_client_user=self.user.pw_name,
                      hsm_remote_p11tool_binary=str(self.p11tool),
                      hsm_remote_proxy_library=str(self.proxy), hsm_remote_key_id='01',
                      hsm_remote_expected_spki_sha256=self.fingerprint,
                      hsm_remote_probe_pin=self.pin, hsm_remote_probe_environment=self.client_env)
        config = self.work / 'probe-inputs.json'
        config.write_text(json.dumps(inputs))
        result = self.native([ANSIBLE, '-i', 'localhost,', play, '-e', f'@{config}'],
                             env=dict(self.env, ANSIBLE_ROLES_PATH=str(ROLE.parent)))
        self.assertIn('failed=0', result.stdout)
        config.write_text(json.dumps(dict(inputs, hsm_remote_expected_spki_sha256='00' * 32)))
        result = self.native([ANSIBLE, '-i', 'localhost,', play, '-e', f'@{config}'],
                             env=dict(self.env, ANSIBLE_ROLES_PATH=str(ROLE.parent)), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Original-key mismatch', result.stdout)
        self.native([self.native_root / 'usr/bin/pkcs11-tool', '--module', self.proxy,
                     '--token-label', 'hsm-1', '--login', '--pin', self.pin,
                     '--keypairgen', '--key-type', 'rsa:2048', '--id', '02', '--label', 'test-extra'],
                    env=self.client_env, client=True)
        config.write_text(json.dumps(inputs))
        result = self.native([ANSIBLE, '-i', 'localhost,', play, '-e', f'@{config}'],
                             env=dict(self.env, ANSIBLE_ROLES_PATH=str(ROLE.parent)), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Dedicate this token to one original signing key', result.stdout)
