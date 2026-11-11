"""Fresh guest configuration stays on the controller and preserves original state."""

from copy import deepcopy
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ManagedGuestSetup(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_new_generated_controller_recipes_and_role_tasks_pass_native_syntax(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        environment = dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg'))
        for name in ('logging-storage', 'logging-verify', 'openxpki-certificates', 'openxpki-token',
                     'infrastructure-handover', 'software-consumer', 'vault-configure'):
            result = subprocess.run(['ansible-playbook', '--syntax-check', '-i',
                str(repo / 'ansible/inventory/hosts.yml.example'), '-e', 'software_consumer_group=foundation_logging',
                str(repo / f'ansible/playbooks/deployment/{name}.yml')], cwd=repo,
                env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, name + result.stdout + result.stderr)
        roles = [repo / 'ansible/roles/syslog_ng/tasks/firewall-bootstrap.yml',
                 repo / 'ansible/roles/openxpki/tasks/certificates.yml',
                 repo / 'ansible/roles/openxpki/tasks/token.yml',
                 repo / 'ansible/roles/infrastructure_runner/tasks/deployment-inputs.yml',
                 repo / 'ansible/roles/infrastructure_runner/tasks/handover.yml']
        roles += list((repo / 'ansible/roles/vault/tasks').glob('*.yml'))
        roles += [repo / 'ansible/roles/control_applications/tasks/vault-api.yml',
                  repo / 'ansible/roles/control_applications/tasks/vault-seal.yml']
        roles += list((self.root / 'verify-shared/ansible/roles/baseline/tasks').glob('*.yml'))
        check = self.parent / 'native-syntax.yml'
        check.write_text(yaml.safe_dump([dict(hosts='localhost', gather_facts=False, tasks=[
            {'ansible.builtin.import_tasks': str(path)} for path in roles])], sort_keys=False))
        result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', 'localhost,', str(check)],
                                cwd=repo, env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_syslog_storage_and_remote_verification_are_generated(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        storage = yaml.safe_load((repo / 'ansible/playbooks/deployment/logging-storage.yml').read_text())
        self.assertEqual(storage[0]['vars']['guest_ready_group'], 'foundation_logging')
        self.assertEqual(storage[1]['tasks'][0]['ansible.builtin.include_role'],
                         {'name': 'syslog_ng', 'tasks_from': 'storage'})
        self.assertTrue((repo / 'ansible/playbooks/deployment/logging-verify.yml').is_file())
        guide = (self.root / 'verify-architecture/docs/auto-docs/03-deployment/stage-2-logging/README.md').read_text()
        self.assertIn('--ansible-only --playbook deployment/logging-storage.yml', guide)
        self.assertNotRegex(guide, r'(?m)^\s*ssh\s')

    def test_normal_stage_guides_do_not_require_interactive_guest_ssh(self):
        stages = (UPSTREAM / 'docs/03-deployment').glob('stage-*')
        for page in (page for stage in stages for page in stage.rglob('*.md')):
            for block in re.findall(r'```bash\n(.*?)```', page.read_text(), re.S):
                self.assertNotRegex(block, r'(?m)^\s*(?:ssh|scp|sftp)\s', str(page))
        cluster = UPSTREAM / 'docs/03-deployment/stage-4-kubernetes/step-1b-existing-cluster.md'
        self.assertIn('existing owner manages its nodes through IaC', cluster.read_text())
        self.assertNotIn('In the Proxmox UI, make', cluster.read_text())

    def test_generated_connection_gate_and_custodian_recipes_resolve(self):
        self.generate()
        ready = self.root / 'verify-shared/ansible/playbooks/guest-ready.yml'
        self.assertIn('ansible.builtin.wait_for_connection', ready.read_text())
        for name in ('openxpki-certificates', 'openxpki-token', 'infrastructure-handover'):
            self.assertTrue((self.root / f'verify-tier-0/ansible/playbooks/deployment/{name}.yml').is_file())
        handover = (self.root / 'verify-tier-0/ansible/roles/infrastructure_runner/tasks/handover.yml').read_text()
        for guard in ('checksum_algorithm: sha256', 'verify_host: true', 'delete: false',
                      '--exclude=.env*', '--exclude=**/.terraform/plans/***', 'Fu=rwX', 'no_log: true'):
            self.assertIn(guard, handover)


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
class ManagedGuestGuards(unittest.TestCase):
    @unittest.skipUnless(shutil.which('rsync'), 'Requires native rsync')
    def test_native_handover_copy_preserves_state_and_execution_without_bootstrap_environment(self):
        import pwd
        import grp
        role = UPSTREAM / 'tier-0/ansible/roles/infrastructure_runner/tasks/handover.yml'
        tasks = yaml.safe_load(role.read_text())
        copy_task = deepcopy(next(task for task in tasks if 'ansible.posix.synchronize' in task))
        # Only fixture ownership/transport differs: the production runner account is not created here.
        options = copy_task['ansible.posix.synchronize']['rsync_opts']
        options[:] = [f'--chown={pwd.getpwuid(os.getuid()).pw_name}:{grp.getgrgid(os.getgid()).gr_name}'
                      if option.startswith('--chown=') else option for option in options]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, target = base / 'original', base / 'runner'
            state = Path('example-tier-0/.terraform/state/syslog/prod/terraform.tfstate')
            (source / state).parent.mkdir(parents=True)
            (source / state).write_text('{"lineage":"original","serial":7}')
            (source / 'example-tier-0/.env.local').write_text('FAKE_BOOTSTRAP_INPUT=fixture')
            for cache in ('data/providers', 'plans'):
                path = source / f'example-tier-0/.terraform/{cache}/must-not-transfer'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('disposable fixture')
            executable = source / 'example-tier-0/deploy.sh'
            executable.write_text('#!/bin/sh\nexit 0\n')
            executable.chmod(0o700)
            target.mkdir()
            (target / 'retained-record').write_text('keep')
            play = base / 'copy.yml'
            select_states = next(task for task in tasks if task['name'] ==
                                 'Retain only authoritative state files rather than disposable backend metadata')
            discovered = dict(files=[dict(path=str(source / state)),
                dict(path=str(source / 'example-tier-0/.terraform/data/prod/terraform.tfstate'))])
            play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                vars=dict(handover_source_root=str(source), infrastructure_runner_workspace=str(target),
                          handover_states=discovered),
                tasks=[select_states, {'ansible.builtin.assert': {'that': ['handover_state_files | length == 1']}},
                       copy_task])], sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((target / state).read_bytes(), (source / state).read_bytes())
            self.assertFalse((target / 'example-tier-0/.env.local').exists())
            self.assertFalse((target / 'example-tier-0/.terraform/plans').exists())
            self.assertFalse((target / 'example-tier-0/.terraform/data').exists())
            self.assertEqual((target / 'example-tier-0/deploy.sh').stat().st_mode & 0o777, 0o700)
            self.assertEqual((target / state).stat().st_mode & 0o777, 0o600)
            self.assertEqual((target / 'retained-record').read_text(), 'keep')

    def test_real_package_token_and_handover_assertions_reject_unsafe_inputs(self):
        baseline = UPSTREAM / 'shared/ansible/roles/baseline/tasks/package_sources.yml'
        repo_assertion = yaml.safe_load(baseline.read_text())[0]
        token = yaml.safe_load((UPSTREAM / 'tier-0/ansible/roles/openxpki/tasks/token.yml').read_text())
        token_assertion = next(task for task in token if 'ansible.builtin.assert' in task)
        handover = yaml.safe_load((UPSTREAM / 'tier-0/ansible/roles/infrastructure_runner/tasks/handover.yml').read_text())
        state_assertion = next(task for task in handover if task['name'] == 'Refuse replacement of different destination state')
        valid_repo = dict(ansible_os_family='RedHat', baseline_rpm_repositories=[dict(
            name='approved', baseurl='https://mirror.example.com/el10',
            gpgkey='https://mirror.example.com/key.asc', fingerprint='A' * 40)])
        cases = []
        for name, field, value in [('http source', 'baseurl', 'http://mirror.example.com/el10'),
                                    ('http key', 'gpgkey', 'http://mirror.example.com/key.asc'),
                                    ('unverified key', 'fingerprint', 'REPLACE_ME')]:
            variables = deepcopy(valid_repo)
            variables['baseline_rpm_repositories'][0][field] = value
            cases.append((name, [repo_assertion], variables, True))
        cases.append(('approved repository', [repo_assertion], valid_repo, False))
        valid_token = dict(openxpki_activate_runtime=True, openxpki_managed_cli=True,
                           openxpki_token_operation='inspect', openxpki_token_alias='')
        cases.append(('inspect token', [token_assertion], valid_token, False))
        for name, changes in [('arbitrary CLI', dict(openxpki_token_operation='shell')),
                               ('inactive issuer', dict(openxpki_activate_runtime=False)),
                               ('alias injection', dict(openxpki_token_operation='check', openxpki_token_alias='x;bad'))]:
            cases.append((name, [token_assertion], dict(valid_token, **changes), True))
        for name, checksum, reject in [('same state', 'approved', False), ('different lineage', 'different', True)]:
            values = {'handover_previous_states': {'results': [dict(stat=dict(exists=True, checksum=checksum),
                item=dict(stat=dict(checksum='approved')))]}}
            cases.append((name, [state_assertion], values, reject))
        plays = []
        for name, checks, values, reject in cases:
            tasks = checks if not reject else [
                {'ansible.builtin.set_fact': {'unsafe_rejected': False}},
                {'block': checks, 'rescue': [{'ansible.builtin.set_fact': {'unsafe_rejected': True}}]},
                {'ansible.builtin.assert': {'that': ['unsafe_rejected'], 'fail_msg': name}}]
            plays.append(dict(name=name, hosts='localhost', connection='local', gather_facts=False,
                              vars=values, tasks=tasks))
        with tempfile.TemporaryDirectory() as directory:
            play = Path(directory) / 'guards.yml'
            play.write_text(yaml.safe_dump(plays, sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
