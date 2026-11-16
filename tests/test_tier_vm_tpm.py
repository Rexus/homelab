"""Native provider plans for fresh per-VM TPM identities across the Linux roots."""

import copy
import json
import os
import shutil
import subprocess
import unittest

import hcl2

from tier_repo_test_support import TierRepositoryTestCase


class VmTpmStarters(TierRepositoryTestCase):
    def test_fresh_starters_select_tpm_without_changing_local_configs_or_state_on_refresh(self):
        self.generate()
        retained = {}
        services = 0
        builders = 0
        for tier in range(3):
            repo = self.root / f'verify-tier-{tier}'
            for deployment in sorted((repo / 'terraform/deployments').iterdir()):
                main = deployment / 'main.tf'
                if not main.is_file() or 'each.value.tpm' not in main.read_text():
                    continue
                example = deployment / 'terraform.tfvars.example'
                values = hcl2.loads(example.read_text(), serialization_options=hcl2.SerializationOptions(
                    strip_string_quotes=True, with_comments=False,
                ))
                guests = values['vm_instances']
                self.assertTrue(guests)
                self.assertTrue(all('tpm' not in guest for guest in values.get('lxc_instances', {}).values()))
                if deployment.name in ('immutable-template', 'template-refresh'):
                    builders += 1
                    self.assertTrue(all(guest.get('tpm') is None for guest in guests.values()))
                    continue
                services += 1
                self.assertTrue(all(guest['tpm'] == {} for guest in guests.values()), example)
                self.assertIn('tpm = null to opt out (legacy default)', example.read_text())
                self.assertIn('tpm_state_present = false', example.read_text())
                local = deployment / 'terraform.tfvars'
                local.write_text('# Existing site selection stays local.\nvm_instances = {}\n')
                state = repo / f'.terraform/state/{deployment.name}/prod/terraform.tfstate'
                state.parent.mkdir(parents=True)
                state.write_text(json.dumps({'version': 4, 'serial': 7, 'resources': [],
                                             'outputs': {'recovery': {'value': 'preserve'}}}))
                retained.update({local: local.read_bytes(), state: state.read_bytes()})
        self.assertEqual((services, builders), (14, 2))
        self.generate('--refresh')
        for path, original in retained.items():
            self.assertEqual(path.read_bytes(), original, path)


@unittest.skipUnless(os.name != 'nt' and shutil.which('terraform'), 'Requires native Terraform')
class VmTpm(TierRepositoryTestCase):
    def terraform(self, fixture, *arguments, success=True):
        result = subprocess.run(['terraform', *arguments], cwd=fixture, text=True,
                                capture_output=True, timeout=60)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def fixture(self, deployment):
        fixture = self.root / ('tpm-' + deployment.parts[-3] + '-' + deployment.name)
        fixture.mkdir()
        hosts = fixture / 'hosts.yml'
        group = 'cluster_endpoint' if deployment.name == 'cluster-endpoint' else 'guests'
        hosts.write_text(json.dumps({'all': {'children': {group: {'hosts': {
            'guest-1': {}, 'guest-2': {},
        }}}}}))
        group_vars = fixture / 'all.yml'
        group_vars.write_text(json.dumps({'platform_host_ips': {'guest-1': 'dhcp', 'guest-2': 'dhcp'}}))
        inputs = {
            'source': os.path.relpath(deployment, fixture), 'ansible_inventory_path': str(hosts),
            'ansible_group_vars_paths': [str(group_vars)],
            'proxmox_api_url': 'https://127.0.0.1:9/',
            'proxmox_api_token_id': 'fixture@pve!plan', 'proxmox_api_token_secret': 'fixture-only',
            'proxmox_storage_classes': {'local': {'vm_disk': 'disk-store'}},
            'default_platform_node_name': 'node-a', 'default_linux_vm_template_id': 9101,
            'default_vm_network_zone_key': 'application',
            'network_zones': {'application': {'bridge': 'services', 'cidr_ipv4': '192.0.2.0/24'}},
            'proxmox_template_catalog': {'9101': {
                'title': 'Approved Linux image', 'family': 'redhat', 'node_name': 'node-a',
                'bios': 'ovmf', 'machine': 'q35', 'scsi_hardware': 'virtio-scsi-single',
                'efi_pre_enrolled_keys': False, 'tpm_state_present': False,
            }},
            'vm_instances': {'guest-1': {'vm_id': 701, 'disk_size_gb': 30}},
        }
        if deployment.name == 'cluster-endpoint':
            group_vars.write_text(json.dumps({'platform_host_ips': {
                'guest-1': '192.0.2.10', 'guest-2': '192.0.2.11',
            }}))
            inputs['network_zones']['application']['gateway_ipv4'] = '192.0.2.1'
            inputs['vm_instances']['guest-1']['proxmox_node_name'] = 'node-a'
            inputs['vm_instances']['guest-2'] = {
                'vm_id': 702, 'disk_size_gb': 30, 'proxmox_node_name': 'node-b',
            }
        configuration = {
            'terraform': {'required_providers': {
                'proxmox': {'source': 'bpg/proxmox', 'version': '= 0.112.0'},
                'external': {'source': 'hashicorp/external', 'version': '= 2.4.2'},
            }},
            'module': {'deployment': inputs},
        }
        self.write(fixture, configuration)
        self.terraform(fixture, 'init', '-input=false')
        return fixture, configuration, inputs

    def write(self, fixture, configuration):
        (fixture / 'main.tf.json').write_text(json.dumps(configuration))

    def plan(self, fixture):
        self.terraform(fixture, 'plan', '-refresh=false', '-input=false', '-out=review.tfplan')
        result = json.loads(self.terraform(fixture, 'show', '-json', 'review.tfplan'))
        return next(item['change'] for item in result['resource_changes'] if item['address'] ==
                    'module.deployment.module.vms["guest-1"].proxmox_virtual_environment_vm.this')

    def test_every_linux_root_passes_creation_only_tpm_and_null_keeps_no_tpm(self):
        self.generate()
        count = 0
        for tier in range(3):
            deployments = self.root / f'verify-tier-{tier}/terraform/deployments'
            for deployment in sorted(deployments.iterdir()):
                main = deployment / 'main.tf'
                if not main.is_file() or 'each.value.firmware' not in main.read_text():
                    continue
                with self.subTest(tier=tier, setup=deployment.name):
                    count += 1
                    fixture, configuration, inputs = self.fixture(deployment)
                    absent = self.plan(fixture)
                    self.assertEqual(absent['actions'], ['create'])
                    self.assertEqual(absent['after']['tpm_state'], [])
                    guest = inputs['vm_instances']['guest-1']
                    guest['tpm'] = {'datastore_id': 'tpm-store'}
                    self.write(fixture, configuration)
                    selected = self.plan(fixture)
                    self.assertEqual(selected['actions'], ['create'])
                    self.assertEqual(selected['after']['tpm_state'],
                                     [{'version': 'v2.0', 'datastore_id': 'tpm-store'}])
                    # An empty selection inherits VM-image storage rather than local-lvm.
                    guest['tpm'] = {}
                    self.write(fixture, configuration)
                    inherited = self.plan(fixture)
                    self.assertEqual(inherited['after']['tpm_state'],
                                     [{'version': 'v2.0', 'datastore_id': 'disk-store'}])
        self.assertEqual(count, 16, 'Update the test coverage when adding a Linux deployment root.')

    def test_tpm_rejects_unverified_or_populated_sources_invalid_values_and_template_reuse(self):
        self.generate()
        for tier, setup in enumerate(('foundation', 'development', 'cache')):
            deployment = self.root / f'verify-tier-{tier}/terraform/deployments/{setup}'
            fixture, configuration, inputs = self.fixture(deployment)
            baseline = copy.deepcopy(inputs)
            cases = (
                ('version', {'tpm': {'version': 'v1.2'}}, False, 'version v2.0 only'),
                ('storage', {'tpm': {'datastore_id': ''}}, False, 'non-empty Proxmox datastore ID'),
                ('unverified', {'tpm': {}}, None, 'Never clone a populated template TPM'),
                ('populated', {'tpm': {}}, True, 'Never clone a populated template TPM'),
                ('implicit copy', {}, True, 'Never clone a populated template TPM'),
                ('template', {'tpm': {}, 'template': True}, False, 'Never clone a populated template TPM'),
            )
            for name, guest, source_tpm, message in cases:
                with self.subTest(tier=tier, case=name):
                    inputs.clear()
                    inputs.update(copy.deepcopy(baseline))
                    inputs['vm_instances']['guest-1'].update(guest)
                    if source_tpm is None:
                        inputs['proxmox_template_catalog']['9101'].pop('tpm_state_present')
                    else:
                        inputs['proxmox_template_catalog']['9101']['tpm_state_present'] = source_tpm
                    # A tag/catalog alias cannot qualify the actual source's TPM identity.
                    inputs['proxmox_template_catalog']['9102'] = copy.deepcopy(
                        baseline['proxmox_template_catalog']['9101'])
                    inputs['vm_instances']['guest-1']['template_catalog_id'] = 9102
                    self.write(fixture, configuration)
                    result = self.terraform(fixture, 'plan', '-refresh=false', '-input=false',
                                            '-no-color', success=False)
                    self.assertIn(message, result)
