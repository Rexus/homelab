"""Execute maintenance roles against a journaled local API double, without a cluster."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
OLD = 'a' * 40
NEW = 'b' * 40
SOURCES = ('platform', 'tier1-platform', 'tier1-applications')


API_MODULE = r'''
import copy
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

MODE = MODE_PLACEHOLDER
module = AnsibleModule(argument_spec=dict(
    kubeconfig=dict(type='str', required=True), context=dict(type='str'),
    validate_certs=dict(type='bool'), api_version=dict(type='str'),
    kind=dict(type='str'), name=dict(type='str'), namespace=dict(type='str'),
    definition=dict(type='dict'), merge_type=dict(type='list'), patch=dict(type='list'),
))
parameters = module.params
path = Path(parameters['kubeconfig'])
state = json.loads(path.read_text())
definition = parameters.get('definition') or {}
kind = definition.get('kind', parameters.get('kind'))
name = definition.get('metadata', {}).get('name', parameters.get('name'))
identity = kind + '/' + name
event = dict(mode=MODE, kind=kind, name=name)
state['events'].append(event)

def save():
    path.write_text(json.dumps(state))

if identity not in state['objects']:
    save()
    if MODE == 'k8s_info':
        module.exit_json(changed=False, resources=[])
    module.fail_json(msg='The selected existing object is missing')

resource = state['objects'][identity]
if MODE == 'k8s_json_patch':
    event['patch'] = parameters['patch']
    if state.get('concurrent_update'):
        resource['metadata']['resourceVersion'] = 'concurrent'
    expected = parameters['patch'][0]
    if expected != dict(op='test', path='/metadata/resourceVersion', value=resource['metadata']['resourceVersion']):
        save()
        module.fail_json(msg='Resource version precondition failed')
    change = parameters['patch'][1]
    if change['op'] != 'add' or change['path'] != '/spec/ref':
        module.fail_json(msg='Unexpected source mutation')
    resource['spec']['ref'] = change['value']
elif MODE == 'k8s':
    event['definition'] = definition
    if kind != 'Kustomization' or set(definition['spec']) != {'suspend'}:
        module.fail_json(msg='Only the selected reconciliation fence may be merged')
    resource['spec']['suspend'] = definition['spec']['suspend']

if MODE != 'k8s_info':
    resource['metadata']['generation'] += 1
    resource['metadata']['resourceVersion'] = str(resource['metadata']['generation'])
    save()
    module.exit_json(changed=True, result=resource)

result = copy.deepcopy(resource)
source = name if kind == 'GitRepository' or name in ('platform', 'tier1-platform', 'tier1-applications') else resource['spec'].get('sourceRef', {}).get('name', 'tier1-platform')
reference = state['objects']['GitRepository/' + source]['spec']['ref']
revision = reference.get('commit') or state['branch_head']
generation = result['metadata']['generation']
unready = kind == 'GitRepository' and name in state.get('unready_initial', []) and generation == 1
unready = unready or name in state.get('unhealthy', [])
result['status'] = dict(observedGeneration=generation,
    conditions=[dict(type='Ready', status='False' if unready else 'True', observedGeneration=generation)])
if kind == 'GitRepository':
    result['status']['artifact'] = dict(revision='delivery@sha1:' + revision)
else:
    result['status']['lastAppliedRevision'] = 'delivery@sha1:' + revision
save()
module.exit_json(changed=False, resources=[result])
'''


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
class FluxMaintenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix='flux-maintenance-')
        cls.addClassCleanup(cls.workspace.cleanup)
        cls.root = Path(cls.workspace.name)
        cls.roles = cls.root / 'roles'
        for name in ('flux_maintenance', 'flux_recovery_git', 'cluster_platform'):
            shutil.copytree(ROOT / 'shared/ansible/roles' / name, cls.roles / name)
        cls.collections = cls.root / 'collections'
        modules = cls.collections / 'ansible_collections/kubernetes/core/plugins/modules'
        modules.mkdir(parents=True)
        for name in ('k8s_info', 'k8s', 'k8s_json_patch'):
            (modules / (name + '.py')).write_text(API_MODULE.replace('MODE_PLACEHOLDER', repr(name)))

    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory(dir=self.root)))
        self.state_path = self.directory / 'api.json'
        self.output = self.directory / 'receipts'
        objects = {}
        for name in SOURCES:
            metadata = dict(name=name, namespace='flux-system', generation=1, resourceVersion='1')
            objects['GitRepository/' + name] = dict(metadata=dict(metadata), spec=dict(
                url='https://independent.test/' + name, ref={'commit': OLD}, secretRef={'name': 'retained'}))
            objects['Kustomization/' + name] = dict(metadata=dict(metadata), spec={'suspend': False})
        objects['Kustomization/platform-base-flux2-release'] = dict(
            metadata=dict(name='platform-base-flux2-release', generation=1, resourceVersion='1'), spec={})
        objects['Kustomization/application-release'] = dict(
            metadata=dict(name='application-release', generation=1, resourceVersion='1'),
            spec={'sourceRef': {'name': 'tier1-applications'}})
        self.state = dict(objects=objects, events=[], branch_head=NEW)
        self.helper = self.directory / 'custody.py'
        self.helper.write_text('import json,sys\nfrom pathlib import Path\n'
            f'path=Path({str(self.state_path)!r})\nstate=json.loads(path.read_text())\n'
            'state["events"].append(dict(mode="custody", argv=sys.argv[1:]))\n'
            'path.write_text(json.dumps(state))\nraise SystemExit(1 if state.get("fail_custody") else 0)\n')

    def play(self, variables, tasks=None, role='flux_maintenance'):
        play = dict(hosts='localhost', connection='local', gather_facts=False, vars=variables)
        if tasks is None:
            play['roles'] = [role]
        else:
            play['tasks'] = tasks
        path = self.directory / 'play.yml'
        path.write_text(yaml.safe_dump([play]))
        config = self.directory / 'ansible.cfg'
        config.write_text('[defaults]\nretry_files_enabled = False\n')
        environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_ROLES_PATH=str(self.roles),
            ANSIBLE_COLLECTIONS_PATH=str(self.collections), ANSIBLE_COLLECTIONS_PATHS=str(self.collections),
            ANSIBLE_LOCAL_TEMP=str(self.directory / 'local'), ANSIBLE_REMOTE_TEMP=str(self.directory / 'remote'),
            ANSIBLE_PIPELINING='true', ANSIBLE_PYTHON_INTERPRETER=sys.executable)
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)], env=environment,
                              capture_output=True, text=True, timeout=90)

    def maintain(self, operation='advance', source='tier1-platform', **overrides):
        self.state_path.write_text(json.dumps(self.state))
        variables = dict(flux_maintenance_action='apply', flux_maintenance_operation=operation,
            flux_maintenance_source=source, flux_maintenance_revision=NEW, flux_maintenance_approved=True,
            flux_maintenance_kubeconfig=str(self.state_path), flux_maintenance_output=str(self.output),
            flux_maintenance_recovery_directory=str(self.directory), flux_maintenance_custody_accepted=True,
            flux_maintenance_artifact_lock_sha256='c' * 64, flux_maintenance_recovery_tool=str(self.helper),
            flux_maintenance_retries=1, flux_maintenance_delay=0, flux_maintenance_health_checks=[dict(
                api_version='kustomize.toolkit.fluxcd.io/v1', kind='Kustomization',
                name='application-release' if source == 'tier1-applications' else 'platform-base-flux2-release',
                namespace='flux-system')])
        variables.update(overrides)
        result = self.play(variables)
        self.state = json.loads(self.state_path.read_text())
        return result

    def receipt(self):
        return json.loads((self.output / 'last-operation.json').read_text())

    def test_authorized_platform_repair_changes_only_exact_ref_with_other_source_down(self):
        self.state['unready_initial'] = ['tier1-platform']
        del self.state['objects']['GitRepository/tier1-applications']
        before = dict(self.state['objects']['GitRepository/tier1-platform']['spec'])
        result = self.maintain()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = self.state['objects']['GitRepository/tier1-platform']['spec']
        self.assertEqual(after, dict(before, ref={'commit': NEW}))
        events = self.state['events']
        custody = next(index for index, event in enumerate(events) if event['mode'] == 'custody')
        patch = next(index for index, event in enumerate(events) if event['mode'] == 'k8s_json_patch')
        self.assertLess(custody, patch)
        self.assertEqual(events[patch]['patch'][0]['value'], '1')
        self.assertIn('tier1-platform=' + NEW, events[custody]['argv'])
        self.assertTrue(self.receipt()['reconciled'])
        proposed = json.loads((self.output / 'proposed-change.json').read_text())
        self.assertEqual(self.receipt()['operation_id'], proposed['operation_id'])
        observations = json.loads((self.output / 'accepted-revisions.json').read_text())
        self.assertTrue(observations['observation_only'])
        self.assertFalse(observations['sources']['tier1-platform']['ready'])
        self.assertTrue(observations['sources']['tier1-applications']['missing'])

    def test_recovery_fences_before_pinning_and_receipt_does_not_claim_reconciliation(self):
        result = self.maintain(operation='recover', source='tier1-applications')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        writes = [event for event in self.state['events'] if event['mode'] in ('k8s', 'k8s_json_patch')]
        self.assertEqual([event['mode'] for event in writes], ['k8s', 'k8s_json_patch'])
        self.assertTrue(writes[0]['definition']['spec']['suspend'])
        self.assertEqual(self.state['objects']['GitRepository/tier1-applications']['spec']['ref'], {'commit': NEW})
        self.assertTrue(self.receipt()['suspended'])
        self.assertFalse(self.receipt()['reconciled'])

    def test_application_resume_waits_for_exact_branch_before_unfencing(self):
        result = self.maintain(operation='resume', source='tier1-applications',
            flux_maintenance_data_restored=True, flux_maintenance_executions_fenced=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = self.state['events']
        writes = [(index, event) for index, event in enumerate(events) if event['mode'] in ('k8s', 'k8s_json_patch')]
        self.assertEqual([event['mode'] for _, event in writes], ['k8s', 'k8s_json_patch', 'k8s'])
        self.assertTrue(writes[0][1]['definition']['spec']['suspend'])
        self.assertEqual(writes[1][1]['patch'][1]['value'], {'branch': 'delivery'})
        self.assertFalse(writes[2][1]['definition']['spec']['suspend'])
        self.assertTrue(any(event['mode'] == 'k8s_info' and event['kind'] == 'GitRepository'
            and event['name'] == 'tier1-applications' for event in events[writes[1][0] + 1:writes[2][0]]))

    def test_wrong_branch_head_stays_fenced_and_cannot_reuse_previous_receipt(self):
        self.state['branch_head'] = OLD
        self.output.mkdir()
        (self.output / 'last-operation.json').write_text(json.dumps({'operation_id': 'previous-success'}))
        result = self.maintain(operation='resume', source='tier1-applications',
            flux_maintenance_data_restored=True, flux_maintenance_executions_fenced=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-applications']['spec']['suspend'])
        proposed = json.loads((self.output / 'proposed-change.json').read_text())
        self.assertNotEqual(self.receipt()['operation_id'], proposed['operation_id'])

    def test_platform_resume_checks_current_pin_and_reports_failed_health(self):
        self.state['unhealthy'] = ['tier1-platform']
        result = self.maintain(operation='resume', flux_maintenance_revision='')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.output / 'last-operation.json').exists())
        self.assertIn('Wait for the expected native resource', result.stdout)

    def test_platform_resume_uses_the_existing_pin_when_no_new_revision_is_selected(self):
        result = self.maintain(operation='resume', flux_maintenance_revision='')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.receipt()['commit'], OLD)
        self.assertTrue(self.receipt()['reconciled'])
        self.assertFalse(self.receipt()['suspended'])

    def test_inspection_does_not_claim_fence_state_and_suspended_readiness_is_rejected(self):
        self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'] = True
        result = self.maintain(operation='inspect', flux_maintenance_approved=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(self.receipt()['suspended'])
        self.assertEqual(self.receipt()['commit'], OLD)
        self.assertEqual(self.receipt()['requested_commit'], NEW)
        previous = self.receipt()['operation_id']
        result = self.maintain()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Reject historical readiness', result.stdout)
        self.assertEqual(self.receipt()['operation_id'], previous)

    def test_custody_failure_and_concurrent_update_cannot_overwrite_source(self):
        for failure in ('fail_custody', 'concurrent_update'):
            with self.subTest(failure=failure):
                self.state[failure] = True
                result = self.maintain()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.state['objects']['GitRepository/tier1-platform']['spec']['ref'], {'commit': OLD})
                self.assertFalse((self.output / 'last-operation.json').exists())
                self.state[failure] = False
                self.state['objects']['GitRepository/tier1-platform']['metadata']['resourceVersion'] = '1'

    def test_unauthorized_scopes_and_unaccepted_application_resume_have_no_api_calls(self):
        cases = [dict(flux_maintenance_source='tier0'),
                 dict(flux_maintenance_source='tier1-applications'),
                 dict(flux_maintenance_operation='recover'),
                 dict(flux_maintenance_approved=False),
                 dict(flux_maintenance_source='platform'),
                 dict(flux_maintenance_operation='resume', flux_maintenance_source='tier1-applications')]
        for inputs in cases:
            with self.subTest(inputs=inputs):
                self.state['events'] = []
                result = self.maintain(**inputs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.state['events'], [])

    def test_recovery_git_rejects_reused_keys_and_serves_quoted_scoped_upload_commands(self):
        role = self.roles / 'flux_recovery_git'
        tasks = yaml.safe_load((role / 'tasks/main.yml').read_text())
        assertions = tasks[:next(index for index, task in enumerate(tasks) if 'ansible.builtin.package' in task)]
        keys = {name: 'ssh-ed25519 AAAA' + str(index) + ' source' for index, name in enumerate(SOURCES)}
        variables = dict(ansible_os_family='RedHat', flux_recovery_git_package='/retained',
            flux_recovery_git_root=str(self.directory / 'served'), flux_recovery_git_user='flux-recovery',
            flux_recovery_git_artifact_lock_sha256='c' * 64, flux_recovery_git_source_keys=keys)
        bad_keys = {name: 'ssh-ed25519 AAAA same-key-' + str(index) for index, name in enumerate(SOURCES)}
        for override in (dict(flux_recovery_git_source_keys=bad_keys),
                         dict(flux_recovery_git_root='////'),
                         dict(flux_recovery_git_source_keys=dict(keys, platform=keys['platform'] + '\n'))):
            result = self.play(dict(variables, **override), tasks=assertions)
            self.assertNotEqual(result.returncode, 0)
        destination = self.directory / 'authorized_keys'
        result = self.play(variables, tasks=assertions + [{'ansible.builtin.template': dict(
            src=str(role / 'templates/authorized_keys.j2'), dest=str(destination))}])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = destination.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            name = re.search(r'/(platform|tier1-platform|tier1-applications)\.git', line).group(1)
            command = re.search(r'command="([^"]+)"', line).group(1)
            self.assertEqual(command, f"git-upload-pack '{variables['flux_recovery_git_root']}/{name}.git'")
            self.assertTrue(line.startswith('restrict,command='))
            repository = Path(variables['flux_recovery_git_root']) / (name + '.git')
            subprocess.run(['git', 'init', '--bare', '--quiet', str(repository)], check=True, capture_output=True)
            result = subprocess.run(['git-shell', '-c', command], input=b'0000', capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_recovery_git_checks_the_served_application_branch_on_every_run(self):
        tasks = yaml.safe_load((self.roles / 'flux_recovery_git/tasks/main.yml').read_text())
        gate = next(task for task in tasks if task['name'] == 'Reject drift in the read-only application recovery branch')
        for commits, success in (([OLD, OLD], True), ([OLD, NEW], False), ([OLD], False)):
            with self.subTest(commits=commits):
                result = self.play({'flux_recovery_git_branch': {'stdout_lines': commits}}, tasks=[gate])
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
