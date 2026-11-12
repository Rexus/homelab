"""Automatic local runtime preparation without touching system packages or live APIs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from urllib.parse import unquote, urlsplit

import yaml

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipIf(os.name == 'nt', 'Requires native Bash/Python on Linux/WSL')
class TemplateRuntime(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.generate('--repo', 'tier-0')
        self.repo = self.root / 'verify-tier-0'
        self.commands = self.root / 'commands'
        self.commands.mkdir()
        self.marker = self.root / 'terraform-called'
        terraform = self.commands / 'terraform'
        terraform.write_text('#!/bin/sh\ntouch "$TEST_TERRAFORM_MARKER"\n')
        terraform.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.commands) + ':' + os.environ['PATH'],
                        TEMPLATE_RUNTIME_MODE='auto', TEMPLATE_PYTHON=sys.executable,
                        PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1',
                        TEST_TERRAFORM_MARKER=str(self.marker))

    def run_wrapper(self, **overrides):
        return subprocess.run(['bash', 'scripts/proxmox-templates.sh', 'verify'], cwd=self.repo,
                              env=dict(self.env, **overrides), capture_output=True, text=True)

    def test_generated_bootstrap_is_standalone_and_check_mode_does_not_install(self):
        for relative in ('scripts/lib/template-runtime.sh', 'ansible/runtime-requirements.txt',
                         'ansible/playbooks/prepare-template-runtime.yml',
                         'ansible/playbooks/vars/template-collection-source.yml', 'ansible/requirements.yml'):
            self.assertTrue((self.repo / relative).is_file(), relative)
        self.assertFalse((self.root / 'verify-shared').exists())
        result = subprocess.run(['bash', '-c', 'set -euo pipefail; source "$1/scripts/lib/template-runtime.sh"; '
                                 'prepare_template_runtime "$1" verify', 'runtime-test', str(self.repo)],
                                env=dict(self.env, TEMPLATE_RUNTIME_MODE='check'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / '.venv').exists())

    def test_bad_explicit_python_and_failed_install_preserve_state_and_plan(self):
        state = self.repo / '.terraform/state/proxmox-templates/terraform.tfstate'
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 4}')
        plan = self.repo / '.terraform/plans/proxmox-templates.tfplan'
        plan.parent.mkdir(parents=True)
        plan.write_text('reviewed plan')
        wrong = self.commands / 'old-python'
        wrong.write_text('#!/bin/sh\nexit 1\n')
        wrong.chmod(0o755)
        self.assertNotEqual(self.run_wrapper(TEMPLATE_PYTHON=str(wrong)).returncode, 0)
        empty_wheels = self.root / 'empty-wheels'
        empty_wheels.mkdir()
        result = self.run_wrapper(PIP_FIND_LINKS=str(empty_wheels))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists(), 'Dependency failure must precede Terraform')
        self.assertEqual(json.loads(state.read_text()), {'serial': 4})
        self.assertEqual(plan.read_text(), 'reviewed plan')

    def native_collection_runtime(self):
        playbook = shutil.which('ansible-playbook')
        if not playbook:
            self.skipTest('Requires native ansible-playbook and ansible-galaxy')
        galaxy = str(Path(playbook).with_name('ansible-galaxy'))
        if not Path(galaxy).is_file() or not shutil.which('git'):
            self.skipTest('Requires native ansible-galaxy and Git')
        # Exercise collection acquisition without unrelated module-wheel downloads.
        (self.repo / 'ansible/requirements.txt').write_text('')
        target = self.repo / '.venv/collections'
        env = dict(self.env, ANSIBLE_CONFIG=str(self.repo / 'ansible/ansible.cfg'),
                   ANSIBLE_COLLECTIONS_PATH=str(target), ANSIBLE_COLLECTIONS_SCAN_SYS_PATH='false',
                   ANSIBLE_HOME=str(self.root / 'ansible-home'),
                   HTTP_PROXY='http://127.0.0.1:1', HTTPS_PROXY='http://127.0.0.1:1', NO_PROXY='')
        env.pop('CONTROL_NODE_COLLECTIONS_SOURCE', None)
        return playbook, galaxy, target, env

    def collection_git_fixture(self, version='2.1.0', dependencies=None):
        source = self.root / ('upstream-proxmox-' + version)
        source.mkdir()
        (source / 'galaxy.yml').write_text(yaml.safe_dump({
            'namespace': 'community', 'name': 'proxmox', 'version': version,
            'readme': 'README.md', 'authors': ['Runtime fixture'], 'license': ['MIT'],
            'dependencies': dependencies or {},
        }))
        (source / 'README.md').write_text('Pinned fixture release\n')
        subprocess.run(['git', 'init', '--quiet', str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
        commit = ['git', '-C', str(source), '-c', 'user.name=Runtime fixture',
                  '-c', 'user.email=runtime@example.invalid', 'commit', '--quiet', '-m']
        subprocess.run(commit + ['Pinned fixture release'], check=True)
        revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        (source / 'README.md').write_text('Unselected later commit\n')
        subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
        subprocess.run(commit + ['Later unselected commit'], check=True)
        return {'repository': source.as_uri(), 'revision': revision, 'version': version}

    def run_collection_play(self, playbook, env, pin=None, **extra):
        variables = dict(extra)
        if pin is not None:
            variables['control_node_collection_git_overrides'] = {'community.proxmox': pin}
        return subprocess.run(
            [playbook, '-i', 'localhost,', '-c', 'local',
             str(self.repo / 'ansible/playbooks/prepare-template-runtime.yml'),
             '-e', json.dumps(variables)], cwd=self.repo, env=env,
            capture_output=True, text=True, timeout=90,
        )

    def test_native_git_install_uses_pinned_commit_and_reuses_compatible_collection(self):
        playbook, _, target, env = self.native_collection_runtime()
        pin = self.collection_git_fixture()
        self.assertFalse(target.exists(), 'Start with no isolated collection directory')
        first = self.run_collection_play(playbook, env, pin)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        installed = target / 'ansible_collections/community/proxmox'
        self.assertEqual((installed / 'README.md').read_text(), 'Pinned fixture release\n')
        manifest = installed / 'MANIFEST.json'
        self.assertEqual(json.loads(manifest.read_text())['collection_info']['version'], '2.1.0')
        before = manifest.stat().st_mtime_ns
        target.chmod(0o700)
        # A compatible install must not need the source or an available proxy on rerun.
        shutil.rmtree(Path(unquote(urlsplit(pin['repository']).path)))
        repeated = self.run_collection_play(playbook, env, pin)
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertIn('changed=0', repeated.stdout)
        self.assertEqual(manifest.stat().st_mtime_ns, before)
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.root / 'verify-shared').exists())

    def test_native_isolated_compatible_copy_wins_sorted_foreign_copy_and_accepts_galaxy(self):
        playbook, galaxy, target, env = self.native_collection_runtime()
        pin = self.collection_git_fixture(version='2.2.0')
        seed = subprocess.run([galaxy, 'collection', 'install', '--offline',
                               'git+' + pin['repository'] + ',' + pin['revision'],
                               '--collections-path', str(target)],
                              env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(seed.returncode, 0, seed.stdout + seed.stderr)
        shutil.rmtree(Path(unquote(urlsplit(pin['repository']).path)))
        foreign = self.root / '000-foreign-collections'
        foreign.mkdir()
        incompatible = self.collection_git_fixture(version='3.0.0')
        seed_foreign = subprocess.run(
            [galaxy, 'collection', 'install', '--offline', '--force',
             'git+' + incompatible['repository'] + ',' + incompatible['revision'],
             '--collections-path', str(foreign)],
            env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(seed_foreign.returncode, 0, seed_foreign.stdout + seed_foreign.stderr)
        env['ANSIBLE_COLLECTIONS_PATH'] = os.pathsep.join((str(target), str(foreign)))
        listed = subprocess.run([galaxy, 'collection', 'list', '--format', 'json'],
                                env=env, capture_output=True, text=True, check=True, timeout=20)
        paths = list(json.loads(listed.stdout))
        self.assertLess(paths.index(str(foreign / 'ansible_collections')),
                        paths.index(str(target / 'ansible_collections')))
        manifest = target / 'ansible_collections/community/proxmox/MANIFEST.json'
        before = manifest.stat().st_mtime_ns
        for source in ('git', 'galaxy'):
            with self.subTest(source=source):
                result = self.run_collection_play(
                    playbook, dict(env, CONTROL_NODE_COLLECTIONS_SOURCE=source))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('changed=0', result.stdout)
                self.assertEqual(manifest.stat().st_mtime_ns, before)
                self.assertEqual(json.loads(manifest.read_text())['collection_info']['version'], '2.2.0')

    def test_native_source_and_pin_rejection_precedes_python_installation(self):
        playbook, _, target, env = self.native_collection_runtime()
        pin = self.collection_git_fixture()
        cases = [({'CONTROL_NODE_COLLECTIONS_SOURCE': 'unsupported'}, pin),
                 ({}, dict(pin, revision='main')), ({}, dict(pin, version='3.0.0')),
                 ({}, dict(pin, repository='http://example.invalid/collection.git'))]
        for overrides, selected_pin in cases:
            with self.subTest(overrides=overrides, pin=selected_pin):
                result = self.run_collection_play(playbook, dict(env, **overrides), selected_pin)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('TASK [Install declared Python module requirements', result.stdout)
                self.assertFalse((target / 'ansible_collections/community/proxmox').exists())

    def test_native_incompatible_collection_is_replaced_by_selected_release(self):
        playbook, galaxy, target, env = self.native_collection_runtime()
        incompatible = self.collection_git_fixture(version='3.0.0')
        seed = subprocess.run([galaxy, 'collection', 'install', '--offline',
                               'git+' + incompatible['repository'] + ',' + incompatible['revision'],
                               '--collections-path', str(target)],
                              env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(seed.returncode, 0, seed.stdout + seed.stderr)
        foreign = self.root / 'foreign-collections'
        seed_foreign = subprocess.run(
            [galaxy, 'collection', 'install', '--offline', '--force',
             'git+' + incompatible['repository'] + ',' + incompatible['revision'],
             '--collections-path', str(foreign)],
            env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(seed_foreign.returncode, 0, seed_foreign.stdout + seed_foreign.stderr)
        foreign_manifest = foreign / 'ansible_collections/community/proxmox/MANIFEST.json'
        foreign_contents = foreign_manifest.read_bytes()
        foreign_before = foreign_manifest.stat().st_mtime_ns
        env['ANSIBLE_COLLECTIONS_PATH'] = os.pathsep.join((str(target), str(foreign)))
        selected = self.collection_git_fixture()
        result = self.run_collection_play(playbook, env, selected)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = target / 'ansible_collections/community/proxmox/MANIFEST.json'
        self.assertEqual(json.loads(manifest.read_text())['collection_info']['version'], '2.1.0')

        self.assertEqual(foreign_manifest.read_bytes(), foreign_contents)
        self.assertEqual(foreign_manifest.stat().st_mtime_ns, foreign_before)

    def test_native_git_install_rejects_release_metadata_different_from_pin(self):
        playbook, _, _, env = self.native_collection_runtime()
        pin = self.collection_git_fixture(version='2.2.0')
        result = self.run_collection_play(playbook, env, dict(pin, version='2.1.0'))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('source pin declares 2.1.0', result.stdout + result.stderr)

    def test_native_git_dependency_resolution_rejects_missing_dependency_without_galaxy(self):
        playbook, _, target, env = self.native_collection_runtime()
        pin = self.collection_git_fixture(dependencies={'verify.required': '>=1.0.0'})
        result = self.run_collection_play(playbook, env, pin)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('verify.required', result.stdout + result.stderr)
        self.assertNotIn('Tunnel connection failed', result.stdout + result.stderr)
        self.assertFalse((target / 'ansible_collections/community/proxmox').exists())

    @unittest.skipUnless(os.environ.get('HOMELAB_TEMPLATE_WHEELS'),
                         'Set HOMELAB_TEMPLATE_WHEELS to the declared runtime/module wheelhouse')
    def test_fresh_and_repeated_offline_install_override_old_system_ansible(self):
        collection = next((Path(root) / 'ansible_collections/community/proxmox'
                           for root in os.environ.get('ANSIBLE_COLLECTIONS_PATH', '').split(os.pathsep)
                           if (Path(root) / 'ansible_collections/community/proxmox/MANIFEST.json').is_file()), None)
        if collection is None:
            self.skipTest('Pre-stage the declared community.proxmox collection')
        target = self.repo / '.venv/collections/ansible_collections/community/proxmox'
        shutil.copytree(collection, target)
        old_called = self.root / 'old-ansible-called'
        for tool in ('ansible-playbook', 'ansible-doc', 'ansible-galaxy'):
            path = self.commands / tool
            path.write_text('#!/bin/sh\ntouch "$TEST_OLD_ANSIBLE"\necho "ansible [core 2.16.16]"\nexit 1\n')
            path.chmod(0o755)
        env = dict(self.env, PIP_FIND_LINKS=os.environ['HOMELAB_TEMPLATE_WHEELS'],
                   TEST_OLD_ANSIBLE=str(old_called), ANSIBLE_CONFIG=str(self.repo / 'ansible/ansible.cfg'),
                   HTTPS_PROXY='http://127.0.0.1:1', HTTP_PROXY='http://127.0.0.1:1', NO_PROXY='')
        command = ['bash', 'scripts/proxmox-templates.sh', 'setup']
        first = subprocess.run(command, cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn('core 2.21.', first.stdout)
        self.assertFalse(old_called.exists())
        metadata = next((self.repo / '.venv').glob('proxmox-templates-py*/lib/python*/site-packages/ansible_core-*.dist-info/METADATA'))
        before = metadata.stat().st_mtime_ns
        second = subprocess.run(command, cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('changed=0', second.stdout)
        self.assertEqual(metadata.stat().st_mtime_ns, before)
        self.assertFalse(old_called.exists())
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.repo / '.terraform').exists())
        if os.geteuid() != 0:
            sudo = self.commands / 'sudo'
            sudo.write_text('#!/bin/sh\nexit 1\n')
            sudo.chmod(0o755)
            command = ['bash', '-c', 'set -euo pipefail; '
                       'command() { if [[ "$*" == "-v qemu-img" ]]; then return 1; fi; builtin command "$@"; }; '
                       'source "$1/scripts/lib/template-runtime.sh"; prepare_template_runtime "$1" setup',
                       'runtime-ci-test', str(self.repo)]
            denied = subprocess.run(command, env=dict(env, CI='true'), capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn('noninteractive sudo in CI', denied.stderr)
            self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
