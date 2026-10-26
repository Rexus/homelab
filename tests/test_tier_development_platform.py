"""Real Helm rendering and fail-closed development-platform contracts, without a cluster."""

import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class DevelopmentPlatform(TierRepositoryTestCase):
    def test_generated_ownership_and_privileged_defaults(self):
        self.generate()
        tier0, tier1 = (self.root / f"verify-tier-{n}" for n in (0, 1))
        self.assertIn("infrastructure-runner", (tier0 / ".deployment-setups").read_text())
        self.assertTrue((tier0 / "terraform/deployments/ci-auth/main.tf").is_file())
        self.assertTrue((tier0 / "ci/gitlab-iac.yml.example").is_file())
        self.assertTrue((tier1 / "ansible/roles/development_platform/tasks/release.yml").is_file())
        self.assertIn("jsonpatch", (tier1 / "ansible/requirements.txt").read_text())
        self.assertFalse((self.root / "verify-shared/ansible/inventory").exists())
        defaults = yaml.safe_load((tier0 / "ansible/roles/infrastructure_runner/defaults/main.yml").read_text())
        self.assertIs(defaults["infrastructure_runner_trust_ci_control_plane"], False)
        pipeline = yaml.safe_load((tier0 / "ci/gitlab-iac.yml.example").read_text())
        self.assertNotIn("artifacts", pipeline["iac-plan"])
        self.assertEqual(pipeline["iac-apply"]["when"], "manual")

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("helm"),
                         "Requires Ansible Kubernetes collection and native Helm")
    def test_native_charts_render_source_and_generated_with_scoped_runner(self):
        self.generate()
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo.name):
                output = Path(self.temp.name) / f"render-{repo.parent.name}-{repo.name}"
                inputs = {
                    "development_platform_components": ["gitlab", "runners"],
                    "development_platform_action": "render",
                    "development_platform_output": str(output),
                    "development_platform_gitlab_version": "10.5.0",
                    "development_platform_runner_version": "0.84.0",
                    "development_platform_host": "gitlab.lab.test",
                    "development_platform_domain": "lab.test",
                    "development_platform_ingress_class": "accepted-ingress",
                    "development_platform_database_host": "postgres.lab.test",
                    "development_platform_redis_host": "redis.lab.test",
                    "development_platform_gitaly_host": "gitaly.lab.test",
                    "development_platform_oidc_issuer": "https://sso.lab.test/realms/platform",
                    "development_platform_runner_image": "registry.lab.test/build@sha256:" + "0" * 64,
                    "development_platform_runner_helper_image": "registry.lab.test/helper@sha256:" + "1" * 64,
                    "development_platform_runner_allowed_cidrs": ["192.0.2.10/32"],
                    "development_platform_runner_api_cidrs": ["192.0.2.20/32"],
                }
                fixture = Path(self.temp.name) / "platform-inputs.yml"
                fixture.write_text(yaml.safe_dump(inputs))
                environment = dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"))
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", "ansible/playbooks/deployment/development-platform.yml",
                     "-e", f"@{fixture}"],
                    cwd=repo, env=environment, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                values = yaml.safe_load((output / "gitlab-values.yml").read_text())
                self.assertFalse(values["global"]["gitaly"]["enabled"])
                self.assertEqual(values["global"]["psql"]["sslMode"], "verify-full")
                self.assertEqual(values["global"]["psql"]["ssl"]["serverCA"], "ca.crt")
                self.assertEqual(values["global"]["shell"]["authToken"],
                                 {"secret": "gitlab-shell-auth", "key": "secret"})
                self.assertFalse(values["gitlab-runner"]["install"])
                self.assertTrue(values["global"]["appConfig"]["omniauth"]["blockAutoCreatedUsers"])
                manifests = [doc for doc in yaml.safe_load_all((output / "gitlab-manifests.yml").read_text()) if doc]
                web = next(doc for doc in manifests if doc["kind"] == "Deployment" and "webservice" in doc["metadata"]["name"])
                volumes = web["spec"]["template"]["spec"]["volumes"]
                self.assertTrue(any("gitlab-postgresql-tls" in str(volume) for volume in volumes))
                rendered_config = "\n".join(str(doc.get("data", {})) for doc in manifests
                                            if doc["kind"] == "ConfigMap")
                self.assertIn("sslrootcert", rendered_config)
                self.assertIn("client-certificate.pem", rendered_config)
                self.assertIn("PGSSLMODE", str(web))
                autoscaler = next(doc for doc in manifests if doc["kind"] == "HorizontalPodAutoscaler"
                                  and doc["spec"]["scaleTargetRef"]["name"] == web["metadata"]["name"])
                self.assertEqual(autoscaler["spec"]["minReplicas"], 2)
                self.assertEqual(autoscaler["spec"]["maxReplicas"], 2)
                self.assertFalse(any(doc["kind"] == "StatefulSet" and "gitaly" in doc["metadata"]["name"] for doc in manifests))
                runner = yaml.safe_load((output / "gitlab-runner-values.yml").read_text())
                config = tomllib.loads(runner["runners"]["config"])["runners"][0]["kubernetes"]
                self.assertFalse(config["privileged"])
                self.assertFalse(config["automount_service_account_token"])
                self.assertEqual(config["service_account"], "ci-job")
                rendered = [doc for doc in yaml.safe_load_all((output / "gitlab-runner-manifests.yml").read_text()) if doc]
                manager = next(doc for doc in rendered if doc["kind"] == "Deployment")
                self.assertEqual(manager["spec"]["template"]["metadata"]["labels"]["app"], "gitlab-runner")
                self.assertFalse(any(doc["kind"] == "ClusterRole" for doc in rendered))
                for role in (doc for doc in rendered if doc["kind"] == "Role"):
                    for rule in role["rules"]:
                        self.assertNotIn("*", rule["verbs"])
                        self.assertNotIn("*", rule["resources"])
                support = list(yaml.safe_load_all((output / "gitlab-runner-support.yml").read_text()))
                self.assertFalse(support[0]["automountServiceAccountToken"])
                for path in output.iterdir():
                    self.assertEqual(path.stat().st_mode & 0o077, 0)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires native Ansible")
    def test_infrastructure_runner_refuses_implicit_trust_before_install(self):
        play = Path(self.temp.name) / "reject-runner.yml"
        role = UPSTREAM / "tier-0/ansible/roles/infrastructure_runner"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": {"ansible_os_family": "RedHat"},
            "roles": [str(role)],
        }]))
        result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("TASK [infrastructure_runner : Install approved signed", result.stdout)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires native Ansible and network-validation collection")
    def test_application_preflight_rejects_incomplete_and_unbounded_inputs(self):
        role = UPSTREAM / "tier-1/ansible/roles/development_platform"
        play = Path(self.temp.name) / "guard.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "roles": [str(role)],
        }]))
        valid = {
            "development_platform_host": "gitlab.lab.test",
            "development_platform_runner_version": "0.84.0",
            "development_platform_runner_image": "registry.lab.test/build@sha256:" + "0" * 64,
            "development_platform_runner_helper_image": "registry.lab.test/helper@sha256:" + "1" * 64,
            "development_platform_runner_allowed_cidrs": ["192.0.2.1/32"],
            "development_platform_runner_api_cidrs": ["192.0.2.2/32"],
        }
        cases = [
            {"development_platform_components": ["gitlab"]},
            {"development_platform_components": ["runners"], "development_platform_runner_image": "image:latest"},
            {"development_platform_components": ["runners"], "development_platform_runner_allowed_cidrs": ["0.0.0.0/0"]},
            {"development_platform_components": ["runners"], "development_platform_runner_api_cidrs": ["not-a-network"]},
        ]
        for inputs in cases:
            with self.subTest(inputs=inputs):
                fixture = Path(self.temp.name) / "guard-inputs.yml"
                fixture.write_text(yaml.safe_dump(dict(valid, **inputs)))
                result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", f"@{fixture}"],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("TASK [development_platform : Prepare private", result.stdout)


if __name__ == "__main__":
    unittest.main()
