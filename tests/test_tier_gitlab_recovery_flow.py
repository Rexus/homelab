"""Native Ansible Sidekiq lifetime with a fixed GitLab API adapter.

Kubernetes modules and the production block/always recipe run unchanged against
the loopback API. Native GitLab REST behavior has separate helper tests; these
checks establish ordering and cleanup, not live GitLab cancellation or isolation.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from test_tier_platform_recovery_flow import RecoveryAPI, ROLE


ADAPTER = '''import json,pathlib,sys,urllib.request
root=pathlib.Path(sys.argv[1]); operation=sys.argv[2]
url=(root/'url').read_text()+'/apis/apps/v1/namespaces/gitlab/deployments/gitlab-sidekiq'
with urllib.request.urlopen(url) as response: replicas=json.load(response)['spec']['replicas']
with (root/'events.jsonl').open('a') as log: log.write(json.dumps([operation,replicas])+'\\n')
assert replicas == (1 if operation == 'fence' else 0)
assert not (operation == 'fence' and (root/'fail').exists())
'''


@unittest.skipUnless(os.name == 'posix' and shutil.which('ansible-playbook'), 'Requires native Ansible/kubernetes.core')
class NativeGitLabWorkerLifetime(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='gitlab-worker-lifetime-')))
        self.api = RecoveryAPI(self.root)
        self.addCleanup(self.api.close)
        self.api.resources = dict(self.api.resources, **{'deployments/scale': ('Scale', True, 'apps/v1')})
        (self.root / 'url').write_text(f'http://127.0.0.1:{self.api.server.server_port}')
        self.work = self.root / 'work'
        (self.work / 'receipts').mkdir(parents=True)
        self.config = self.root / 'kubeconfig'
        self.config.write_text(yaml.safe_dump(self.api.kubeconfig()))
        self.role = self.root / 'roles/platform_recovery'
        shutil.copytree(ROLE, self.role, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.root / 'api-adapter.py').write_text(ADAPTER)
        (self.role / 'tasks/gitlab-fence.yml').write_text(yaml.safe_dump([
            {'name': 'Observe fixed native API boundary for the worker lifetime test',
             'ansible.builtin.command': {'argv': [sys.executable, str(self.root / 'api-adapter.py'),
                str(self.root), '{{ recovery_gitlab_fence_operation }}']}, 'changed_when': False}]))
        self.worker = {'apiVersion': 'apps/v1', 'kind': 'Deployment',
            'metadata': {'name': 'gitlab-sidekiq', 'namespace': 'gitlab',
                'annotations': {'recovery.homelab/plan-sha256': 'a' * 64}},
            'spec': {'replicas': 0, 'selector': {'matchLabels': {'app': 'sidekiq'}},
                'template': {'metadata': {'labels': {'app': 'sidekiq'}}, 'spec': {'containers': [
                    {'name': 'sidekiq', 'image': 'independent.test/sidekiq@sha256:' + 'b' * 64}]}}}}
        self.api.put(self.worker)

    def run_role(self, success=True):
        variables = {'ansible_python_interpreter': sys.executable,
            'platform_recovery': {'workspace': str(self.work), 'plan_sha256': 'a' * 64},
            'recovery_kubeconfig': str(self.config), 'recovery_context': 'offline',
            'recovery_health_retries': 1, 'recovery_health_delay': 0,
            'recovery_product': {'name': 'gitlab', 'namespace': 'gitlab', 'gitlab_recovery': {
                'sidekiq_workloads': [{'kind': 'Deployment', 'name': 'gitlab-sidekiq'}]}}}
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': [{'ansible.builtin.include_role': {
                'name': 'platform_recovery', 'tasks_from': 'gitlab-executions'}}]}]))
        result = subprocess.run([shutil.which('ansible-playbook'), '-i', 'localhost,', str(play)],
            env=dict(os.environ, ANSIBLE_ROLES_PATH=str(self.role.parent),
                     ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local')),
            capture_output=True, text=True, timeout=150)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def events(self):
        path = self.root / 'events.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_trigger_pause_precedes_worker_start_and_verified_fence_precedes_worker_drain(self):
        self.run_role()
        self.assertEqual(self.events(), [['pause-triggers', 0], ['fence', 1], ['verify', 0]])
        self.assertEqual(self.worker['spec']['replicas'], 0)
        self.assertEqual(self.api.objects['deployments', 'gitlab', 'gitlab-sidekiq']['spec']['replicas'], 0)
        changes = [body['spec']['replicas'] for method, path, body in self.api.mutations
                   if method == 'PATCH' and path.endswith('/gitlab-sidekiq/scale')]
        self.assertEqual(changes, [1])

    def test_failed_cancellation_always_stops_workers_and_same_targets_can_retry(self):
        (self.root / 'fail').touch()
        self.run_role(False)
        self.assertEqual(self.events(), [['pause-triggers', 0], ['fence', 1]])
        self.assertEqual(self.api.objects['deployments', 'gitlab', 'gitlab-sidekiq']['spec']['replicas'], 0)
        (self.root / 'fail').unlink()
        self.run_role()
        self.assertEqual(self.events()[-3:], [['pause-triggers', 0], ['fence', 1], ['verify', 0]])

    def test_other_workload_or_unowned_target_is_rejected_before_any_api_or_start(self):
        self.worker['spec']['template']['metadata']['labels']['app'] = 'webservice'
        self.api.put(self.worker)
        self.run_role(False)
        self.assertEqual(self.events(), [])
        self.assertEqual(self.api.mutations, [])
