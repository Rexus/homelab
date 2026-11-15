"""Recovery installs every Flux root paused before product restoration can begin."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml

from backup_storage_api_support import BackupStorageAPI
from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'shared/ansible/roles/cluster_platform'
REVISION = 'a' * 40


class RecoveryBootstrap(unittest.TestCase):
    def test_recovery_render_pauses_every_root_and_normal_render_preserves_application_choice(self):
        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(ROLE / 'templates'),
                                         undefined=jinja2.StrictUndefined)
        environment.filters.update(to_json=json.dumps, bool=bool)
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        environment.globals['lookup'] = lambda plugin, name: environment.get_template(name).render(values)
        for owner in ('ansible', 'flux'):
            for recovery in (False, True):
                for paused_apps in (False, True):
                    with self.subTest(owner=owner, recovery=recovery, paused_apps=paused_apps):
                        values.update(cluster_platform_management=owner, cluster_platform_flux_recovery=recovery,
                                      cluster_platform_flux_applications_suspended=paused_apps)
                        document = yaml.safe_load(environment.get_template('flux.yml.j2').render(values))
                        roots = {item['metadata']['name']: item for item in document['after']
                                 if item['kind'] == 'Kustomization'}
                        self.assertEqual(roots['platform']['spec']['suspend'], recovery)
                        if owner == 'flux':
                            self.assertEqual(roots['tier1-platform']['spec']['suspend'], recovery)
                            self.assertEqual(roots['tier1-applications']['spec']['suspend'], recovery or paused_apps)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_native_recovery_gate_observes_all_roots_and_rejects_one_active_root(self):
        class API(BackupStorageAPI):
            resources = dict(BackupStorageAPI.resources,
                gitrepositories=('GitRepository', True, 'source.toolkit.fluxcd.io/v1'),
                kustomizations=('Kustomization', True, 'kustomize.toolkit.fluxcd.io/v1'))
        with tempfile.TemporaryDirectory(prefix='recovery-bootstrap-') as directory:
            root = Path(directory)
            api = API()
            self.addCleanup(api.close)
            api.put({'apiVersion': 'source.toolkit.fluxcd.io/v1', 'kind': 'GitRepository',
                     'metadata': {'name': 'platform', 'namespace': 'flux-system', 'generation': 1},
                     'status': {'observedGeneration': 1, 'artifact': {'revision': 'main@sha1:' + REVISION},
                                'conditions': [{'type': 'Ready', 'status': 'True', 'observedGeneration': 1}]}})
            for name in ('platform', 'tier1-platform', 'tier1-applications'):
                api.put({'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization',
                         'metadata': {'name': name, 'namespace': 'flux-system'}, 'spec': {'suspend': True}})
            kubeconfig = root / 'kubeconfig.yml'
            kubeconfig.write_text(yaml.safe_dump(api.kubeconfig()))
            play = root / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'ansible_python_interpreter': '{{ ansible_playbook_python }}',
                         'cluster_platform_management': 'flux', 'cluster_platform_flux_recovery': True,
                         'cluster_platform_kubeconfig': str(kubeconfig), 'cluster_platform_context': 'offline',
                         'cluster_platform_flux_commit': REVISION, 'cluster_platform_health_retries': 1,
                         'cluster_platform_health_delay': 0},
                'tasks': [{'ansible.builtin.include_role': {'name': 'cluster_platform', 'tasks_from': 'flux'}}]}]))
            environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent),
                               ANSIBLE_LOCAL_TEMP=str(root / 'ansible-temp'))
            def run():
                return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                      env=environment, capture_output=True, text=True, timeout=120)
            result = run()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name in ('platform', 'tier1-platform', 'tier1-applications'):
                self.assertTrue(any(path.endswith('/kustomizations/' + name) for _, path in api.requests))
            self.assertFalse(api.mutations, 'Bootstrap verification must not resume a root')
            api.objects[('kustomizations', 'flux-system', 'tier1-platform')]['spec']['suspend'] = False
            result = run()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Verify recovery roots were installed paused', result.stdout)
            self.assertFalse(api.mutations)
