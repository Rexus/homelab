"""Native collection bounds, effective search precedence and convergence contracts."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


PLAY = yaml.safe_load((UPSTREAM / 'shared/ansible/playbooks/control-node.yml').read_text())[0]
NATIVE = os.name != 'nt' and bool(shutil.which('ansible-playbook'))


def task_named(name):
    return deepcopy(next(task for task in PLAY['tasks'] if task['name'] == name))


@unittest.skipUnless(NATIVE, 'Requires Linux Ansible and community.general')
class ControlNodeVersions(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='control-node-versions-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.collections = self.root / 'collections'
        self.shadowed = self.root / 'shadowed'
        existing = os.getenv('ANSIBLE_COLLECTIONS_PATH', ':'.join([
            str(Path.home() / '.ansible/collections'), '/usr/share/ansible/collections']))
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1',
                        ANSIBLE_COLLECTIONS_PATH=f'{self.collections}:{self.shadowed}:{existing}')

    def collection(self, version, root=None):
        path = (root or self.collections) / 'ansible_collections/journey_probe/bounds'
        path.mkdir(parents=True, exist_ok=True)
        (path / 'MANIFEST.json').write_text(json.dumps({
            'collection_info': dict(namespace='journey_probe', name='bounds', version=version, dependencies={})}))

    def run_tasks(self, tasks, variables):
        path = self.root / 'check.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, tasks=tasks)], sort_keys=False))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)],
                              cwd=UPSTREAM, env=self.env, capture_output=True, text=True, timeout=60)

    def verify(self, requirement, version, accepted):
        self.collection(version)
        result = self.run_tasks([task_named(
            'Require the effective collection version to satisfy every declared bound')], {
                'control_node_required_collections': [dict(name='journey_probe.bounds', version=requirement)]})
        self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
        if not accepted:
            self.assertIn('Correct outdated or unversioned collections earlier', result.stdout + result.stderr)

    def test_native_lookup_enforces_lower_upper_exact_excluded_and_unknown_versions(self):
        minimum = PLAY['vars']['control_node_base_collection_catalog']['community.general']['version']
        cases = [(minimum, '10.0.0', False), (minimum, '10.2.0', True),
                 ('>=1.5.0,<2.0.0', '1.5.0', True), ('>=1.5.0,<2.0.0', '1.4.9', False),
                 ('>=1.5.0,<2.0.0', '2.0.0', False), ('==1.5.0', '1.5.0', True),
                 ('>=1.5.0,!=1.6.0', '1.6.0', False), ('>=1.5.0', '*', False)]
        for requirement, version, accepted in cases:
            with self.subTest(requirement=requirement, version=version):
                self.verify(requirement, version, accepted)

    def test_compatible_shadowed_copy_does_not_hide_incompatible_effective_copy(self):
        self.collection('1.9.0', self.shadowed)
        self.verify('>=1.5.0,<2.0.0', '1.0.0', False)
        # An obsolete, unused system copy must not invalidate a good first-path copy.
        self.collection('1.0.0', self.shadowed)
        self.verify('>=1.5.0,<2.0.0', '1.9.0', True)

    def test_version_lookup_dependency_is_selected_only_for_nonempty_setups(self):
        for selected in ([], ['kubernetes.core']):
            variables = dict(PLAY['vars'], control_node_selected_setup='probe',
                             control_node_setup_collection_names=dict(probe=selected),
                             control_node_collection_catalog={'kubernetes.core': dict(name='kubernetes.core')})
            expected = selected + (['community.general'] if selected else [])
            result = self.run_tasks([task_named('Resolve required collections for selected setup'), {
                'ansible.builtin.assert': {'that': [
                    'control_node_required_collections | map(attribute="name") | list == expected']}}],
                dict(variables, expected=expected))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_present_versioned_collections_still_reach_native_range_convergence(self):
        binary_dir = self.root / 'bin'
        binary_dir.mkdir()
        log = self.root / 'galaxy.jsonl'
        shim = binary_dir / 'ansible-galaxy'
        shim.write_text(
            '#!/usr/bin/env python3\nimport json, os, sys\n'
            'with open(os.environ["GALAXY_TEST_LOG"], "a") as log:\n'
            '    log.write(json.dumps(sys.argv[1:]) + "\\n")\n'
            'print("Nothing to do. All requested collections are already installed.")\n')
        shim.chmod(0o700)
        self.env.update(PATH=f'{binary_dir}:{os.environ["PATH"]}', GALAXY_TEST_LOG=str(log))
        required = [dict(name='journey_probe.bounds', version='>=1.5.0,<2.0.0'),
                    dict(name='journey_probe.present'), dict(name='journey_probe.missing')]
        variables = dict(control_node_required_collections=required,
                         control_node_still_missing_collections=[required[-1]])
        task = task_named('Install missing or incompatible Ansible collections with native Galaxy ranges')
        for _ in range(2):
            result = self.run_tasks([task], variables)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('changed=0', result.stdout)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(calls, [
            ['collection', 'install', 'journey_probe.bounds:>=1.5.0,<2.0.0'],
            ['collection', 'install', 'journey_probe.missing'],
        ] * 2)

    def test_native_galaxy_needs_no_network_for_a_compatible_prestaged_range(self):
        self.collection('1.9.0')
        self.env.update(ANSIBLE_GALAXY_SERVER='https://127.0.0.1:9', ANSIBLE_GALAXY_SERVER_TIMEOUT='1')
        tasks = [task_named(name) for name in [
            'Install missing or incompatible Ansible collections with native Galaxy ranges',
            'Require the effective collection version to satisfy every declared bound']]
        variables = dict(control_node_required_collections=[
            dict(name='journey_probe.bounds', version='>=1.5.0,<2.0.0')],
            control_node_still_missing_collections=[])
        for _ in range(2):
            result = self.run_tasks(tasks, variables)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('changed=0', result.stdout)


if __name__ == '__main__':
    unittest.main()
