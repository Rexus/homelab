"""Disposable HTTPS/GPG fixtures for the real intake tasks; no installer or services.

Native tests require preinstalled Ansible/collections, ClamAV 1.5.4+ and a database
selected through INTAKE_CLAM_DATABASE. They never fetch tools or definitions.
INTAKE_TEST_OLD_DATABASE=1 explicitly permits an OLD upstream test CVD for source-task
tests only (age 10000). This does not qualify current official definitions: separate
tests retain age 2 and the unchanged worker preflight still rejects ages above 7.
The additional EICAR-only signature establishes a deterministic detection fixture,
not general malware coverage. Mount, systemd and installer acceptance are excluded.
"""

import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

if os.name != 'nt':
    import grp
    import pwd

from intake_repository_fixture import RepositoryHttpsFixture, SignedRepositoryFixture
from tier_repo_test_support import UPSTREAM


RUNTIME = UPSTREAM / 'tier-1/ansible/roles/software_intake/files/runtime'
EICAR = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'


def native_requirements():
    if os.name == 'nt':
        return 'Native Linux filesystem and account semantics required'
    for name in ('openssl', 'gpg', 'gpgv', 'curl', 'file', 'rsync'):
        if not shutil.which(name):
            return f'Native {name} is unavailable'
    ansible = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
    if not ansible or not Path(ansible).is_file():
        return 'Set ANSIBLE_PLAYBOOK to installed native Ansible'
    clam = Path(os.environ.get('INTAKE_CLAM_ROOT', '/nonexistent')) / 'usr/bin/clamscan'
    database = Path(os.environ.get('INTAKE_CLAM_DATABASE', '/nonexistent'))
    if not clam.is_file() or not database.is_dir():
        return 'Set INTAKE_CLAM_ROOT and INTAKE_CLAM_DATABASE to approved local fixtures'
    return None


def tree_bytes(path):
    return {str(file.relative_to(path)): file.read_bytes()
            for file in path.rglob('*') if file.is_file()}


class ArtifactPipelineFixture:
    """The real source/seal/verify/scan/publish/quarantine tasks, under a new temp root."""

    def __init__(self, separate_users=False):
        self.temp = tempfile.TemporaryDirectory(prefix='intake-pipeline-')
        self.root = Path(self.temp.name)
        self.root.chmod(0o711)
        self.runtime = self.root / 'runtime'
        shutil.copytree(RUNTIME, self.runtime)
        # Match installed worker-code ownership/modes even when the checkout is on DrvFS.
        for path in [self.runtime, *self.runtime.rglob('*')]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        self.publisher = getpass.getuser()
        self.fetch_user = self.publisher
        self.scan_user = self.publisher
        self.consumer = self.publisher
        self.scan_group = self.read_group = grp.getgrgid(os.getgid()).gr_name
        if separate_users:
            if os.geteuid() != 0:
                raise ValueError('Distinct fixture users require root; no accounts are created')
            for name in ('nobody', 'daemon', 'www-data'):
                pwd.getpwnam(name)
            self.publisher, self.fetch_user, self.scan_user, self.consumer = 'root', 'nobody', 'daemon', 'www-data'
            self.scan_group = grp.getgrgid(pwd.getpwnam(self.scan_user).pw_gid).gr_name
            self.read_group = grp.getgrgid(pwd.getpwnam(self.consumer).pw_gid).gr_name
        self._directory(self.root / 'config', 0o755)
        self._directory(self.root / 'config/keys', 0o755)
        self.data = self.root / 'data'
        for relative, mode, group in (
            ('', 0o711, None), ('staging', 0o711, None), ('publishing', 0o750, self.scan_group),
            ('public', 0o750, self.read_group), ('quarantine', 0o700, None), ('private', 0o700, None),
            ('runtime-tmp', 0o711, None),
        ):
            self._directory(self.data / relative, mode, group)
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.signer = SignedRepositoryFixture(self.root)
        shutil.copyfile(self.signer.keyring, self.root / 'config/keys/fixture.gpg')
        self.https = RepositoryHttpsFixture(self.artifacts, self.root)
        self.https.certificate.chmod(0o644)
        self.database = self.root / 'database'
        shutil.copytree(os.environ['INTAKE_CLAM_DATABASE'], self.database)
        # This one known non-malware signature does not pretend to be a current daily set.
        (self.database / 'fixture.hdb').write_text(
            f'{hashlib.md5(EICAR, usedforsecurity=False).hexdigest()}:{len(EICAR)}:Intake.Fixture.EICAR\n')
        self.tools = self.root / 'native'
        shutil.copytree(os.environ['INTAKE_CLAM_ROOT'], self.tools, symlinks=True)
        self.clamscan = self.tools / 'usr/bin/clamscan'
        self.uses_old_database = os.environ.get('INTAKE_TEST_OLD_DATABASE') == '1'
        self.max_age = 10000 if self.uses_old_database else 2
        self.environment = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_RETRY_FILES_ENABLED='false',
                                ANSIBLE_HOST_KEY_CHECKING='true', ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'),
                                LD_LIBRARY_PATH=str(self.tools / 'usr/lib/x86_64-linux-gnu'),
                                CVD_CERTS_DIR=str(self.tools / 'etc/clamav/certs'))
        self.environment.pop('ANSIBLE_CONFIG', None)
        self.variables = {
            'ansible_python_interpreter': '/usr/bin/python3',
            'ansible_remote_tmp': str(self.data / 'runtime-tmp'), 'intake_owner': self.publisher,
            'intake_read_group': self.read_group, 'intake_scan_group': self.scan_group,
            'intake_fetch_user': self.fetch_user, 'intake_scan_user': self.scan_user,
            'intake_emit_events': False, 'intake_failed_sources': [],
            'intake_config_dir': str(self.root / 'config'), 'intake_data_dir': str(self.data),
            'intake_clamscan_binary': str(self.clamscan), 'intake_clam_database_dir': str(self.database),
            'intake_max_definition_age_days': self.max_age, 'intake_max_file_mb': 2,
            'intake_max_scan_mb': 4, 'intake_quarantine_days': 14,
            'intake_min_free_bytes': 1073741824,
            'intake_environment': {
                'CURL_CA_BUNDLE': str(self.https.certificate), 'http_proxy': '', 'https_proxy': '',
                'HTTP_PROXY': '', 'HTTPS_PROXY': '', 'ALL_PROXY': '', 'no_proxy': '127.0.0.1,localhost',
            },
        }
        # All subprocess state, including gpgv's optional home, stays in this fixture.
        self.environment['HOME'] = str(self.root / 'home')
        (self.root / 'home').mkdir(mode=0o755)

    def _directory(self, path, mode, group=None):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)
        if group:
            os.chown(path, -1, grp.getgrnam(group).gr_gid)

    def close(self):
        self.https.close()
        subprocess.run(['gpgconf', '--homedir', str(self.signer.home), '--kill', 'all'],
                       capture_output=True, check=False)
        # Read-only publications are the desired result; thaw only our own disposable tree.
        for directory, dirs, files in os.walk(self.root):
            Path(directory).chmod(0o700)
            for name in files:
                path = Path(directory) / name
                if not path.is_symlink():
                    path.chmod(0o600)
        self.temp.cleanup()

    def source(self, data=b'known signed fixture artifact\n', filename='fixture.txt', signature=True):
        artifact = self.artifacts / filename
        artifact.write_bytes(data)
        source = dict(name='fixture', kind='artifact', url=self.https.url + '/' + filename,
                      filename=filename, sha256=hashlib.sha256(data).hexdigest())
        if signature:
            self.signer.sign(artifact, self.artifacts / (filename + '.sig'))
            source.update(signature_url=self.https.url + '/' + filename + '.sig',
                          key_fingerprint=self.signer.fingerprint)
        return source

    def run(self, source, *, tasks=None, extra=None, timeout=120):
        values = self.variables | {'intake_source': source, 'intake_sources': [source]} | (extra or {})
        play = self.runtime / 'fixture.json'
        play.write_text(json.dumps([dict(name='Disposable native artifact pipeline', hosts='localhost',
            connection='local', gather_facts=False, environment={name: self.environment[name]
                for name in ('LD_LIBRARY_PATH', 'CVD_CERTS_DIR')},
            vars=values, tasks=tasks or [
                {'ansible.builtin.include_tasks': 'tasks/source.yml'},
                {'ansible.builtin.copy': {'content': '{{ intake_failed_sources | to_json }}',
                                         'dest': str(self.root / 'failed.json'), 'mode': '0600'}},
                {'ansible.builtin.copy': {'content': '{{ intake_scan_result | default({}) | to_json }}',
                                         'dest': str(self.root / 'scan-result.json'), 'mode': '0600'}},
                {'ansible.builtin.assert': {'that': 'intake_failed_sources | length == 0'}},
            ])]))
        argv = [os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook'), '-i', 'localhost,', str(play)]
        return subprocess.run(argv, cwd=self.runtime, env=self.environment, capture_output=True, text=True, timeout=timeout)

    @property
    def public(self):
        return self.data / 'public/fixture'

    def latest(self):
        return json.loads((self.public / 'latest.json').read_text())

    def receipts(self):
        return [json.loads(path.read_text()) for path in (self.data / 'quarantine').glob('*/intake-quarantine.json')]

    def as_user(self, name, command):
        account = pwd.getpwnam(name)
        return subprocess.run(command, user=account.pw_uid, group=account.pw_gid,
                              extra_groups=[], capture_output=True, text=True)
