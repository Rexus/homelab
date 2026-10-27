"""Render pinned official delivery charts and exercise product admission without a cluster."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from native_chart_test_support import native_chart_fixture


NATIVE = os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("helm")
CA = "-----BEGIN CERTIFICATE-----\nOFFLINE-RENDER-FIXTURE\n-----END CERTIFICATE-----"


class DeliveryPlatform(TierRepositoryTestCase):
    def inputs(self, **overrides):
        return dict({
            "delivery_platform_controller": "argocd",
            "delivery_platform_output": str(Path(self.temp.name) / "render"),
            "delivery_platform_ingress_class": "accepted-ingress",
            "delivery_platform_oidc_issuer": "https://sso.lab.test/realms/platform",
            "delivery_platform_oidc_ca_pem": CA,
            "delivery_platform_harbor_version": "1.18.0",
            "delivery_platform_harbor_host": "harbor.lab.test",
            "delivery_platform_harbor_storage_class": "accepted-persistent",
            "delivery_platform_harbor_database_password": "offline-render-fixture-database",
            "delivery_platform_argocd_version": "8.5.6",
            "delivery_platform_argocd_host": "argocd.lab.test",
            "delivery_platform_argocd_admin_group": "tier1-admins",
            "delivery_platform_argocd_reader_group": "tier1-readers",
            "delivery_platform_argocd_repositories": ["https://git.lab.test/platform.git"],
            "delivery_platform_argocd_destinations": ["gitlab", "harbor"],
        }, **overrides)

    def run_role(self, repo, inputs, environment=None):
        fixture = Path(self.temp.name) / "inputs.yml"
        fixture.write_text(yaml.safe_dump(inputs))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", "ansible/playbooks/deployment/delivery-platform.yml",
             "-e", f"@{fixture}"], cwd=repo,
            env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"), **(environment or {})),
            capture_output=True, text=True, timeout=300,
        )

    def test_generated_payload_has_tier_owned_products_and_no_implicit_controller(self):
        self.generate()
        repo = self.root / "verify-tier-1"
        defaults = yaml.safe_load((repo / "ansible/roles/delivery_platform/defaults/main.yml").read_text())
        self.assertEqual(defaults["delivery_platform_controller"], "")
        self.assertEqual(defaults["delivery_platform_action"], "render")
        self.assertFalse(defaults["delivery_platform_manage_secrets"])
        self.assertTrue((repo / "ansible/playbooks/deployment/delivery-platform.yml").is_file())
        self.assertTrue((repo / "ansible/group_vars/delivery_platform_secrets.yml.example").is_file())
        self.assertFalse((self.root / "verify-shared/ansible/roles/delivery_platform").exists())

    @unittest.skipUnless(NATIVE, "Requires native Ansible, kubernetes.core and Helm")
    def test_pinned_official_charts_render_source_and_generated_resources(self):
        self.generate()
        chart_inputs, chart_environment = self.enterContext(native_chart_fixture(
            Path(self.temp.name) / "charts", "kube_app"))
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo):
                inputs = self.inputs(delivery_platform_output=str(Path(self.temp.name) / repo.parent.name))
                inputs.update(chart_inputs)
                result = self.run_role(repo, inputs, chart_environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = Path(inputs["delivery_platform_output"])
                # The upstream TLS template uses a legal trailing tab rejected by PyYAML's Python scanner.
                harbor = list(yaml.load_all((output / "harbor-manifests.yml").read_text(), Loader=yaml.CSafeLoader))
                core = next(doc for doc in harbor if doc and doc["kind"] == "Deployment"
                            and doc["metadata"]["name"] == "harbor-core")
                container = core["spec"]["template"]["spec"]["containers"][0]
                oidc = next(item for item in container["env"] if item["name"] == "CONFIG_OVERWRITE_JSON")
                self.assertEqual(oidc["valueFrom"]["secretKeyRef"], {"name": "harbor-oidc", "key": "config.json"})
                self.assertNotIn("value", oidc)
                claims = [doc for doc in harbor if doc and doc["kind"] == "PersistentVolumeClaim"]
                self.assertGreaterEqual(len(claims), 2)
                self.assertTrue(all(doc["spec"]["storageClassName"] == "accepted-persistent" for doc in claims))
                stateful = [doc for doc in harbor if doc and doc["kind"] == "StatefulSet"]
                self.assertTrue(any("database" in doc["metadata"]["name"] for doc in stateful))
                self.assertTrue(any("redis" in doc["metadata"]["name"] for doc in stateful))
                volume_specs = [doc["spec"] for doc in claims]
                volume_specs.extend(claim["spec"] for doc in stateful
                                    for claim in doc["spec"].get("volumeClaimTemplates", []))
                self.assertEqual(len(volume_specs), 5)
                self.assertTrue(all(spec["storageClassName"] == "accepted-persistent" for spec in volume_specs))
                ingress = next(doc for doc in harbor if doc and doc["kind"] == "Ingress")
                self.assertEqual(ingress["spec"]["tls"][0]["secretName"], "harbor-tls")
                argo = [doc for doc in yaml.safe_load_all((output / "argocd-manifests.yml").read_text()) if doc]
                cm = next(doc for doc in argo if doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "argocd-cm")
                oidc = yaml.safe_load(cm["data"]["oidc.config"])
                self.assertEqual(oidc["issuer"], inputs["delivery_platform_oidc_issuer"])
                self.assertEqual(oidc["clientSecret"], "$argocd-oidc:clientSecret")
                self.assertEqual(oidc["rootCA"].strip(), CA)
                rbac = next(doc for doc in argo if doc["kind"] == "ConfigMap"
                            and doc["metadata"]["name"] == "argocd-rbac-cm")
                self.assertEqual(rbac["data"]["policy.default"], "role:no-access")
                self.assertFalse(any(doc["kind"] == "Secret" and doc["metadata"]["name"] == "argocd-secret" for doc in argo))
                projects = list(yaml.safe_load_all((output / "argocd-after.yml").read_text()))
                self.assertEqual(projects[0]["spec"]["destinations"], [])
                self.assertEqual(projects[1]["spec"]["clusterResourceWhitelist"], [])
                self.assertEqual({d["server"] for d in projects[1]["spec"]["destinations"]},
                                 {"https://kubernetes.default.svc"})
                for path in output.iterdir():
                    self.assertEqual(path.stat().st_mode & 0o077, 0, path)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and Helm")
    def test_native_admission_rejects_incomplete_unbounded_and_invalid_oidc_inputs(self):
        cases = [
            {"delivery_platform_controller": ""},
            {"delivery_platform_harbor_version": "latest"},
            {"delivery_platform_argocd_repositories": ["*"]},
            {"delivery_platform_argocd_destinations": ["kube-system"]},
            {"delivery_platform_manage_secrets": True, "delivery_platform_secrets": {}},
            {"delivery_platform_controller": "spinnaker", "delivery_platform_spinnaker_host": "spin.lab.test"},
        ]
        for denied in cases:
            with self.subTest(denied=denied):
                result = self.run_role(UPSTREAM / "tier-1", self.inputs(**denied))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("TASK [helm_release : Render a pinned chart", result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and Helm")
    def test_harbor_native_oidc_secret_is_checked_before_chart_execution(self):
        oidc = {"auth_mode": "oidc_auth", "oidc_endpoint": "https://sso.lab.test/realms/platform",
                "oidc_verify_cert": False, "oidc_client_id": "harbor", "oidc_client_secret": "fixture-only",
                "oidc_scope": "openid profile email"}
        secrets = {
            "harbor/harbor-tls": {"tls.crt": "fixture", "tls.key": "fixture"},
            "harbor/harbor-ca": {"ca.crt": CA},
            "harbor/harbor-admin": {"HARBOR_ADMIN_PASSWORD": "fixture-only"},
            "harbor/harbor-credentials": dict.fromkeys(
                ["secretKey", "secret", "JOBSERVICE_SECRET", "REGISTRY_HTTP_SECRET"], "x" * 16),
            "harbor/harbor-token": {"tls.crt": "fixture", "tls.key": "fixture"},
            "harbor/harbor-oidc": {"config.json": json.dumps(oidc)},
        }
        secrets["harbor/harbor-credentials"]["CSRF_KEY"] = "x" * 32
        secrets["harbor/harbor-credentials"]["REGISTRY_PASSWD"] = "x" * 24
        secrets["harbor/harbor-credentials"]["REGISTRY_HTPASSWD"] = "harbor_registry_user:fixture"
        result = self.run_role(UPSTREAM / "tier-1", self.inputs(
            delivery_platform_controller="none", delivery_platform_manage_secrets=True,
            delivery_platform_secrets=secrets))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Validate Harbor native OIDC", result.stdout)
        self.assertNotIn("TASK [helm_release : Render a pinned chart", result.stdout)


if __name__ == "__main__":
    unittest.main()
