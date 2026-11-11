"""Selected deployment inputs reach controller checks and generated CI handoffs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ExecutionContracts(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                         'Requires native Ansible; missing selection must stop before any guest task')
    def test_consumer_recipe_parses_without_inputs_but_refuses_an_unselected_group(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0', '--repo', 'tier-1', '--repo', 'tier-2')
        inventory = self.root / 'syntax-inventory.yml'
        inventory.write_text('all: {children: {selected: {hosts: {never-contact-this-host: {}}}}}\n')
        for root, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            for tier in ('tier-0', 'tier-1', 'tier-2'):
                repo = root / f'{prefix}{tier}'
                env = dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg'))
                env.pop('ANSIBLE_ROLES_PATH', None)
                recipe = repo / 'ansible/playbooks/deployment/software-consumer.yml'
                result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', str(inventory),
                    str(recipe)], cwd=repo, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                shared = root / f'{prefix}shared'
            env['ANSIBLE_ROLES_PATH'] = str(shared / 'ansible/roles')
            for selection in ({}, {'software_consumer_group': ''}, {'software_consumer_group': 'all'}):
                result = subprocess.run(['ansible-playbook', '-i', str(inventory),
                    str(shared / 'ansible/playbooks/software-consumer.yml'), '-e', json.dumps(selection)],
                    env=env, capture_output=True, text=True, timeout=30)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn('Select one populated software_consumer_group', output)
                self.assertNotIn('TASK [Wait for CloudInit SSH', output)

    def test_generated_ci_retains_both_reviewed_plan_and_its_required_context(self):
        self.generate('--repo', 'tier-0')
        for repo in (UPSTREAM / 'tier-0', self.root / 'verify-tier-0'):
            recipe = yaml.safe_load((repo / 'ci/gitlab-templates.yml.example').read_text())
            artifacts = recipe['template-plan']['artifacts']
            self.assertEqual(artifacts['access'], 'maintainer')
            paths = artifacts['paths']
            self.assertIn('.terraform/plans/proxmox-templates.tfplan', paths)
            self.assertIn('.terraform/plans/proxmox-templates.tfplan.context', paths)
            self.assertNotIn('untracked', artifacts)
            self.assertEqual(recipe['template-publish']['needs'], ['template-plan'])

    def test_immutable_builder_reuses_the_tier_owned_dependency_catalog(self):
        self.generate('--repo', 'tier-0')
        for repo in (UPSTREAM / 'tier-0', self.root / 'verify-tier-0'):
            play = yaml.safe_load((repo / 'ansible/playbooks/deployment/immutable-template.yml').read_text())[0]
            self.assertEqual(play['ansible.builtin.import_playbook'], '../control-node.yml')
            self.assertEqual(play['vars'], {'control_node_setup': 'immutable-template',
                                           'control_node_require_terraform': False})

    @unittest.skipIf(os.name == 'nt', 'Requires native Bash; every deployment command is intercepted')
    def test_precheck_and_recipe_share_ordered_inputs_and_honor_inventory_and_env_file(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0')
        repo = self.root / 'verify-tier-0'
        commands = self.root / 'commands'
        commands.mkdir()
        log = self.root / 'calls.jsonl'
        executable = commands / 'ansible-playbook'
        executable.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['EXECUTION_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps(dict(args=sys.argv[1:],
        marker=os.getenv('EXECUTION_TEST_MARKER'),
        mode=os.getenv('CONTROL_NODE_COLLECTIONS_MODE'))) + '\\n')
if os.getenv('EXECUTION_TEST_DENY_PRECHECK') == '1' and any(
        arg.endswith('/control-node.yml') for arg in sys.argv):
    sys.exit(17)
''')
        executable.chmod(0o755)
        terraform = commands / 'terraform'
        terraform.write_text('#!/bin/sh\necho unexpected-terraform >&2\nexit 99\n')
        terraform.chmod(0o755)
        environment = dict(os.environ, PATH=f'{commands}:{os.environ["PATH"]}',
                           EXECUTION_TEST_LOG=str(log))
        for name in ('DEPLOYMENT_REPO_DIR', 'SHARED_REPO_DIR'):
            environment.pop(name, None)
        initialized = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'vault',
                                      '--env', 'review'], cwd=repo, env=environment,
                                     capture_output=True, text=True, timeout=30)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        custom = repo / 'custom inputs'
        custom.mkdir()
        inventory = custom / 'inventory.yml'
        inventory.write_text('all: {hosts: {selected-vault: {}}}\n')
        overrides = custom / 'overrides.yml'
        overrides.write_text('control_node_setup: deliberately-overridden\n')
        env_file = custom / 'execution.env'
        env_file.write_text('EXECUTION_TEST_MARKER=selected-environment\n'
                            'CONTROL_NODE_COLLECTIONS_MODE=check\n')
        args = ['bash', 'scripts/deploy.sh', 'vault', '--ansible-only', '--env', 'review',
                '--inventory', str(inventory.relative_to(repo)), '--ansible-vars', str(overrides),
                '--env-file', str(env_file.relative_to(repo))]
        result = subprocess.run(args, cwd=repo, env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(calls), 2, calls)
        expected = [str(repo / 'ansible/group_vars' / (stem + '.yml'))
                    for stem in ('all', 'vault', 'all.review', 'vault.review')] + [str(overrides)]
        for call in calls:
            self.assertEqual([arg[1:] for arg in call['args'] if arg.startswith('@')], expected)
            self.assertEqual(call['marker'], 'selected-environment')
            self.assertEqual(call['mode'], 'check')
        precheck, recipe = [call['args'] for call in calls]
        self.assertEqual(precheck[:2], ['-i', 'localhost,'])
        self.assertEqual(precheck[-4:], ['-e', 'control_node_setup=vault',
                                         '-e', 'control_node_require_terraform=false'])
        self.assertEqual(recipe[:2], ['-i', str(inventory)])
        log.unlink()
        failed = subprocess.run(args, cwd=repo,
            env=dict(environment, EXECUTION_TEST_DENY_PRECHECK='1'), capture_output=True,
            text=True, timeout=30)
        self.assertEqual(failed.returncode, 17, failed.stdout + failed.stderr)
        self.assertEqual(len(log.read_text().splitlines()), 1, 'Failed prechecks must stop deployment')
