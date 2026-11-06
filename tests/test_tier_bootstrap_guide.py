"""First-template -> bootstrap-host -> IaC path, without a circular bootstrap owner."""

import re
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class BootstrapGuide(TierRepositoryTestCase):
    def test_source_and_generated_foundation_have_an_explicit_second_step(self):
        self.generate()
        for docs in (UPSTREAM / 'docs', self.root / 'verify-architecture/docs/auto-docs'):
            foundation = (docs / 'deployment/foundation/README.md').read_text()
            steps = ('## Step 1: Create the first Linux template manually',
                     '## Step 2: Prepare the bootstrap execution host',
                     '## Step 3: Publish and test VM templates')
            self.assertEqual([foundation.index(step) for step in steps],
                             sorted(foundation.index(step) for step in steps))
            self.assertIn('No generated repository,', foundation)
            self.assertIn('Terraform API token or running GitLab is needed', foundation)
            self.assertIn('proxmox/bootstrap.md', foundation)
            self.assertIn('does not enroll the\nbootstrap VM itself into Terraform', foundation)
            self.assertIn('step-2-protect-provisioning-access-and-state', foundation)
            path = (docs / 'paths/tier-0/README.md').read_text()
            self.assertIn('bootstrap execution host', path)
            handover = (docs / 'deployment/stage-9-development/procedures/handover.md').read_text()
            self.assertIn('foundation/proxmox/bootstrap.md', handover)
            self.assertIn('`bootstrap-1`', handover)
            self.assertIn('`iac-1`', handover)
        readme = (self.root / 'verify-tier-0/README.md').read_text()
        self.assertLess(readme.index('bootstrap execution host'), readme.index('bash scripts/proxmox-templates.sh init'))

    def test_manual_profile_is_not_an_invented_terraform_or_inventory_resource(self):
        guide = (UPSTREAM / 'docs/deployment/foundation/proxmox/bootstrap.md').read_text()
        for term in ('**Manual:**', '`bootstrap-1`', 'management', 'example VLAN 10',
                     'Corosync or Ceph', 'not an IaC', 'outside', 'not a CI runner',
                     'one writer per root', 'independent recovery', 'not another name'):
            self.assertIn(term, guide)
        diagram = re.search(r'```mermaid\n(.*?)```', guide, re.DOTALL)[1]
        self.assertEqual(diagram.count('subgraph T0['), 1)
        self.assertLess(diagram.index('subgraph PVE['), diagram.index('subgraph VM['))
        self.assertIn('bootstrap-1 / Linux VM', diagram)
        self.assertIn('Admin -->|SSH to bootstrap-1| T0', diagram)
        for tier in range(3):
            root = UPSTREAM / f'tier-{tier}'
            paths = list((root / 'terraform').rglob('*.tfvars.example'))
            paths += list((root / 'ansible/inventory').glob('*.example'))
            for path in paths:
                self.assertNotIn('bootstrap-1', path.read_text(), str(path))

    def test_tools_artifacts_caller_trust_and_original_state_are_not_skipped(self):
        guide = (UPSTREAM / 'docs/deployment/foundation/proxmox/bootstrap.md').read_text()
        for term in ('local-setup.md#automation-vm-example', '--prefix HomeLab',
                     '/srv/tier0/artifacts', 'unpacked', 'original state',
                     'proxmox-tls.md#step-1-trust-the-bootstrap-ca',
                     'browser workstation is not trust installed here', '--env-file .env.local',
                     'manual Linux template', 'not just tracked', 'never push ignored secrets', 'not boot'):
            self.assertIn(term, guide)
        trust = guide.index('proxmox-tls.md#step-1-trust-the-bootstrap-ca')
        token = guide.index('api-access.md#create-platform-automation-access')
        init = guide.index('bash scripts/proxmox-templates.sh init')
        self.assertLess(trust, token)
        self.assertLess(token, init)
        tooling = (UPSTREAM / 'docs/development/local-setup.md').read_text()
        for package in ('git bash python3', 'python3-pyyaml', 'ca-certificates', 'openssl', 'xz unzip'):
            self.assertIn(package, tooling)

    @unittest.skipUnless(shutil.which('bash'), 'Requires Bash')
    def test_manual_command_blocks_parse_without_executing_them(self):
        for relative in ('deployment/foundation/proxmox/bootstrap.md', 'development/local-setup.md'):
            text = (UPSTREAM / 'docs' / relative).read_text()
            for block in re.findall(r'```bash\n(.*?)```', text, re.DOTALL):
                result = subprocess.run(['bash', '-n'], input=block, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
