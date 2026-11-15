"""Fixed OS endpoints preserve repository policy without installing packages or using the network."""

import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
ROLE = UPSTREAM / 'shared/ansible/roles/baseline'


class SourceProfileExport(TierRepositoryTestCase):
    def test_source_profile_and_supported_os_examples_are_exported(self):
        self.generate()
        generated = self.root / 'verify-shared/ansible/roles/baseline'
        for path in [*(ROLE / 'tasks').glob('repository_profile*.yml'),
                     ROLE / 'vars/package-source-profiles.yml']:
            self.assertEqual(path.read_bytes(), (generated / path.relative_to(ROLE)).read_bytes())
        for tier in range(3):
            text = (self.root / f'verify-tier-{tier}/ansible/group_vars/all.yml.example').read_text()
            self.assertIn('baseline_package_source_profile:', text)
        inputs = yaml.safe_load((self.root / 'verify-tier-2/ansible/group_vars/cache.yml.example').read_text())
        self.assertIn('.ubuntu.com', inputs['cache_squid_allowed_domains'])
        consumer = yaml.safe_load((ROLE / 'tasks/package_consumer.yml').read_text())
        profile = next(i for i, task in enumerate(consumer)
                       if task.get('ansible.builtin.include_tasks') == 'repository_profile.yml')
        refresh = next(i for i, task in enumerate(consumer) if 'ansible.builtin.command' in task)
        self.assertLess(profile, refresh)
        for name in ['main', 'package_consumer']:
            tasks = yaml.safe_load((ROLE / f'tasks/{name}.yml').read_text())
            includes = [task.get('ansible.builtin.include_tasks') for task in tasks]
            self.assertLess(includes.index('repository_profile.yml'), includes.index('trust_anchors.yml'))


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires native Linux/WSL Ansible')
class NativeSourceProfiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='source-profile-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dnf = self.root / 'yum.repos.d'
        self.apt = self.root / 'apt/sources.list.d'
        self.dnf.mkdir()
        self.apt.mkdir(parents=True)
        self.main = self.apt.parent / 'sources.list'
        self.config = self.root / 'ansible.cfg'
        self.config.write_text('[defaults]\nretry_files_enabled=false\n')

    def run_profile(self, distribution='Rocky', success=True, entrypoint='repository_profile', **overrides):
        values = dict(
            ansible_become=False, ansible_python_interpreter=sys.executable,
            ansible_distribution=distribution, ansible_architecture='x86_64',
            baseline_package_source_profile='official',
            repository_proxy_dnf_repo_dir=str(self.dnf),
            baseline_package_source_apt_main_path=str(self.main),
            baseline_package_source_apt_dir=str(self.apt),
        ) | overrides
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([dict(
            hosts='localhost', connection='local', gather_facts=False, become=False, vars=values,
            tasks=[{'ansible.builtin.include_role': dict(name='baseline', tasks_from=entrypoint)}],
        )]))
        environment = dict(os.environ, ANSIBLE_CONFIG=str(self.config), ANSIBLE_NOCOLOR='1',
                           ANSIBLE_ROLES_PATH=str(ROLE.parent),
                           ANSIBLE_LOCAL_TEMP=str(self.root / 'local-temp'),
                           ANSIBLE_REMOTE_TEMP=str(self.root / 'remote-temp'))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)], env=environment,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def rpm(self, section, enabled=1):
        return (f'[{section}]\nname=Vendor {section}\nenabled={enabled}\n'
                'baseurl=https://old.invalid/$releasever/$basearch/\n'
                'mirrorlist=https://mirror-list.invalid/list\nmetalink=https://mirror-list.invalid/meta\n'
                'gpgcheck=1\nrepo_gpgcheck=1\ngpgkey=file:///fixture/vendor-key\n'
                'sslverify=1\npriority=20\n')

    def test_rpm_distributions_keep_trust_disabled_and_custom_sources_idempotently(self):
        for distribution, host in [('Rocky', 'dl.rockylinux.org/pub/rocky'),
                                   ('AlmaLinux', 'repo.almalinux.org/almalinux')]:
            with self.subTest(distribution=distribution):
                path = self.dnf / 'vendor.repo'
                path.write_text(self.rpm('baseos') + self.rpm('appstream') +
                                self.rpm('crb') + self.rpm('devel', 0) + self.rpm('third-party') + self.rpm('epel'))
                before = configparser.ConfigParser(interpolation=None)
                before.read(path)
                values = dict(repository_proxy_dnf_sources=[dict(
                    file='vendor.repo', section='appstream', baseurl='https://internal.invalid/AppStream/')])
                self.run_profile(distribution, **values)
                after = configparser.ConfigParser(interpolation=None)
                after.read(path)
                self.assertEqual(after['baseos']['baseurl'], f'https://{host}/$releasever/BaseOS/$basearch/os/')
                self.assertEqual(after['crb']['baseurl'], f'https://{host}/$releasever/CRB/$basearch/os/')
                self.assertEqual(after['epel']['baseurl'],
                                 'https://dl.fedoraproject.org/pub/epel/$releasever/Everything/$basearch/')
                for section in ['baseos', 'crb', 'epel']:
                    expected = dict(before[section], baseurl=after[section]['baseurl'])
                    expected.pop('mirrorlist')
                    expected.pop('metalink')
                    self.assertEqual(dict(after[section]), expected)
                for section in ['appstream', 'devel', 'third-party']:
                    self.assertEqual(dict(after[section]), dict(before[section]))
                retained = {p: p.read_bytes() for p in self.dnf.iterdir()}
                self.assertRegex(self.run_profile(distribution, **values), r'changed=0\b')
                self.assertEqual({p: p.read_bytes() for p in self.dnf.iterdir()}, retained)

    def test_debian_legacy_and_deb822_preserve_release_components_keys_and_other_sources(self):
        for release in ['bookworm', 'trixie']:
            with self.subTest(release=release):
                original = (f'deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] '
                            f'http://regional.invalid/debian {release} main non-free-firmware\n'
                            f'deb http://regional.invalid/debian-security {release}-security main\n'
                            'deb https://packages.openxpki.org/v3/bookworm/ bookworm release\n')
                self.main.write_text(original)
                modern = self.apt / 'debian.sources'
                content = (f'Types: deb deb-src\nURIs: http://regional.invalid/debian/ '
                           f'https://second.invalid/debian\nSuites: {release} {release}-updates\n'
                           'Components: main contrib\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n')
                modern.write_text(content)
                third_party = self.apt / 'third-party.sources'
                third_party.write_text('URIs: https://independent.invalid/debian\n')
                self.run_profile('Debian')
                self.assertEqual(self.main.read_text(), original.replace(
                    'http://regional.invalid/debian-security', 'https://security.debian.org/debian-security')
                    .replace('http://regional.invalid/debian', 'https://deb.debian.org/debian'))
                self.assertEqual(modern.read_text(), content.replace('http://regional.invalid/debian/',
                    'https://deb.debian.org/debian').replace('https://second.invalid/debian',
                    'https://deb.debian.org/debian'))
                self.assertEqual(third_party.read_text(), 'URIs: https://independent.invalid/debian\n')
                self.assertRegex(self.run_profile('Debian'), r'changed=0\b')

    def test_ubuntu_native_sources_choose_archive_security_or_ports_without_release_changes(self):
        path = self.apt / 'ubuntu.sources'
        original = ('Types: deb\nURIs: http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/\n'
                    'Suites: noble noble-updates noble-backports\nComponents: main restricted universe\n'
                    'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\n'
                    'Types: deb\nURIs: http://security.ubuntu.com/ubuntu/\nSuites: noble-security\n'
                    'Components: main restricted universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n')
        for architecture in ['x86_64', 'aarch64']:
            with self.subTest(architecture=architecture):
                path.write_text(original)
                self.run_profile('Ubuntu', ansible_architecture=architecture)
                archive = ('https://archive.ubuntu.com/ubuntu' if architecture == 'x86_64' else
                           'https://ports.ubuntu.com/ubuntu-ports')
                security = ('https://security.ubuntu.com/ubuntu' if architecture == 'x86_64' else archive)
                self.assertEqual(path.read_text(), original.replace(
                    'http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/', archive)
                    .replace('http://security.ubuntu.com/ubuntu/', security))
                self.assertRegex(self.run_profile('Ubuntu', ansible_architecture=architecture), r'changed=0\b')

    def test_debian_cloud_local_mirror_lists_become_direct_sources_without_modifying_the_lists(self):
        path = self.apt / 'debian.sources'
        content = ('Types: deb\nURIs: mirror+file:///etc/apt/mirrors/debian.list\n'
                   'Suites: bookworm bookworm-updates\nComponents: main non-free-firmware\n'
                   'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg\n\n'
                   'Types: deb\nURIs: mirror+file:/etc/apt/mirrors/debian-security.list\n'
                   'Suites: bookworm-security\nComponents: main\n'
                   'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg\n')
        path.write_text(content)
        self.run_profile('Debian')
        self.assertEqual(path.read_text(), content.replace('mirror+file:///etc/apt/mirrors/debian.list',
            'https://deb.debian.org/debian').replace('mirror+file:/etc/apt/mirrors/debian-security.list',
            'https://security.debian.org/debian-security'))
        self.assertRegex(self.run_profile('Debian'), r'changed=0\b')
        if shutil.which('apt-get'):
            lists = self.root / 'lists'
            (lists / 'partial').mkdir(parents=True)
            parsed = subprocess.run(['apt-get', '-o', f'Dir::Etc::sourcelist={path}',
                '-o', 'Dir::Etc::sourceparts=-', '-o', 'Dir::State::status=/dev/null',
                '-o', f'Dir::State::lists={lists}', 'indextargets'], capture_output=True, text=True, timeout=20)
            self.assertEqual(parsed.returncode, 0, parsed.stdout + parsed.stderr)

    def test_unrecognized_layouts_fail_without_creating_vendor_sources(self):
        self.run_profile('Rocky', success=False)
        self.run_profile('Debian', success=False)
        self.assertEqual(list(self.apt.iterdir()), [])
        self.assertEqual(list(self.dnf.iterdir()), [])

    def test_preserve_custom_apt_and_invalid_profile_choices_do_not_rewrite_files(self):
        path = self.apt / 'debian.sources'
        original = 'URIs: https://internal.invalid/debian\nSuites: bookworm\nComponents: main\n'
        path.write_text(original)
        for values in [dict(baseline_package_source_profile='preserve'),
                       dict(baseline_apt_repositories=[dict(name='internal')])]:
            self.assertRegex(self.run_profile('Debian', **values), r'changed=0\b')
            self.assertEqual(path.read_text(), original)
        self.run_profile('Fedora', success=False)
        self.run_profile('Debian', success=False, baseline_package_source_profile='typo')
        self.assertEqual(path.read_text(), original)
        self.assertEqual(list(self.apt.iterdir()), [path])

    def test_linked_apt_source_is_rejected_without_touching_its_destination(self):
        outside = self.root / 'retained.sources'
        outside.write_text('URIs: http://regional.invalid/debian\n')
        (self.apt / 'debian.sources').symlink_to(outside)
        self.run_profile('Debian', success=False)
        self.assertEqual(outside.read_text(), 'URIs: http://regional.invalid/debian\n')

    def test_bootstrap_proxy_subset_selects_sources_without_full_host_baseline(self):
        path = self.apt / 'debian.sources'
        path.write_text('URIs: http://regional.invalid/debian\nSuites: bookworm\nComponents: main\n')
        values = dict(repository_proxy_enabled=False, repository_proxy_manage_hosts_entry=False,
                      repository_proxy_remove_when_disabled=False, repository_proxy_manage_dnf=False,
                      repository_proxy_manage_apt=False)
        self.run_profile('Debian', entrypoint='repository_proxy', **values)
        self.assertEqual(path.read_text(), 'URIs: https://deb.debian.org/debian\nSuites: bookworm\nComponents: main\n')
        self.assertRegex(self.run_profile('Debian', entrypoint='repository_proxy', **values), r'changed=0\b')
        self.assertEqual(list(self.dnf.iterdir()), [])

    def test_explicit_epel_proxy_is_idempotent_and_can_return_to_global_inheritance(self):
        path = self.dnf / 'epel.repo'
        path.write_text(self.rpm('epel'))
        source = dict(file='epel.repo', section='epel',
                      baseurl='https://dl.fedoraproject.org/pub/epel/$releasever/Everything/$basearch/',
                      proxy='http://cache.example.internal:3128')
        values = dict(repository_proxy_enabled=False, repository_proxy_manage_hosts_entry=False,
                      repository_proxy_remove_when_disabled=False, repository_proxy_manage_dnf=True,
                      repository_proxy_manage_apt=False, repository_proxy_dnf_sources=[source])
        self.run_profile('Rocky', entrypoint='repository_proxy', **values)
        parsed = configparser.ConfigParser(interpolation=None)
        parsed.read(path)
        self.assertEqual(parsed['epel']['proxy'], source['proxy'])
        self.assertEqual(parsed['epel']['gpgcheck'], '1')
        self.assertEqual(parsed['epel']['sslverify'], '1')
        self.assertRegex(self.run_profile('Rocky', entrypoint='repository_proxy', **values), r'changed=0\b')
        original = path.read_bytes()
        source['proxy'] = 'http://operator:fixture@cache.example.internal:3128'
        self.run_profile('Rocky', success=False, entrypoint='repository_proxy', **values)
        self.assertEqual(path.read_bytes(), original)
        source['proxy'] = ''
        self.run_profile('Rocky', entrypoint='repository_proxy', **values)
        parsed = configparser.ConfigParser(interpolation=None)
        parsed.read(path)
        self.assertNotIn('proxy', parsed['epel'])
        self.assertRegex(self.run_profile('Rocky', entrypoint='repository_proxy', **values), r'changed=0\b')


if __name__ == '__main__':
    unittest.main()
