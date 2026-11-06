"""Preserve display casing while using lowercase collection/repository paths."""

import json
import os
import re
import subprocess
import sys
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generate import REPOSITORIES


class PrefixCasing(TierRepositoryTestCase):
    def test_mixed_case_display_prefix_has_lowercase_paths_and_working_links(self):
        preview = self.generate('--prefix', 'HomeLab', '--dry-run')
        self.assertIn('homelab-iac', preview.stdout)
        self.assertFalse(self.parent.exists())
        self.generate('--prefix', 'HomeLab')
        collection = self.parent / 'homelab-iac'
        self.assertEqual({path.name for path in self.parent.iterdir()}, {'homelab-iac'})
        self.assertEqual({path.name for path in collection.iterdir()},
                         {f'homelab-{name}' for name in REPOSITORIES})
        for repo in collection.iterdir():
            self.assertTrue((repo / 'README.md').read_text().startswith('# HomeLab '))
            for path in repo.rglob('*'):
                if not path.is_file() or path.name == '.generated-files.json':
                    continue
                content = path.read_text(encoding='utf-8')
                self.assertNotIn('HomeLab-', content, str(path))
                if path.suffix == '.md':
                    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                        target = target.split('#')[0]
                        if target and ':' not in target:
                            self.assertTrue((path.parent / target).exists(), (path, target))
        architecture = collection / 'homelab-architecture'
        self.assertTrue((architecture / 'docs/README.md').read_text().startswith('# HomeLab '))
        self.assertTrue((architecture / 'docs/naming-conventions.md').read_text().startswith('# HomeLab '))
        self.assertIn('records for HomeLab.', (architecture / 'README.md').read_text())
        script = collection / 'homelab-tier-0/scripts/proxmox-templates.sh'
        self.assertIn('../homelab-shared/config/platform.tfvars', script.read_text())
        if os.name != 'nt':
            for tier in range(3):
                result = subprocess.run(['bash', 'scripts/check-shared.sh'],
                                        cwd=collection / f'homelab-tier-{tier}', capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_parent_directory_keeps_its_existing_case(self):
        parent = self.parent / 'KeepRootCase'
        self.generate('--prefix', 'HomeLab', '--root', str(parent), '--repo', 'shared')
        self.assertEqual({path.name for path in self.parent.iterdir()}, {'KeepRootCase'})
        self.assertTrue((parent / 'homelab-iac/homelab-shared/README.md').is_file())

    def test_refresh_reuses_lowercase_paths_and_preserves_owned_content_and_state(self):
        self.generate('--prefix', 'HomeLab')
        collection = self.parent / 'homelab-iac'
        repo = collection / 'homelab-tier-0'
        state = repo / '.terraform/state/proxmox-templates/terraform.tfstate'
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 7}\n')
        readme = repo / 'README.md'
        before = readme.read_bytes()
        self.generate('--prefix', 'HOMELAB', '--refresh')
        self.assertEqual(readme.read_bytes(), before)
        self.assertEqual(state.read_text(), '{"serial": 7}\n')
        self.assertEqual({path.name for path in self.parent.iterdir()}, {'homelab-iac'})
        manifest = json.loads((repo / '.generated-files.json').read_text())
        self.assertIn('README.md', manifest['owned'])

    def assert_legacy_case_is_rejected(self, legacy):
        legacy.mkdir(parents=True)
        marker = legacy / 'state-must-not-move'
        marker.write_text('preserved\n')
        result = subprocess.run(
            [sys.executable, str(UPSTREAM / 'scripts/tier-repos/generate.py'),
             '--root', str(self.parent), '--prefix', 'HomeLab', '--repo', 'shared', '--refresh'],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Existing mixed-case path', result.stderr)
        self.assertIn('no automatic directory/state migration', result.stderr)
        self.assertEqual(marker.read_text(), 'preserved\n')
        self.assertFalse(list(self.parent.rglob('.generated-files.json')))

    def test_legacy_mixed_case_collection_is_not_duplicated_or_renamed(self):
        self.assert_legacy_case_is_rejected(self.parent / 'HomeLab-iac')
        self.assertEqual({path.name for path in self.parent.iterdir()}, {'HomeLab-iac'})

    def test_legacy_unselected_sibling_stops_generation_before_any_write(self):
        collection = self.parent / 'homelab-iac'
        self.assert_legacy_case_is_rejected(collection / 'HomeLab-tier-0')
        self.assertEqual({path.name for path in collection.iterdir()}, {'HomeLab-tier-0'})


if __name__ == '__main__':
    unittest.main()
