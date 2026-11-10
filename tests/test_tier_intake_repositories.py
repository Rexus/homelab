"""Native repository signatures and full post-copy integrity, with no live feeds."""

import importlib.util
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from intake_repository_fixture import RepositoryHttpsFixture, SignedRepositoryFixture
from tier_repo_test_support import UPSTREAM

RUNTIME = UPSTREAM / 'tier-1/ansible/roles/software_intake/files/runtime'
NATIVE_APT = os.name != 'nt' and all(shutil.which(tool) for tool in ('gpg', 'gpgv', 'apt-ftparchive', 'dpkg-deb'))
NATIVE_RPM = os.name != 'nt' and all(shutil.which(tool) for tool in
                                   ('gpg', 'gpgv', 'rpm', 'rpmkeys', 'rpmbuild', 'rpmsign', 'createrepo_c'))


class RepositoryAdapterContracts(unittest.TestCase):
    def test_acquisition_is_scoped_and_never_publishes(self):
        for kind in ('rpm', 'apt'):
            tasks = yaml.safe_load((RUNTIME / f'tasks/acquire-{kind}.yml').read_text())
            for task in tasks:
                if any(key in task for key in ('ansible.builtin.command', 'ansible.builtin.get_url')):
                    self.assertIs(task['become'], True)
                    self.assertEqual(task['become_user'], '{{ intake_fetch_user }}')
            encoded = str(tasks)
            self.assertNotIn('shell', encoded)
            self.assertNotIn('--newest-only', encoded)
            self.assertNotIn('createrepo_c', encoded)
        rpm = (RUNTIME / 'tasks/acquire-rpm.yml').read_text()
        self.assertIn('--download-metadata', rpm)
        self.assertIn('--gpgcheck', rpm)
        self.assertIn('/fetch/rpm-root', rpm)
        self.assertIn('gpgcheck=1', (RUNTIME / 'templates/rpm.conf.j2').read_text())
        apt = (RUNTIME / 'tasks/acquire-apt.yml').read_text()
        for flag in ('--check-gpg', '--checksums', '--state-cache-days=0', '--keyring=', '/fetch/debmirror.conf'):
            self.assertIn(flag, apt)
        self.assertEqual(yaml.safe_load(apt)[1]['ansible.builtin.copy']['content'], '1;\n')
        self.assertNotIn('--ignore-release-gpg', apt)

    def test_final_verification_uses_scan_identity_and_sealed_payload(self):
        for kind in ('rpm', 'apt'):
            task = yaml.safe_load((RUNTIME / f'tasks/verify-{kind}.yml').read_text())[0]
            self.assertIs(task['become'], True)
            self.assertEqual(task['become_user'], '{{ intake_scan_user }}')
            argv = task['ansible.builtin.command']['argv']
            self.assertIn('--payload={{ intake_verification_path }}', argv)
            self.assertIn(f'--work={{{{ intake_work.path }}}}/scan/{kind}', argv)
            self.assertIs(task['changed_when'], False)


class RepositoryVerificationCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='intake-repository-case-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'sealed'
        shutil.copytree(self.original, self.payload)

    def verify(self, kind='apt', **options):
        argv = [sys.executable, str(RUNTIME / 'repository_verify.py'), f'--kind={kind}',
                f'--payload={self.payload}', f'--work={self.root}/verification',
                f'--key={self.fixture.key}', f'--keyring={self.fixture.keyring}',
                f'--fingerprint={self.fixture.fingerprint}', '--architectures=amd64' if kind == 'apt'
                else '--architectures=noarch', '--distribution=fixture', '--components=main']
        argv.extend(f'--{key.replace("_", "-")}={value}' for key, value in options.items())
        return subprocess.run(argv, capture_output=True, text=True)

    def assert_unreferenced_files_rejected(self, kind):
        for name in ('evil.sh', 'README', 'bin/tool', '.hidden'):
            with self.subTest(unreferenced_file=name):
                path = self.payload / name
                path.parent.mkdir(exist_ok=True)
                path.write_text('Harmless scanner content, but no publisher authentication.\n')
                try:
                    result = self.verify(kind=kind)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Unauthenticated extra repository files', result.stderr)
                    self.assertTrue(path.is_file(), 'Verification must not remove untrusted files after sealing')
                finally:
                    path.unlink()


@unittest.skipUnless(NATIVE_APT, 'Requires native GPG and Debian package tools on Linux')
class AptRepositoryVerification(RepositoryVerificationCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec('debian') is None:
            raise unittest.SkipTest('Install python3-debian for native APT metadata parsing')
        cls.temp = tempfile.TemporaryDirectory(prefix='intake-repository-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture = SignedRepositoryFixture(Path(cls.temp.name))
        cls.addClassCleanup(cls.fixture.close)
        cls.original = cls.fixture.apt()

    def test_signed_release_binds_every_package_without_writing_payload(self):
        before = {str(path.relative_to(self.payload)): path.read_bytes()
                  for path in self.payload.rglob('*') if path.is_file()}
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['packages_verified'], 1)
        self.assertTrue(evidence['metadata_signature'])
        self.assertTrue(evidence['release_expiry_enforced'])
        self.assertEqual(before, {str(path.relative_to(self.payload)): path.read_bytes()
                                 for path in self.payload.rglob('*') if path.is_file()})

    def test_tampered_package_or_index_is_rejected(self):
        for relative in ('pool/main/i/intake-fixture/fixture_1.0_all.deb', 'dists/fixture/main/binary-amd64/Packages.gz'):
            with self.subTest(tampered=relative):
                path = self.payload / relative
                original = path.read_bytes()
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                result = self.verify()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('checksum mismatch', result.stderr)
                path.write_bytes(original)

    def test_wrong_key_and_expired_release_are_rejected(self):
        result = self.verify(fingerprint='0' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pinned primary key', result.stderr)
        expired = self.fixture.apt(name='apt-expired', expired=True)
        shutil.rmtree(self.payload)
        shutil.copytree(expired, self.payload)
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('expired', result.stderr)

    def test_pocket_path_can_bind_an_explicit_vendor_codename(self):
        pocket = self.fixture.apt(name='apt-pocket', distribution='fixture-updates', codename='fixture', origin='Ubuntu')
        shutil.rmtree(self.payload)
        shutil.copytree(pocket, self.payload)
        rejected = self.verify(distribution='fixture-updates')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('codename differs', rejected.stderr)
        accepted = self.verify(distribution='fixture-updates', expected_codename='fixture')
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)['codename'], 'fixture')

    def test_tampered_detached_release_cannot_hide_behind_valid_inrelease(self):
        release = self.payload / 'dists/fixture/Release'
        release.write_bytes(release.read_bytes() + b'\nChanged: unauthenticated\n')
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, 'gpgv verification failed|bad publisher signature')

    def test_multisigned_release_still_requires_the_pinned_valid_signer(self):
        other = self.fixture.add_signer()
        distribution = self.payload / 'dists/fixture'
        for signers in ([self.fixture.fingerprint, other], [other]):
            with self.subTest(pinned_signer_present=self.fixture.fingerprint in signers):
                self.fixture.sign(distribution / 'Release', distribution / 'Release.gpg', signers=signers)
                self.fixture.sign(distribution / 'Release', distribution / 'InRelease', clearsign=True, signers=signers)
                result = self.verify()
                if len(signers) == 2:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Missing valid pinned', result.stderr)

    def test_release_without_vendor_expiry_is_reported_without_claiming_expiry_enforcement(self):
        distribution = self.payload / 'dists/fixture'
        release = distribution / 'Release'
        release.write_text('\n'.join(line for line in release.read_text().splitlines()
                                     if not line.startswith('Valid-Until:')) + '\n')
        self.fixture.sign(release, distribution / 'Release.gpg')
        self.fixture.sign(release, distribution / 'InRelease', clearsign=True)
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertIsNone(evidence['release_valid_until'])
        self.assertIs(evidence['release_expiry_enforced'], False)

    def test_unreferenced_clean_scripts_and_other_files_cannot_be_published(self):
        self.assert_unreferenced_files_rejected('apt')


@unittest.skipUnless(NATIVE_RPM, 'Requires native RPM signing, createrepo_c and GPG on Linux')
class RpmRepositoryVerification(RepositoryVerificationCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec('createrepo_c') is None:
            raise unittest.SkipTest('Install the native createrepo_c Python library')
        cls.temp = tempfile.TemporaryDirectory(prefix='intake-rpm-repository-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fixture = SignedRepositoryFixture(Path(cls.temp.name))
        cls.addClassCleanup(cls.fixture.close)
        cls.original = cls.fixture.rpm()

    def test_signed_release_binds_every_package_without_writing_payload(self):
        result = self.verify(kind='rpm', repo_gpgcheck='true')
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['packages_verified'], 2)
        self.assertTrue(evidence['metadata_signature'])

    def test_tampered_package_or_index_is_rejected(self):
        for path in (next(self.payload.glob('*.rpm')), next((self.payload / 'repodata').glob('*primary*'))):
            with self.subTest(tampered=path.name):
                original = path.read_bytes()
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                result = self.verify(kind='rpm', repo_gpgcheck='true')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('checksum mismatch', result.stderr)
                path.write_bytes(original)

    def test_wrong_key_is_rejected(self):
        result = self.verify(kind='rpm', repo_gpgcheck='true', fingerprint='0' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pinned primary key', result.stderr)

    def test_unsigned_rpm_with_correct_metadata_hash_is_rejected(self):
        unsigned = self.fixture.rpm(name='unsigned', signed=False)
        shutil.rmtree(self.payload)
        shutil.copytree(unsigned, self.payload)
        for metadata_check in ('true', 'false'):
            with self.subTest(repo_gpgcheck=metadata_check):
                result = self.verify(kind='rpm', repo_gpgcheck=metadata_check)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('rpmkeys verification failed', result.stderr)

    def test_explicit_unsigned_metadata_variant_still_checks_every_signed_package(self):
        (self.payload / 'repodata/repomd.xml.asc').unlink()
        result = self.verify(kind='rpm', repo_gpgcheck='false')
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['packages_verified'], 2)
        self.assertIs(evidence['metadata_signature'], False)

    def test_unreferenced_clean_scripts_and_other_files_cannot_be_published(self):
        self.assert_unreferenced_files_rejected('rpm')


@unittest.skipUnless(NATIVE_RPM and NATIVE_APT and all(shutil.which(tool) for tool in
                     ('ansible-playbook', 'openssl', 'dnf', 'debmirror')),
                     'Requires native mirror tools, Ansible and signed-fixture tools')
class NativeRepositoryAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='intake-native-acquisition-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = SignedRepositoryFixture(self.root)
        self.addCleanup(self.fixture.close)

    def acquire(self, kind, pocket=False):
        repository = self.fixture.rpm() if kind == 'rpm' else self.fixture.apt(
            distribution='fixture-updates' if pocket else 'fixture', codename='fixture', origin='Ubuntu')
        server = RepositoryHttpsFixture(repository, self.root)
        self.addCleanup(server.close)
        runtime = self.root / 'runtime'
        shutil.copytree(RUNTIME, runtime)
        job = self.root / 'job'
        for name in ('fetch', 'content', 'scan'):
            (job / name).mkdir(parents=True)
        keys = self.root / 'config/keys'
        keys.mkdir(parents=True)
        for extension, source in (('asc', self.fixture.key), ('gpg', self.fixture.keyring)):
            shutil.copyfile(source, keys / f'fixture.{extension}')
        # The extracted DNF uses a private plugin path and this fixture's CA, never TLS bypass.
        tools = self.root / 'tools'
        tools.mkdir()
        native_dnf = shutil.which('dnf')
        options = [f'--setopt=sslcacert={server.certificate}']
        if os.getenv('HOMELAB_INTAKE_DNF_PLUGINPATH'):
            options.append('--setopt=pluginpath=' + os.environ['HOMELAB_INTAKE_DNF_PLUGINPATH'])
        wrapper = tools / 'dnf'
        wrapper.write_text('#!/usr/bin/env python3\nimport os,sys\n'
                           f'os.execv({native_dnf!r}, [{native_dnf!r}, *{options!r}, *sys.argv[1:]])\n')
        wrapper.chmod(0o755)
        source = {'name': 'fixture', 'kind': kind, 'url': server.url, 'releasever': '10',
                  'key_fingerprint': self.fixture.fingerprint, 'repo_gpgcheck': True,
                  'architectures': ['x86_64', 'noarch'] if kind == 'rpm' else ['amd64'],
                  'distribution': 'fixture-updates' if pocket else 'fixture', 'expected_codename': 'fixture',
                  'components': ['main']}
        environment = dict(os.environ, PATH=f'{tools}:{os.environ["PATH"]}')
        proxy = {'http_proxy': '', 'https_proxy': '', 'HTTP_PROXY': '', 'HTTPS_PROXY': '', 'ALL_PROXY': '',
                 'no_proxy': '127.0.0.1,localhost', 'SSL_CERT_FILE': str(server.certificate),
                 'PERL_LWP_SSL_CA_FILE': str(server.certificate)}
        play = runtime / 'native-acquisition.json'
        play.write_text(json.dumps([{'name': 'Native HTTPS acquisition fixture', 'hosts': 'localhost',
            'connection': 'local', 'gather_facts': False, 'vars': {
                'ansible_python_interpreter': '/usr/bin/python3', 'ansible_user': getpass.getuser(),
                'intake_fetch_user': getpass.getuser(), 'intake_scan_user': getpass.getuser(),
                'intake_work': {'path': str(job)},
                'intake_payload': str(job / 'content'), 'intake_source': source,
                'intake_config_dir': str(self.root / 'config'), 'intake_environment': proxy},
            'tasks': [{'ansible.builtin.include_tasks': f'tasks/acquire-{kind}.yml'},
                      {'ansible.builtin.copy': {'src': str(job / 'content') + '/',
                                               'dest': str(self.root / 'sealed') + '/', 'remote_src': True}},
                      {'ansible.builtin.set_fact': {'intake_verification_path': str(self.root / 'sealed')}},
                      {'ansible.builtin.include_tasks': f'tasks/verify-{kind}.yml'}]}]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)], cwd=self.root,
                                env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return repository, job / 'content'

    def test_native_dnf_keeps_both_versions_and_original_metadata(self):
        original, mirrored = self.acquire('rpm')
        self.assertEqual(len(list(mirrored.glob('*.rpm'))), 2)
        self.assertEqual((original / 'repodata/repomd.xml').read_bytes(),
                         (mirrored / 'repodata/repomd.xml').read_bytes())

    def test_native_debmirror_preserves_vendor_release_and_packages(self):
        original, mirrored = self.acquire('apt')
        self.assertEqual(len(list(mirrored.rglob('*.deb'))), 1)
        self.assertEqual((original / 'dists/fixture/Release').read_bytes(),
                         (mirrored / 'dists/fixture/Release').read_bytes())
        self.assertFalse((mirrored / '.temp').exists())
        self.assertFalse((mirrored / 'project/trace').exists())
        self.assertTrue((self.root / 'job/fetch/debmirror-state').is_dir())
        self.assertTrue((self.root / 'job/fetch/debmirror-trace').is_dir())

    def test_native_debmirror_accepts_signed_ubuntu_pocket(self):
        original, mirrored = self.acquire('apt', pocket=True)
        self.assertEqual((original / 'dists/fixture-updates/Release').read_bytes(),
                         (mirrored / 'dists/fixture-updates/Release').read_bytes())


if __name__ == '__main__':
    unittest.main()
