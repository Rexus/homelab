"""Verified provider defaults and entry-point guards, without a live API or credentials."""

import os
import re
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ProviderTls(TierRepositoryTestCase):
    def test_source_and_generated_provider_roots_explicitly_verify_tls(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            providers = [path for tier in range(3) for path in
                         (collection / f'{prefix}tier-{tier}/terraform/deployments').glob('*/providers.tf')]
            self.assertGreaterEqual(len(providers), 16)
            for path in providers:
                if path.parent.name == 'ci-auth':
                    self.assertRegex(path.read_text(), r'skip_tls_verify\s*=\s*false')
                    self.assertNotRegex(path.read_text(), r'skip_tls_verify\s*=\s*true')
                    continue
                flags = re.findall(r'^\s*insecure\s*=\s*(\S+)', path.read_text(), re.MULTILINE)
                self.assertEqual(flags, ['false'], str(path))

    def test_manual_acceptance_is_separate_from_supplied_mechanisms(self):
        self.generate()
        manual = (UPSTREAM / '.ai/operational-verification.md').read_text()
        for group, count in (('TLS', 4), ('LOG', 5), ('TRUST', 5)):
            for number in range(1, count + 1):
                self.assertIn(f'**{group}-{number}:', manual)
        main = (UPSTREAM / '.ai/operator-walkthrough.md').read_text()
        self.assertIn('## Implemented priority mechanisms', main)
        self.assertIn('## Remaining implementation before an end-to-end installation', main)
        self.assertIn('## Manual operational verification', main)
        self.assertIn('- [x] **P1: Logging integration - sources (selected Linux path).', main)
        self.assertNotRegex(manual, r'(?m)^- \[x\]')
        self.assertIn('transport', manual)
        for repo in self.root.iterdir():
            self.assertFalse((repo / '.ai/operational-verification.md').exists())

    @unittest.skipIf(os.name == 'nt', 'Requires Linux/WSL Bash')
    def test_provisioning_rejects_environment_bypasses_before_terraform(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for stem in ('inventory/hosts', 'group_vars/all', 'group_vars/foundation'):
            shutil.copyfile(repo / f'ansible/{stem}.yml.example', repo / f'ansible/{stem}.yml')
        shutil.copyfile(repo / 'terraform/deployments/foundation/terraform.tfvars.example',
                        repo / 'terraform/deployments/foundation/terraform.tfvars')
        commands = self.parent / 'commands'
        commands.mkdir()
        log = self.parent / 'terraform-calls.jsonl'
        terraform = commands / 'terraform'
        terraform.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['TEST_TLS_LOG'], 'a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
for argument in sys.argv[1:]:
    if argument.startswith('-out='):
        pathlib.Path(argument[5:]).write_text('disposable saved plan')
""")
        terraform.chmod(0o755)
        ansible = commands / 'ansible-playbook'
        ansible.write_text('#!/bin/sh\nexit 0\n')
        ansible.chmod(0o755)
        environment = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", TEST_TLS_LOG=str(log),
                           PROXMOX_API_URL='https://disposable.invalid:8006/',
                           PROXMOX_API_TOKEN_ID='test@pve!disposable', PROXMOX_API_TOKEN_SECRET='not-a-real-token')
        for name in ('DEPLOYMENT_REPO_DIR', 'SHARED_REPO_DIR', 'PROXMOX_VE_INSECURE', 'PM_VE_INSECURE',
                     'TEMPLATE_STATE_PATH', 'TEMPLATE_CATALOG_FILE'):
            environment.pop(name, None)

        def run(script, *arguments, overrides=None):
            return subprocess.run(['bash', f'scripts/{script}', *arguments], cwd=repo,
                                  env=dict(environment, **(overrides or {})), capture_output=True, text=True)

        for script in ('proxmox-templates.sh', 'kubernetes-cluster.sh'):
            result = run(script, 'init', overrides={'PROXMOX_VE_INSECURE': 'true'})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        callers = (
            ('deploy.sh', ('foundation', '--plan-only'), None),
            ('kubernetes-cluster.sh', ('plan',), '.terraform/plans/talos.tfplan'),
            ('proxmox-templates.sh', ('plan',), '.terraform/plans/proxmox-templates.tfplan'),
        )
        for script, arguments, saved_plan in callers:
            for option in ('PROXMOX_VE_INSECURE', 'PM_VE_INSECURE'):
                for value in ('true', 'TRUE', '1', 'yes', 'unexpected'):
                    if saved_plan:
                        target = repo / saved_plan
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text('old plan')
                    log.unlink(missing_ok=True)
                    result = run(script, *arguments, overrides={option: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f'Refusing Proxmox TLS bypass: unset {option}', result.stderr)
                    self.assertFalse(log.exists(), result.stdout + result.stderr)
                    if saved_plan:
                        self.assertFalse((repo / saved_plan).exists())
            log.unlink(missing_ok=True)
            result = run(script, *arguments, overrides={'PROXMOX_VE_INSECURE': 'false', 'PM_VE_INSECURE': '0'})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(log.exists())
        local_env = repo / '.env.local'
        local_env.write_text('PROXMOX_VE_INSECURE=true\n')
        log.unlink(missing_ok=True)
        result = run('deploy.sh', 'foundation', '--plan-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing Proxmox TLS bypass', result.stderr)
        self.assertFalse(log.exists())
        result = run('deploy.sh', 'foundation', '--ansible-only')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(log.exists())
