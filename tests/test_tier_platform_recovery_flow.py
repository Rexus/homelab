"""Recovery coordinator with real Ansible/kubernetes.core against loopback fixtures.

The validated-plan boundary, physical hypervisor/Talos CLIs, hosted Git and Flux
controller are fixed adapters. The production recovery role, local journals,
native Kubernetes modules and TLS/content checks run unchanged. This is not a
live restore or a substitute for source/package and product-engine qualification.
"""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import yaml

from backup_storage_api_support import BackupStorageAPI
import test_tier_flux_recovery as recovery_tests

ROLE, RUNNER = recovery_tests.ROLE, recovery_tests.RUNNER


class RecoveryAPI(BackupStorageAPI):
    """Only the native resources used by these recovery journeys."""

    resources = dict(BackupStorageAPI.resources, **{
        'deployments': ('Deployment', True, 'apps/v1'),
        'statefulsets': ('StatefulSet', True, 'apps/v1'),
        'statefulsets/scale': ('Scale', True, 'apps/v1'),
        'pods': ('Pod', True, 'v1'),
        'jobs': ('Job', True, 'batch/v1'),
        'cronjobs': ('CronJob', True, 'batch/v1'),
        'secrets': ('Secret', True, 'v1'),
        'configmaps': ('ConfigMap', True, 'v1'),
        'gitrepositories': ('GitRepository', True, 'source.toolkit.fluxcd.io/v1'),
        'kustomizations': ('Kustomization', True, 'kustomize.toolkit.fluxcd.io/v1'),
    })

    def __init__(self, root):
        self.root = root
        self.fail_restore = False
        self.deny_content = False
        self.fail_health = False
        self.pod_reads = 0
        self.drain_after = 1
        self.job_intents = []
        self.search_requests = []
        self.search_restored = False
        self.search_failed_shards = False
        self.search_index_uid = 'restored-native-index'
        self.search_provenance = 'accepted-snapshot'
        super().__init__()
        fixture = self
        parent_handler = self.server.RequestHandlerClass

        class Handler(parent_handler):
            def do_GET(self):
                path = urlsplit(self.path).path
                if path.startswith(('/_cluster/', '/_snapshot/', '/_cat/', '/records/_recovery')):
                    fixture.search_requests.append(('GET', path, None))
                    if path.startswith('/_cluster/'):
                        return self.reply({'status': 'yellow', 'timed_out': False})
                    if path.startswith('/_snapshot/'):
                        return self.reply({'snapshots': [{'uuid': 'native-snapshot-uid', 'state': 'SUCCESS',
                            'indices': ['records'], 'shards': {'failed': 0}}]})
                    if path.startswith('/_cat/'):
                        return self.reply([{'index': 'records', 'uuid': fixture.search_index_uid}])
                    if not fixture.search_restored:
                        return self.reply({'error': 'index_not_found_exception'}, 404)
                    return self.reply({'records': {'shards': [{'id': 0, 'primary': True, 'stage': 'DONE',
                        'type': 'SNAPSHOT', 'source': {'repository': 'retained', 'snapshot': fixture.search_provenance}}]}})
                if path in ('/health', '/retained', '/denied'):
                    fixture.requests.append(('GET', path))
                    status = 403 if (path == '/denied' or (path == '/retained' and fixture.deny_content) or
                                     (path == '/health' and fixture.fail_health)) else 200
                    data = b'retained native dataset'
                    self.send_response(status)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                key = fixture.key(path)
                if key and key[0] == 'pods' and key[2] is None:
                    fixture.requests.append(('GET', self.path))
                    selector = parse_qs(urlsplit(self.path).query).get('labelSelector', [''])[0]
                    fixture.pod_reads += 1
                    pods = [obj for (resource, ns, _), obj in fixture.objects.items()
                            if resource == 'pods' and ns == key[1]]
                    if selector.startswith('app=writer') and fixture.pod_reads > fixture.drain_after:
                        pods = []
                    if selector.startswith('batch.kubernetes.io/controller-uid='):
                        uid = selector.partition('=')[2]
                        pods = [obj for obj in pods if obj['metadata']['labels'].get(
                            'batch.kubernetes.io/controller-uid') == uid]
                    return self.reply({'apiVersion': 'v1', 'kind': 'PodList', 'metadata': {}, 'items': pods})
                return super().do_GET()

            def do_POST(self):
                path = urlsplit(self.path).path
                obj = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if path.startswith('/_snapshot/'):
                    fixture.search_requests.append(('POST', path, obj))
                    fixture.search_restored = True
                    return self.reply({'snapshot': {'shards': {'total': 1,
                        'successful': 0 if fixture.search_failed_shards else 1,
                        'failed': 1 if fixture.search_failed_shards else 0}}})
                fixture.mutations.append(('POST', path, copy.deepcopy(obj)))
                if obj['kind'] == 'Job':
                    # Observe the journal at the API boundary, not after the role has finished.
                    journals = list((fixture.root / 'workspace/receipts').glob('job-*.json'))
                    planned = [json.loads(p.read_text()) for p in journals
                               if json.loads(p.read_text()).get('name') == obj['metadata']['name']]
                    fixture.job_intents.append(planned)
                fixture.put(obj)
                return self.reply(obj, 201)

            def do_PATCH(self):
                path = urlsplit(self.path).path
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                key = fixture.key(path)
                fixture.mutations.append(('PATCH', path, copy.deepcopy(body)))
                obj = copy.deepcopy(fixture.objects[key])
                if isinstance(body, list):
                    for operation in body:
                        target = obj
                        parts = operation['path'].strip('/').split('/')
                        for part in parts[:-1]:
                            target = target[part]
                        if operation['op'] == 'test':
                            if target[parts[-1]] != operation['value']:
                                return self.reply({'kind': 'Status', 'code': 409}, 409)
                        else:
                            target[parts[-1]] = operation['value']
                else:
                    def merge(actual, update):
                        for name, value in update.items():
                            if isinstance(value, dict) and isinstance(actual.get(name), dict):
                                merge(actual[name], value)
                            else:
                                actual[name] = value
                    merge(obj, {'spec': body['spec']} if path.endswith('/scale') else body)
                fixture.put(obj)
                return self.reply(obj)

            def do_PUT(self):
                path = urlsplit(self.path).path
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.search_requests.append(('PUT', path, body))
                return self.reply({'acknowledged': True})

            def do_DELETE(self):
                path = urlsplit(self.path).path
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
                key = fixture.key(path)
                fixture.mutations.append(('DELETE', path, body))
                removed = fixture.objects.pop(key, None)
                if removed:
                    uid = removed['metadata']['uid']
                    for owned, pod in list(fixture.objects.items()):
                        if owned[0] == 'pods' and any(ref.get('uid') == uid
                                for ref in pod['metadata'].get('ownerReferences', [])):
                            fixture.objects.pop(owned)
                return self.reply({'apiVersion': 'v1', 'kind': 'Status', 'status': 'Success', 'code': 200})

        self.server.RequestHandlerClass = Handler

    def put(self, obj):
        if obj['kind'] in ('Deployment', 'StatefulSet'):
            obj['metadata'].setdefault('generation', 1)
            replicas = obj.get('spec', {}).get('replicas', 1)
            obj['status'] = {'observedGeneration': obj['metadata']['generation'],
                'replicas': replicas, 'readyReplicas': replicas, 'updatedReplicas': replicas,
                'availableReplicas': replicas}
        if obj['kind'] == 'Job':
            failed = self.fail_restore and obj['metadata']['name'].startswith('restore-')
            obj['status'] = {'failed': 1} if failed else {'succeeded': 1,
                'conditions': [{'type': 'Complete', 'status': 'True'}]}
        return super().put(obj)


COMMAND_ADAPTER = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
root=pathlib.Path(os.environ['RECOVERY_FIXTURE'])
command=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
with (root/'commands.jsonl').open('a') as stream:
 stream.write(json.dumps([command,args])+'\n')
state=root/'vm.json'
if command=='pvesm':
 sys.stdout.buffer.write((root/'backup-config').read_bytes())
elif command=='pvesh':
 if args[1]=='/cluster/ha/resources': print('[]')
 elif args[1]=='/cluster/resources': print('[]')
 elif state.exists(): print(state.read_text())
 else: print('does not exist',file=sys.stderr);sys.exit(2)
elif command=='qmrestore': state.write_text('{}')
elif command=='qm' and args[0]=='set':
 data=json.loads(state.read_text()) if state.exists() else {}
 data[args[2].lstrip('-')]=args[3]; state.write_text(json.dumps(data))
elif command=='skopeo' and args[0]=='inspect': print('sha256:'+'d'*64)
elif command=='kubectl': print(json.dumps({'clusters':[{'cluster':{'server':'https://192.0.2.1:6443'}}]}))
elif command=='git' and args[0]=='ls-remote': print('c'*40+'\trefs/heads/accepted')
'''


FLUX_ADAPTER = [
    {'name': 'Model the separately qualified Flux controller without changing recovery tasks',
     'ansible.builtin.file': {'path': '{{ flux_maintenance_output }}', 'state': 'directory'}},
    {'ansible.builtin.copy': {'dest': '{{ flux_maintenance_output }}/scope-receipt.json',
        'content': '{{ {"resources": {"root": {"kind": "Kustomization", "namespace": "flux-system", '
                   '"name": flux_maintenance_source, "uid": "root-" ~ flux_maintenance_source, '
                   '"previous_suspend": true}}} | to_json }}'}},
    {'ansible.builtin.copy': {'dest': '{{ platform_recovery.workspace }}/flux-{{ flux_maintenance_operation }}-{{ flux_maintenance_source }}',
        'content': '{{ flux_maintenance_resume_checks | default([]) | to_json }}'}},
    {'kubernetes.core.k8s': {'kubeconfig': '{{ flux_maintenance_kubeconfig }}',
        'context': '{{ flux_maintenance_context }}', 'state': 'present', 'definition': {
            'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization',
            'metadata': {'namespace': 'flux-system', 'name': '{{ flux_maintenance_source }}'},
            'spec': {'suspend': '{{ flux_maintenance_operation != "resume" }}'}}}},
]


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('openssl'),
                     'Requires the prepared Linux Ansible runtime and OpenSSL')
class NativeRecoveryFlow(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='recovery-flow-')))
        self.api = RecoveryAPI(self.root)
        self.addCleanup(self.api.close)
        self.health = BackupStorageAPI()
        self.addCleanup(self.health.close)
        self.health.server.RequestHandlerClass = self.api.server.RequestHandlerClass
        certificate, key = self.root / 'ca.pem', self.root / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
            '-keyout', str(key), '-out', str(certificate)], check=True, capture_output=True)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(certificate, key)
        self.health.server.socket = tls.wrap_socket(self.health.server.socket, server_side=True)
        self.url = f'https://127.0.0.1:{self.health.server.server_port}'
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.tier = self.root / 'retained-tier-1'
        self.shared = self.root / 'retained-shared'
        for repo in (self.tier, self.shared):
            repo.mkdir()
            recovery_tests.RecoveryInputs.git(repo, 'init', '--quiet')
        shutil.copytree(ROLE, self.tier / 'ansible/roles/platform_recovery',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        flux = self.shared / 'ansible/roles/flux_maintenance/tasks'
        flux.mkdir(parents=True)
        (flux / 'main.yml').write_text(yaml.safe_dump(FLUX_ADAPTER))
        play = self.tier / 'ansible/playbooks/maintenance/platform-recovery.yml'
        play.parent.mkdir(parents=True)
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': {'ansible_python_interpreter': '{{ ansible_playbook_python }}',
                     'recovery_health_retries': 1, 'recovery_health_delay': 0},
            'tasks': [{'ansible.builtin.include_role': {'name': 'platform_recovery'}}]}]))
        (self.tier / 'ansible/ansible.cfg').write_text('[defaults]\nroles_path=roles:../../../shared/ansible/roles\n')
        scripts = self.tier / 'scripts'
        scripts.mkdir()
        (scripts / 'recovery_payload.py').write_text(
            'import argparse,json,pathlib\np=argparse.ArgumentParser();p.add_argument("--inputs");p.add_argument("--output");'
            'a=p.parse_args();v=json.loads(pathlib.Path(a.inputs).read_text())["platform_recovery"];'
            'pathlib.Path(a.output).write_text(json.dumps({"plan_sha256":v["plan_sha256"],"resources":[]}))\n')
        (scripts / 'recovery_talos.py').write_text(
            'import argparse,json,pathlib\np=argparse.ArgumentParser();p.add_argument("--inputs");p.add_argument("--tier");'
            'a=p.parse_args();v=json.loads(pathlib.Path(a.inputs).read_text())["platform_recovery"];'
            '(pathlib.Path(v["workspace"])/"receipts"/("tier-"+a.tier+"-reconstruction.json")).write_text("{}")\n')
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        for name in ('pvesm', 'pvesh', 'qmrestore', 'qm', 'ha-manager', 'skopeo', 'kubectl', 'git', 'ansible-playbook'):
            target = self.tools / name
            target.write_text(COMMAND_ADAPTER)
            target.chmod(0o700)
        self.backup_config = b'boot: order=scsi0\nnet0: virtio=02:00:00:00:00:01,bridge=vmbr0\n\n'
        (self.root / 'backup-config').write_bytes(self.backup_config)
        package = self.root / 'package'
        package.mkdir()
        (package / 'manifest.json').write_text('{}')
        (package / 'artifact-lock.json').write_text(json.dumps({'files': [{'path': 'tool.oci'}]}))
        self.plan = {'version': 1, 'scope': 'tier1', 'recovery_id': 'accepted', 'automation': {},
            'inventory': 'tier-1/ansible/inventory/recovery.yml', 'recovery_git_inputs': 'tier-1/secrets/git.yml',
            'package': {'directory': str(package), 'manifest_sha256': RUNNER.checksum(package / 'manifest.json'),
                'artifact_lock_sha256': RUNNER.checksum(package / 'artifact-lock.json'),
                'sources': {name: 'c' * 40 for name in ('platform', 'tier1-platform', 'tier1-applications')}},
            'artifact_supply': [{'kind': 'oci', 'path': 'tool.oci', 'digest': 'd' * 64,
                'destination': 'independent.test/tool', 'auth_file': 'tier-1/secrets/auth.json'}],
            'virtual_machines': [{'tier': 1, 'node': 'pve01', 'vmid': 1301, 'backup': 'local:backup/retained.vma.zst',
                'backup_config_sha256': hashlib.sha256(self.backup_config).hexdigest(), 'storage': 'local-zfs',
                'network': {'net0': 'virtio=02:00:00:00:00:01,bridge=vmbr9,firewall=1'},
                'health_checks': [{'kind': 'tcp', 'host': '127.0.0.1', 'port': self.health.server.server_port, 'timeout': 1},
                    {'kind': 'https', 'url': self.url + '/health', 'status': 200,
                     'ca_path': 'tier-1/secrets/ca.pem', 'timeout': 1}]}],
            'clusters': [{'tier': 1, 'kubeconfig': 'tier-1/secrets/talos/kubeconfig', 'context': 'offline',
                'api_server': 'https://192.0.2.1:6443', 'previous_namespace_uid': 'old-cluster',
                'nodes': [{'node': 'pve01', 'name': 'cp-1', 'vmid': 1101}], 'canary_sha256': 'c' * 64,
                'bootstrap_inputs': 'tier-1/secrets/bootstrap.yml', 'restore_resources': 'tier-1/secrets/resources.yml'}],
            'products': [{'tier': 1, 'kind': 'victoriametrics', 'name': 'metrics', 'namespace': 'metrics',
                'namespace_uid': 'new', 'backup_id': 's3://independent/retained', 'claim': 'metrics-data',
                'image': 'independent.test/tool@sha256:' + 'd' * 64, 'credentials_secret': 'backup-credentials',
                'writers': [{'kind': 'Deployment', 'name': 'writer'}],
                'python_image': 'independent.test/tool@sha256:' + 'd' * 64,
                'verification_ca_secret': 'recovery-ca', 'verification_headers_secret': 'recovery-auth',
                'checks': [{'url': self.url + '/retained', 'status': 200, 'ca_path': 'tier-1/secrets/ca.pem',
                    'content_sha256': hashlib.sha256(b'retained native dataset').hexdigest()},
                    {'url': self.url + '/denied', 'status': 403, 'ca_path': 'tier-1/secrets/ca.pem'}]}],
            'cutover': {'resume_roots': ['platform'], 'health_checks': [{'kind': 'Deployment', 'name': 'writer'}],
                'sources': {}, 'virtual_machines': [{'node': 'pve01', 'vmid': vmid,
                    'network': [{'name': 'net0', 'configuration': 'virtio,bridge=vmbr0'}]} for vmid in (1301, 1101)]}}
        self.plan['clusters'][0]['package'] = self.plan['package']
        # Tier-1-only recovery can reconstruct its cluster without restoring an
        # additional prerequisite VM. Dedicated tests add that VM explicitly.
        self.prerequisite_vm = self.plan['virtual_machines'].pop()
        self.plan['cutover']['virtual_machines'] = [self.plan['cutover']['virtual_machines'][1]]
        private = {'ansible/inventory/recovery.yml': yaml.safe_dump({'all': {'hosts': {
                'localhost': {'ansible_connection': 'local'}, 'pve01': {'ansible_connection': 'local', 'ansible_become': False}}}}),
            'secrets/git.yml': '{}', 'secrets/auth.json': '{}', 'secrets/identity': 'retained-test-only',
            'secrets/known_hosts': 'retained-host-key', 'secrets/ca.pem': certificate.read_text(),
            'secrets/bootstrap.yml': yaml.safe_dump({'cluster_platform_action': 'apply', 'cluster_platform_management': 'flux',
                'cluster_platform_flux_recovery': True, 'cluster_platform_flux_applications_suspended': True}),
            'secrets/talos/kubeconfig': yaml.safe_dump(self.api.kubeconfig()),
            'secrets/resources.yml': yaml.safe_dump_all([
                {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'metrics'}},
                {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
                 'metadata': {'name': 'metrics-data', 'namespace': 'metrics'},
                 'spec': {'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': '1Gi'}}}},
                {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': 'writer', 'namespace': 'metrics'},
                 'spec': {'replicas': 0, 'selector': {'matchLabels': {'app': 'writer'}}}}])}
        for name in self.plan['package']['sources']:
            relative = 'secrets/' + name + '.yml'
            private[relative] = yaml.safe_dump({'apiVersion': 'v1', 'kind': 'Secret',
                'metadata': {'name': name + '-git', 'namespace': 'flux-system'}, 'stringData': {'identity': 'retained'}})
            self.plan['cutover']['sources'][name] = {'url': 'ssh://git@restored.test/' + name,
                'ref': 'refs/heads/accepted', 'secret_name': name + '-git', 'secret_file': 'tier-1/' + relative,
                'identity_file': 'tier-1/secrets/identity', 'known_hosts_file': 'tier-1/secrets/known_hosts'}
            self.api.put({'apiVersion': 'source.toolkit.fluxcd.io/v1', 'kind': 'GitRepository',
                'metadata': {'name': name, 'namespace': 'flux-system'},
                'spec': {'url': 'ssh://git@independent.test/' + name, 'secretRef': {'name': 'bootstrap'}},
                'status': {'artifact': {'revision': 'recovery@sha1:' + 'c' * 40},
                           'conditions': [{'type': 'Ready', 'status': 'True'}]}})
        self.api.put({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'kube-system', 'uid': 'new-cluster'}})
        self.api.put({'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': 'terminating-writer', 'namespace': 'metrics',
            'deletionTimestamp': '2026-01-01T00:00:00Z', 'labels': {'app': 'writer'}}, 'status': {'phase': 'Running'}})
        for owner, repo in (('tier-1', self.tier), ('shared', self.shared)):
            recovery_tests.RecoveryInputs.git(repo, 'add', '.')
            recovery_tests.RecoveryInputs.git(repo, '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '--allow-empty', '-m', 'retained automation')
            entries = []
            if owner == 'tier-1':
                for relative, content in private.items():
                    target = repo / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    entries.append({'path': relative, 'sha256': RUNNER.checksum(target)})
            self.plan['automation'][owner] = {'directory': str(repo), 'commit': recovery_tests.RecoveryInputs.git(repo, 'rev-parse', 'HEAD'),
                'private_files': entries}
        self.plan_path = self.root / 'plan.json'
        self.plan_path.write_text(json.dumps(self.plan))
        self.digest = RUNNER.checksum(self.plan_path)
        self.ansible = shutil.which('ansible-playbook')

    def run_coordinator(self, phase='restore', success=True):
        # Retain real repository/package staging and the actual Ansible mainflow.
        # Only intercept execution to put the fixed physical-command adapters on PATH.
        native_run = subprocess.run
        self.last_output = ''
        if not (self.workspace / 'accepted-plan.sha256').exists():
            self.plan_path.write_text(json.dumps(self.plan))
            self.digest = RUNNER.checksum(self.plan_path)
        def execute(argv, *args, **kwargs):
            coordinator = argv[0] == 'ansible-playbook'
            if coordinator:
                argv = [self.ansible, *argv[1:]]
                env = dict(kwargs['env'], RECOVERY_FIXTURE=str(self.root),
                    PATH=str(self.tools) + os.pathsep + os.environ['PATH'],
                    ANSIBLE_ROLES_PATH=os.pathsep.join([str(self.workspace / 'tier-1/ansible/roles'),
                                                     str(self.workspace / 'shared/ansible/roles')]),
                    ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp'))
                kwargs.update(env=env, capture_output=True, text=True, timeout=180)
            try:
                result = native_run(argv, *args, **kwargs)
            except subprocess.CalledProcessError as error:
                if coordinator:
                    self.last_output = (error.stdout or '') + (error.stderr or '')
                raise
            if coordinator:
                self.last_output = result.stdout + result.stderr
            return result
        with patch.object(RUNNER, 'read_plan', return_value=copy.deepcopy(self.plan)), \
                patch.object(subprocess, 'run', side_effect=execute):
            arguments = argparse.Namespace(plan=self.plan_path, expect_plan=self.digest,
                                            workspace=self.workspace, phase=phase)
            if success:
                try:
                    RUNNER.run_recovery(arguments, lambda args: None)
                except subprocess.CalledProcessError as error:
                    self.fail((error.stdout or '') + (error.stderr or ''))
            else:
                with self.assertRaises(subprocess.CalledProcessError) as failed:
                    RUNNER.run_recovery(arguments, lambda args: None)
                self.assertEqual(Path(failed.exception.cmd[0]).resolve(), Path(self.ansible).resolve(),
                                 str(failed.exception))
                self.assertIn('failed=', failed.exception.stdout or '', str(failed.exception))

    def commands(self):
        path = self.root / 'commands.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def restore_creates(self):
        return [body for method, _, body in self.api.mutations if method == 'POST' and body and
                body.get('kind') == 'Job' and body['metadata']['name'].startswith('restore-')]

    def run_writer(self, writer, success=True):
        (self.workspace / 'receipts').mkdir(exist_ok=True)
        config = self.root / 'writer-kubeconfig'
        config.write_text(yaml.safe_dump(self.api.kubeconfig()))
        variables = {'platform_recovery': {'workspace': str(self.workspace), 'plan_sha256': 'a' * 64},
            'recovery_writer': writer, 'recovery_product': {'name': 'metrics', 'namespace': 'metrics'},
            'recovery_kubeconfig': str(config), 'recovery_context': 'offline',
            'recovery_health_retries': 1, 'recovery_health_delay': 0}
        play = self.root / 'writer.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': dict(variables, ansible_python_interpreter='{{ ansible_playbook_python }}'),
            'tasks': [{'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'writer'}}]}]))
        result = subprocess.run([self.ansible, '-i', 'localhost,', str(play)], env=dict(os.environ,
            ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp')),
            capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stdout

    def prepare_search(self):
        (self.workspace / 'receipts').mkdir(exist_ok=True)
        for name in ('ca.pem', 'key.pem'):
            shutil.copyfile(self.root / name, self.workspace / name)
        config = self.root / 'search-kubeconfig'
        config.write_text(yaml.safe_dump(self.api.kubeconfig()))
        (self.workspace / 'repository.yml').write_text(yaml.safe_dump({
            'type': 's3', 'settings': {'bucket': 'independently-retained', 'readonly': True}}))
        self.search_product = {'kind': 'opensearch', 'name': 'search', 'namespace': 'search',
            'url': self.url, 'client_cert': 'ca.pem', 'client_key': 'key.pem', 'ca_path': 'ca.pem',
            'repository': 'retained', 'repository_spec_file': 'repository.yml',
            'backup_id': 'accepted-snapshot', 'backup_uid': 'native-snapshot-uid', 'indices': ['records'],
            'data_claims': ['search-data'], 'claim_uids': {'search-data': 'new'},
            'restore_workloads': [{'name': 'search-data', 'replicas': 1}]}
        self.search_variables = {'platform_recovery': {'workspace': str(self.workspace), 'plan_sha256': 'a' * 64},
            'recovery_product': self.search_product, 'recovery_writer': {'kind': 'StatefulSet', 'name': 'search-data'},
            'recovery_kubeconfig': str(config), 'recovery_context': 'offline',
            'recovery_health_retries': 1, 'recovery_health_delay': 0,
            'ansible_python_interpreter': '{{ ansible_playbook_python }}'}
        self.api.put({'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
            'metadata': {'namespace': 'search', 'name': 'search-data', 'uid': 'original-search-claim',
                'annotations': {'recovery.homelab/plan-sha256': 'a' * 64}},
            'spec': {'accessModes': ['ReadWriteOnce']}})
        self.api.put({'apiVersion': 'apps/v1', 'kind': 'StatefulSet',
            'metadata': {'namespace': 'search', 'name': 'search-data',
                'annotations': {'recovery.homelab/plan-sha256': 'a' * 64}},
            'spec': {'replicas': 0, 'selector': {'matchLabels': {'app': 'search'}},
                'template': {'spec': {'containers': [{'name': 'search', 'image': 'independent@sha256:' + 'd' * 64}],
                    'volumes': [{'name': 'data', 'persistentVolumeClaim': {'claimName': 'search-data'}}]}}}})

    def run_search(self, success=True):
        play = self.root / 'search.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': self.search_variables, 'tasks': [
                {'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'writer'}},
                {'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'opensearch'}}]}]))
        result = subprocess.run([self.ansible, '-i', 'localhost,', str(play)], env=dict(os.environ,
            ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp')),
            capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result.stdout

    def assert_not_cutover(self):
        self.assertFalse((self.workspace / 'receipts/cutover.json').exists())
        self.assertFalse(list(self.workspace.glob('flux-resume-*')))
        self.assertFalse(any(command == 'qm' and args[-1].endswith('bridge=vmbr0')
                             for command, args in self.commands()))

    def test_interrupted_content_check_retries_restore_once_then_explicit_cutover_and_readonly_retry(self):
        self.api.deny_content = True
        self.run_coordinator(success=False)
        self.assertEqual(len(self.restore_creates()), 1, self.last_output)
        self.assert_not_cutover()
        self.assertFalse((self.workspace / 'receipts/data-verified.json').exists())
        self.api.deny_content = False
        self.run_coordinator()
        self.assertEqual(len(self.restore_creates()), 1)
        self.assertTrue((self.workspace / 'receipts/data-verified.json').exists())
        self.assert_not_cutover()
        self.run_coordinator(phase='resume')
        self.assertEqual(len(self.restore_creates()), 1)
        self.assertTrue((self.workspace / 'receipts/cutover.json').exists())
        self.assertEqual(len(self.api.job_intents), 2)  # native restore and content verification
        for intents in self.api.job_intents:
            self.assertEqual(len(intents), 1)
            self.assertEqual(intents[0]['phase'], 'planned')
            self.assertNotIn('uid', intents[0])
        verifier = self.api.objects[('jobs', 'metrics', 'verify-metrics-accepted')]['spec']['template']['spec']
        self.assertTrue(verifier['securityContext']['runAsNonRoot'])
        self.assertEqual(verifier['securityContext']['runAsUser'], 65532)
        self.assertEqual(verifier['securityContext']['seccompProfile']['type'], 'RuntimeDefault')
        for container in verifier['containers'] + verifier.get('initContainers', []):
            self.assertFalse(container['securityContext']['allowPrivilegeEscalation'])
            self.assertIn('ALL', container['securityContext']['capabilities']['drop'])
        for name in self.plan['cutover']['sources']:
            source = self.api.objects[('gitrepositories', 'flux-system', name)]
            self.assertEqual(source['spec']['url'], 'ssh://git@restored.test/' + name)
        commands, mutations = len(self.commands()), len(self.api.mutations)
        self.run_coordinator(phase='resume')
        self.assertEqual(len(self.commands()), commands)
        self.assertEqual(len(self.api.mutations), mutations)

    def test_failed_native_restore_blocks_cutover_and_is_not_recreated_on_retry(self):
        self.api.fail_restore = True
        self.run_coordinator(phase='resume', success=False)
        self.assertEqual(len(self.restore_creates()), 1)
        self.assert_not_cutover()
        self.run_coordinator(phase='resume', success=False)
        self.assertEqual(len(self.restore_creates()), 1)
        self.assert_not_cutover()

    def test_missing_or_replaced_restore_job_blocks_coordinator_retry_without_recreation(self):
        self.run_coordinator()
        key = ('jobs', 'metrics', 'restore-metrics-accepted')
        original = self.api.objects.pop(key)
        self.run_coordinator(phase='resume', success=False)
        self.assertEqual(len(self.restore_creates()), 1, self.last_output)
        self.assert_not_cutover()
        replacement = copy.deepcopy(original)
        replacement['metadata']['uid'] = 'replacement-job-uid'
        self.api.put(replacement)
        self.run_coordinator(phase='resume', success=False)
        self.assertEqual(len(self.restore_creates()), 1, self.last_output)
        self.assert_not_cutover()

    def test_terminating_writer_pod_blocks_restore_even_after_zero_replica_status(self):
        self.api.drain_after = 1000
        self.run_coordinator(phase='resume', success=False)
        self.assertEqual(self.api.objects[('deployments', 'metrics', 'writer')]['status']['replicas'], 0)
        self.assertEqual(self.restore_creates(), [])
        self.assert_not_cutover()
        self.assertTrue(any('labelSelector=app%3Dwriter' in path or 'labelSelector=app=writer' in path
                            for method, path in self.api.requests if method == 'GET'))

    def test_backup_configuration_bytes_are_not_trimmed_before_identity_verification(self):
        self.plan['virtual_machines'] = [self.prerequisite_vm]
        self.plan['virtual_machines'][0]['backup_config_sha256'] = hashlib.sha256(self.backup_config.rstrip()).hexdigest()
        self.plan_path.write_text(json.dumps(self.plan))
        self.digest = RUNNER.checksum(self.plan_path)
        self.run_coordinator(success=False)
        self.assertIn('Backup configuration or complete NIC inventory differs', self.last_output)
        self.assertFalse(any(command == 'qmrestore' for command, _ in self.commands()))
        self.assert_not_cutover()

    def test_failed_verified_https_prerequisite_health_prevents_cluster_construction(self):
        self.plan['virtual_machines'] = [self.prerequisite_vm]
        self.api.fail_health = True
        self.run_coordinator(phase='resume', success=False)
        self.assertTrue(any(command == 'qmrestore' for command, _ in self.commands()))
        self.assertFalse(any(command == 'ansible-playbook' and any('cluster-platform' in arg for arg in args)
                             for command, args in self.commands()))
        self.assertEqual(self.restore_creates(), [])
        self.assert_not_cutover()

    def test_prerequisite_restore_preserves_backup_bytes_and_checks_health_before_cluster_work(self):
        self.plan['virtual_machines'] = [self.prerequisite_vm]
        self.run_coordinator()
        commands = self.commands()
        restore = next(index for index, (name, _) in enumerate(commands) if name == 'qmrestore')
        start = next(index for index, (name, args) in enumerate(commands) if name == 'qm' and args[0] == 'start')
        self.assertEqual(commands[restore][1][-4:], ['--unique', '0', '--start', '0'])
        isolated = [index for index, (name, args) in enumerate(commands)
                    if name == 'qm' and args[-1] == self.prerequisite_vm['network']['net0']]
        self.assertTrue(isolated)
        self.assertLess(restore, isolated[0])
        self.assertLess(isolated[0], start)
        self.assertIn(('GET', '/health'), self.api.requests)
        self.assertTrue(any(name == 'ansible-playbook' and any('cluster-platform' in arg for arg in args)
                            for name, args in commands))
        self.assertEqual(len(self.restore_creates()), 1)
        self.assert_not_cutover()

    def test_cronjob_suspension_drains_owned_pending_work_with_foreground_deletion(self):
        self.api.put({'apiVersion': 'batch/v1', 'kind': 'CronJob',
            'metadata': {'name': 'scheduled-writer', 'namespace': 'metrics', 'uid': 'schedule-owner'},
            'spec': {'schedule': '* * * * *', 'suspend': False}})
        for name, owner in [('owned-job', 'schedule-owner'), ('unrelated-job', 'another-schedule')]:
            self.api.put({'apiVersion': 'batch/v1', 'kind': 'Job',
                'metadata': {'name': name, 'namespace': 'metrics', 'uid': name,
                    'ownerReferences': [{'uid': owner}]}, 'spec': {}})
            self.api.objects[('jobs', 'metrics', name)]['status'] = {'active': 1}
            self.api.put({'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name + '-pod',
                'namespace': 'metrics', 'labels': {'batch.kubernetes.io/controller-uid': name},
                'ownerReferences': [{'uid': name}], 'deletionTimestamp': '2026-01-01T00:00:00Z'},
                'status': {'phase': 'Pending'}})
        self.run_writer({'kind': 'CronJob', 'name': 'scheduled-writer'})
        self.assertTrue(self.api.objects[('cronjobs', 'metrics', 'scheduled-writer')]['spec']['suspend'])
        deletes = [(path, body) for method, path, body in self.api.mutations if method == 'DELETE']
        self.assertEqual(len(deletes), 1)
        self.assertTrue(deletes[0][0].endswith('/jobs/owned-job'))
        self.assertEqual(deletes[0][1]['propagationPolicy'], 'Foreground')
        self.assertIn(('jobs', 'metrics', 'unrelated-job'), self.api.objects)
        self.assertIn(('pods', 'metrics', 'unrelated-job-pod'), self.api.objects)
        journal = json.loads((self.workspace / 'receipts/metrics-scheduled-writer-writer.json').read_text())
        self.assertFalse(journal['resource']['spec']['suspend'])

    def test_native_writer_selector_preserves_matchlabels_and_expressions_during_pod_drain(self):
        self.api.put({'apiVersion': 'apps/v1', 'kind': 'Deployment',
            'metadata': {'name': 'writer', 'namespace': 'metrics'},
            'spec': {'replicas': 2, 'selector': {'matchLabels': {'app': 'writer'},
                'matchExpressions': [{'key': 'component', 'operator': 'In', 'values': ['ingest', 'query']},
                                     {'key': 'retired', 'operator': 'DoesNotExist'}]}}})
        self.run_writer({'kind': 'Deployment', 'name': 'writer'})
        requests = [parse_qs(urlsplit(path).query)['labelSelector'][0] for method, path in self.api.requests
                    if method == 'GET' and '/pods?' in path]
        self.assertGreaterEqual(len(requests), 2)
        self.assertEqual(requests[0], 'app=writer,component in (ingest,query),!retired')
        self.assertEqual(requests[-1], requests[0])
        journal = json.loads((self.workspace / 'receipts/metrics-writer-writer.json').read_text())
        self.assertEqual(journal['resource']['spec']['replicas'], 2)

    def test_search_registers_readonly_repository_then_restores_once_and_rejects_changed_index_identity(self):
        self.prepare_search()
        self.run_search()
        requests = self.api.search_requests
        self.assertTrue(requests[0][1].startswith('/_cluster/health'))
        registration = next(index for index, (method, _, _) in enumerate(requests) if method == 'PUT')
        restoration = next(index for index, (method, _, _) in enumerate(requests) if method == 'POST')
        self.assertLess(registration, restoration)
        self.assertTrue(requests[registration][2]['settings']['readonly'])
        self.assertEqual(requests[restoration][2], {'indices': 'records', 'include_global_state': False,
            'include_aliases': True, 'partial': False})
        checkpoint = json.loads((self.workspace / 'receipts/search-search-snapshot.json').read_text())
        self.assertEqual(checkpoint['backup_uid'], 'native-snapshot-uid')
        self.run_search()
        self.assertEqual(sum(method == 'POST' for method, _, _ in requests), 1)
        self.api.search_index_uid = 'unrelated-replacement-index'
        self.run_search(success=False)
        self.assertEqual(sum(method == 'POST' for method, _, _ in requests), 1)

    def test_search_claim_replacement_is_rejected_before_starting_native_nodes(self):
        self.prepare_search()
        self.run_search()
        self.api.objects[('persistentvolumeclaims', 'search', 'search-data')]['metadata']['uid'] = 'replaced-search-claim'
        self.run_search(success=False)
        self.assertEqual(self.api.objects[('statefulsets', 'search', 'search-data')]['spec']['replicas'], 0)
        self.assertEqual(sum(method == 'POST' for method, _, _ in self.api.search_requests), 1)

    def test_search_writable_repository_and_unjournaled_wrong_snapshot_provenance_block_restore(self):
        self.prepare_search()
        (self.workspace / 'repository.yml').write_text(yaml.safe_dump({
            'type': 's3', 'settings': {'readonly': False}}))
        self.run_search(success=False)
        self.assertFalse(any(method in ('PUT', 'POST') for method, _, _ in self.api.search_requests))
        (self.workspace / 'repository.yml').write_text(yaml.safe_dump({
            'type': 's3', 'settings': {'readonly': True}}))
        self.api.search_restored = True
        self.api.search_provenance = 'unselected-snapshot'
        self.run_search(success=False)
        self.assertFalse(any(method == 'POST' for method, _, _ in self.api.search_requests))

    def test_search_failed_shards_do_not_record_a_completed_native_restore(self):
        self.prepare_search()
        self.api.search_failed_shards = True
        self.run_search(success=False)
        self.assertEqual(sum(method == 'POST' for method, _, _ in self.api.search_requests), 1)
        self.assertFalse((self.workspace / 'receipts/search-search-snapshot.json').exists())


if __name__ == '__main__':
    unittest.main()
