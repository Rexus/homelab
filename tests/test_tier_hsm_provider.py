"""Focused provider guards, read-only inspection and native USB plan checks."""

import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/hsm_provider'
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None
TERRAFORM = shutil.which('terraform')


class GeneratedHSMProvider(TierRepositoryTestCase):
    def setUp(self):
        # Native temporary output avoids slow/permission-sensitive WSL mounted-drive writes.
        self.temp = tempfile.TemporaryDirectory(prefix='hsm-generated-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'

    def test_generated_provider_and_usb_inputs_are_shipped(self):
        self.generate()
        tier = self.root / 'verify-tier-0'
        for relative in (
            'ansible/roles/hsm_provider/tasks/main.yml',
            'ansible/roles/hsm_provider/tasks/issuer-csr.yml',
            'ansible/playbooks/deployment/hsm-issuer.yml',
            'ansible/playbooks/deployment/hsm-inspect.yml',
            'ansible/playbooks/deployment/hsm-token.yml',
            'ansible/playbooks/deployment/hsm-remote.yml',
            'ansible/playbooks/deployment/hsm-remote-client.yml',
            'ansible/playbooks/deployment/hsm-remote-check.yml',
            'ansible/roles/hsm_remote/tasks/main.yml',
            'ansible/roles/hsm_remote/tasks/probe.yml',
            'ansible/group_vars/hsm_remoting.yml.example',
            'terraform/modules/vm/usb.tf',
            'terraform/deployments/hsm/usb.tf',
        ):
            expected = (UPSTREAM / 'tier-0' / relative).read_text().replace(
                '../../../../shared/', '../../../../verify-shared/')
            self.assertEqual((tier / relative).read_text(), expected, relative)
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.assertFalse(defaults['hsm_issuer_create_csr'])


@unittest.skipUnless(ANSIBLE, 'Requires Ansible on Linux/WSL')
class NativeProviderChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hsm-provider-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.library = self.root / 'selected-pkcs11.so'
        self.library.touch()
        self.tool = self.root / 'pkcs11-tool-fixture'
        self.calls = self.root / 'calls.json'
        self.tool.write_text(
            '#!/usr/bin/env python3\nimport json, os, sys\n'
            f'open({str(self.calls)!r}, "w").write(json.dumps(sys.argv[1:]))\n'
            'print("Slot 0: accepted fixture\\n  token label: issuer\\n  serial num : 123456")\n'
        )
        self.tool.chmod(0o755)
        self.inputs = {
            'ansible_connection': 'local', 'ansible_become': False,
            'ansible_python_interpreter': shutil.which('python3'),
            'ansible_os_family': 'Debian', 'ansible_service_mgr': 'systemd',
            'hsm_provider': 'opensc', 'hsm_provider_mode': 'usb',
            'hsm_provider_packages': ['opensc'], 'hsm_provider_library': str(self.library),
            'hsm_provider_tool': str(self.tool), 'hsm_provider_user': getpass.getuser(),
            'hsm_provider_expected_serial': '123456',
        }

    def run_tasks(self, task_file, overrides=None, syntax=False):
        playbook = self.root / 'playbook.yml'
        playbook.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'gather_facts': False,
            'tasks': [{'ansible.builtin.import_role': {'name': 'hsm_provider', 'tasks_from': task_file}}],
        }]))
        variables = self.root / 'inputs.json'
        variables.write_text(json.dumps(dict(self.inputs, **(overrides or {}))))
        command = [ANSIBLE, '-i', 'localhost,', str(playbook), '-e', f'@{variables}']
        if syntax:
            command.append('--syntax-check')
        result = subprocess.run(command, env=dict(
            os.environ,
            ANSIBLE_ROLES_PATH=str(ROLE.parent),
            ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'),
            ANSIBLE_NOCOLOR='1',
        ), capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr

    def test_preflight_supports_selected_native_transports_and_rejects_bad_inputs(self):
        for override in (
            {}, {'ansible_os_family': 'RedHat'}, {'hsm_provider': 'picohsm'},
            {'hsm_provider': 'yubihsm2', 'hsm_yubihsm_serial': '123456'},
            {'hsm_provider': 'yubihsm', 'hsm_yubihsm_serial': '123456'},
            {'hsm_provider': 'pkcs11', 'hsm_provider_mode': 'client'},
        ):
            with self.subTest(valid=override):
                code, output = self.run_tasks('preflight', override)
                self.assertEqual(code, 0, output)
        for override in (
            {'hsm_provider': ''}, {'hsm_provider': 'invented-gateway'},
            {'hsm_provider_packages': []}, {'hsm_provider_library': 'relative.so'},
            {'hsm_provider_expected_serial': ''}, {'ansible_os_family': 'Darwin'},
            {'hsm_provider': 'opensc', 'hsm_provider_mode': 'client'},
            {'hsm_provider': 'pkcs11', 'hsm_provider_mode': 'usb'},
            {'hsm_provider': 'yubihsm', 'hsm_yubihsm_serial': ''},
            {'hsm_provider': 'yubihsm', 'hsm_yubihsm_serial': '123456',
             'hsm_yubihsm_connector_url': 'http://0.0.0.0:12345'},
            {'hsm_provider_config_files': [{'src': 'config', 'dest': '/etc/../tmp/config'}]},
            {'hsm_provider_environment': {'OPENSSL_CONF': '/tmp/unreviewed.conf'}},
        ):
            with self.subTest(invalid=override):
                code, output = self.run_tasks('preflight', override)
                self.assertNotEqual(code, 0, output)
        self.assertFalse(self.calls.exists(), 'Preflight must never invoke a device tool')

    def test_inspection_only_lists_without_login_and_matches_complete_serial(self):
        for provider in ('opensc', 'yubihsm', 'pkcs11'):
            code, output = self.run_tasks('inspect', {'hsm_provider': provider})
            self.assertEqual(code, 0, output)
            self.assertNotRegex(output, r'changed=[1-9]')
            self.assertEqual(json.loads(self.calls.read_text()),
                             ['--module', str(self.library), '--list-token-slots'])
        for serial in ('12345', '23456', '1234567', 'absent'):
            code, output = self.run_tasks('inspect', {'hsm_provider_expected_serial': serial})
            self.assertNotEqual(code, 0, output)
        self.calls.unlink()
        code, output = self.run_tasks('inspect', {'hsm_provider_expected_serial': ''})
        self.assertNotEqual(code, 0, output)
        self.assertFalse(self.calls.exists(), 'An unspecified device must fail before device access')
        self.library.unlink()
        code, output = self.run_tasks('inspect')
        self.assertNotEqual(code, 0, output)
        self.assertFalse(self.calls.exists(), 'A missing middleware library must fail before device access')

    def test_provider_and_original_key_csr_syntax(self):
        for task_file in ('main', 'issuer', 'token'):
            code, output = self.run_tasks(task_file, syntax=True)
            self.assertEqual(code, 0, output)

    def test_issuer_credential_guard_accepts_only_ready_nonfactory_credentials(self):
        inputs = {'hsm_provider_custody_ready': True, 'hsm_issuer_pin': 'synthetic-changed-credential'}
        code, output = self.run_tasks('issuer-credentials', inputs)
        self.assertEqual(code, 0, output)
        self.assertFalse(self.calls.exists())

    def test_direct_issuer_operations_reject_unready_factory_or_short_credentials_first(self):
        ceremony = {'openxpki_data_mount': str(self.root),
                    'hsm_issuer_csr_path': str(self.root / 'identity/issuer.csr'),
                    'hsm_issuer_common_name': 'Fixture issuer'}
        for task_file in ('issuer-csr', 'token', 'issuer-public-key'):
            for overrides in (
                {'hsm_issuer_pin': 'synthetic-changed-credential'},
                {'hsm_provider_custody_ready': True, 'hsm_issuer_pin': '648219'},
                {'hsm_provider_custody_ready': True, 'hsm_issuer_pin': '0001password'},
                {'hsm_provider_custody_ready': True, 'hsm_issuer_pin': '12'},
            ):
                with self.subTest(entrypoint=task_file, credentials=overrides):
                    code, output = self.run_tasks(task_file, dict(ceremony, **overrides))
                    self.assertNotEqual(code, 0, output)
                    self.assertNotIn('Inspect any existing public CSR', output)
                    self.assertNotIn('Check original issuer runtime and storage', output)
                    self.assertNotIn('Render native public-key inspection configuration', output)
                    self.assertFalse(self.calls.exists(), 'Rejected credentials must precede device access')

    def test_direct_recipes_parse_before_controller_collections_are_installed(self):
        collections = self.root / 'empty-collections'
        collections.mkdir()
        for name in ('hsm-issuer.yml', 'hsm-token.yml', 'hsm-inspect.yml',
                     'hsm-remote.yml', 'hsm-remote-client.yml', 'hsm-remote-check.yml'):
            recipe = UPSTREAM / 'tier-0/ansible/playbooks/deployment' / name
            result = subprocess.run(
                [ANSIBLE, '-i', 'localhost,', str(recipe), '--syntax-check'],
                env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent),
                         ANSIBLE_COLLECTIONS_PATH=str(collections), ANSIBLE_COLLECTIONS_SCAN_SYS_PATH='false',
                         ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'), ANSIBLE_NOCOLOR='1'),
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inspection_entrypoint_never_runs_installation_and_rejects_empty_inventory(self):
        inventory = self.root / 'hosts.yml'
        variables = self.root / 'inputs.json'
        variables.write_text(json.dumps(self.inputs))
        playbook = UPSTREAM / 'tier-0/ansible/playbooks/deployment/hsm-inspect.yml'
        for selected in (True, False):
            inventory.write_text(yaml.safe_dump({'all': {'children': {
                'hsm_gateways': {'hosts': {'localhost': {}} if selected else {}},
            }}}))
            result = subprocess.run(
                [ANSIBLE, '-i', str(inventory), str(playbook), '-e', f'@{variables}'],
                env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent),
                         ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'), ANSIBLE_NOCOLOR='1',
                         CONTROL_NODE_COLLECTIONS_MODE='check'),
                capture_output=True, text=True,
            )
            output = result.stdout + result.stderr
            self.assertIn('Verify Terraform is installed', output)
            self.assertNotIn('command not found: terraform', output)
            if selected:
                self.assertEqual(result.returncode, 0, output)
                self.assertNotRegex(output, r'changed=[1-9]')
            else:
                self.assertNotEqual(result.returncode, 0, output)
            self.assertNotIn('Install approved middleware', output)

    def test_issuer_binding_rejects_replacement_keys_and_wrong_device_identity(self):
        bundle = self.root / 'config.d/realm/infrastructure'
        bundle.mkdir(parents=True)
        key = 'pkcs11:token=issuer;serial=123456;id=%01;type=private'
        signer = {'engine': 'PKCS11', 'key_store': 'ENGINE', 'key': key,
                  'engine_section': f'MODULE_PATH = {self.library}\ndynamic_path = {self.library}\nPIN = __PIN__'}
        configuration = bundle / 'crypto.yaml'
        configuration.write_text(yaml.safe_dump({'token': {'ca-signer': signer}}))
        inputs = {'openxpki_release_dir': str(self.root), 'openxpki_realm': 'infrastructure',
                  'hsm_issuer_engine_library': str(self.library), 'hsm_issuer_key': key}
        code, output = self.run_tasks('issuer-identity', inputs)
        self.assertEqual(code, 0, output)
        for override in (
            {'openxpki_create_issuer_key': True},
            {'hsm_issuer_key': key.replace('123456', 'other-device')},
            {'hsm_issuer_key': key.replace(';id=%01', '')},
            {'hsm_issuer_key': key.replace(';type=private', '')},
            {'hsm_issuer_key': key + ';pin-value=secret'},
            {'hsm_issuer_key': '/srv/openxpki/keys/issuer.pem'},
            {'hsm_issuer_key': key.replace('%01', '%02')},
        ):
            with self.subTest(invalid=override):
                code, output = self.run_tasks('issuer-identity', dict(inputs, **override))
                self.assertNotEqual(code, 0, output)
        self.assertFalse(self.calls.exists(), 'Identity validation must never generate or access a private key')


@unittest.skipUnless(TERRAFORM, 'Requires Terraform and an available bpg provider')
class NativeUSBAttachment(unittest.TestCase):
    def test_native_usb_plan_and_invalid_selectors(self):
        with tempfile.TemporaryDirectory(prefix='hsm-usb-') as temporary:
            root = Path(temporary)
            module = root / 'tier-0/terraform/modules/vm'
            module.mkdir(parents=True)
            for source in (UPSTREAM / 'tier-0/terraform/modules/vm').glob('*.tf'):
                shutil.copy2(source, module)
            config = root / 'shared/config'
            config.mkdir(parents=True)
            shutil.copy2(UPSTREAM / 'shared/config/guest-sizes.json', config)
            (module / 'tests').mkdir()
            (module / 'tests/usb.tftest.hcl').write_text('''
mock_provider "proxmox" {}
variables {
  name = "hsm-1"
  node_name = "pve01"
  template_vm_id = 9100
  bridge = "crypto"
  disk_size_gb = 30
}
run "mapped_token" {
  command = plan
  variables { usb_devices = [{ mapping = "hsm-1-token", usb3 = true }] }
  assert {
    condition = proxmox_virtual_environment_vm.this.usb[0].mapping == "hsm-1-token" && proxmox_virtual_environment_vm.this.usb[0].usb3
    error_message = "The selected native USB mapping and USB3 flag must reach Proxmox."
  }
}
run "selected_port" {
  command = plan
  variables { usb_devices = [{ host = "1-2.3" }] }
  assert {
    condition = proxmox_virtual_environment_vm.this.usb[0].host == "1-2.3"
    error_message = "The selected native USB port must reach Proxmox."
  }
}
run "no_implicit_device" {
  command = plan
  assert {
    condition = length(proxmox_virtual_environment_vm.this.usb) == 0
    error_message = "Existing module callers must not acquire implicit USB devices."
  }
}
run "ambiguous_selector" {
  command = plan
  variables { usb_devices = [{ host = "1-2", mapping = "token" }] }
  expect_failures = [var.usb_devices]
}
run "missing_selector" {
  command = plan
  variables { usb_devices = [{}] }
  expect_failures = [var.usb_devices]
}
run "empty_selector" {
  command = plan
  variables { usb_devices = [{ mapping = "" }] }
  expect_failures = [var.usb_devices]
}
''')
            for args in (['init', '-backend=false', '-input=false'], ['test']):
                result = subprocess.run([TERRAFORM, f'-chdir={module}', *args, '-no-color'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
