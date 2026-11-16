"""Native boot-policy rendering and authenticated guest-proof refusal paths."""

import copy
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

spec = importlib.util.spec_from_file_location('talos_boot_security', UPSTREAM / 'shared/scripts/talos-boot-security.py')
security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)


class BootPolicy(unittest.TestCase):
    def test_existing_nodes_cannot_change_boot_or_encryption_policy(self):
        def plan(previous, desired, before):
            return {'planned_values': {'outputs': {'boot_security': {'value': desired}}},
                    'prior_state': {'values': {'outputs': {'boot_security': {'value': previous}}}},
                    'resource_changes': [{'type': 'proxmox_virtual_environment_vm', 'change': {'before': before}}]}
        secure = {'mode': 'secureboot', 'encrypt_system_disks': True}
        security.guard(plan(None, secure, None))
        security.guard(plan(secure, secure, {'id': '101'}))
        for previous, desired in ((None, secure), (secure, None), (secure, dict(secure, encrypt_system_disks=False))):
            with self.assertRaisesRegex(ValueError, 'Existing nodes retain'):
                security.guard(plan(previous, desired, {'id': '101'}))

    def test_security_proof_requires_real_boolean_and_both_boot_controls(self):
        for spec in ({'secureBoot': False, 'bootedWithUKI': True},
                     {'secureBoot': 'true', 'bootedWithUKI': True}, {'secureBoot': True}):
            with self.assertRaises(ValueError):
                security.check_security([{'spec': spec}])
        security.check_security([{'spec': {'secureBoot': True, 'bootedWithUKI': True}}])

    def test_tpm_volume_proof_rejects_plaintext_wrong_slot_and_failed_sync(self):
        original = {'metadata': {'id': 'STATE'}, 'spec': {
            'phase': 'ready', 'encryptionProvider': 'luks2', 'encryptionSlot': 0,
            'configuredEncryptionKeys': ['tpm']}}
        security.check_volume([original], 'STATE')
        for overrides in ({'phase': 'failed'}, {'encryptionProvider': ''}, {'encryptionSlot': 1},
                          {'configuredEncryptionKeys': ['static:0']}, {'encryptionFailedSyncs': ['tpm:0']}):
            changed = copy.deepcopy(original)
            changed['spec'].update(overrides)
            with self.assertRaises(ValueError):
                security.check_volume([changed], 'STATE')
        self.assertEqual(len(security.resources(json.dumps(original) + '\n' + json.dumps(original))), 2)


TALOSCTL = os.environ.get('HOMELAB_TALOSCTL') or shutil.which('talosctl')


@unittest.skipUnless(os.name != 'nt' and shutil.which('terraform') and shutil.which('openssl') and TALOSCTL,
                     'Requires native Terraform/providers, OpenSSL and Talos 1.13 on Linux')
class NativeSecureBoot(TierRepositoryTestCase):
    def test_signed_iso_and_tpm_encryption_render_with_native_schema(self):
        self.generate()
        for tier in ('tier-0', 'tier-1', 'tier-2'):
            with self.subTest(tier=tier):
                self.check_signed_configuration(tier)

    def check_signed_configuration(self, tier):
        root = self.root / f'verify-{tier}/terraform/deployments/kubernetes'
        source_tests = UPSTREAM / tier / 'terraform/deployments/kubernetes/tests'
        shutil.copytree(source_tests / 'fixtures', root / 'tests/fixtures')
        iso = root / 'tests/fixtures/secureboot.iso'
        iso.write_bytes(b'fixture bytes for checksum and provider-plan tests; not boot media')
        tampered_iso = root / 'tests/fixtures/tampered-secureboot.iso'
        tampered_iso.write_bytes(iso.read_bytes() + b'changed after checksum acceptance')
        cert, key = root / 'api.crt', root / 'api.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        requests = []

        class StorageApi(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                parts = parsed.path.strip('/').split('/')
                query = parse_qs(parsed.query)
                requests.append((self.server.profile, parts, query, self.headers.get('Authorization')))
                if (len(parts) != 5 or parts[:3] != ['api2', 'json', 'nodes']
                        or parts[4] != 'storage' or parts[3] not in ('pve01', 'pve02', 'pve03')
                        or query != {'storage': ['iso-store'], 'content': ['iso']}
                        or self.headers.get('Authorization') != 'PVEAPIToken=fixture@pve!stores=fixture-only'):
                    self.send_error(400)
                    return
                stores = [{'storage': 'iso-store', 'type': 'dir', 'active': 1, 'enabled': 1,
                           'shared': int(self.server.profile == 'shared'), 'content': 'iso'}]
                if self.server.profile == 'missing' and parts[3] == 'pve01':
                    stores = []
                payload = json.dumps({'data': stores}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        endpoints = {}
        for profile in ('local', 'shared', 'missing'):
            server = ThreadingHTTPServer(('127.0.0.1', 0), StorageApi)
            server.profile = profile
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(thread.join)
            self.addCleanup(server.shutdown)
            endpoints[profile] = f'https://127.0.0.1:{server.server_port}/'

        # The pinned datasource's list/flags are optional, so mocks cannot populate them.
        # Bind only this test copy's discovery read to a real provider and loopback HTTPS API.
        discovery = root / 'secure-boot.tf'
        original = discovery.read_text()
        anchor = 'data "proxmox_datastores" "secure_boot" {\n'
        self.assertEqual(original.count(anchor), 1)
        discovery.write_text(original.replace(anchor, anchor + '  provider = proxmox.storage_native\n'))
        (root / 'fixture-storage.tf').write_text(f'''
variable "fixture_storage_endpoint" {{ default = {json.dumps(endpoints['local'])} }}
provider "proxmox" {{
  alias = "storage_native"
  endpoint = var.fixture_storage_endpoint
  api_token = "fixture@pve!stores=fixture-only"
  insecure = false
}}
''')
        header = (source_tests / 'cluster.tftest.hcl').read_text().split('run "clone_and_bootstrap_contract"', 1)[0]
        header = header.replace('mock_provider "proxmox" {}', '''mock_provider "proxmox" {
  mock_resource "proxmox_virtual_environment_file" { defaults = { id="iso-store:iso/fixture.iso" } }
}''')
        media = f'''template_vm_id = null
    vm_firmware = {{bios="ovmf",machine="q35",scsi_hardware="virtio-scsi-pci"}}
    cluster = {{name="test-control",endpoint="https://kubernetes.example.com:6443",bootstrap_node="k8ctl-1",
      talos_version="v1.13.0",kubernetes_version="1.34.0",
      installer_image="factory.talos.dev/nocloud-installer-secureboot/{'a'*64}:v1.13.0",
      pod_cidr="10.244.0.0/16",service_cidr="10.96.0.0/12"}}
    bootstrap_network = {{prefix_length=24,gateway="192.0.2.1"}}
    secure_boot = {{iso_path={json.dumps(str(iso))},iso_sha256=filesha256({json.dumps(str(iso))}),iso_datastore_id="iso-store"}}'''
        # Select altered bytes while retaining the original artifact's accepted SHA256.
        tampered_media = media.replace(f'iso_path={json.dumps(str(iso))}',
                                       f'iso_path={json.dumps(str(tampered_iso))}')
        installer_override = f'''machine_config_patches = [yamlencode({{
      machine = {{install = {{image = "factory.talos.dev/installer/{'b'*64}:v1.13.0"}}}}
    }})]'''
        content = header + '''
run "legacy_clone_unchanged" {
  command = plan
  assert {
    condition = alltrue([for vm in proxmox_virtual_environment_vm.node : length(vm.clone)==1 && length(vm.tpm_state)==0])
    error_message = "Old clusters keep their original clone/TPM contract."
  }
}
''' + f'''
run "reject_unsigned_firmware" {{
  command = plan
  variables {{
    {media}
    vm_firmware = {{bios="seabios"}}
  }}
  expect_failures = [terraform_data.configuration]
}}
run "reject_unavailable_iso_store" {{
  command = plan
  variables {{
    {media}
    fixture_storage_endpoint = {json.dumps(endpoints['missing'])}
  }}
  expect_failures = [terraform_data.configuration]
}}
run "reject_tampered_iso" {{
  command = plan
  variables {{
    {tampered_media}
  }}
  expect_failures = [terraform_data.configuration]
}}
run "secure_hardware_and_media" {{
  command = plan
  variables {{
    {media}
  }}
  assert {{
    condition = alltrue([for vm in proxmox_virtual_environment_vm.node :
      length(vm.clone)==0 && length(vm.tpm_state)==1 && vm.tpm_state[0].version=="v2.0" &&
      vm.bios=="ovmf" && vm.efi_disk[0].type=="4m" && !vm.efi_disk[0].pre_enrolled_keys &&
      vm.operating_system[0].type=="l26" && vm.serial_device[0].device=="socket" &&
      length(vm.cdrom)==1 && vm.cdrom[0].interface=="ide0" && length(vm.initialization)==1])
    error_message = "Each ISO-built node needs private TPM/EFI state, Linux guest type, socket recovery console and network-only NoCloud drive."
  }}
  assert {{
    condition = (length(proxmox_virtual_environment_file.secure_boot_iso)==3 &&
      alltrue([for file in proxmox_virtual_environment_file.secure_boot_iso : !file.overwrite && file.content_type=="iso"]))
    error_message = "Local stores need one checksum-pinned API upload per target host, without overwriting existing media."
  }}
}}
run "shared_iso_upload_once" {{
  command = plan
  variables {{
    {media}
    fixture_storage_endpoint = {json.dumps(endpoints['shared'])}
  }}
  assert {{
    condition = length(proxmox_virtual_environment_file.secure_boot_iso)==1
    error_message = "Shared ISO storage must have only one upload owner."
  }}
}}
run "plaintext_selection_and_media_eject" {{
  command = plan
  variables {{
    {media.replace('iso_datastore_id="iso-store"', 'iso_datastore_id="iso-store",encrypt_system_disks=false,install_media_attached=false')}
  }}
  assert {{
    condition = (length(local.secure_boot_volume_patches)==0 &&
      alltrue([for vm in proxmox_virtual_environment_vm.node : vm.cdrom[0].file_id=="none" && length(vm.tpm_state)==1]))
    error_message = "Opting out of encryption and ejecting media must retain unique TPM hardware."
  }}
}}
run "native_signed_encrypted_configuration" {{
  command = apply
  providers = {{proxmox=proxmox,talos=talos.native}}
  override_resource {{target=talos_machine_configuration_apply.node}}
  override_resource {{target=talos_machine_bootstrap.cluster}}
  override_resource {{target=talos_cluster_kubeconfig.cluster}}
  variables {{
    {media}
    {installer_override}
  }}
}}
'''
        for name, command, attached in (('media_eject_plan', 'plan', 'false'),
                                         ('media_eject_apply', 'apply', 'false'),
                                         ('media_reattach_plan', 'plan', 'true')):
            maintenance_media = media.replace('iso_datastore_id="iso-store"',
                                              f'iso_datastore_id="iso-store",install_media_attached={attached}')
            content += f'''
run "{name}" {{
  command = {command}
  providers = {{proxmox=proxmox,talos=talos.native}}
  override_resource {{target=talos_machine_configuration_apply.node}}
  override_resource {{target=talos_machine_bootstrap.cluster}}
  override_resource {{target=talos_cluster_kubeconfig.cluster}}
  variables {{
    {maintenance_media}
    {installer_override}
  }}
}}
'''
        # Replace the firmware expression inside this refusal case, not duplicate the HCL attribute.
        content = content.replace('run "reject_unsigned_firmware" {\n  command = plan\n  variables {\n    ' + media,
                                  'run "reject_unsigned_firmware" {\n  command = plan\n  variables {\n    ' + media.replace('    vm_firmware = {bios="ovmf",machine="q35",scsi_hardware="virtio-scsi-pci"}\n', ''))
        (root / 'tests/secure-boot.tftest.hcl').write_text(content)
        env = dict(os.environ, TF_IN_AUTOMATION='1', CHECKPOINT_DISABLE='1', SSL_CERT_FILE=str(cert))
        init = subprocess.run(['terraform', f'-chdir={root}', 'init', '-backend=false', '-input=false', '-lockfile=readonly', '-no-color'],
                              env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(init.returncode, 0, init.stderr)
        result = subprocess.run(['terraform', f'-chdir={root}', 'test', '-json', '-verbose'],
                                env=env, capture_output=True, text=True, timeout=180)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        diagnostics = [(event.get('@testrun'), event['diagnostic'])
                       for event in events if event['type']=='diagnostic']
        self.assertEqual(result.returncode, 0, diagnostics)
        for name, file_id in (('media_eject_plan', 'none'),
                              ('media_reattach_plan', 'iso-store:iso/fixture.iso')):
            plan = next(event['test_plan'] for event in events
                        if event.get('@testrun') == name and event['type'] == 'test_plan')
            changes = [resource['change'] for resource in plan['resource_changes']
                       if resource['type'] == 'proxmox_virtual_environment_vm']
            self.assertEqual(len(changes), 4)
            for change in changes:
                self.assertEqual(change['actions'], ['update'])
                before, after = change['before'], change['after']
                self.assertEqual(before['boot_order'], ['scsi0', 'ide0'])
                self.assertEqual(after['boot_order'], before['boot_order'])
                self.assertEqual(after['cdrom'][0]['interface'], before['cdrom'][0]['interface'])
                self.assertEqual(after['cdrom'][0]['file_id'], file_id)
                for field in ('bios', 'machine', 'scsi_hardware', 'efi_disk', 'tpm_state', 'initialization'):
                    self.assertEqual(after[field], before[field])
            security.guard(plan)
        for profile in endpoints:
            self.assertEqual({parts[3] for observed, parts, _, _ in requests if observed == profile},
                             {'pve01', 'pve02', 'pve03'})
        state = next(event['test_state'] for event in events if event.get('@testrun')=='native_signed_encrypted_configuration' and event['type']=='test_state')
        configurations = state['outputs']['machine_configurations']['value']
        for name, configuration in configurations.items():
            documents = list(yaml.safe_load_all(configuration))
            machine = next(doc['machine'] for doc in documents if 'machine' in doc)
            self.assertEqual(machine['install']['image'],
                             f"factory.talos.dev/nocloud-installer-secureboot/{'a'*64}:v1.13.0")
            selected = root / f'{name}.yaml'
            selected.touch(mode=0o600)
            selected.write_text(configuration)
            validation = subprocess.run([TALOSCTL, 'validate', '--config', str(selected), '--mode', 'metal', '--strict'],
                                        capture_output=True, text=True, timeout=45)
            self.assertEqual(validation.returncode, 0, 'Native Talos rejected the configuration; sensitive output withheld')
            volumes = [doc for doc in documents if doc.get('kind')=='VolumeConfig']
            self.assertEqual({doc['name'] for doc in volumes}, {'STATE','EPHEMERAL'})
            for doc in volumes:
                self.assertEqual(doc['encryption']['provider'], 'luks2')
                self.assertEqual(doc['encryption']['keys'], [{'slot':0,'tpm':{'checkSecurebootStatusOnEnroll':True}}])
