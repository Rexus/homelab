"""Execute maintenance roles against a journaled local API double, without a cluster."""

import json
import importlib.util
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
    label_selectors=dict(type='list'),
))
parameters = module.params
path = Path(parameters['kubeconfig'])
state = json.loads(path.read_text())
kind, name = parameters.get('kind'), parameters.get('name')
event = dict(mode=MODE, kind=kind, name=name)
state['events'].append(event)

def save():
    path.write_text(json.dumps(state))

def view(resource):
    result = copy.deepcopy(resource)
    kind, name = result['kind'], result['metadata']['name']
    generation = result['metadata']['generation']
    if kind == 'Job':
        result['status'] = (dict(active=0, conditions=[]) if name in state.get('pending_jobs', []) else
                           dict(conditions=[dict(type='Complete', status='True')], active=0))
        return result
    source = name if kind == 'GitRepository' or name in ('platform', 'tier1-platform', 'tier1-applications') else resource['spec'].get('sourceRef', {}).get('name', 'tier1-platform')
    reference = state['objects'].get('GitRepository/' + source, {'spec': {'ref': {'commit': 'a' * 40}}})['spec']['ref']
    revision = reference.get('commit') or state['branch_head']
    unready = kind == 'GitRepository' and name in state.get('unready_initial', []) and generation == 1
    unready = unready or name in state.get('unhealthy', [])
    status = result.setdefault('status', {})
    status.update(observedGeneration=generation,
        conditions=[dict(type='Ready', status='False' if unready else 'True', observedGeneration=generation)])
    if name in state.get('busy', []):
        status['conditions'].append(dict(type='Reconciling', status='True'))
    if kind == 'GitRepository':
        status['artifact'] = dict(revision='delivery@sha1:' + revision)
    else:
        status['lastAppliedRevision'] = 'delivery@sha1:' + revision
    return result

# Simulate independent controller ticks and parent writes, not only patch responses.
# The test explicitly remains an API/controller model, without a Kubernetes cluster.
if MODE == 'k8s_info':
    for controller in state['objects'].values():
        if controller['kind'] not in ('Kustomization', 'HelmRelease') or controller['spec'].get('suspend'):
            continue
        state.setdefault('reconciliations', {}).setdefault(controller['metadata']['name'], 0)
        state['reconciliations'][controller['metadata']['name']] += 1
        for entry in controller.get('status', {}).get('inventory', {}).get('entries', []):
            namespace, child_name, group, child_kind = entry['id'].split('_')
            child = state['objects'].get(child_kind + '/' + child_name)
            if child and child['metadata'].get('annotations', {}).get('kustomize.toolkit.fluxcd.io/reconcile') != 'disabled':
                if child['kind'] == 'GitRepository':
                    child['spec']['ref'] = dict(commit='a' * 40)
                if not child['spec'].get('desired_suspended', False):
                    child['spec']['suspend'] = False

if MODE == 'k8s_info' and name is None:
    resources = [view(resource) for resource in state['objects'].values() if resource['kind'] == kind]
    save()
    module.exit_json(changed=False, resources=resources)

identity = kind + '/' + name
if identity not in state['objects']:
    save()
    module.exit_json(changed=False, resources=[])
resource = state['objects'][identity]
if MODE == 'k8s_json_patch':
    event['patch'] = parameters['patch']
    if state.get('concurrent_update') and kind == 'GitRepository':
        resource['metadata']['resourceVersion'] = 'concurrent'
    for change in parameters['patch']:
        keys = [key.replace('~1', '/').replace('~0', '~') for key in change['path'].strip('/').split('/')]
        parent = resource
        for key in keys[:-1]:
            parent = parent[key]
        if change['op'] == 'test':
            if parent.get(keys[-1]) != change['value']:
                save()
                module.fail_json(msg='Resource identity/version precondition failed')
        elif change['op'] == 'add':
            parent[keys[-1]] = change['value']
        elif change['op'] == 'remove':
            parent.pop(keys[-1])
        else:
            module.fail_json(msg='Unexpected patch')
    resource['metadata']['generation'] += 1
    resource['metadata']['resourceVersion'] = str(resource['metadata']['generation'])
    save()
    module.exit_json(changed=True, result=resource)

save()
module.exit_json(changed=False, resources=[view(resource)])
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
            metadata = dict(name=name, namespace='flux-system', generation=1, resourceVersion='1', uid=name + '-uid')
            objects['GitRepository/' + name] = dict(metadata=dict(metadata), spec=dict(
                url='https://independent.test/' + name, ref={'commit': OLD}, secretRef={'name': 'retained'}))
            objects['Kustomization/' + name] = dict(metadata=dict(metadata), spec={'suspend': False})
        objects['Kustomization/platform-base-flux2-release'] = dict(
            metadata=dict(name='platform-base-flux2-release', namespace='flux-system', generation=1, resourceVersion='1', uid='release-uid'), spec={})
        objects['Kustomization/application-release'] = dict(
            metadata=dict(name='application-release', namespace='flux-system', generation=1, resourceVersion='1', uid='application-uid'),
            spec={'sourceRef': {'name': 'tier1-applications'}})
        for key, resource in objects.items():
            resource['kind'] = key.split('/')[0]
            resource['apiVersion'] = 'source.toolkit.fluxcd.io/v1' if resource['kind'] == 'GitRepository' else 'kustomize.toolkit.fluxcd.io/v1'
        for source, child in [('tier1-platform', 'platform-base-flux2-release'), ('tier1-applications', 'application-release')]:
            objects['Kustomization/' + source]['spec']['sourceRef'] = dict(kind='GitRepository', name=source)
            objects['Kustomization/' + source]['status'] = dict(inventory=dict(entries=[dict(id='flux-system_' + child + '_kustomize.toolkit.fluxcd.io_Kustomization', v='v1')]))
        objects['Job/recovery-verified'] = dict(apiVersion='batch/v1', kind='Job',
            metadata=dict(name='recovery-verified', namespace='recovery', generation=1, resourceVersion='1', uid='verified-uid'), spec={})
        self.state = dict(objects=objects, events=[], branch_head=NEW)
        self.helper = self.directory / 'custody.py'
        self.helper.write_text('import json,sys\nfrom pathlib import Path\n'
            f'path=Path({str(self.state_path)!r})\nstate=json.loads(path.read_text())\n'
            'state["events"].append(dict(mode="custody", argv=sys.argv[1:]))\n'
            'if state.get("pause_during_custody"):\n'
            '    state["objects"]["Kustomization/tier1-platform"]["spec"]["suspend"] = True\n'
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
                              capture_output=True, text=True, timeout=180)

    def maintain(self, operation='advance', source='tier1-platform', **overrides):
        self.state_path.write_text(json.dumps(self.state))
        variables = dict(flux_maintenance_action='apply', flux_maintenance_operation=operation,
            flux_maintenance_source=source,
            flux_maintenance_revision='' if operation == 'resume' and source != 'tier1-applications' else NEW,
            flux_maintenance_approved=True,
            flux_maintenance_kubeconfig=str(self.state_path), flux_maintenance_output=str(self.output),
            flux_maintenance_recovery_directory=str(self.directory), flux_maintenance_custody_accepted=True,
            flux_maintenance_artifact_lock_sha256='c' * 64, flux_maintenance_recovery_tool=str(self.helper),
            flux_maintenance_retries=1, flux_maintenance_delay=0, flux_maintenance_resume_checks=[dict(api_version='batch/v1', kind='Job', name='recovery-verified', namespace='recovery', uid='verified-uid')], flux_maintenance_health_checks=[dict(
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

    def scope_receipt(self):
        return json.loads((self.output / 'scope-receipt.json').read_text())

    def test_staging_requires_a_complete_pause_before_source_mutation(self):
        result = self.maintain(operation='stage-paused', source='tier1-applications')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(event['mode'] == 'k8s_json_patch' for event in self.state['events']))
        self.assertEqual(self.maintain(operation='suspend', source='tier1-applications').returncode, 0)
        result = self.maintain(operation='stage-paused', source='tier1-applications')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.state['objects']['Kustomization/tier1-applications']['spec']['suspend'])
        self.assertTrue(self.state['objects']['Kustomization/application-release']['spec']['suspend'])
        self.assertEqual(self.scope_receipt()['phase'], 'staged')
        self.assertFalse(self.receipt()['reconciled'])

    def test_application_resume_waits_for_exact_branch_before_unfencing(self):
        self.assertEqual(self.maintain(operation='suspend', source='tier1-applications').returncode, 0)
        self.state['events'] = []
        result = self.maintain(operation='resume', source='tier1-applications')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = self.state['events']
        branch = next(index for index, event in enumerate(events) if event['mode'] == 'k8s_json_patch'
                      and event['kind'] == 'GitRepository')
        unfence = next(index for index, event in enumerate(events) if event['mode'] == 'k8s_json_patch'
                       and any(patch.get('path') == '/spec/suspend' and patch.get('value') is False for patch in event['patch']))
        self.assertLess(branch, unfence)
        self.assertTrue(any(event['mode'] == 'k8s_info' and event['kind'] == 'GitRepository'
            and event['name'] == 'tier1-applications' for event in events[branch + 1:unfence]))
        self.assertEqual(self.scope_receipt()['phase'], 'resumed')
        self.assertNotIn('kustomize.toolkit.fluxcd.io/reconcile',
                         self.state['objects']['Kustomization/application-release']['metadata'].get('annotations', {}))

    def test_wrong_branch_head_stays_fenced(self):
        self.assertEqual(self.maintain(operation='suspend', source='tier1-applications').returncode, 0)
        self.state['branch_head'] = OLD
        result = self.maintain(operation='resume', source='tier1-applications')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-applications']['spec']['suspend'])
        self.assertTrue(self.state['objects']['Kustomization/application-release']['spec']['suspend'])

    def test_platform_resume_uses_existing_pin_and_preserves_intentional_suspension(self):
        self.state['objects']['Kustomization/platform-base-flux2-release']['spec']['suspend'] = True
        self.state['objects']['Kustomization/platform-base-flux2-release']['spec']['desired_suspended'] = True
        self.assertEqual(self.maintain(operation='suspend').returncode, 0)
        self.state['objects']['Kustomization/platform-base-flux2-release']['spec']['desired_suspended'] = False
        result = self.maintain(operation='resume', flux_maintenance_revision='', flux_maintenance_health_checks=[])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.receipt()['commit'], OLD)
        self.assertFalse(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        self.assertNotIn('kustomize.toolkit.fluxcd.io/reconcile',
                         self.state['objects']['Kustomization/tier1-platform']['metadata'].get('annotations', {}))
        self.assertTrue(self.state['objects']['Kustomization/platform-base-flux2-release']['spec']['suspend'])
        self.assertEqual(self.state['objects']['Kustomization/platform-base-flux2-release']['metadata']['annotations']['kustomize.toolkit.fluxcd.io/reconcile'], 'disabled')
        self.assertFalse(self.state['objects']['Kustomization/tier1-applications']['spec']['suspend'])

    def test_suspended_root_is_rejected_before_custody_or_source_patch(self):
        self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'] = True
        result = self.maintain(operation='inspect', flux_maintenance_approved=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(self.receipt()['suspended'])
        self.state['events'] = []
        result = self.maintain()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state['objects']['GitRepository/tier1-platform']['spec']['ref'], {'commit': OLD})
        self.assertFalse(any(event['mode'] in ('custody', 'k8s_json_patch') for event in self.state['events']))

    def test_parent_pausing_during_custody_blocks_source_advance(self):
        self.state['pause_during_custody'] = True
        result = self.maintain()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state['objects']['GitRepository/tier1-platform']['spec']['ref'], {'commit': OLD})
        self.assertTrue(any(event['mode'] == 'custody' for event in self.state['events']))
        self.assertFalse(any(event['mode'] == 'k8s_json_patch' for event in self.state['events']))

    def test_pending_operation_blocks_staging_and_retry_preserves_original_states(self):
        self.state['busy'] = ['platform-base-flux2-release']
        result = self.maintain(operation='suspend')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.scope_receipt()['phase'], 'preparing')
        self.assertFalse(self.scope_receipt()['resources']['Kustomization/flux-system/tier1-platform']['previous_suspend'])
        self.assertTrue(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        self.state['busy'] = []
        result = self.maintain(operation='suspend')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.scope_receipt()['resources']['Kustomization/flux-system/tier1-platform']['previous_suspend'])
        self.assertEqual(self.scope_receipt()['phase'], 'paused')

    def test_scope_stops_independent_helm_children_and_preserves_unrelated_controllers(self):
        self.state['objects']['HelmRelease/service'] = dict(
            apiVersion='helm.toolkit.fluxcd.io/v2', kind='HelmRelease',
            metadata=dict(name='service', namespace='services', uid='helm-uid', generation=1, resourceVersion='1'),
            spec={}, status={'history': [{'status': 'deployed', 'name': 'service'}]})
        self.state['objects']['Kustomization/platform-base-flux2-release']['status'] = dict(
            inventory=dict(entries=[dict(id='services_service_helm.toolkit.fluxcd.io_HelmRelease', v='v2')]))
        result = self.maintain(operation='suspend')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        before = dict(self.state['reconciliations'])
        # Inspection drives more modeled controller ticks while the selected scope remains paused.
        result = self.maintain(operation='inspect', flux_maintenance_approved=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('tier1-platform', 'platform-base-flux2-release', 'service'):
            self.assertEqual(self.state['reconciliations'].get(name, 0), before.get(name, 0))
        self.assertGreater(self.state['reconciliations']['tier1-applications'], before['tier1-applications'])
        self.assertFalse(self.state['objects']['Kustomization/tier1-applications']['spec']['suspend'])
        self.assertIn('HelmRelease/services/service', self.scope_receipt()['resources'])

    def test_failed_dependency_resume_refences_scope_and_retries_original_state(self):
        self.assertEqual(self.maintain(operation='suspend').returncode, 0)
        self.state['unhealthy'] = ['platform-base-flux2-release']
        result = self.maintain(operation='resume')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        self.assertTrue(self.state['objects']['Kustomization/platform-base-flux2-release']['spec']['suspend'])
        self.assertEqual(self.scope_receipt()['phase'], 'paused')
        self.state['unhealthy'] = []
        result = self.maintain(operation='resume')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.scope_receipt()['phase'], 'resumed')

    def test_parent_cannot_rewind_staged_source_or_unpause_protected_children(self):
        self.state['objects']['Kustomization/platform']['status'] = dict(inventory=dict(entries=[
            dict(id='flux-system_tier1-platform_kustomize.toolkit.fluxcd.io_Kustomization', v='v1'),
            dict(id='flux-system_tier1-platform_source.toolkit.fluxcd.io_GitRepository', v='v1')]))
        self.state['objects']['Kustomization/tier1-platform']['spec']['dependsOn'] = [dict(name='platform')]
        self.assertEqual(self.maintain(operation='suspend').returncode, 0)
        self.assertEqual(self.maintain(operation='stage-paused').returncode, 0)
        result = self.maintain(operation='resume')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state['objects']['GitRepository/tier1-platform']['spec']['ref'], dict(commit=NEW))
        self.assertEqual(self.state['objects']['GitRepository/tier1-platform']['metadata']['annotations']['kustomize.toolkit.fluxcd.io/reconcile'], 'disabled')
        self.assertTrue(self.scope_receipt()['resources']['Kustomization/flux-system/platform']['control_only'])

    def test_writer_control_retains_replica_count_and_refuses_unrelated_writer(self):
        self.state['objects']['Deployment/writer'] = dict(apiVersion='apps/v1', kind='Deployment',
            metadata=dict(name='writer', namespace='applications', uid='writer-uid', generation=1, resourceVersion='1'),
            spec=dict(replicas=3, selector=dict(matchLabels=dict(app='writer'))))
        selected = dict(api_version='apps/v1', kind='Deployment', namespace='applications', name='writer')
        result = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state['objects']['Deployment/writer']['spec']['replicas'], 3)
        self.state['objects']['Kustomization/platform-base-flux2-release']['status'] = dict(
            inventory=dict(entries=[dict(id='applications_writer_apps_Deployment', v='v1')]))
        result = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state['objects']['Deployment/writer']['spec']['replicas'], 0)
        self.assertEqual(self.scope_receipt()['writers']['Deployment/applications/writer']['previous_value'], 3)
        result = self.maintain(operation='resume')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state['objects']['Deployment/writer']['spec']['replicas'], 3)

    def test_replaced_resources_and_wrong_verification_jobs_cannot_resume(self):
        self.assertEqual(self.maintain(operation='suspend').returncode, 0)
        result = self.maintain(operation='resume', flux_maintenance_resume_checks=[dict(
            api_version='batch/v1', kind='Job', namespace='recovery', name='recovery-verified', uid='wrong-uid')])
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        self.state['objects']['Kustomization/platform-base-flux2-release']['metadata']['uid'] = 'replacement'
        result = self.maintain(operation='resume')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])

    def test_cronjob_children_and_terminating_pods_block_until_actual_writers_drain(self):
        cron = dict(apiVersion='batch/v1', kind='CronJob', metadata=dict(
            name='backup', namespace='applications', uid='cron-uid', generation=1, resourceVersion='1'),
            spec=dict(suspend=False), status=dict(active=[]))
        job = dict(apiVersion='batch/v1', kind='Job', metadata=dict(
            name='backup-child', namespace='applications', uid='child-uid', generation=1, resourceVersion='1',
            ownerReferences=[dict(uid='cron-uid')]), spec={})
        pod = dict(apiVersion='v1', kind='Pod', metadata=dict(
            name='backup-pod', namespace='applications', uid='pod-uid', generation=1, resourceVersion='1',
            ownerReferences=[dict(uid='child-uid')]), spec={}, status=dict(phase='Pending'))
        self.state['objects'].update({'CronJob/backup': cron, 'Job/backup-child': job, 'Pod/backup-pod': pod})
        self.state['objects']['Kustomization/platform-base-flux2-release']['status'] = dict(
            inventory=dict(entries=[dict(id='applications_backup_batch_CronJob', v='v1')]))
        selected = dict(api_version='batch/v1', kind='CronJob', namespace='applications', name='backup')
        self.state['pending_jobs'] = ['backup-child']
        blocked = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('Drain actual CronJob children', blocked.stdout)
        self.assertTrue(self.state['objects']['CronJob/backup']['spec']['suspend'])
        self.state['pending_jobs'] = []
        blocked = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('Drain remaining CronJob Pods', blocked.stdout)
        self.state['objects']['Pod/backup-pod']['status']['phase'] = 'Succeeded'
        self.state['objects']['Pod/backup-pod']['metadata']['deletionTimestamp'] = '2026-11-15T00:00:00Z'
        blocked = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertNotEqual(blocked.returncode, 0)
        del self.state['objects']['Pod/backup-pod']['metadata']['deletionTimestamp']
        unrelated = json.loads(json.dumps(pod))
        unrelated['metadata'].update(name='unrelated-pod', uid='unrelated-uid', ownerReferences=[dict(uid='another-job')])
        unrelated['status']['phase'] = 'Running'
        self.state['objects']['Pod/unrelated-pod'] = unrelated
        drained = self.maintain(operation='suspend', flux_maintenance_writers=[selected])
        self.assertEqual(drained.returncode, 0, drained.stdout + drained.stderr)
        self.assertEqual(self.scope_receipt()['writers']['CronJob/applications/backup']['previous_value'], False)
        resumed = self.maintain(operation='resume')
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertFalse(self.state['objects']['CronJob/backup']['spec']['suspend'])

    def test_initially_paused_root_requires_deliberate_uid_bound_recovery_handoff(self):
        self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'] = True
        result = self.maintain(operation='suspend')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.maintain(operation='resume', flux_maintenance_resume_suspended_uids=['another-root-uid'])
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        result = self.maintain(operation='resume', flux_maintenance_resume_suspended_uids=['tier1-platform-uid'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.state['objects']['Kustomization/tier1-platform']['spec']['suspend'])
        self.assertNotIn('kustomize.toolkit.fluxcd.io/reconcile',
                         self.state['objects']['Kustomization/tier1-platform']['metadata'].get('annotations', {}))

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
                 dict(flux_maintenance_roots=['only-one-component']),
                 dict(flux_maintenance_source='tier1-applications'),
                 dict(flux_maintenance_operation='stage-paused', flux_maintenance_revision=''),
                 dict(flux_maintenance_approved=False),
                 dict(flux_maintenance_source='platform'),
                 dict(flux_maintenance_operation='resume', flux_maintenance_source='tier1-applications', flux_maintenance_resume_checks=[])]
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


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires Ansible filter runtime')
class FluxScopeGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('flux_scope', ROOT /
            'shared/ansible/roles/flux_maintenance/filter_plugins/flux_scope.py')
        cls.filters = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.filters)

    def resource(self, kind, name, namespace='flux-system', **spec):
        return dict(apiVersion='helm.toolkit.fluxcd.io/v2' if kind == 'HelmRelease'
                    else 'kustomize.toolkit.fluxcd.io/v1', kind=kind,
                    metadata=dict(name=name, namespace=namespace, uid=namespace + '-' + name,
                                  generation=1, resourceVersion='1'), spec=spec)

    def test_inventory_owners_source_consumers_and_dependencies_define_exact_scope(self):
        ancestor = self.resource('Kustomization', 'platform')
        root = self.resource('Kustomization', 'tier1-platform', sourceRef=dict(
            kind='GitRepository', name='tier1-platform'))
        stage = self.resource('Kustomization', 'database')
        release = self.resource('HelmRelease', 'database', namespace='database')
        dependent = self.resource('HelmRelease', 'application', namespace='database',
                                  dependsOn=[dict(name='database')])
        unrelated = self.resource('Kustomization', 'tier0')
        ancestor['status'] = dict(inventory=dict(entries=[dict(
            id='flux-system_tier1-platform_kustomize.toolkit.fluxcd.io_Kustomization', v='v1')]))
        root['status'] = dict(inventory=dict(entries=[dict(
            id='flux-system_database_kustomize.toolkit.fluxcd.io_Kustomization', v='v1')]))
        for resource in (release, dependent):
            resource['metadata']['labels'] = {'kustomize.toolkit.fluxcd.io/name': 'database',
                                             'kustomize.toolkit.fluxcd.io/namespace': 'flux-system'}
        scope = self.filters.flux_scope([ancestor, root, stage, release, dependent, unrelated], 'tier1-platform')
        self.assertEqual(len(scope['resources']), 5)
        self.assertTrue(scope['resources']['Kustomization/flux-system/platform']['control_only'])
        self.assertLess(scope['suspend_order'].index('Kustomization/flux-system/platform'),
                        scope['suspend_order'].index('Kustomization/flux-system/tier1-platform'))
        self.assertLess(scope['resume_order'].index('HelmRelease/database/database'),
                        scope['resume_order'].index('HelmRelease/database/application'))
        self.assertNotIn('Kustomization/flux-system/tier0', scope['resources'])

    def test_cycles_replacements_and_pending_helm_actions_fail_closed(self):
        root = self.resource('Kustomization', 'tier1-platform')
        root['spec']['dependsOn'] = [dict(name='tier1-platform')]
        with self.assertRaisesRegex(Exception, 'cycle'):
            self.filters.flux_scope([root], 'tier1-platform')
        root['spec'] = {}
        scope = self.filters.flux_scope([root], 'tier1-platform')
        receipt = self.filters.flux_scope_receipt(scope, {}, 'operation', 'source-uid')
        receipt['phase'] = 'paused'
        scope['resources'][scope['root']]['uid'] = 'replacement'
        with self.assertRaisesRegex(Exception, 'replaced'):
            self.filters.flux_scope_validate(scope, receipt, 'source-uid')
        helm = self.resource('HelmRelease', 'service')
        helm['status'] = dict(history=[dict(status='pending-upgrade')])
        self.assertFalse(self.filters.flux_drained(helm))
        helm['status'] = dict(conditions=[dict(type='Reconciling', status='True')])
        self.assertFalse(self.filters.flux_drained(helm))

    def test_scope_refresh_retains_original_states_when_staged_dependencies_change(self):
        root = self.resource('Kustomization', 'tier1-platform', sourceRef=dict(
            kind='GitRepository', name='tier1-platform'))
        database = self.resource('Kustomization', 'database', sourceRef=dict(
            kind='GitRepository', name='tier1-platform'))
        scope = self.filters.flux_scope([root, database], 'tier1-platform')
        receipt = self.filters.flux_scope_receipt(scope, {}, 'original', 'source-uid')
        receipt['phase'] = 'paused'
        root['spec']['suspend'] = True
        database['spec']['suspend'] = True
        verification = self.resource('Kustomization', 'backup', suspend=True,
            sourceRef=dict(kind='GitRepository', name='tier1-platform'))
        database['spec']['dependsOn'] = [dict(name='backup')]
        refreshed = self.filters.flux_scope([root, database, verification], 'tier1-platform')
        receipt = self.filters.flux_scope_receipt(refreshed, receipt, 'retry', 'source-uid')
        self.assertEqual(receipt['operation_id'], 'original')
        self.assertFalse(receipt['resources']['Kustomization/flux-system/database']['previous_suspend'])
        self.assertTrue(receipt['resources']['Kustomization/flux-system/backup']['previous_suspend'])
        self.assertLess(receipt['resume_order'].index('Kustomization/flux-system/backup'),
                        receipt['resume_order'].index('Kustomization/flux-system/database'))


class FluxMaintenanceGenerated(unittest.TestCase):
    def test_generation_delivers_filter_and_refresh_preserves_private_inputs_and_pipelines(self):
        with tempfile.TemporaryDirectory(prefix='flux-scope-generated-') as directory:
            command = [sys.executable, str(ROOT / 'scripts/tier-repos/generate.py'), '--prefix', 'scope',
                       '--root', directory, '--repo', 'shared', '--repo', 'tier-1']
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            collection = Path(directory) / 'scope-iac'
            generated = collection / 'scope-shared/ansible/roles/flux_maintenance/filter_plugins/flux_scope.py'
            self.assertTrue(generated.is_file(), 'Shared role Python filters must be part of the generated payload')
            inputs = collection / 'scope-tier-1/ansible/group_vars/flux_maintenance.yml'
            pipeline = collection / 'scope-tier-1/pipelines/flux-promotion.yml.j2'
            inputs.write_text('flux_maintenance_context: private-context\n')
            pipeline.write_text('project-owned-pipeline\n')
            result = subprocess.run(command + ['--refresh'], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(generated.is_file())
            self.assertEqual(inputs.read_text(), 'flux_maintenance_context: private-context\n')
            self.assertEqual(pipeline.read_text(), 'project-owned-pipeline\n')


if __name__ == '__main__':
    unittest.main()
