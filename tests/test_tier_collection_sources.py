"""Pinned native Git acquisition, no distribution-server fallback and retained local state."""

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

SHARED = UPSTREAM / 'shared/ansible/playbooks'
PLAY = yaml.safe_load((SHARED / 'control-node.yml').read_text())[0]
PINS = SHARED / 'vars/collection-sources.yml'
NATIVE = os.name != 'nt' and all(shutil.which(tool) for tool in ('ansible-playbook', 'ansible-galaxy', 'git'))


class CollectionSources(TierRepositoryTestCase):
    def test_every_declared_collection_has_one_compatible_source_pin_in_generated_output(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0', '--repo', 'tier-1', '--repo', 'tier-2')
        defaults = yaml.safe_load(PINS.read_text())['control_node_collection_git_defaults']
        evidence = {item['name']: item for item in json.loads(
            (UPSTREAM / 'tests/fixtures/collection-runtime.json').read_text())['collections']}
        catalog = dict(PLAY['vars']['control_node_base_collection_catalog'])
        for tier in range(3):
            profile = yaml.safe_load((UPSTREAM / f'tier-{tier}/ansible/playbooks/control-node.yml').read_text())[0]
            catalog.update(profile['vars']['control_node_collection_catalog'])
        self.assertEqual(set(defaults), set(catalog))
        for name, pin in defaults.items():
            self.assertRegex(pin['repository'], r'^https://github\.com/[^/]+/[^/]+\.git$')
            self.assertRegex(pin['revision'], r'^[0-9a-f]{40}$')
            self.assertEqual(pin['version'], evidence[name]['version'])
            lower, upper = re.fullmatch(r'>=([\d.]+),<([\d.]+)', catalog[name]['version']).groups()
            version = lambda value: tuple(map(int, value.split('.')))
            self.assertLessEqual(version(lower), version(pin['version']))
            self.assertLess(version(pin['version']), version(upper))
        generated = self.root / 'verify-shared/ansible/playbooks'
        for relative in ('vars/collection-sources.yml', 'tasks/control-node-git.yml'):
            self.assertEqual((generated / relative).read_bytes(), (SHARED / relative).read_bytes())
        template_pin = yaml.safe_load((UPSTREAM /
            'tier-0/ansible/playbooks/vars/template-collection-source.yml').read_text())
        self.assertEqual(template_pin['template_runtime_collection_git_default'], defaults['community.proxmox'])


@unittest.skipUnless(NATIVE, 'Requires Linux native Ansible, Git and prepared community.general')
class NativeCollectionSources(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='collection-git-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.collections = self.root / 'collections'
        (self.collections / 'ansible_collections').mkdir(parents=True)
        self.commands = self.root / 'commands'
        self.commands.mkdir()
        self.log = self.root / 'galaxy.jsonl'
        galaxy = shutil.which('ansible-galaxy')
        shim = self.commands / 'ansible-galaxy'
        shim.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                        'with open(os.environ["COLLECTION_SOURCE_LOG"], "a") as stream:\n'
                        '    stream.write(json.dumps(sys.argv[1:]) + "\\n")\n'
                        f'os.execv({galaxy!r}, [{galaxy!r}, *sys.argv[1:]])\n')
        shim.chmod(0o700)
        requests = self.requests = []

        class RefuseGalaxy(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                self.send_error(503, 'Fixture must never contact Galaxy')

        server = ThreadingHTTPServer(('127.0.0.1', 0), RefuseGalaxy)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        existing = os.environ.get('ANSIBLE_COLLECTIONS_PATH', '')
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_CONFIG=str(self.root / 'ansible.cfg'),
                        ANSIBLE_COLLECTIONS_PATH=str(self.collections) + (':' + existing if existing else ''),
                        PATH=str(self.commands) + ':' + os.environ['PATH'], COLLECTION_SOURCE_LOG=str(self.log),
                        ANSIBLE_GALAXY_SERVER=f'http://127.0.0.1:{server.server_port}',
                        ANSIBLE_GALAXY_SERVER_TIMEOUT='1')
        (self.root / 'ansible.cfg').write_text('[defaults]\nstdout_callback = default\n')
        self.pins = {
            'journey_probe.base': self.repository('base'),
            'journey_probe.consumer': self.repository('consumer', {'journey_probe.base': '>=1.0.0,<2.0.0'}),
        }
        self.required = [dict(name=name, version='>=1.0.0,<2.0.0') for name in self.pins]

    def repository(self, name, dependencies=None):
        repo = self.root / f'{name}.git'
        repo.mkdir()
        (repo / 'galaxy.yml').write_text(yaml.safe_dump(dict(namespace='journey_probe', name=name,
            version='1.2.3', readme='README.md', authors=['Disposable fixture'], license=['MIT'],
            dependencies=dependencies or {})))
        (repo / 'README.md').write_text('Retain this pinned payload.\n')
        for args in (['init', '--quiet'], ['add', '.'],
                     ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '--quiet', '-m', 'Disposable collection']):
            subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)
        revision = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                  check=True, capture_output=True, text=True).stdout.strip()
        return dict(repository=repo.as_uri(), revision=revision, version='1.2.3')

    def run_git(self, pins=None, required=None, mode='auto', check=False):
        variables = dict(PLAY['vars'], control_node_collection_git_defaults=pins if pins is not None else self.pins,
                         control_node_required_collections=required if required is not None else self.required,
                         control_node_collections_mode=mode, control_node_collections_source='git',
                         ansible_python_interpreter='{{ ansible_playbook_python }}')
        tasks = [deepcopy(next(task for task in PLAY['tasks'] if task['name'] == name)) for name in (
            'Validate collection acquisition source', 'Install required collections from pinned upstream Git sources',
            'Require the effective collection version to satisfy every declared bound')]
        tasks[1]['ansible.builtin.include_tasks'] = str(SHARED / 'tasks/control-node-git.yml')
        path = self.root / 'install.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, tasks=tasks)], sort_keys=False))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path), *(['--check'] if check else [])],
                              env=self.env, capture_output=True, text=True, timeout=90)

    def test_native_git_batch_resolves_dependencies_and_rerun_preserves_installed_files(self):
        first = self.run_git()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        files = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                 for path in self.collections.rglob('*') if path.is_file()}
        self.assertTrue(files)
        for name in ('base', 'consumer'):
            manifest = json.loads((self.collections / f'ansible_collections/journey_probe/{name}/MANIFEST.json').read_text())
            self.assertEqual(manifest['collection_info']['version'], '1.2.3')
        second = self.run_git()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('changed=0', second.stdout)
        self.assertEqual(files, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                                for path in self.collections.rglob('*') if path.is_file()})
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        installs = [args for args in calls if args[:2] == ['collection', 'install']]
        self.assertEqual(len(installs), 1, calls)
        self.assertIn('--offline', installs[0])
        self.assertNotIn('--no-deps', installs[0])
        self.assertEqual(sum(arg.startswith('git+file:///') for arg in installs[0]), 2)
        self.assertEqual(self.requests, [])

    def test_invalid_pin_fails_before_any_install_and_never_uses_galaxy_fallback(self):
        cases = ({}, dict(self.pins, **{'journey_probe.base': dict(self.pins['journey_probe.base'], revision='main')}),
                 dict(self.pins, **{'journey_probe.base': dict(self.pins['journey_probe.base'], version='3.0.0')}))
        for pins in cases:
            result = self.run_git(pins=pins)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('No Galaxy fallback is performed', result.stdout + result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertTrue(all(args[:2] == ['collection', 'list'] for args in calls), calls)
        self.assertFalse((self.collections / 'ansible_collections/journey_probe').exists())
        self.assertEqual(self.requests, [])

    def test_check_modes_never_acquire_missing_collections(self):
        for mode, dry_run in (('check', False), ('auto', True)):
            result = self.run_git(mode=mode, check=dry_run)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('TASK [Read locally installed collection metadata', result.stdout)
        self.assertFalse(self.log.exists())
        self.assertEqual(self.requests, [])

    def test_generated_tier_precheck_uses_git_by_default_and_accepts_local_source_overrides(self):
        parent = self.root / 'workspace with spaces'
        generated = subprocess.run([sys.executable, str(UPSTREAM / 'scripts/tier-repos/generate.py'),
            '--root', str(parent), '--prefix', 'probe', '--repo', 'shared', '--repo', 'tier-2'],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        repo = parent / 'probe-iac/probe-tier-2'
        variables = dict(control_node_setup='probe', control_node_require_terraform=False,
                         control_node_setup_collection_names={'probe': list(self.pins)},
                         control_node_collection_catalog={name: dict(name=name, version='>=1.0.0,<2.0.0',
                             os_packages={}) for name in self.pins},
                         control_node_collection_git_overrides=self.pins)
        env = dict(self.env, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg'))
        env.pop('CONTROL_NODE_COLLECTIONS_SOURCE', None)
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', 'ansible/playbooks/control-node.yml',
                                 '-e', json.dumps(variables)], cwd=repo, env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        installs = [args for args in calls if args[:2] == ['collection', 'install']]
        self.assertEqual(len(installs), 1, calls)
        self.assertTrue(all('git+file:///' in arg for arg in installs[0] if arg.startswith('git+')))
        self.assertIn('--offline', installs[0])
        self.assertEqual(self.requests, [])

    def test_search_precedence_preserves_compatible_primary_and_repairs_incompatible_primary(self):
        primary, shadow = self.root / 'z-primary', self.root / 'a-shadow'
        existing = self.env['ANSIBLE_COLLECTIONS_PATH']
        self.env['ANSIBLE_COLLECTIONS_PATH'] = f'{primary}:{shadow}:{existing}'

        def versions(destination, release):
            for name in ('base', 'consumer'):
                folder = destination / f'ansible_collections/journey_probe/{name}'
                folder.mkdir(parents=True, exist_ok=True)
                (folder / 'MANIFEST.json').write_text(json.dumps({'collection_info': dict(
                    namespace='journey_probe', name=name, version=release, dependencies={})}))

        versions(primary, '1.2.3')
        versions(shadow, '9.0.0')
        result = self.run_git()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertFalse(any(args[:2] == ['collection', 'install'] for args in calls))
        versions(primary, '3.0.0')
        versions(shadow, '1.2.3')
        shadow_files = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                        for path in shadow.rglob('*') if path.is_file()}
        result = self.run_git()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('base', 'consumer'):
            info = json.loads((primary / f'ansible_collections/journey_probe/{name}/MANIFEST.json').read_text())
            self.assertEqual(info['collection_info']['version'], '1.2.3')
        self.assertEqual(shadow_files, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                                        for path in shadow.rglob('*') if path.is_file()})
        self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main()
