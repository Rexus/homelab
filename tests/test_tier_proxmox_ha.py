"""Explicit existing-VM HA selection, native schema and pre-mutation validation."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/proxmox_ha'
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('ansible-doc')
RESOURCES = {'k8ctl-1': {'vmid': 101}, 'k8ctl-2': {'vmid': 102}, 'k8ctl-3': {'vmid': 103}}
RULES = {'control-plane-separate': dict(type='resource-affinity', affinity='negative',
                                     resources=list(RESOURCES))}


class ProxmoxHAInputs(TierRepositoryTestCase):
    def test_generated_payload_and_selected_prechecks_are_complete(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0')
        owner = self.root / 'verify-tier-0'
        for source in ROLE.rglob('*.yml'):
            relative = source.relative_to(UPSTREAM / 'tier-0')
            self.assertEqual((owner / relative).read_bytes(), source.read_bytes())
        path = Path('ansible/playbooks/proxmox-ha.yml')
        self.assertEqual((owner / path).read_bytes(), (UPSTREAM / 'tier-0' / path).read_bytes())
        play = yaml.safe_load((owner / path).read_text())
        self.assertEqual(play[0]['ansible.builtin.import_playbook'], 'control-node.yml')
        self.assertEqual(play[0]['vars'], dict(control_node_setup='proxmox-ha',
                                             control_node_require_terraform=False))
        self.assertEqual(play[1]['hosts'], 'localhost')
        self.assertEqual(play[1]['connection'], 'local')
        selected = yaml.safe_load((owner / 'ansible/playbooks/control-node.yml').read_text())[0]['vars']
        self.assertEqual(selected['control_node_setup_collection_names']['proxmox-ha'], ['community.proxmox'])
        dependencies = yaml.safe_load((self.root / 'verify-shared/ansible/playbooks/tasks/control-node-python.yml')
                                      .read_text())[0]['vars']['control_node_python_catalog']
        clients = next(item for item in dependencies if item['collection'] == 'community.proxmox')
        self.assertEqual(clients['imports'], ['proxmoxer', 'requests'])
        self.assertIn('proxmoxer>=2.3.0', clients['requirements'])
        example = yaml.safe_load((owner / 'ansible/group_vars/proxmox_ha.yml.example').read_text())
        self.assertEqual(example, dict(proxmox_ha_resources={}, proxmox_ha_rules={}))
        self.assertNotIn('proxmox-ha', (owner / '.deployment-setups').read_text().splitlines())
        self.assertFalse((owner / 'terraform/deployments/proxmox-ha').exists())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'Requires native Bash')
    def test_initializer_creates_and_preserves_ha_inputs_without_a_terraform_root(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0', '--repo', 'tier-1')
        owner = self.root / 'verify-tier-0'
        command = ['bash', 'scripts/init-local-files.sh', '--setup', 'proxmox-ha']
        result = subprocess.run(command, cwd=owner, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        local = owner / 'ansible/group_vars/proxmox_ha.yml'
        self.assertEqual(local.read_bytes(), local.with_suffix('.yml.example').read_bytes())
        local.write_text('proxmox_ha_resources: {chosen: {vmid: 123}}\nproxmox_ha_rules: {}\n')
        preserved = local.read_bytes()
        result = subprocess.run(command + ['--env', 'lab'], cwd=owner, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(local.read_bytes(), preserved)
        self.assertTrue((owner / 'ansible/group_vars/proxmox_ha.lab.yml').is_file())
        self.assertFalse((owner / 'terraform/deployments/proxmox-ha').exists())
        rejected = subprocess.run(command, cwd=self.root / 'verify-tier-1', capture_output=True,
                                  text=True, timeout=30)
        self.assertNotEqual(rejected.returncode, 0)

    def test_removal_order_and_native_operations_preserve_guest_lifecycle_ownership(self):
        tasks = yaml.safe_load((ROLE / 'tasks/apply.yml').read_text())
        expected = [
            ('community.proxmox.proxmox_cluster_ha_rules', 'absent'),
            ('community.proxmox.proxmox_cluster_ha_resources', 'present'),
            ('community.proxmox.proxmox_cluster_ha_rules', 'present'),
            ('community.proxmox.proxmox_cluster_ha_resources', 'absent'),
        ]
        actual = []
        for task in tasks:
            module = next(key for key in task if key.startswith('community.proxmox.'))
            actual.append((module, task[module]['state']))
            self.assertTrue(task['no_log'])
        self.assertEqual(actual, expected)
        self.assertFalse(tasks[2][expected[2][0]]['force'])
        self.assertNotIn('proxmox_kvm', (ROLE / 'tasks/apply.yml').read_text())


@unittest.skipUnless(NATIVE, 'Requires prepared Linux Ansible and community.proxmox')
class ProxmoxHANative(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='proxmox-ha-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_ROLES_PATH=str(ROLE.parent),
                        ANSIBLE_LOCALHOST_WARNING='False', ANSIBLE_INVENTORY_UNPARSED_WARNING='False')

    def run_tasks(self, inputs=None, tasks=None, success=True):
        variables = dict(proxmox_ha_resources=deepcopy(RESOURCES), proxmox_ha_rules=deepcopy(RULES))
        variables.update(inputs or {})
        play = [dict(hosts='localhost', connection='local', gather_facts=False, vars=variables,
                     tasks=tasks or [{'ansible.builtin.include_role': dict(name='proxmox_ha', tasks_from='validate')}])]
        path = self.root / 'validate.yml'
        path.write_text(yaml.safe_dump(play, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)], cwd=self.root,
                                env=self.env, capture_output=True, text=True, timeout=45)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        return output

    def test_valid_resource_and_node_rules_and_explicit_removal(self):
        self.run_tasks()
        rules = deepcopy(RULES)
        rules['eligible-hosts'] = dict(type='node-affinity', resources=list(RESOURCES),
                                      nodes=['pve01:10', 'pve02:10', 'pve03:10'], strict=True)
        self.run_tasks(dict(proxmox_ha_rules=rules))
        self.run_tasks(dict(proxmox_ha_resources={'retired': dict(vmid=123, state='absent')},
                            proxmox_ha_rules={'retired-rule': dict(state='absent')}))

    def test_invalid_selections_fail_before_any_api_task(self):
        invalid = [
            dict(proxmox_ha_resources={}),
            dict(proxmox_ha_resources=[]),
            dict(proxmox_ha_resources={'first': '101'}),
            dict(proxmox_ha_resources={'first': dict(vmid=True)}),
            dict(proxmox_ha_resources={'first': dict(vmid='101')}),
            dict(proxmox_ha_resources={'first': dict(vmid=101, max_restart=-1)}),
            dict(proxmox_ha_resources={'first': dict(vmid=101, failback=False)}),
            dict(proxmox_ha_rules={'bad': dict(type='resource-affinity', affinity='negative', resources=['missing'])}),
            dict(proxmox_ha_rules={'bad': dict(type='resource-affinity', affinity='negative', resources=['k8ctl-1'] * 2)}),
            dict(proxmox_ha_rules={'bad': dict(type='resource-affinity', affinity='negative', resources=['k8ctl-1'])}),
            dict(proxmox_ha_rules={'bad': dict(type='resource-affinity', affinity='negative', resources=list(RESOURCES), strict=True)}),
            dict(proxmox_ha_rules={'bad': dict(type='node-affinity', resources=list(RESOURCES), nodes=['pve01', 'pve01:10'])}),
            dict(proxmox_ha_rules={'bad': dict(type='node-affinity', resources=list(RESOURCES), nodes=['pve01'], affinity='negative')}),
            dict(proxmox_ha_resources={**deepcopy(RESOURCES), 'k8ctl-1': dict(vmid=101, state='absent')}),
        ]
        for inputs in invalid:
            with self.subTest(inputs=inputs):
                self.run_tasks(inputs, success=False)

    def test_existing_rule_blocks_unselected_membership_removal_and_type_changes(self):
        task = {'ansible.builtin.include_role': dict(name='proxmox_ha', tasks_from='validate-existing-rule')}
        inputs = dict(proxmox_ha_resources={'chosen': dict(vmid=123, state='absent')},
                      proxmox_ha_rules={}, proxmox_ha_resolved_resources={'chosen': 'vm:123'},
                      proxmox_ha_existing_rule=dict(rule='outside', type='resource-affinity', resources=['vm:123']))
        self.run_tasks(inputs, [task], success=False)
        inputs['proxmox_ha_rules'] = {'outside': dict(state='absent')}
        self.run_tasks(inputs, [task])
        inputs['proxmox_ha_rules'] = {'outside': dict(type='node-affinity')}
        self.run_tasks(inputs, [task], success=False)
        inputs['proxmox_ha_resources'] = {'chosen': dict(vmid=123)}
        inputs['proxmox_ha_existing_rule'].update(type='node-affinity', affinity='negative')
        self.run_tasks(inputs, [task], success=False)
        inputs['proxmox_ha_existing_rule']['affinity'] = 'positive'
        self.run_tasks(inputs, [task])

    def test_native_client_honors_the_https_endpoint_port(self):
        api = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())[-1]['vars']['proxmox_ha_api_defaults']
        for endpoint, port in (('https://api.example.com', 443), ('https://pve.example.com:8006', 8006),
                               ('https://api.example.com:8443', 8443)):
            with self.subTest(endpoint=endpoint):
                self.run_tasks(dict(proxmox_ha_endpoint=endpoint), [{
                    'ansible.builtin.assert': {'that': [f'selected_port | int == {port}']},
                    'vars': {'selected_port': api['api_port']},
                }])

    def test_name_resolution_deleted_vm_removal_and_duplicate_vm_bindings(self):
        resolve = yaml.safe_load((ROLE / 'tasks/resolve-resource.yml').read_text())
        # Replace only the read-only API query. Run the actual resolution assertions/fact.
        resolved_info = dict(proxmox_vms=[dict(vmid=101, template=False)])
        resolve[0] = {'ansible.builtin.set_fact': dict(proxmox_ha_vm_info=resolved_info)}
        inputs = dict(proxmox_ha_resource=dict(key='k8ctl-1', value={}), proxmox_ha_resolved_resources={})
        expected = {'ansible.builtin.assert': {'that': ["proxmox_ha_resolved_resources == {'k8ctl-1': 'vm:101'}"]}}
        self.run_tasks(inputs, resolve + [expected])
        inputs['proxmox_ha_resource']['value'] = dict(vmid=101, state='absent')
        resolve[0] = {'ansible.builtin.set_fact': dict(proxmox_ha_vm_info=dict(skipped=True))}
        self.run_tasks(inputs, resolve + [expected])
        inputs['proxmox_ha_resource']['value'] = {}
        resolve[0] = {'ansible.builtin.set_fact': dict(proxmox_ha_vm_info=dict(proxmox_vms=[]))}
        self.run_tasks(inputs, resolve, success=False)
        rejection = next(task for task in yaml.safe_load((ROLE / 'tasks/reconcile.yml').read_text())[0]['block']
                         if task['name'] == 'Reject aliases which select the same VM more than once')
        self.run_tasks(dict(proxmox_ha_resolved_resources={'a': 'vm:101', 'b': 'vm:101', 'c': 'vm:103'}),
                       [rejection], success=False)

    def test_credential_aliases_and_conflicts_keep_the_secret_out_of_output(self):
        task = {'ansible.builtin.include_role': dict(name='proxmox_ha', tasks_from='credentials')}
        secret = 'fixture-secret-never-printed'
        for variable in ('PROXMOX_API_URL', 'PROXMOX_VE_ENDPOINT', 'PROXMOX_API_TOKEN_ID',
                         'PROXMOX_API_TOKEN_SECRET', 'PROXMOX_VE_API_TOKEN'):
            self.env.pop(variable, None)
        self.env.update(PROXMOX_API_URL='https://pve.example.com:8006/',
                        PROXMOX_API_TOKEN_ID='ha@pve!membership', PROXMOX_API_TOKEN_SECRET=secret)
        self.assertNotIn(secret, self.run_tasks(tasks=[task]))
        self.env['PROXMOX_VE_API_TOKEN'] = 'different@pve!token=' + secret
        output = self.run_tasks(tasks=[task], success=False)
        self.assertIn('Export PROXMOX_API_TOKEN_ID', output)
        self.assertNotIn(secret, output)
        self.env.pop('PROXMOX_API_TOKEN_ID')
        self.env.pop('PROXMOX_API_TOKEN_SECRET')
        self.assertNotIn(secret, self.run_tasks(tasks=[task]))

    def test_native_module_schema_and_public_playbook_syntax(self):
        modules = ['proxmox_cluster_ha_resources', 'proxmox_cluster_ha_rules', 'proxmox_cluster_ha_rules_info',
                   'proxmox_vm_info', 'proxmox_node_info']
        result = subprocess.run(['ansible-doc', '--json', *['community.proxmox.' + name for name in modules]],
                                env=self.env, capture_output=True, text=True, check=True, timeout=40)
        schemas = json.loads(result.stdout)
        self.assertEqual(schemas['community.proxmox.proxmox_node_info']['doc']['attributes']['check_mode']['support'], 'full')
        for task in yaml.safe_load((ROLE / 'tasks/apply.yml').read_text()):
            module = next(key for key in task if key.startswith('community.proxmox.'))
            self.assertTrue(set(task[module]).issubset(schemas[module]['doc']['options']))
        tier = UPSTREAM / 'tier-0'
        env = dict(self.env, ANSIBLE_CONFIG=str(tier / 'ansible/ansible.cfg'))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '--syntax-check',
                                 str(tier / 'ansible/playbooks/proxmox-ha.yml')],
                                cwd=tier, env=env, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
