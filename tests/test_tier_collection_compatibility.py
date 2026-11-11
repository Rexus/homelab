"""Dependency contracts match verified upstream runtime metadata and generated output."""

import json
from pathlib import Path
import re
import tempfile

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


EVIDENCE = json.loads((UPSTREAM / 'tests/fixtures/collection-runtime.json').read_text())


def version_tuple(value):
    return tuple(map(int, value.split('.')))


class CollectionCompatibility(TierRepositoryTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='collection-contracts-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'

    def test_source_and_generated_manifests_match_catalogs_and_verified_release_lines(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0', '--repo', 'tier-1', '--repo', 'tier-2')
        evidence = {item['name']: item for item in EVIDENCE['collections']}
        for root, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            shared = root / f'{prefix}shared'
            common = yaml.safe_load((shared / 'ansible/playbooks/control-node.yml').read_text())[0]
            catalogs = dict(common['vars']['control_node_base_collection_catalog'])
            for owner in ('shared', 'tier-0', 'tier-1', 'tier-2'):
                repo = root / f'{prefix}{owner}'
                if owner != 'shared':
                    variables = yaml.safe_load((repo / 'ansible/playbooks/control-node.yml').read_text())[0]['vars']
                    catalogs.update(variables.get('control_node_collection_catalog', {}))
                    if owner == 'tier-0':
                        self.assertIn('community.crypto', variables['control_node_setup_collection_names']['vault'])
                manifest = repo / 'ansible/requirements.yml'
                self.assertEqual(manifest.read_bytes(), (UPSTREAM / owner / 'ansible/requirements.yml').read_bytes())
                for item in yaml.safe_load(manifest.read_text())['collections']:
                    self.assertEqual(item['version'], catalogs[item['name']]['version'], item['name'])
            self.assertEqual(set(catalogs), set(evidence))
            for name, item in catalogs.items():
                match = re.fullmatch(r'>=(\d+\.\d+\.\d+),<(\d+\.\d+\.\d+)', item['version'])
                self.assertIsNotNone(match, name)
                release = evidence[name]
                self.assertLessEqual(version_tuple(match[1]), version_tuple(release['version']), name)
                self.assertLess(version_tuple(release['version']), version_tuple(match[2]), name)
                self.assertIn('/' + release['version'] + '/', release['source'].replace('/v', '/'))
                self.assertTrue(release['requires_ansible'].startswith('>='), name)
                required = release['requires_ansible'].removeprefix('>=')
                if version_tuple(required) > version_tuple(EVIDENCE['baseline']):
                    self.assertEqual(name, 'community.proxmox')
                    self.assertEqual(item['min_ansible_core'], required)
                else:
                    self.assertLessEqual(version_tuple(required), version_tuple(EVIDENCE['baseline']), name)
            local = root / f'{prefix}tier-1/ansible/roles/development_data/requirements.yml'
            for item in yaml.safe_load(local.read_text())['collections']:
                self.assertEqual(item['version'], catalogs[item['name']]['version'], item['name'])
            for tier in ('tier-0', 'tier-1', 'tier-2'):
                path = root / f'{prefix}{tier}/ansible/requirements.txt'
                self.assertIn('setuptools>=65,<82', path.read_text().splitlines())
