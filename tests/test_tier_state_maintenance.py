"""State runbook errors stop maintenance without terminating the operator's login."""

import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import time
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipIf(os.name == 'nt' or not shutil.which('bash'), 'Requires Linux Bash and a PTY')
class StateMaintenance(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        import pty

        self.generate()
        self.tier = self.root / 'verify-tier-0'
        self.shared = self.root / 'verify-shared'
        self.setup = 'infrastructure-runner'
        variables = self.tier / 'ansible/group_vars/infrastructure_runner.yml'
        variables.write_text('{}\n')
        inputs = self.tier / f'terraform/deployments/{self.setup}/terraform.tfvars'
        inputs.write_text('vm_instances = {}\n')
        self.state = self.tier / f'.terraform/state/{self.setup}/prod/terraform.tfstate'
        self.state.parent.mkdir(parents=True)
        self.state.write_text('{"fixture": "original state"}\n')
        self.original = self.state.read_bytes()
        tools = self.parent / 'tools'
        tools.mkdir()
        self.calls = self.parent / 'calls.jsonl'
        self.fail_init = self.parent / 'fail-init'
        terraform = tools / 'terraform'
        terraform.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['STATE_TEST_CALLS'], 'a') as log: log.write(json.dumps(args)+'\\n')
command=args[1:]
if command[0]=='init' and Path(os.environ['STATE_TEST_FAIL_INIT']).exists(): raise SystemExit(1)
if command[:2]==['workspace','show']: print('default')
elif command[:2]==['state','pull']: print('{"fixture": "original state"}')
elif command[:2]==['state','list']: print('module.vms["worker-7"].proxmox_virtual_environment_vm.this')
''')
        terraform.chmod(0o755)
        guide = (UPSTREAM / 'docs/05-operations/06-resilience/recovery/terraform-import.md').read_text()
        blocks = re.findall(r'```bash\n(.*?)```', guide, re.S)
        self.shell = blocks[0]
        self.selection = self.parent / 'selection.sh'
        self.selection.write_text(blocks[1])
        self.prepare = self.parent / 'prepare.sh'
        self.prepare.write_text(blocks[2])
        self.master, slave = pty.openpty()
        environment = dict(os.environ, PS1='login> ', TERM='dumb',
                           PATH=str(tools) + os.pathsep + os.environ['PATH'],
                           STATE_TEST_CALLS=str(self.calls), STATE_TEST_FAIL_INIT=str(self.fail_init))
        self.process = subprocess.Popen(['bash', '--noprofile', '--norc', '-i'], cwd=self.tier,
                                        env=environment, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        self.addCleanup(self.cleanup_shell)
        self.pending = ''
        self.expect('login> ')

    def cleanup_shell(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        os.close(self.master)

    def send(self, command):
        os.write(self.master, (command + '\n').encode())

    def expect(self, marker):
        deadline = time.monotonic() + 20
        while marker not in self.pending and time.monotonic() < deadline:
            if select.select([self.master], [], [], 0.1)[0]:
                self.pending += os.read(self.master, 65536).decode(errors='replace')
        self.assertIn(marker, self.pending)
        self.assertIsNone(self.process.poll(), 'Parent login shell exited')
        output, self.pending = self.pending.split(marker, 1)
        return output

    def select_inputs(self):
        self.send(self.shell)
        self.expect('state-maintenance> ')
        self.send(f'source "{self.selection}"')
        self.expect('Original deployment setup: ')
        self.send(self.setup)
        self.expect('Setup group-vars filename [infrastructure_runner.yml]: ')
        self.send('')
        self.expect('Shared repository directory [../verify-shared]: ')

    def test_bad_shared_path_reprompts_without_terraform_and_keeps_context(self):
        self.select_inputs()
        self.send('missing_shared')
        self.expect('Shared checkout not found: missing_shared/scripts/deploy.sh')
        self.assertFalse(self.calls.exists())
        self.send('')
        self.expect('state-maintenance> ')
        self.send('printf "RESOLVED=%s\\n" "$IAC_SHARED"')
        self.expect('RESOLVED=' + str(self.shared))
        self.send(f'source "{self.prepare}"')
        self.expect('module.vms["worker-7"].proxmox_virtual_environment_vm.this')
        self.assertEqual(self.state.read_bytes(), self.original)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertTrue(any(call[1] == 'init' for call in calls))
        self.send('exit')
        self.expect('login> ')
        self.send('printf "LOGIN_ALIVE\\n"')
        self.expect('LOGIN_ALIVE\r\n')

    def test_missing_state_returns_to_login_before_any_terraform_call(self):
        self.state.unlink()
        self.select_inputs()
        self.send('')
        self.expect('state-maintenance> ')
        self.send(f'source "{self.prepare}"')
        self.expect('Original state missing or empty: ')
        self.expect('login> ')
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state.exists())
        self.send('printf "LOGIN_ALIVE\\n"')
        self.expect('LOGIN_ALIVE\r\n')

    def test_failed_initialization_returns_to_login_without_pulling_state(self):
        self.fail_init.touch()
        self.select_inputs()
        self.send('')
        self.expect('state-maintenance> ')
        self.send(f'source "{self.prepare}"')
        self.expect('login> ')
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 'init')
        self.assertEqual(self.state.read_bytes(), self.original)
