"""Exercise native runner registration tasks without installing packages or services."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


# Match the native list command's JSON protocol, including exit zero on bad TOML.
# Registration records arguments and writes a local config; it never calls GitLab.
RUNNER_CLI = r'''#!/usr/bin/env python3
import json, pathlib, sys, tomllib
args = sys.argv[1:]
path = pathlib.Path(args[args.index('--config') + 1])
if 'list' in args:
    if args[:3] != ['--log-format', 'json', 'list']:
        raise SystemExit('Fixture requires native JSON log mode')
    try:
        config = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        print(json.dumps({'level': 'warning', 'msg': 'Failed to load config'}), file=sys.stderr)
        sys.exit(0)
    print(json.dumps({'ConfigFile': str(path), 'msg': 'Listing configured runners'}), file=sys.stderr)
    for runner in config.get('runners', []):
        print(json.dumps({'Executor': runner['executor'], 'URL': runner['url'],
                          'Token': runner['token'], 'msg': runner['name']}), file=sys.stderr)
elif 'register' in args:
    record = path.with_suffix('.registrations.json')
    calls = json.loads(record.read_text()) if record.exists() else []
    record.write_text(json.dumps(calls + [args]))
    with path.open('a') as output:
        output.write('\n[[runners]]\nname="fixture"\nexecutor="shell"\n'
                     'url="https://gitlab.lab.test"\ntoken="glrt-fixture"\n')
else:
    raise SystemExit('Unexpected runner command')
'''


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook') and tomllib is not None,
                     'Requires native Ansible and Python 3.11+ for the isolated TOML fixture')
class PodmanRunner(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.work = Path(self.temp.name)
        self.role = UPSTREAM / 'tier-1/ansible/roles/podman_runner'
        self.tasks = yaml.safe_load((self.role / 'tasks/main.yml').read_text())
        binary = self.work / 'bin/gitlab-runner'
        binary.parent.mkdir()
        binary.write_text(RUNNER_CLI)
        binary.chmod(0o700)
        config = self.work / 'ansible.cfg'
        config.write_text('[defaults]\nhost_key_checking = True\n')
        self.environment = dict(os.environ, PATH=str(binary.parent) + ':' + os.environ['PATH'],
                                ANSIBLE_CONFIG=str(config))

    def run_tasks(self, tasks, variables):
        play = self.work / 'play.yml'
        inputs = self.work / 'inputs.yml'
        inputs.write_text(yaml.safe_dump(variables))
        play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars_files': [str(self.role / 'defaults/main.yml')], 'tasks': tasks,
        }], sort_keys=False))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play), '-e', '@' + str(inputs)],
                              env=self.environment, capture_output=True, text=True)

    def test_config_entries_control_registration_and_modern_token_arguments(self):
        start = next(i for i, task in enumerate(self.tasks)
                     if task['name'] == 'Check GitLab Runner configuration')
        tasks = self.tasks[start:]
        existing = ('[[runners]]\nname="existing"\nexecutor="shell"\n'
                    'url="https://gitlab.lab.test"\ntoken="glrt-existing"\n')
        cases = [
            ('absent', None, 'glrt-fixture', True, True),
            ('package-empty', 'concurrent = 1\n', 'glrt-fixture', True, True),
            ('existing', existing, 'glrt-fixture', True, False),
            ('malformed', '[[runners\n', 'glrt-fixture', False, False),
            ('legacy-token', '', 'legacy-fixture', False, False),
        ]
        for name, contents, token, succeeds, registers in cases:
            with self.subTest(config=name):
                directory = self.work / name
                directory.mkdir()
                config = directory / 'custom-config.toml'
                if contents is not None:
                    config.write_text(contents)
                inputs = {
                    'podman_runner_install_gitlab_runner': True,
                    'podman_runner_register': True,
                    'podman_runner_config_file': str(config),
                    'podman_runner_gitlab_url': 'https://gitlab.lab.test',
                    'podman_runner_authentication_token': token,
                    'podman_runner_description': 'fixture',
                }
                result = self.run_tasks(tasks, inputs)
                self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)
                record = config.with_suffix('.registrations.json')
                self.assertEqual(record.exists(), registers)
                if not registers:
                    self.assertEqual(config.read_text(), contents)
                else:
                    calls = json.loads(record.read_text())
                    self.assertEqual(len(calls), 1)
                    args = calls[0]
                    self.assertEqual(args[args.index('--config') + 1], str(config))
                    self.assertEqual(args[args.index('--token') + 1], token)
                    self.assertEqual(args[args.index('--executor') + 1], 'shell')
                    self.assertFalse(set(args) & {'--registration-token', '--tag-list',
                                                 '--run-untagged', '--locked'})
                    self.assertEqual(len(tomllib.loads(config.read_text())['runners']), 1)
                if succeeds:
                    before = config.read_bytes()
                    again = self.run_tasks(tasks, inputs)
                    self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
                    self.assertEqual(config.read_bytes(), before)
                    self.assertIn('changed=0', again.stdout)
                    if registers:
                        self.assertEqual(len(json.loads(record.read_text())), 1)

    def test_supported_family_is_checked_before_host_mutation(self):
        for family in ('RedHat', 'Debian'):
            with self.subTest(family=family):
                result = self.run_tasks([self.tasks[0]], {'ansible_os_family': family})
                self.assertEqual(result.returncode == 0, family == 'RedHat', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
