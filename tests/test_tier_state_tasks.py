"""Run generic state instructions against disposable native Terraform backends."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from tier_repo_test_support import UPSTREAM


TERRAFORM = shutil.which('terraform')


@unittest.skipUnless(os.name != 'nt' and TERRAFORM and shutil.which('bash'),
                     'Requires Linux Bash and Terraform')
class StateTasks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='state tasks with spaces ')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        guide = UPSTREAM / 'docs/05-operations/01-hosting/terraform-state.md'
        self.blocks = re.findall(r'```bash\n(.*?)```', guide.read_text(), re.S)
        self.assertEqual(len(self.blocks), 6)
        for block in self.blocks:
            subprocess.run(['bash', '-n'], input=block, text=True, capture_output=True, check=True)

    def context(self, repository, setup, state_key):
        repo = self.directory / repository
        root = repo / 'terraform/deployments' / setup
        root.mkdir(parents=True)
        (root / 'main.tf').write_text('''terraform {
  backend "local" {}
}
resource "terraform_data" "item" {
  for_each = toset(["primary", "retained"])
  input = each.key
}
''')
        state = repo / '.terraform/state' / state_key / 'terraform.tfstate'
        state.parent.mkdir(parents=True)
        data = repo / '.terraform/data' / state_key
        data.mkdir(parents=True)
        peer = repo / '.terraform/state/unrelated/terraform.tfstate'
        peer.parent.mkdir(parents=True)
        peer.write_text('{"fixture": "unrelated deployment"}\n')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(('TF_', 'TERRAFORM_'))}
        environment.update(TF_DATA_DIR=str(data), TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1')
        for arguments in (['init', '-input=false', '-reconfigure', f'-backend-config=path={state}'],
                          ['apply', '-input=false', '-auto-approve']):
            subprocess.run([TERRAFORM, f'-chdir={root}', *arguments], env=environment,
                           text=True, capture_output=True, check=True, timeout=30)
        return repo, root, state, data, peer, environment

    def run_blocks(self, context, indexes, replies):
        repo, _, _, _, _, environment = context
        return subprocess.run(['bash', '-euo', 'pipefail', '-c', '\n'.join(self.blocks[i] for i in indexes)],
                              cwd=repo, env=environment, input='\n'.join(replies) + '\n',
                              text=True, capture_output=True, timeout=40)

    def test_original_context_selection_across_repositories_and_layouts(self):
        cases = [('alpha-tier-0', 'infrastructure-runner', 'infrastructure-runner/stage'),
                 ('beta-tier-1', 'intake', 'intake/prod'),
                 ('gamma-tier-2', 'lab', 'lab/test'),
                 ('delta-tier-0', 'templates', 'proxmox-templates'),
                 ('omega-tier-1', 'kubernetes', 'talos'),
                 ('another-repository', 'custom-root', 'recorded-custom-state')]
        for repository, setup, state_key in cases:
            with self.subTest(repository=repository, setup=setup):
                context = self.context(repository, setup, state_key)
                repo, root, state, data, peer, _ = context
                before, unrelated = state.read_bytes(), peer.read_bytes()
                if setup == 'custom-root':
                    shutil.rmtree(data)
                result = self.run_blocks(context, [1, 2],
                                         [str(root.relative_to(repo)), str(state.relative_to(repo)),
                                          str(data.relative_to(repo))])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('terraform_data.item["primary"]', result.stdout)
                self.assertEqual(state.read_bytes(), before)
                self.assertEqual(peer.read_bytes(), unrelated)
                backups = list((repo / '.local-archive').glob('*/before.tfstate'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(json.loads(backups[0].read_text()), json.loads(state.read_text()))

    def test_exact_removal_and_retirement_preserve_other_bindings_and_state(self):
        context = self.context('owner-repository', 'selected-service', 'selected-service/prod')
        repo, root, state, data, peer, environment = context
        unrelated = peer.read_bytes()
        selected = 'terraform_data.item["primary"]'
        inputs = [str(root), str(state), str(data), selected]
        result = self.run_blocks(context, [1, 2, 3, 4], inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        listing = subprocess.check_output([TERRAFORM, f'-chdir={root}', 'state', 'list'],
                                          env=environment, text=True)
        self.assertNotIn(selected, listing)
        self.assertIn('terraform_data.item["retained"]', listing)
        self.assertEqual(peer.read_bytes(), unrelated)
        # Retire the remaining disposable Terraform-only object before archiving this one state.
        subprocess.run([TERRAFORM, f'-chdir={root}', 'destroy', '-auto-approve', '-input=false'],
                       env=environment, capture_output=True, text=True, check=True, timeout=30)
        retired = state.read_bytes()
        result = self.run_blocks(context, [1, 2, 5],
                                 [str(root), str(state), str(data), str(state)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(state.exists())
        self.assertTrue(data.is_dir())
        self.assertEqual(peer.read_bytes(), unrelated)
        archives = list((repo / '.local-archive').glob('*/terraform.tfstate'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].read_bytes(), retired)
