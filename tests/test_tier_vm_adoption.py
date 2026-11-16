"""Native provider plans for imported VMs, without contacting a Proxmox API."""

import copy
import json
import os
import re
import shutil
import subprocess
import unittest
import uuid

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipUnless(os.name != 'nt' and shutil.which('terraform'), 'Requires native Terraform')
class VmAdoption(TierRepositoryTestCase):
    def run_terraform(self, directory, *arguments):
        result = subprocess.run(['terraform', *arguments], cwd=directory, text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def plan(self, directory):
        self.run_terraform(directory, 'plan', '-refresh=false', '-input=false', '-out=review.tfplan')
        result = json.loads(self.run_terraform(directory, 'show', '-json', 'review.tfplan'))
        return next(item for item in result['resource_changes'] if item['address'] ==
                    'module.vm.proxmox_virtual_environment_vm.this')['change']

    def test_imported_clone_keeps_inherited_attributes_and_managed_changes_remain_visible(self):
        self.generate()
        for tier in range(3):
            with self.subTest(tier=tier):
                fixture = self.root / f'adoption-plan-{tier}'
                fixture.mkdir()
                module = self.root / f'verify-tier-{tier}/terraform/modules/vm'
                inventory = fixture / 'hosts.yml'
                inventory.write_text(json.dumps({'all': {'children': {'guests': {'hosts': {'guest-1': {}}}}}}))
                group_vars = fixture / 'all.yml'
                group_vars.write_text(json.dumps({'platform_host_ips': {'guest-1': 'dhcp'}}))
                catalog_entry = {'title': 'Approved Linux image', 'family': 'redhat', 'node_name': 'node-a',
                                 'bios': 'ovmf', 'machine': 'q35', 'scsi_hardware': 'virtio-scsi-single',
                                 'efi_pre_enrolled_keys': False}
                configuration = {
                    'terraform': {'required_providers': {'proxmox': {
                        'source': 'bpg/proxmox', 'version': '= 0.112.0'},
                        'external': {'source': 'hashicorp/external', 'version': '= 2.4.2'}}},
                    'provider': {'proxmox': {'endpoint': 'https://127.0.0.1:9/',
                                              'api_token': 'fixture@pve!plan=fixture-only',
                                              'insecure': False}},
                    'module': {'environment': {
                        'source': str(self.root / f'verify-tier-{tier}/terraform/modules/environment_guests'),
                        'ansible_inventory_path': str(inventory), 'ansible_group_vars_paths': [str(group_vars)],
                        'default_platform_node_name': 'node-a', 'default_vm_template_id': 9101,
                        'proxmox_template_catalog': {'9101': catalog_entry},
                        'network_zones': {'application': {'bridge': 'services', 'cidr_ipv4': '192.0.2.0/24'}},
                        'vm_instances': {'guest-1': {'disk_size_gb': 30}},
                    }, 'vm': {
                        'source': str(module), 'name': 'guest-1', 'node_name': 'node-a',
                        'vm_id': 701, 'template_vm_id': 9101, 'template_node_name': 'node-a',
                        'bridge': 'services', 'disk_size_gb': 30, 'memory': 2048,
                        'datastore_id': 'disk-store', 'initialization_datastore_id': 'disk-store',
                        'firmware': '${module.environment.vm_instances["guest-1"].firmware}',
                        'extra_disks': [{'interface': 'scsi1', 'size_gb': 100}],
                    }},
                }
                main = fixture / 'main.tf.json'
                main.write_text(json.dumps(configuration))
                self.run_terraform(fixture, 'init', '-input=false')
                creation = self.plan(fixture)
                self.assertEqual(creation['actions'], ['create'])
                self.assertEqual(creation['after']['clone'][0]['vm_id'], 9101)
                self.assertTrue(creation['after']['clone'][0]['full'])
                self.assertEqual(creation['after']['bios'], 'ovmf')
                self.assertEqual(creation['after']['machine'], 'q35')
                self.assertEqual(creation['after']['scsi_hardware'], 'virtio-scsi-single')
                self.assertEqual(len(creation['after']['efi_disk']), 1)
                schema = json.loads(self.run_terraform(fixture, 'providers', 'schema', '-json'))
                version = schema['provider_schemas']['registry.terraform.io/bpg/proxmox'][
                    'resource_schemas']['proxmox_virtual_environment_vm']['version']
                observed = copy.deepcopy(creation['after'])
                observed.update(id='701', clone=[], description='Approved source image',
                                operating_system=[{'type': 'l26'}], serial_device=[{'device': 'socket'}],
                                boot_order=['scsi0', 'net0'],
                                tpm_state=[{'datastore_id': 'disk-store', 'version': 'v2.0'}])
                for index, disk in enumerate(observed['disk']):
                    disk.update(file_format='raw', path_in_datastore=f'vm-701-disk-{index + 1}')
                observed['efi_disk'][0]['file_format'] = 'raw'
                state = {'version': 4, 'terraform_version': '1.16.6', 'serial': 1,
                         'lineage': str(uuid.uuid4()), 'outputs': {}, 'resources': [{
                             'module': 'module.vm', 'mode': 'managed',
                             'type': 'proxmox_virtual_environment_vm', 'name': 'this',
                             'provider': 'provider["registry.terraform.io/bpg/proxmox"]',
                             'instances': [{'schema_version': version, 'attributes': observed}],
                         }]}
                (fixture / 'terraform.tfstate').write_text(json.dumps(state))
                source = module / 'main.tf'
                current = source.read_text()
                source.write_text(re.sub(r'ignore_changes\s*=\s*\[[^\]]+\]',
                                         'ignore_changes = [node_name]', current, count=1))
                try:
                    previous = self.plan(fixture)
                    self.assertIn('delete', previous['actions'])
                    self.assertIn('create', previous['actions'])
                    self.assertTrue(any(path[0] == 'clone' for path in previous['replace_paths']))
                finally:
                    source.write_text(current)
                # Omitted TPM configuration must not remove an adopted guest's TPM identity.
                source.write_text(current.replace('boot_order, tpm_state,', 'boot_order,'))
                try:
                    unprotected_tpm = self.plan(fixture)
                    self.assertEqual(unprotected_tpm['after']['tpm_state'], [])
                finally:
                    source.write_text(current)
                adopted = self.plan(fixture)
                self.assertNotIn('delete', adopted['actions'])
                self.assertNotIn('create', adopted['actions'])
                for attribute in ('description', 'operating_system', 'serial_device', 'efi_disk',
                                  'boot_order', 'tpm_state'):
                    self.assertEqual(adopted['after'][attribute], observed[attribute], attribute)
                for actual, original in zip(adopted['after']['disk'], observed['disk'], strict=True):
                    for attribute in ('interface', 'datastore_id', 'path_in_datastore', 'file_format',
                                      'size', 'cache', 'discard', 'iothread', 'ssd', 'backup', 'replicate'):
                        self.assertEqual(actual[attribute], original[attribute], attribute)
                self.assertEqual(adopted['after']['bios'], 'ovmf')
                self.assertEqual(adopted['after']['machine'], 'q35')
                self.assertEqual(adopted['after']['scsi_hardware'], 'virtio-scsi-single')
                hardware = {field: catalog_entry[field] for field in
                            ('bios', 'machine', 'scsi_hardware', 'efi_pre_enrolled_keys')}
                catalog_entry.update(bios='seabios', machine='pc', scsi_hardware='lsi')
                main.write_text(json.dumps(configuration))
                changed_profile = self.plan(fixture)
                self.assertNotIn('delete', changed_profile['actions'])
                self.assertNotIn('create', changed_profile['actions'])
                for attribute in ('bios', 'machine', 'scsi_hardware', 'efi_disk', 'boot_order', 'tpm_state'):
                    self.assertEqual(changed_profile['after'][attribute], observed[attribute], attribute)
                catalog_entry.update(hardware)
                configuration['module']['vm']['memory'] = 4096
                main.write_text(json.dumps(configuration))
                resized = self.plan(fixture)
                self.assertEqual(resized['actions'], ['update'])
                self.assertEqual(resized['after']['memory'][0]['dedicated'], 4096)
                configuration['module']['vm']['extra_disks'][0]['size_gb'] = 140
                main.write_text(json.dumps(configuration))
                storage_growth = self.plan(fixture)
                self.assertEqual(storage_growth['actions'], ['update'])
                self.assertEqual(storage_growth['after']['disk'][1]['size'], 140)
                for field in hardware:
                    catalog_entry.pop(field)
                main.write_text(json.dumps(configuration))
                missing_firmware = self.plan(fixture)
                for attribute in ('bios', 'machine', 'scsi_hardware', 'efi_disk', 'boot_order', 'tpm_state'):
                    self.assertEqual(missing_firmware['after'][attribute], observed[attribute], attribute)
                catalog_entry.update(hardware)
                catalog_entry.update(bios='seabios', machine='pc', scsi_hardware='lsi')
                configuration['module']['vm']['vm_id'] = 702
                main.write_text(json.dumps(configuration))
                renumbered = self.plan(fixture)
                self.assertIn('delete', renumbered['actions'])
                self.assertIn('create', renumbered['actions'])
                self.assertEqual(renumbered['after']['bios'], 'seabios')
                self.assertEqual(renumbered['after']['machine'], 'pc')
                self.assertEqual(renumbered['after']['scsi_hardware'], 'lsi')
                self.assertFalse(renumbered['after']['efi_disk'])
