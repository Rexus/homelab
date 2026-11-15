"""Run actual upgrade tasks against journaled API doubles, without a cluster or databases."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
API = r'''
import copy
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule

module = AnsibleModule(argument_spec=dict(
    kubeconfig=dict(type='str'), context=dict(type='str'), validate_certs=dict(type='bool'),
    api_version=dict(type='str'), kind=dict(type='str'), namespace=dict(type='str'), name=dict(type='str'),
    definition=dict(type='raw'), state=dict(type='str'), wait=dict(type='bool'), wait_timeout=dict(type='int'),
    label_selectors=dict(type='list'), merge_type=dict(type='list'),
))
path = Path(module.params['kubeconfig'])
state = json.loads(path.read_text())
mode = MODE
kind, name = module.params.get('kind'), module.params.get('name')
state['events'].append(dict(mode=mode, kind=kind, name=name))
def save():
    path.write_text(json.dumps(state))
def finish(**result):
    save()
    module.exit_json(**result)
if mode == 'info':
    values = [copy.deepcopy(obj) for obj in state['objects'].values()
              if obj['kind'] == kind and (not name or obj['metadata']['name'] == name)]
    finish(changed=False, resources=values)
if module.params.get('state') == 'absent':
    state['objects'].pop(kind + '/' + name, None)
    state['objects'].pop('Pod/backup-pod', None)
    finish(changed=True)
definitions = module.params['definition']
if not isinstance(definitions, list):
    definitions = [definitions]
for definition in definitions:
    identity = definition['kind'] + '/' + definition['metadata']['name']
    if definition['kind'] == 'ConfigMap' and 'source-sha256' in definition.get('data', {}):
        if state.pop('interrupt_before_receipt', False):
            save()
            module.fail_json(msg='Simulated process interruption after verified backup')
    if identity in state['objects']:
        if definition['kind'] == 'Kustomization':
            definition['metadata']['uid'] = state['objects'][identity]['metadata']['uid']
            state['objects'][identity] = definition
        continue
    definition['metadata']['uid'] = 'uid-' + str(len(state['objects']))
    if definition['kind'] == 'Job':
        assert state['paused'], 'Backup cannot start with active application writers'
        state['backups'] += 1
        failed = state.get('fail_backup', False)
        definition['status'] = dict(failed=1) if failed else dict(succeeded=1)
        state['objects']['Pod/backup-pod'] = dict(
            apiVersion='v1', kind='Pod', metadata=dict(name='backup-pod', namespace='spinnaker',
                uid='pod-' + str(state['backups']), ownerReferences=[dict(uid=definition['metadata']['uid'])]),
            status=dict(phase='Failed' if failed else 'Succeeded',
                initContainerStatuses=[dict(name=product, state=dict(terminated=dict(exitCode=0)))
                    for product in ('verify-mysql-import', 'verify-redis-rdb')],
                containerStatuses=[dict(name='independent-copy', state=dict(terminated=dict(
                    exitCode=1 if failed else 0, message='a' * 64)))]))
    state['objects'][identity] = definition
    if definition['kind'] == 'Kustomization' and state.pop('interrupt_graph_install', False):
        save()
        module.fail_json(msg='Simulated interruption during paused graph installation')
finish(changed=True, result=state['objects'][identity])
'''

PAUSE = r'''
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule
module = AnsibleModule(argument_spec=dict(path=dict(type='str'), source=dict(type='str'),
    operation=dict(type='str'), revision=dict(type='str'), resume_uids=dict(type='list'), output=dict(type='str')))
assert module.params['source'] == 'tier1-platform'
path = Path(module.params['path'])
state = json.loads(path.read_text())
operation = module.params['operation']
if operation == 'suspend':
    state['paused'] = True
elif operation == 'stage-paused':
    assert state['paused'], 'Source cannot advance before complete scoped pause'
    state['source_revision'] = module.params['revision']
elif operation == 'resume':
    assert state['paused'], 'Resume requires an existing complete scoped pause'
    assert all(obj['spec']['suspend'] for obj in state['objects'].values() if obj['kind'] == 'Kustomization')
    state['resumed_uids'] = module.params['resume_uids']
    state['resumed_parent_intent'] = json.loads((Path(module.params['output']) / 'scope-receipt.json').read_text())['resources']
    state['paused'] = False
state['events'].append(dict(mode=operation))
path.write_text(json.dumps(state))
resources = {'Kustomization/' + obj['metadata']['namespace'] + '/' + obj['metadata']['name']:
    {'uid': obj['metadata']['uid'], 'previous_reconcile': obj['metadata'].get('annotations', {}).get('kustomize.toolkit.fluxcd.io/reconcile')}
    for obj in state['objects'].values() if obj['kind'] == 'Kustomization'}
module.exit_json(changed=True, scope_receipt={'resources': resources})
'''


@unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
class SpinnakerUpgrade(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spinnaker-upgrade-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        roles = self.root / "roles"
        shutil.copytree(ROLE, roles / "delivery_platform")
        tasks_file = roles / "delivery_platform/tasks/spinnaker-upgrade.yml"
        tasks = yaml.safe_load(tasks_file.read_text())
        for task in tasks:
            if "retries" in task:
                task.update(retries=1, delay=0)
        tasks_file.write_text(yaml.safe_dump(tasks))
        maintenance = roles / "flux_maintenance/tasks"
        maintenance.mkdir(parents=True)
        (maintenance / "main.yml").write_text(yaml.safe_dump([
            {"journal_pause": {"path": "{{ flux_maintenance_kubeconfig }}", "source": "{{ flux_maintenance_source }}",
                "operation": "{{ flux_maintenance_operation }}", "revision": "{{ flux_maintenance_revision | default('') }}",
                "resume_uids": "{{ flux_maintenance_resume_suspended_uids | default([]) }}",
                "output": "{{ flux_maintenance_output }}"}, 'register': 'fixture_pause'},
            {"ansible.builtin.set_fact": {"flux_maintenance_record_sources": {
                "tier1-platform": {"commit": "a" * 40}},
                "flux_maintenance_scope_receipt": "{{ fixture_pause.scope_receipt }}"}}]))
        library = self.root / "library"
        library.mkdir()
        (library / "journal_pause.py").write_text(PAUSE)
        collection = self.root / "collections/ansible_collections/kubernetes/core/plugins/modules"
        collection.mkdir(parents=True)
        (collection / "k8s.py").write_text(API.replace("MODE", "'apply'"))
        (collection / "k8s_info.py").write_text(API.replace("MODE", "'info'"))
        (self.root / "ansible.cfg").write_text(
            f"[defaults]\nroles_path={roles}\nlibrary={library}\ncollections_path={self.root / 'collections'}\n")
        self.current = []
        for product in ("mysql", "redis"):
            self.current.append(dict(apiVersion="apps/v1", kind="StatefulSet", metadata=dict(
                name=f"spinnaker-{product}", namespace="spinnaker", uid=f"current-{product}"), spec=dict(
                template=dict(spec=dict(containers=[dict(name=product, image=f"accepted-{product}:1",
                    volumeMounts=[dict(name="data", mountPath="/data")])],
                    volumes=[dict(name="config", configMap=dict(name=f"accepted-{product}-config"))])),
                volumeClaimTemplates=[dict(metadata=dict(name="data"))]), status=dict(readyReplicas=1)))
        self.state_file = self.root / "api.json"
        self.state(dict(objects={f"StatefulSet/{obj['metadata']['name']}": obj for obj in self.current},
                        events=[], backups=0, paused=False))
        self.variables = dict(delivery_platform_kubeconfig=str(self.state_file), delivery_platform_context="isolated",
            delivery_platform_output=str(self.root / "records"), spinnaker_upgrade_namespace="spinnaker",
            spinnaker_upgrade_component="platform-delivery", spinnaker_upgrade_id="c" * 20,
            spinnaker_upgrade_source_sha256="d" * 64, spinnaker_upgrade_target_sha256="e" * 64,
            spinnaker_upgrade_expected_data=self.current, spinnaker_upgrade_writers=["orca", "echo", "gate"],
            spinnaker_upgrade_scripts=dict(apiVersion="v1", kind="ConfigMap", metadata=dict(
                name="accepted-upgrade-scripts", namespace="spinnaker"), data={}),
            spinnaker_upgrade_backup_job=dict(apiVersion="batch/v1", kind="Job", metadata=dict(
                name="accepted-backup-job", namespace="spinnaker"), spec={}))

    def state(self, value=None):
        if value is not None:
            self.state_file.write_text(json.dumps(value))
        return json.loads(self.state_file.read_text())

    def run_tasks(self):
        playbook = self.root / "play.yml"
        playbook.write_text(yaml.safe_dump([dict(hosts="localhost", connection="local", gather_facts=False,
            vars=self.variables, tasks=[{"ansible.builtin.include_role": {
                "name": "delivery_platform", "tasks_from": "spinnaker-upgrade.yml"}}])]))
        return subprocess.run(["ansible-playbook", "-i", "localhost,", str(playbook)], capture_output=True,
            text=True, timeout=300, env=dict(os.environ, ANSIBLE_CONFIG=str(self.root / "ansible.cfg"),
                ANSIBLE_COLLECTIONS_PATH=str(self.root / "collections"), ANSIBLE_LOCAL_TEMP=str(self.root / "local")))

    def test_interruption_after_backup_reuses_original_job_and_binds_checkpoint_to_target(self):
        state = self.state()
        state["interrupt_before_receipt"] = True
        self.state(state)
        interrupted = self.run_tasks()
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertIn("Simulated process interruption", interrupted.stdout)
        self.assertTrue(self.state()["paused"])
        self.assertEqual(self.state()["backups"], 1)
        resumed = self.run_tasks()
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.state()["backups"], 1)
        receipt = self.state()["objects"]["ConfigMap/spinnaker-upgrade-" + "c" * 20]
        self.assertTrue(receipt["immutable"])
        self.assertEqual(receipt["data"]["target-sha256"], "e" * 64)
        self.assertEqual(receipt["data"]["snapshot"], "a" * 64)
        retry = self.run_tasks()
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        self.assertEqual(self.state()["backups"], 1)
        state = self.state()
        state["objects"]["ConfigMap/spinnaker-upgrade-" + "c" * 20]["data"]["target-sha256"] = "f" * 64
        self.state(state)
        refused = self.run_tasks()
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("checkpoint cannot be verified", refused.stdout)

    def test_failed_backup_blocks_receipt_and_retries_only_the_failed_export_job(self):
        self.make_graph_checkout()
        state = self.state()
        state["fail_backup"] = True
        self.state(state)
        failed = self.run_tasks()
        self.assertNotEqual(failed.returncode, 0)
        self.assertTrue(self.state()["paused"])
        self.assertNotIn("ConfigMap/spinnaker-upgrade-" + "c" * 20, self.state()["objects"])
        self.assertNotIn("stage-paused", [event["mode"] for event in self.state()["events"]])
        for product in ("mysql", "redis"):
            actual = self.state()["objects"][f"StatefulSet/spinnaker-{product}"]
            self.assertEqual(actual["spec"]["template"]["spec"]["containers"][0]["image"], f"accepted-{product}:1")
        state = self.state()
        state["fail_backup"] = False
        self.state(state)
        retried = self.run_tasks()
        self.assertEqual(retried.returncode, 0, retried.stdout + retried.stderr)
        self.assertEqual(self.state()["backups"], 2)
        self.assertTrue(list((self.root / "records").rglob("failed-backup-*.json")))

    def test_changed_current_database_runtime_is_refused_before_any_backup(self):
        state = self.state()
        state["objects"]["StatefulSet/spinnaker-mysql"]["spec"]["template"]["spec"]["containers"][0]["image"] = "proposed-mysql:2"
        self.state(state)
        refused = self.run_tasks()
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("current data runtime differs", refused.stdout)
        self.assertEqual(self.state()["backups"], 0)
        self.assertTrue(self.state()["paused"])

    def make_graph_checkout(self, unrelated_change=False):
        checkout = self.root / "configuration"
        graph_file = checkout / "clusters/tier1/platform/delivery/reconciliation.yaml"
        graph_file.parent.mkdir(parents=True)
        graph_file.write_text("# accepted previous configuration\n")
        def git(*arguments):
            result = subprocess.run(["git", "-C", str(checkout), *arguments], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout.strip()
        git("init", "--quiet")
        git("add", ".")
        git("-c", "commit.gpgsign=false", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--quiet", "-m", "accepted fixture")
        previous = git("rev-parse", "HEAD")
        graph = []
        prefix = "platform-delivery"
        for name, dependencies in ((prefix + "-inputs", []),
                (prefix + "-spinnaker-preupgrade-backup", [prefix + "-inputs"]),
                (prefix + "-spinnaker-prerequisites", [prefix + "-spinnaker-preupgrade-backup"]),
                (prefix, [prefix + "-spinnaker-prerequisites"])):
            graph.append(dict(apiVersion="kustomize.toolkit.fluxcd.io/v1", kind="Kustomization",
                metadata=dict(name=name, namespace="flux-system"), spec=dict(
                    sourceRef=dict(kind="GitRepository", name="tier1-platform"), serviceAccountName="platform-reconciler",
                    prune=False, force=False, dependsOn=[dict(name=dependency) for dependency in dependencies])))
        graph_file.write_text(yaml.safe_dump_all(graph))
        if unrelated_change:
            unrelated = checkout / "clusters/tier1/platform/other/resources.yaml"
            unrelated.parent.mkdir()
            unrelated.write_text("kind: ConfigMap\n")
        git("add", ".")
        git("-c", "commit.gpgsign=false", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--quiet", "-m", "proposed fixture")
        self.variables.update(spinnaker_upgrade_operation="apply", spinnaker_upgrade_revision=git("rev-parse", "HEAD"),
            spinnaker_upgrade_source_checkout=str(checkout), spinnaker_upgrade_recovery_directory=str(self.root / "custody"),
            spinnaker_upgrade_artifact_lock_sha256="f" * 64, spinnaker_upgrade_graph_file=str(graph_file),
            spinnaker_upgrade_component_path="platform/delivery")
        self.variables["spinnaker_upgrade_fixture_previous_commit"] = previous
        maintenance = self.root / "roles/flux_maintenance/tasks/main.yml"
        maintenance.write_text(maintenance.read_text().replace("a" * 40, previous))
        return graph

    def test_apply_keeps_children_paused_across_source_and_graph_change_and_resumes_new_nodes_after_retry(self):
        graph = self.make_graph_checkout()
        state = self.state()
        state["interrupt_graph_install"] = True
        self.state(state)
        interrupted = self.run_tasks()
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertIn("Simulated interruption during paused graph", interrupted.stdout)
        self.assertTrue(self.state()["paused"])
        retried = self.run_tasks()
        self.assertEqual(retried.returncode, 0, retried.stdout + retried.stderr)
        state = self.state()
        self.assertFalse(state["paused"])
        self.assertEqual(state["backups"], 1)
        self.assertEqual(len(state["resumed_uids"]), len(graph))
        self.assertTrue(all(record['previous_reconcile'] is None
                            for record in state['resumed_parent_intent'].values()))
        events = [event["mode"] for event in state["events"]]
        self.assertLess(events.index("stage-paused"), events.index("resume"))

    def test_apply_refuses_a_revision_changing_unrelated_platform_payloads_before_source_advance(self):
        self.make_graph_checkout(unrelated_change=True)
        refused = self.run_tasks()
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("changes another platform component", refused.stdout)
        self.assertNotIn("stage-paused", [event["mode"] for event in self.state()["events"]])
        self.assertTrue(self.state()["paused"])


if __name__ == "__main__":
    unittest.main()
