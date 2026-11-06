"""Native wrappers accept a symlinked collection without changing state ownership."""

import json
import os
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipIf(os.name == 'nt', 'Requires Linux/WSL directory symlinks and Bash')
class WrapperPaths(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.generate('--prefix', 'HomeLab')
        self.collection = self.parent / 'homelab-iac'
        self.alias = self.parent / 'linked collection'
        self.alias.symlink_to(self.collection, target_is_directory=True)
        commands = self.parent / 'commands'
        commands.mkdir()
        self.calls = self.parent / 'terraform-calls.jsonl'
        terraform = commands / 'terraform'
        terraform.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['CALLS'], 'a') as stream:
    stream.write(json.dumps({'args': sys.argv[1:], 'data': os.environ['TF_DATA_DIR']}) + '\\n')
for argument in sys.argv:
    if argument.startswith('-out='):
        pathlib.Path(argument[5:]).write_text('disposable plan')
''')
        terraform.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(self.calls), CDPATH='')
        for name in ('DEPLOYMENT_REPO_DIR', 'TF_DATA_DIR', 'TEMPLATE_STATE_PATH',
                     'TEMPLATE_CATALOG_FILE', 'PROXMOX_VE_INSECURE', 'PM_VE_INSECURE'):
            self.env.pop(name, None)

    def run_from(self, directory, script, action):
        # Enter with Bash so PWD retains the logical alias, as in an interactive shell.
        return subprocess.run(['bash', '-c', 'cd -- "$1" && bash "$2" "$3"',
                               'wrapper-path-test', str(directory), script, action],
                              cwd=self.parent, env=self.env, capture_output=True, text=True)

    def assert_owned_terraform_context(self, repo, setup):
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertTrue(calls)
        for call in calls:
            self.assertEqual(call['data'], str(repo / f'.terraform/data/{setup}'))
        init = next(call for call in calls if 'init' in call['args'])
        self.assertIn(f'-backend-config=path={repo}/.terraform/state/{setup}/terraform.tfstate', init['args'])
        self.calls.unlink()

    def test_templates_accept_logical_parent_and_keep_physical_state_paths(self):
        script = 'scripts/proxmox-templates.sh'
        alias = self.alias / 'homelab-tier-0'
        repo = self.collection / 'homelab-tier-0'
        for action in ('init', 'plan'):
            result = self.run_from(alias, script, action)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((repo / 'templates/proxmox.yml').is_file())
        self.assert_owned_terraform_context(repo, 'proxmox-templates')
        plan = repo / '.terraform/plans/proxmox-templates.tfplan'
        before = plan.read_bytes()
        result = self.run_from(self.alias / 'homelab-tier-1', str(repo / script), 'plan')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Tier 0 repository root', result.stderr)
        self.assertEqual(plan.read_bytes(), before)
        self.assertFalse(self.calls.exists())

    def test_cluster_wrappers_accept_logical_parent_for_each_tier(self):
        for tier in range(3):
            with self.subTest(tier=tier):
                alias = self.alias / f'homelab-tier-{tier}'
                repo = self.collection / f'homelab-tier-{tier}'
                for action in ('init', 'plan'):
                    result = self.run_from(alias, 'scripts/kubernetes-cluster.sh', action)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_owned_terraform_context(repo, 'talos')
                plan = repo / '.terraform/plans/talos.tfplan'
                before = plan.read_bytes()
                self.env['DEPLOYMENT_REPO_DIR'] = str(repo)
                result = self.run_from(
                    self.alias, str(self.collection / 'homelab-shared/scripts/kubernetes-cluster.sh'), 'plan'
                )
                self.env.pop('DEPLOYMENT_REPO_DIR')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('owning tier repository root', result.stderr)
                self.assertEqual(plan.read_bytes(), before)
                self.assertFalse(self.calls.exists())


if __name__ == '__main__':
    unittest.main()
