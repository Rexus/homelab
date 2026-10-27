"""Controller and admission continuity across the reference application journey."""

import json
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]


class ReferenceApplicationJourney(unittest.TestCase):
    def test_explicit_localhost_applications_use_the_accepted_controller_python(self):
        entrypoints = [
            'tier-0/ansible/playbooks/deployment/control-applications.yml',
            'tier-1/ansible/playbooks/deployment/observability-platform.yml',
            'tier-2/ansible/playbooks/deployment/lab-environment.yml',
        ]
        for entrypoint in entrypoints:
            with self.subTest(entrypoint=entrypoint):
                play = yaml.safe_load((ROOT / entrypoint).read_text())[0]
                self.assertEqual(play['hosts'], 'localhost')
                self.assertEqual(play['connection'], 'local')
                self.assertEqual(
                    play.get('vars', {}).get('ansible_python_interpreter'),
                    '{{ ansible_playbook_python }}',
                    'Explicit localhost inventory must use the controller virtualenv that holds '
                    'the documented Kubernetes dependencies, rather than discovered system Python.',
                )

    def test_workload_collector_meets_its_namespace_seccomp_requirement(self):
        role = ROOT / 'tier-2/ansible/roles/workload_telemetry'
        tasks = yaml.safe_load((role / 'tasks/main.yml').read_text())
        release = tasks[-1]['vars']['kube_apps_releases'][0]
        self.assertEqual(release['namespace_labels']['pod-security.kubernetes.io/enforce'], 'restricted')
        inputs = yaml.safe_load(
            (ROOT / 'tier-2/ansible/group_vars/workload_telemetry.yml.example').read_text()
        )
        environment = Environment(undefined=StrictUndefined)
        environment.filters['to_json'] = json.dumps
        values = yaml.safe_load(environment.from_string(
            (role / 'templates/values.yml.j2').read_text()
        ).render(inputs))
        profiles = [
            values.get(scope, {}).get('seccompProfile', {}).get('type')
            for scope in ('podSecurityContext', 'securityContext')
        ]
        self.assertTrue(
            any(profile in ('RuntimeDefault', 'Localhost') for profile in profiles),
            'The native Collector chart does not add a seccomp profile; the restricted '
            'namespace requires one at pod or container scope before any Collector can start.',
        )


if __name__ == '__main__':
    unittest.main()
