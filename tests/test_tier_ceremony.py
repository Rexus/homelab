"""Exercise ceremony generation, native public bundle acceptance and offline VM plans."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/ceremony_image'
ARCHIVE = Path(os.environ.get('ORCA_TEST_CLCA_ARCHIVE', UPSTREAM / '.tmp/orca-source/clca.tar.gz'))
REVISION = 'd560135cf4bbdc1916fa4c5545012085b96d4a21'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helper():
    spec = importlib.util.spec_from_file_location('ceremony_inputs', ROLE / 'files/public-inputs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CeremonyGeneration(TierRepositoryTestCase):
    def test_refresh_reports_new_setup_registration_without_changing_local_selection(self):
        self.generate('--repo', 'tier-0')
        manifest = self.root / 'verify-tier-0/.deployment-setups'
        retained = [line for line in manifest.read_text().splitlines() if line not in ('ceremony', 'ceremony-build')]
        manifest.write_text('\n'.join(retained) + '\n')
        result = self.generate('--repo', 'tier-0', '--refresh')
        self.assertEqual(manifest.read_text().splitlines(), retained)
        self.assertIn('New deployment roots available in tier-0: ceremony, ceremony-build', result.stdout)

    def test_generated_setups_have_real_native_entrypoints_and_no_offline_ssh_hosts(self):
        self.generate('--repo', 'tier-0', '--repo', 'shared')
        repo = self.root / 'verify-tier-0'
        for setup in ('ceremony-build', 'ceremony'):
            self.assertIn(setup, (repo / '.deployment-setups').read_text().splitlines())
            self.assertTrue((repo / f'terraform/deployments/{setup}/main.tf').is_file())
            self.assertTrue((repo / f'ansible/playbooks/{setup}.yml').is_file())
            self.assertTrue((repo / f'ansible/group_vars/{setup.replace("-", "_")}.yml.example').is_file())
        inventory = yaml.safe_load((repo / 'ansible/inventory/hosts.yml.example').read_text())
        groups = inventory['all']['children']
        connected = {name for group in groups.values() for name in (group or {}).get('hosts', {})}
        self.assertIn('cbuild-1', connected)
        self.assertFalse({'cadm-1', 'orca-1'} & connected)
        for path in ('files/public-inputs.py', 'files/build-image.sh', 'files/0100-ceremony.hook.chroot.sh',
                     'tasks/main.yml', 'tasks/fetch.yml'):
            self.assertTrue((repo / 'ansible/roles/ceremony_image' / path).is_file())
        image = repo / 'ansible/roles/ceremony_image'
        tasks = yaml.safe_load((image / 'tasks/main.yml').read_text())
        package_list = next(task['ansible.builtin.copy']['content'] for task in tasks
                            if task.get('ansible.builtin.copy', {}).get('dest', '').endswith(
                                '/build/config/package-lists/ceremony.list.chroot'))
        packages = set(package_list.split())
        self.assertTrue({'systemd', 'systemd-sysv', 'cryptsetup-bin', 'fido2-tools', 'libfido2-1'} <= packages)
        self.assertNotIn('systemd-cryptsetup', packages, 'Bookworm ships these tools in systemd')
        hook = 'files/0100-ceremony.hook.chroot.sh'
        self.assertEqual((image / hook).read_bytes(), (ROLE / hook).read_bytes())
        if os.name != 'nt':
            result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'ceremony-build',
                                     '--setup', 'ceremony'], cwd=repo, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for setup in ('ceremony-build', 'ceremony'):
                self.assertTrue((repo / f'terraform/deployments/{setup}/terraform.tfvars').is_file())
            local = repo / 'ansible/group_vars/ceremony_build.yml'
            local.write_text('ceremony_build_revision: retained-custom-revision\n')
            result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'ceremony-build'],
                                    cwd=repo, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('retained-custom-revision', local.read_text())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_generated_recipes_pass_native_ansible_syntax(self):
        self.generate('--repo', 'tier-0', '--repo', 'shared')
        repo = self.root / 'verify-tier-0'
        shutil.copyfile(repo / 'ansible/inventory/hosts.yml.example', repo / 'ansible/inventory/hosts.yml')
        environment = dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg'))
        for name in ('ceremony-build', 'ceremony'):
            result = subprocess.run(['ansible-playbook', '--syntax-check', '-i',
                str(repo / 'ansible/inventory/hosts.yml'), str(repo / f'ansible/playbooks/{name}.yml')],
                cwd=repo, env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(ARCHIVE.is_file(), 'Requires the official pinned clca archive fixture')
class PublicImageInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / 'kit'
        self.kit.mkdir()
        with tarfile.open(ARCHIVE) as archive:
            prefix = f'clca-{REVISION}/'
            for entry in archive.getmembers():
                name = entry.name.removeprefix(prefix)
                if entry.isfile() and (name.startswith(('bin/', 'lib/')) or name == 'LICENSE'):
                    path = self.kit / 'clca' / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.extractfile(entry).read())
        for name in ('scripts/offline-root.sh', 'templates/offline-root/orca.conf.example',
                     'templates/offline-root/clca.cfg.example', 'templates/offline-root/openssl.cnf.example'):
            path = self.kit / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(UPSTREAM / 'tier-0' / name, path)
        defaults = (self.kit / 'templates/offline-root/orca.conf.example').read_text()
        settings = {}
        for line in defaults.splitlines():
            if line.startswith('ORCA_'):
                key, value = line.split('=', 1)
                if key != 'ORCA_CLCA_SOURCE':
                    settings[key] = value.strip('"\'')
        settings['ORCA_BACKUP_RECIPIENT'] = 'age1testpublicrecipient'
        (self.kit / 'templates/offline-root/orca.conf').write_text(''.join(
            f'{key}="{value}"\n' for key, value in settings.items()))
        (self.kit / 'source.txt').write_text('Pinned official clca test input\n')
        self.accepted = self.manifest()

    def manifest(self):
        files = sorted(path for path in self.kit.rglob('*') if path.is_file()
                       and path.name not in ('manifest.sha256', 'orca.conf'))
        path = self.kit / 'manifest.sha256'
        path.write_text(''.join(f'{sha(item)}  {item.relative_to(self.kit).as_posix()}\n' for item in files))
        return sha(path)

    def validate(self, accepted=None):
        return helper().validate_kit(self.kit, accepted or self.accepted, UPSTREAM / 'tier-0')

    def test_accepts_exact_native_payload_and_records_public_policy_identity(self):
        result = self.validate()
        self.assertIn('clca/bin/clca', result['files'])
        self.assertEqual(result['manifest_sha256'], self.accepted)
        self.assertEqual(result['public_policy_sha256'], sha(self.kit / 'templates/offline-root/orca.conf'))

    def test_refuses_unmanifested_private_file_even_with_accepted_old_manifest(self):
        (self.kit / 'root-private.key').write_text('private fixture must never enter image')
        with self.assertRaisesRegex(ValueError, 'Unexpected/unmanifested'):
            self.validate()

    def test_refuses_private_file_added_to_newly_accepted_manifest(self):
        (self.kit / 'custody-secret').write_text('private fixture')
        with self.assertRaisesRegex(ValueError, 'Only the native'):
            self.validate(self.manifest())

    def test_refuses_changed_native_payload_even_with_updated_manifest(self):
        with (self.kit / 'clca/bin/clca').open('ab') as stream:
            stream.write(b'\n# tampered native payload\n')
        with self.assertRaisesRegex(ValueError, 'audited pin'):
            self.validate(self.manifest())

    def test_refuses_secret_fields_in_unmanifested_public_configuration(self):
        path = self.kit / 'templates/offline-root/orca.conf'
        original = path.read_text()
        for field in ('ORCA_PASSPHRASE', 'ORCA_FIDO2_PIN', 'ORCA_LUKS_PASSPHRASE'):
            with self.subTest(field=field):
                path.write_text(original + f'{field}="must-not-enter-image"\n')
                with self.assertRaisesRegex(ValueError, 'known literal public'):
                    self.validate()

    @unittest.skipIf(os.name == 'nt', 'Requires native symlinks')
    def test_refuses_symlinked_input(self):
        (self.kit / 'outside').symlink_to(self.root / 'not-public')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.validate()


class FrozenBuildRevision(unittest.TestCase):
    def test_repeat_accepts_original_inputs_and_changes_require_new_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('recipe.json', 'public-inputs.py', 'build-image.sh'):
                (root / name).write_text('public fixture\n')
            for name in ('includes.chroot', 'hooks/live', 'package-lists', 'packages.chroot'):
                path = root / 'build/config' / name
                path.mkdir(parents=True)
                (path / 'fixture').write_text('public fixture\n')
            value = helper().seal(root)
            self.assertEqual(helper().seal(root), value)
            (root / 'ceremony-output.iso').write_text('output is not an input')
            self.assertEqual(helper().seal(root), value)
            (root / 'build/config/includes.chroot/fixture').write_text('different tool policy')
            with self.assertRaisesRegex(ValueError, 'NEW ceremony_build_revision'):
                helper().seal(root)

    def test_fido2_package_and_probe_changes_require_a_new_sealed_revision(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        package_list = next(task['ansible.builtin.copy']['content'] for task in tasks
                            if task.get('ansible.builtin.copy', {}).get('dest', '').endswith(
                                '/build/config/package-lists/ceremony.list.chroot'))
        hook = (ROLE / 'files/0100-ceremony.hook.chroot.sh').read_text()
        for selected, original, updated in (
            ('package-lists/ceremony.list.chroot', package_list.replace('fido2-tools libfido2-1', ''), package_list),
            ('hooks/live/0100-ceremony.hook.chroot', '# previous accepted hook\n', hook),
        ):
            with self.subTest(input=selected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in ('recipe.json', 'public-inputs.py', 'build-image.sh'):
                    (root / name).write_text('public fixture\n')
                for name in ('includes.chroot', 'hooks/live', 'package-lists', 'packages.chroot'):
                    (root / 'build/config' / name).mkdir(parents=True)
                changed = root / 'build/config' / selected
                changed.write_text(original)
                accepted = helper().seal(root)
                self.assertEqual(helper().seal(root), accepted)
                changed.write_text(updated)
                with self.assertRaisesRegex(ValueError, 'NEW ceremony_build_revision'):
                    helper().seal(root)


class NativeDiskUnlockTools(unittest.TestCase):
    @unittest.skipUnless(os.name != 'nt' and Path('/etc/debian_version').is_file()
                         and Path('/etc/debian_version').read_text().strip().startswith('12.')
                         and shutil.which('fido2-token') and shutil.which('systemd-cryptenroll'),
                         'Requires native Debian 12 with fido2-tools and systemd; no token is needed')
    def test_image_hook_native_probes_without_enrollment_or_hardware(self):
        # Only the initial read-only probes run; the remaining hook mutates a build chroot.
        probes = (ROLE / 'files/0100-ceremony.hook.chroot.sh').read_text().split("python3 - <<'PY'", 1)[0]
        result = subprocess.run(['sh', '-s'], input=probes, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('+FIDO2', result.stdout)
        self.assertIn('attach', result.stdout)


@unittest.skipUnless(os.name != 'nt' and shutil.which('terraform'), 'Requires native Terraform with cached providers')
class OfflineSessionPlan(unittest.TestCase):
    def test_real_provider_schema_and_mocked_plan_keep_sessions_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(UPSTREAM / 'tier-0/terraform/deployments/ceremony', root, dirs_exist_ok=True)
            # Omitted optional/computed provider blocks remain unknown during plan. Their absence
            # is intentional in the native configuration; test explicit planned controls below.
            self.assertNotRegex((root / 'main.tf').read_text(),
                                r'(?m)^  (?:network_device|disk|initialization|clone)\s*\{')
            (root / 'public.iso').write_bytes(b'public ISO plan fixture')
            (root / 'ceremony.tftest.hcl').write_text('''
mock_provider "proxmox" {}
variables {
  proxmox_api_url = "https://pve.example.internal:8006/"
  proxmox_api_token_id = "fixture@pve!provision"
  proxmox_api_token_secret = "fixture-only"
  ceremony_hypervisor_trust_accepted = true
  ceremony_iso_path = "public.iso"
  ceremony_iso_sha256 = "''' + sha(root / 'public.iso') + '''"
  ceremony_iso_datastore_id = "local"
  ceremony_pool_id = "ceremony"
  ceremony_sessions = {
    "cadm-1" = {vm_id = 621, node_name = "pve01", usb_mappings = ["issuer-token"]}
    "orca-1" = {vm_id = 623, node_name = "pve01", usb_mappings = ["orca-work", "orca-transfer", "orca-backup"]}
  }
}
run "offline_console_sessions" {
  command = plan
  assert {
    condition = alltrue([for vm in proxmox_virtual_environment_vm.session :
      vm.started == false && vm.on_boot == false && vm.agent[0].enabled == false &&
      vm.pool_id == "ceremony"])
    error_message = "Ceremony sessions must have no network, cloned disks, cloud-init or agent and never auto-start."
  }
}
run "reject_duplicate_usb_mapping" {
  command = plan
  variables {
    ceremony_sessions = {
      "cadm-1" = {vm_id = 621, node_name = "pve01", usb_mappings = ["same-token"]}
      "orca-1" = {vm_id = 623, node_name = "pve01", usb_mappings = ["same-token"]}
    }
  }
  expect_failures = [var.ceremony_sessions]
}
run "reject_implicit_hypervisor_trust" {
  command = plan
  variables { ceremony_hypervisor_trust_accepted = false }
  expect_failures = [proxmox_virtual_environment_file.image]
}
run "reject_unaccepted_image_bytes" {
  command = plan
  variables { ceremony_iso_sha256 = "''' + '0' * 64 + '''" }
  expect_failures = [proxmox_virtual_environment_file.image]
}
''')
            for command in (['terraform', 'init', '-backend=false', '-input=false', '-lockfile=readonly'],
                            ['terraform', 'validate', '-no-color'], ['terraform', 'test', '-no-color']):
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
