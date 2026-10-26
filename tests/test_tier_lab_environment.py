"""Native application rendering and namespace-isolation contracts."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class LabEnvironment(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('helm')
                         and os.getenv('HOMELAB_NATIVE_CHART_TESTS') == '1', 'Requires native Helm chart tests')
    def test_native_scoped_collector_has_persistent_queues_and_authenticated_routes(self):
        self.generate()
        for repo in (UPSTREAM / 'tier-2', self.root / 'verify-tier-2'):
            output = Path(self.temp.name) / ('telemetry-' + repo.name)
            values = {
                'workload_telemetry_namespace': 'lab-demo',
                'workload_telemetry_chart_version': '0.177.0',
                'workload_telemetry_image_tag': '0.163.2',
                'workload_telemetry_storage_class': 'accepted-csi',
                'workload_telemetry_metrics_endpoint': 'otel.lab.test:30317',
                'workload_telemetry_application_endpoint': 'otel.lab.test:30400',
                'workload_telemetry_gateway_cidrs': ['192.0.2.5/32'],
                'workload_telemetry_gateway_ports': [30317, 30400],
                'workload_telemetry_output': str(output),
            }
            inputs = Path(self.temp.name) / 'telemetry-inputs.yml'
            inputs.write_text(yaml.safe_dump(values))
            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', 'ansible/playbooks/deployment/workload-telemetry.yml',
                 '-e', f'@{inputs}'], cwd=repo, capture_output=True, text=True,
                env=dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg')))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifests = list(filter(None, yaml.safe_load_all((output / 'otel-agent-manifests.yml').read_text())))
            stateful = next(obj for obj in manifests if obj['kind'] == 'StatefulSet')
            self.assertEqual(stateful['metadata']['name'], 'otel-agent')
            self.assertEqual(stateful['spec']['replicas'], 2)
            self.assertEqual(stateful['spec']['volumeClaimTemplates'][0]['metadata']['name'], 'queue')
            self.assertFalse(any(obj['kind'] == 'ClusterRole' for obj in manifests))
            config = yaml.safe_load((output / 'otel-agent-values.yml').read_text())['config']
            self.assertEqual(set(config['service']['pipelines']), {'logs', 'metrics', 'traces'})
            self.assertEqual(config['service']['pipelines']['logs']['exporters'], ['otlp/application'])
            self.assertEqual(config['service']['pipelines']['metrics']['exporters'], ['otlp/metrics'])
            for name in ('metrics', 'application'):
                exporter = config['exporters'][f'otlp/{name}']
                self.assertNotIn('insecure', exporter['tls'])
                self.assertEqual(exporter['sending_queue']['storage'], 'file_storage')
            policies = list(yaml.safe_load_all((output / 'otel-agent-before.yml').read_text()))
            self.assertEqual(len(policies), 2)
            self.assertNotIn('0.0.0.0/0', str(policies))

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_source_and_generated_render_the_selected_app_and_boundary(self):
        self.generate()
        for repo in (UPSTREAM / 'tier-2', self.root / 'verify-tier-2'):
            with self.subTest(repo=repo):
                output = Path(self.temp.name) / ('render-' + repo.name)
                values = {
                    'lab_environment_name': 'lab-demo', 'lab_environment_owner_group': 'demo-readers',
                    'lab_environment_image': 'registry.lab.test/app@sha256:' + 'a' * 64,
                    'lab_environment_host': 'demo.lab.test', 'lab_environment_ingress_class': 'traefik',
                    'lab_environment_ingress_namespace': 'ingress-system',
                    'lab_environment_output': str(output),
                }
                inputs = Path(self.temp.name) / 'lab-inputs.yml'
                inputs.write_text(yaml.safe_dump(values))
                command = ['ansible-playbook', '-i', 'localhost,',
                           'ansible/playbooks/deployment/lab-environment.yml', '-e', f'@{inputs}']
                result = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                                        env=dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg')))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                path = output / 'lab-demo.yml'
                objects = list(yaml.safe_load_all(path.read_text()))
                by_kind = {obj['kind']: obj for obj in objects}
                self.assertEqual(by_kind['Namespace']['metadata']['labels']['pod-security.kubernetes.io/enforce'],
                                 'restricted')
                deployment = by_kind['Deployment']
                self.assertEqual(deployment['spec']['replicas'], 2)
                pod = deployment['spec']['template']['spec']
                self.assertFalse(pod['automountServiceAccountToken'])
                self.assertEqual(pod['containers'][0]['image'], values['lab_environment_image'])
                self.assertTrue(pod['containers'][0]['securityContext']['readOnlyRootFilesystem'])
                deny = next(obj for obj in objects if obj['metadata']['name'] == 'default-deny')
                self.assertEqual(deny['spec']['policyTypes'], ['Ingress', 'Egress'])
                self.assertNotIn('egress', deny['spec'])
                self.assertEqual(by_kind['Role']['rules'][0]['verbs'], ['get', 'list', 'watch'])
                self.assertNotIn('Secret', by_kind)
                self.assertEqual(path.stat().st_mode & 0o077, 0)
                invalid = subprocess.run(command + ['-e', 'lab_environment_image=unreviewed:latest'], cwd=repo,
                                         capture_output=True, text=True,
                                         env=dict(os.environ, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg')))
                self.assertNotEqual(invalid.returncode, 0)
                self.assertNotIn('Prepare private application', invalid.stdout)

    def test_iac_and_guide_use_the_same_names_and_no_privileged_access(self):
        example = yaml.safe_load((UPSTREAM / 'tier-2/ansible/group_vars/lab_environment.yml.example').read_text())
        guide = (UPSTREAM / 'docs/deployment/stage-10-lab-environments/README.md').read_text()
        self.assertIn(example['lab_environment_name'], guide)
        self.assertEqual(example['lab_environment_replicas'], 2)
        template = (UPSTREAM / 'tier-2/ansible/roles/lab_environment/templates/environment.yml.j2').read_text()
        self.assertNotIn('hostPath', template)
        self.assertNotIn('privileged: true', template)
        self.assertNotIn('ClusterRole', template)


if __name__ == '__main__':
    unittest.main()
