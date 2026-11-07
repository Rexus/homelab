"""Publication defaults and native adoption discovery, without a live Proxmox API."""

import json
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import shutil
import ssl
import subprocess
import threading
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class TemplatePublication(TierRepositoryTestCase):
    def test_catalog_common_fields_and_implementation_are_not_duplicated(self):
        catalog = yaml.safe_load((UPSTREAM / 'tier-0/templates/proxmox.yml.example').read_text())
        self.assertEqual(catalog['all']['storage_class'], 'shared')
        self.assertEqual(catalog['all']['vlan_id'], 10)
        self.assertFalse({'scsi_hardware', 'nic_mtu', 'nic_firewall', 'qemu_agent'} & catalog['all'].keys())
        shared = (UPSTREAM / 'shared/templates/proxmox-catalog.tfvars').read_text()
        self.assertNotIn('family    = "alma"', shared)
        self.assertNotIn('family    = "rocky"', shared)
        for build in catalog['templates'].values():
            self.assertFalse({'datastore_id', 'image_datastore_id', 'qemu_agent', 'bios', 'bridge'} & build.keys())
            self.assertEqual(build['tags'], [])
        root = UPSTREAM / 'tier-0/terraform/deployments/templates'
        self.assertIn('merge(try(local.catalog.all, {}), image)', (root / 'main.tf').read_text())
        imports = (root / 'imports.tf').read_text()
        for target in ('proxmox_virtual_environment_file.image', 'proxmox_virtual_environment_vm.template'):
            self.assertIn(f'to       = module.templates.{target}[each.key]', imports)
        self.assertNotIn('local-exec', imports)

    @unittest.skipUnless(shutil.which('terraform') and shutil.which('openssl') and os.name != 'nt',
                         'Requires native Terraform and OpenSSL under Linux/WSL')
    def test_native_root_merges_overrides_and_discovers_only_exact_imports(self):
        terraform = self.root / 'tier-0/terraform'
        root = terraform / 'deployments/templates'
        shutil.copytree(UPSTREAM / 'tier-0/terraform/deployments/templates', root)
        # Terraform mocks cannot perform real import refreshes. Exercise the actual discovery
        # and safety gate here; import declarations are validated by the unmodified root.
        imports = root / 'imports.tf'
        discovery = imports.read_text().split('\nimport {', 1)[0]
        # Framework nested-list mocks cannot populate files. Read those via the pinned
        # provider against a loopback-only HTTPS fixture; all resource operations stay mocked.
        discovery = discovery.replace('data "proxmox_files" "existing" {',
                                       'data "proxmox_files" "existing" {\n  provider = proxmox.files')
        imports.write_text(discovery)
        module = terraform / 'modules/proxmox_templates'
        shutil.copytree(UPSTREAM / 'tier-0/terraform/modules/proxmox_templates', module)
        # Observe the actual provider's disk model without adding a product output.
        with (module / 'outputs.tf').open('a') as output:
            output.write('''
output "test_disk_interfaces" {
  value = { for key, vm in proxmox_virtual_environment_vm.template : key => [for disk in vm.disk : disk.interface] }
}
output "test_template_tags" {
  value = { for key, vm in proxmox_virtual_environment_vm.template : key => vm.tags }
}
output "test_cpu_architectures" {
  value = { for key, vm in proxmox_virtual_environment_vm.template : key => vm.cpu[0].architecture }
}
''')
        tests = root / 'tests'
        tests.mkdir()
        fixture = module / 'tests/fixtures/template-image.qcow2'
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
        catalog = {
            'all': dict(node_name='pve01', storage_class='shared', image_datastore_id='local',
                        bridge='control', vlan_id=10, family='redhat', bios='ovmf',
                        tags=['approved'], cloud_init_drive=True, memory_mb=4096, disk_size_gb=32),
            'templates': {
                'alma': dict(distribution='alma', release='10.0', vm_id=9100, name='alma-template',
                             image_path=str(fixture), sha256=digest, image_file_name='manual.qcow2'),
                'rocky': dict(distribution='rocky', release='10.0', vm_id=9101, name='rocky-template',
                              image_path=str(fixture), sha256=digest, datastore_id='override',
                              qemu_agent=False, vlan_id=20),
            },
        }
        path = tests / 'catalog.yml'
        path.write_text(yaml.safe_dump(catalog))
        cert, key = tests / 'fixture.crt', tests / 'fixture.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)

        requests = []
        cloud_init_type = 'nocloud'

        class FilesApi(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                api_path = self.path.split('?', 1)[0]
                if api_path.startswith('/api2/json/nodes/pve01/storage/local/content'):
                    data = [dict(volid='local:import/manual.qcow2', format='qcow2', content='import', size=12)]
                elif api_path == '/api2/json/version':
                    data = dict(version='9.2', release='9.2')
                elif api_path == '/api2/json/cluster/resources':
                    data = [dict(vmid=9100, node='pve01', name='alma-template', template=1, status='stopped', type='qemu')]
                elif api_path == '/api2/json/nodes':
                    data = [dict(node='pve01', status='online')]
                elif api_path == '/api2/json/nodes/pve01/qemu':
                    data = [dict(vmid=9100, name='alma-template', template=1, status='stopped')]
                elif api_path == '/api2/json/nodes/pve01/qemu/9100/config':
                    data = dict(name='alma-template', template=1, bios='ovmf', cores=2,
                                sockets=1, cpu='x86-64-v3', memory=4096, balloon=0,
                                agent='enabled=1', scsihw='virtio-scsi-single', ostype='l26',
                                boot='order=scsi0', serial0='socket', onboot=0,
                                ide2='ceph-vm:vm-9100-cloudinit,media=cdrom', ipconfig0='ip=dhcp',
                                tags='alma;approved;template;tier-0',
                                description=f'redhat 10.0; sha256={digest}',
                                scsi0='ceph-vm:base-9100-disk-0,discard=on,iothread=1,size=32G',
                                efidisk0='ceph-vm:base-9100-disk-1,efitype=4m,pre-enrolled-keys=0,size=4M',
                                net0='virtio=02:00:00:00:00:01,bridge=control,tag=10,firewall=1,mtu=1500',
                                unused0='ceph-vm:base-9100-disk-9')
                    if cloud_init_type is not None:
                        data['citype'] = cloud_init_type
                elif api_path == '/api2/json/nodes/pve01/qemu/9100/status/current':
                    data = dict(status='stopped', qmpstatus='stopped')
                elif api_path.startswith('/api2/json/nodes/pve01/storage/ceph-vm/content/'):
                    data = dict(format='raw', size=(4 * 1024**2 if 'disk-1' in api_path else 32 * 1024**3),
                                content='images', volid=api_path.rsplit('/', 1)[-1])
                elif api_path == '/api2/json/pools':
                    data = []
                else:
                    self.send_error(404)
                    return
                body = json.dumps(dict(data=data)).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), FilesApi)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        root.joinpath('fixture-provider.tf').write_text(f'''provider "proxmox" {{
  alias = "files"
  endpoint = "https://127.0.0.1:{server.server_port}/"
  api_token = "fixture@pve!template=fixture-not-a-secret"
  insecure = false
}}
''')
        # Mock import reads and verify discovery independently from real infrastructure.
        test = '''mock_provider "proxmox" {}
variables {
  catalog_file = CATALOG_PATH
  proxmox_storage_classes = { shared = { vm_disk = "ceph-vm" } }
}
run "resolve_common_and_build_overrides" {
  command = plan
  assert {
    condition = local.images.alma.datastore_id == "ceph-vm" && local.images.rocky.datastore_id == "override"
    error_message = "A build datastore must override the shared class."
  }
  assert {
    condition = local.images.alma.vlan_id == 10 && local.images.rocky.vlan_id == 20
    error_message = "A shared catalog VLAN must reach every build unless that build overrides it."
  }
  assert {
    condition = module.templates.catalog.alma.distribution == "alma" && length(local.vm_imports) == 0
    error_message = "Normal plans must not discover/adopt resources."
  }
}
run "discover_matching_template_and_file" {
  command = plan
  variables { adopt_existing = true }
  override_data {
    target = data.proxmox_virtual_environment_vms.existing[0]
    values = { vms = [
      { vm_id = 9100, name = "alma-template", node_name = "pve01", template = true, status = "stopped", tags = [] },
      { vm_id = 9999, name = "unrelated", node_name = "pve01", template = false, status = "running", tags = [] }
    ] }
  }
  assert {
    condition = length(local.vm_imports) == 1 && try(local.vm_imports.alma, "") == "pve01/9100" && length(local.file_imports) == 1 && try(local.file_imports.alma, "") == "pve01/local:import/manual.qcow2"
    error_message = "Adoption must select only the exact catalog VMID and image basename."
  }
}
'''.replace('CATALOG_PATH', json.dumps(str(path)))
        matching = test[test.index('run "discover_matching_template_and_file"'):]
        for name, old, replacement in (
            ('ordinary_vm', 'template = true', 'template = false'),
            ('running_template', 'status = "stopped"', 'status = "running"'),
            ('wrong_name', 'name = "alma-template"', 'name = "unrelated-template"'),
            ('wrong_node', 'node_name = "pve01"', 'node_name = "pve02"'),
        ):
            test += matching.replace('discover_matching_template_and_file', f'reject_{name}').replace(
                old, replacement, 1).replace('command = plan',
                                             'command = plan\n  expect_failures = [output.template_candidates]')
        tests.joinpath('publication.tftest.hcl').write_text(test)
        env = dict(os.environ, TF_IN_AUTOMATION='1', SSL_CERT_FILE=str(cert))
        env.pop('TF_DATA_DIR', None)
        for command in (['init', '-backend=false', '-input=false', '-lockfile=readonly'], ['test']):
            result = subprocess.run(['terraform', f'-chdir={root}', *command, '-no-color'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # Reproduce invalid operator inputs: each diagnostic must name the field and catalog key.
        invalid_catalog = dict(catalog, templates={key: dict(image) for key, image in catalog['templates'].items()})
        invalid_catalog['templates']['alma']['release'] = 'REPLACE_WITH_EXACT_RELEASE_AND_BUILD'
        invalid_catalog['templates']['rocky']['vm_id'] = 99
        invalid_path = tests / 'invalid-catalog.yml'
        invalid_path.write_text(yaml.safe_dump(invalid_catalog))
        tests.joinpath('publication.tftest.hcl').write_text('''mock_provider "proxmox" {}
run "invalid_operator_inputs" {
  command = plan
  variables {
    catalog_file = CATALOG_PATH
    proxmox_storage_classes = { shared = { vm_disk = "ceph-vm" } }
  }
}
'''.replace('CATALOG_PATH', json.dumps(str(invalid_path))))
        result = subprocess.run(['terraform', f'-chdir={root}', 'test', '-no-color'],
                                env=env, capture_output=True, text=True)
        diagnostics = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, diagnostics)
        for expected in ('Invalid release:', 'alma.release=', 'REPLACE_WITH_EXACT_RELEASE_AND_BUILD',
                         'Invalid vm_id:', 'rocky.vm_id=99'):
            self.assertIn(expected, diagnostics)

        # Exercise real file and VM import refreshes against the same isolated provider API.
        imports.write_text((UPSTREAM / 'tier-0/terraform/deployments/templates/imports.tf').read_text())
        tests.joinpath('publication.tftest.hcl').write_text((root / 'fixture-provider.tf').read_text() + '''run "native_resource_imports" {
  command = plan
  providers = { proxmox = proxmox.files }
  variables {
    catalog_file = CATALOG_PATH
    proxmox_storage_classes = { shared = { vm_disk = "ceph-vm" } }
    adopt_existing = true
  }
  assert {
    condition = length(local.file_imports) == 1 && local.file_imports.alma == "pve01/local:import/manual.qcow2" && length(local.vm_imports) == 1
    error_message = "The actual provider must accept the discovered file and VM identities for native import."
  }
  assert {
    condition = length(module.templates.test_disk_interfaces.alma) == 1 && module.templates.test_disk_interfaces.alma[0] == "scsi0"
    error_message = "A retained unused rollback disk must not enter Terraform's managed disk list."
  }
  assert {
    condition = toset(module.templates.test_template_tags.alma) == toset(["el10", "alma", "x86-64-v3", "cloud-init", "approved"])
    error_message = "Import must replace legacy template/tier tags with reusable image metadata without replacing the VM."
  }
  assert {
    condition = module.templates.test_cpu_architectures.alma == ""
    error_message = "Adoption must not introduce an explicit root-only CPU architecture override on an implicit x86 guest."
  }
}
'''.replace('CATALOG_PATH', json.dumps(str(path))))
        # Both explicit publications and GUI defaults must import without replacement.
        # prevent_destroy makes the test fail if an import tries to recreate the VM.
        for cloud_init_type in ('nocloud', None):
            result = subprocess.run(['terraform', f'-chdir={root}', 'test', '-no-color'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0,
                             f'citype={cloud_init_type!r}\n' + result.stdout + result.stderr + str(requests))


if __name__ == '__main__':
    unittest.main()
