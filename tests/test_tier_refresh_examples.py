"""Refresh reference examples without changing or disclosing operational inputs."""

import contextlib
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generated_files import RepositoryWriter
from refresh_review import print_refresh_review


class ExampleRefresh(TierRepositoryTestCase):
    def snapshot(self):
        return {path.relative_to(self.root): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def test_current_examples_replace_edits_and_flag_preserved_live_files(self):
        self.generate()
        examples = [self.root / relative for relative in (
            'verify-tier-0/ansible/group_vars/bootstrap.yml.example',
            'verify-tier-0/terraform/common.tfvars.example',
            'verify-tier-0/templates/proxmox.yml.example',
            'verify-tier-0/env.local.example',
            'verify-tier-0/ci/gitlab-templates.yml.example',
            'verify-tier-2/workloads/cluster-profiles.json.example',
            'verify-shared/ci/gitlab-secrets.yml.example',
        )]
        expected = {example: example.read_bytes() for example in examples}
        local = {example: (example.parent / '.env.local' if example.name == 'env.local.example'
                           else example.with_suffix('')) for example in examples}
        private = b'LOCAL_ONLY_VALUE=must-not-appear-in-refresh-output\n'
        for example in examples:
            example.write_bytes(b'# Old local example\n')
            local[example].write_bytes(private)
        # Upgrade both formerly owned references and examples missing from old provenance.
        manifest_path = self.root / 'verify-tier-0/.generated-files.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files'].pop('ci/gitlab-templates.yml.example')
        manifest['owned'].append('ci/gitlab-templates.yml.example')
        manifest['files'].pop('terraform/common.tfvars.example')
        manifest_path.write_text(json.dumps(manifest))
        result = self.generate('--refresh', '--code-conflicts', 'preserve', '--color', 'always')
        review = result.stdout.split('\nRefresh review\n')[1]
        self.assertIn('Examples: 7 refreshed; 7 local configurations to compare.', review)
        for example in examples:
            self.assertEqual(example.read_bytes(), expected[example])
            self.assertEqual(local[example].read_bytes(), private)
            self.assertIn(f'\033[33mYELLOW {local[example]}', review)
            self.assertIn(f'Current example: {example}', review)
        self.assertNotIn(private.decode().strip(), result.stdout)
        manifest = json.loads(manifest_path.read_text())
        self.assertNotIn('ci/gitlab-templates.yml.example', manifest['owned'])
        self.assertEqual(manifest['files']['ci/gitlab-templates.yml.example'],
                         hashlib.sha256(expected[examples[4]]).hexdigest())
        self.assertFalse((self.root / '.refresh-review').exists())
        self.assertFalse((self.root / '.refresh-backups').exists())
        second = self.generate('--refresh', '--color', 'never').stdout.split('\nRefresh review\n')[1]
        self.assertNotIn('Examples:', second)
        for path in local.values():
            self.assertNotIn(str(path), second)

    def test_dry_run_is_write_free_and_restored_examples_point_to_live_inputs(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        example = repo / 'ansible/group_vars/syslog.yml.example'
        expected = example.read_bytes()
        example.unlink()
        live = example.with_suffix('')
        live.write_text('site-owned configuration\n')
        before = self.snapshot()
        result = self.generate('--repo', 'tier-0', '--refresh', '--dry-run', '--color', 'never')
        self.assertEqual(self.snapshot(), before)
        self.assertIn(f'YELLOW {live} [example would be refreshed; compare after refresh]', result.stdout)
        self.assertIn(f'Planned example: {example}', result.stdout)
        self.assertIn(f'Source template: {UPSTREAM / "tier-0/ansible/group_vars/syslog.yml.example"}', result.stdout)
        self.assertNotIn('\033[', result.stdout)
        result = self.generate('--repo', 'tier-0', '--refresh')
        self.assertEqual(example.read_bytes(), expected)
        self.assertEqual(live.read_text(), 'site-owned configuration\n')
        self.assertIn(f'Current example: {example}', result.stdout)

    def test_unselected_examples_and_custom_examples_remain_untouched(self):
        self.generate()
        selected = self.root / 'verify-tier-0/env.local.example'
        unselected = self.root / 'verify-tier-2/env.local.example'
        custom = selected.parent / 'project-local.yml.example'
        expected = selected.read_bytes()
        for path in (selected, unselected, custom):
            path.write_bytes(b'local reference\n')
        result = self.generate('--repo', 'tier-0', '--refresh')
        self.assertEqual(selected.read_bytes(), expected)
        self.assertEqual(unselected.read_bytes(), b'local reference\n')
        self.assertEqual(custom.read_bytes(), b'local reference\n')
        self.assertNotIn(str(unselected), result.stdout)
        self.assertNotIn(str(custom), result.stdout)
        self.assertIn('Examples: 1 refreshed; 0 local configurations to compare.', result.stdout)

    def test_example_refresh_ignores_code_conflict_prompts_but_generation_preserves_edits(self):
        for policy in ('replace', 'preserve', 'ask'):
            with self.subTest(policy=policy), contextlib.redirect_stdout(io.StringIO()):
                repo = self.root / policy
                example = repo / 'config.yml.example'
                writer = RepositoryWriter(repo)
                writer.write('config.yml.example', 'original\n', owned=True)
                writer.finish()
                manifest = json.loads((repo / '.generated-files.json').read_text())
                self.assertNotIn('config.yml.example', manifest['owned'])
                example.write_text('local edit\n')
                writer = RepositoryWriter(repo)
                writer.write('config.yml.example', 'current reference\n')
                writer.finish()
                self.assertEqual(example.read_text(), 'local edit\n')
                writer = RepositoryWriter(repo, refresh=True, code_conflicts=policy)
                with patch('builtins.input', side_effect=AssertionError('Examples must not prompt')):
                    writer.write('config.yml.example', 'current reference\n', owned=True, automation=True)
                writer.finish()
                self.assertEqual(example.read_text(), 'current reference\n')

    def test_prose_comparisons_are_quiet_and_references_need_no_live_counterpart(self):
        repo = self.root / 'references'
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(repo)
            for relative in ('README.md.example', 'unused.yml.example'):
                writer.write(relative, 'old reference\n')
            writer.finish()
            (repo / 'README.md').write_text('owned prose\n')
            writer = RepositoryWriter(repo, refresh=True)
            for relative in ('README.md.example', 'unused.yml.example'):
                writer.write(relative, 'current reference\n')
            writer.finish()
        report = io.StringIO()
        print_refresh_review([writer.review], self.root, stream=report)
        self.assertIn('Examples: 2 refreshed; 0 local configurations to compare.', report.getvalue())
        self.assertNotIn('YELLOW ' + str(repo / 'README.md'), report.getvalue())
        self.assertEqual((repo / 'README.md').read_text(), 'owned prose\n')
        self.assertFalse((repo / 'unused.yml').exists())

    @unittest.skipIf(os.name == 'nt', 'Requires unprivileged symlinks')
    def test_reference_refresh_cannot_overwrite_external_content_through_symlinks(self):
        repo = self.root / 'symlink-check'
        repo.mkdir(parents=True)
        outside = self.root / 'external.yml'
        outside.write_text('retain external content\n')
        (repo / 'config.yml.example').symlink_to(outside)
        writer = RepositoryWriter(repo, refresh=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            writer.write('config.yml.example', 'new reference\n')
        self.assertEqual(outside.read_text(), 'retain external content\n')


if __name__ == '__main__':
    unittest.main()
