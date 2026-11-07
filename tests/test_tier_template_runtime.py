"""Automatic local runtime preparation without touching system packages or live APIs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipIf(os.name == 'nt', 'Requires native Bash/Python on Linux/WSL')
class TemplateRuntime(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.generate('--repo', 'tier-0')
        self.repo = self.root / 'verify-tier-0'
        self.commands = self.root / 'commands'
        self.commands.mkdir()
        self.marker = self.root / 'terraform-called'
        terraform = self.commands / 'terraform'
        terraform.write_text('#!/bin/sh\ntouch "$TEST_TERRAFORM_MARKER"\n')
        terraform.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.commands) + ':' + os.environ['PATH'],
                        TEMPLATE_RUNTIME_MODE='auto', TEMPLATE_PYTHON=sys.executable,
                        PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1',
                        TEST_TERRAFORM_MARKER=str(self.marker))

    def run_wrapper(self, **overrides):
        return subprocess.run(['bash', 'scripts/proxmox-templates.sh', 'verify'], cwd=self.repo,
                              env=dict(self.env, **overrides), capture_output=True, text=True)

    def test_generated_bootstrap_is_standalone_and_check_mode_does_not_install(self):
        for relative in ('scripts/lib/template-runtime.sh', 'ansible/runtime-requirements.txt',
                         'ansible/playbooks/prepare-template-runtime.yml', 'ansible/requirements.yml'):
            self.assertTrue((self.repo / relative).is_file(), relative)
        self.assertFalse((self.root / 'verify-shared').exists())
        result = subprocess.run(['bash', '-c', 'set -euo pipefail; source "$1/scripts/lib/template-runtime.sh"; '
                                 'prepare_template_runtime "$1" verify', 'runtime-test', str(self.repo)],
                                env=dict(self.env, TEMPLATE_RUNTIME_MODE='check'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / '.venv').exists())

    def test_bad_explicit_python_and_failed_install_preserve_state_and_plan(self):
        state = self.repo / '.terraform/state/proxmox-templates/terraform.tfstate'
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 4}')
        plan = self.repo / '.terraform/plans/proxmox-templates.tfplan'
        plan.parent.mkdir(parents=True)
        plan.write_text('reviewed plan')
        wrong = self.commands / 'old-python'
        wrong.write_text('#!/bin/sh\nexit 1\n')
        wrong.chmod(0o755)
        self.assertNotEqual(self.run_wrapper(TEMPLATE_PYTHON=str(wrong)).returncode, 0)
        empty_wheels = self.root / 'empty-wheels'
        empty_wheels.mkdir()
        result = self.run_wrapper(PIP_FIND_LINKS=str(empty_wheels))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists(), 'Dependency failure must precede Terraform')
        self.assertEqual(json.loads(state.read_text()), {'serial': 4})
        self.assertEqual(plan.read_text(), 'reviewed plan')

    @unittest.skipUnless(os.environ.get('HOMELAB_TEMPLATE_WHEELS'),
                         'Set HOMELAB_TEMPLATE_WHEELS to the declared runtime/module wheelhouse')
    def test_fresh_and_repeated_offline_install_override_old_system_ansible(self):
        collection = next((Path(root) / 'ansible_collections/community/proxmox'
                           for root in os.environ.get('ANSIBLE_COLLECTIONS_PATH', '').split(os.pathsep)
                           if (Path(root) / 'ansible_collections/community/proxmox/MANIFEST.json').is_file()), None)
        if collection is None:
            self.skipTest('Pre-stage the declared community.proxmox collection')
        target = self.repo / '.venv/collections/ansible_collections/community/proxmox'
        shutil.copytree(collection, target)
        old_called = self.root / 'old-ansible-called'
        for tool in ('ansible-playbook', 'ansible-doc', 'ansible-galaxy'):
            path = self.commands / tool
            path.write_text('#!/bin/sh\ntouch "$TEST_OLD_ANSIBLE"\necho "ansible [core 2.16.16]"\nexit 1\n')
            path.chmod(0o755)
        env = dict(self.env, PIP_FIND_LINKS=os.environ['HOMELAB_TEMPLATE_WHEELS'],
                   TEST_OLD_ANSIBLE=str(old_called), ANSIBLE_CONFIG=str(self.repo / 'ansible/ansible.cfg'),
                   HTTPS_PROXY='http://127.0.0.1:1', HTTP_PROXY='http://127.0.0.1:1', NO_PROXY='')
        command = ['bash', 'scripts/proxmox-templates.sh', 'setup']
        first = subprocess.run(command, cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn('core 2.21.', first.stdout)
        self.assertFalse(old_called.exists())
        metadata = next((self.repo / '.venv').glob('proxmox-templates-py*/lib/python*/site-packages/ansible_core-*.dist-info/METADATA'))
        before = metadata.stat().st_mtime_ns
        second = subprocess.run(command, cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('changed=0', second.stdout)
        self.assertEqual(metadata.stat().st_mtime_ns, before)
        self.assertFalse(old_called.exists())
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.repo / '.terraform').exists())
        if os.geteuid() != 0:
            sudo = self.commands / 'sudo'
            sudo.write_text('#!/bin/sh\nexit 1\n')
            sudo.chmod(0o755)
            command = ['bash', '-c', 'set -euo pipefail; '
                       'command() { if [[ "$*" == "-v qemu-img" ]]; then return 1; fi; builtin command "$@"; }; '
                       'source "$1/scripts/lib/template-runtime.sh"; prepare_template_runtime "$1" setup',
                       'runtime-ci-test', str(self.repo)]
            denied = subprocess.run(command, env=dict(env, CI='true'), capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn('noninteractive sudo in CI', denied.stderr)
            self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
