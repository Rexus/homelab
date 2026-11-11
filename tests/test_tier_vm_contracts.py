"""Configuration must reach VM resources without typed boundaries dropping fields."""

from pathlib import Path

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class VmConfigurationFlow(TierRepositoryTestCase):
    def test_every_guest_root_preserves_the_environment_contract_and_resource_bindings(self):
        import hcl2
        self.generate()
        fields = ('full_clone', 'firmware', 'initialization_datastore_id', 'nic_firewall',
                  'extra_disks', 'started', 'template', 'stop_on_destroy')

        def load(path):
            return hcl2.loads(path.read_text(), serialization_options=hcl2.SerializationOptions(
                strip_string_quotes=True, with_comments=False))

        for base, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            checked = 0
            for tier in range(3):
                owner = base / f'{prefix}tier-{tier}/terraform'
                environment = load(owner / 'modules/environment_guests/variables.tf')
                schema = next(item['vm_instances']['type'] for item in environment['variable']
                              if 'vm_instances' in item)
                for main in (owner / 'deployments').glob('*/main.tf'):
                    modules = {name: value for item in load(main).get('module', []) for name, value in item.items()}
                    if modules.get('vms', {}).get('for_each') != '${module.environment.vm_instances}':
                        continue
                    root_inputs = load(main.parent / 'variables.tf')
                    root_schema = next(item['vm_instances']['type'] for item in root_inputs['variable']
                                       if 'vm_instances' in item)
                    self.assertEqual(root_schema, schema, main)
                    for name in fields + (('usb_devices',) if tier == 0 else ()):
                        self.assertEqual(modules['vms'][name], '${each.value.' + name + '}', (main, name))
                    checked += 1
            self.assertEqual(checked, 16)
