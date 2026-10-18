"""Validate CA-specific Terraform input types without providers or infrastructure access."""

import json
import os
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class CertificateAuthorityCompute(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('terraform'), 'Requires Terraform on Linux/WSL')
    def test_native_foundation_types_keep_old_inputs_and_forward_data_disks(self):
        self.parent.mkdir(parents=True)
        shutil.copyfile(UPSTREAM / 'tier-0/terraform/deployments/foundation/variables.tf',
                        self.parent / 'variables.tf')
        (self.parent / 'main.tf.json').write_text(json.dumps({
            'output': {'guests': {'value': '${var.vm_instances}'}},
        }))
        self.terraform('init', '-backend=false', '-input=false')
        inputs = dict(proxmox_storage_classes={}, vm_instances={
            'old-guest': {'disk_size_gb': 30},
            'ca-1': {'disk_size_gb': 30, 'template_vm_id': 9103, 'extra_disks': [
                {'interface': 'scsi1', 'size_gb': 40, 'storage_class': 'local', 'iothread': True},
            ]},
        })
        (self.parent / 'inputs.tfvars.json').write_text(json.dumps(inputs))
        self.terraform('apply', '-auto-approve', '-input=false', '-var-file=inputs.tfvars.json')
        guests = json.loads(self.terraform('output', '-json', 'guests').stdout)
        self.assertEqual(guests['old-guest']['extra_disks'], [])
        self.assertEqual(guests['ca-1']['template_vm_id'], 9103)
        disk = guests['ca-1']['extra_disks'][0]
        self.assertEqual(disk['interface'], 'scsi1')
        self.assertEqual(disk['size_gb'], 40)
        self.assertTrue(disk['iothread'])

    @unittest.skipUnless(os.name != 'nt' and shutil.which('terraform'), 'Requires Terraform on Linux/WSL')
    def test_native_template_validation_accepts_debian_and_rejects_unknown_families(self):
        self.parent.mkdir(parents=True)
        shutil.copyfile(UPSTREAM / 'tier-0/terraform/modules/proxmox_templates/variables.tf',
                        self.parent / 'variables.tf')
        (self.parent / 'main.tf.json').write_text(json.dumps({
            'output': {'images': {'value': '${var.images}'}},
        }))
        self.terraform('init', '-backend=false', '-input=false')
        image = dict(family='debian', release='12.0-build-1', vm_id=9103, name='debian-issuer', node_name='pve01',
                     datastore_id='local-lvm', image_datastore_id='local', bridge='control',
                     image_path='/approved/debian.qcow2', sha256='a' * 64)
        inputs = self.parent / 'inputs.tfvars.json'
        inputs.write_text(json.dumps({'images': {'debian': image}}))
        self.terraform('apply', '-auto-approve', '-input=false', '-var-file=inputs.tfvars.json')
        image['family'] = 'unknown'
        inputs.write_text(json.dumps({'images': {'unknown': image}}))
        result = subprocess.run(['terraform', f'-chdir={self.parent}', 'plan', '-input=false',
                                 '-var-file=inputs.tfvars.json'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Supported image families', result.stdout + result.stderr)

    def terraform(self, *args):
        result = subprocess.run(['terraform', f'-chdir={self.parent}', *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result
