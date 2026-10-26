"""Render pinned official delivery charts and exercise product admission without a cluster."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


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

    def run_role(self, repo, inputs):
        fixture = Path(self.temp.name) / "inputs.yml"
        fixture.write_text(yaml.safe_dump(inputs))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", "ansible/playbooks/deployment/delivery-platform.yml",
             "-e", f"@{fixture}"], cwd=repo,
            env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
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
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo):
                inputs = self.inputs(delivery_platform_output=str(Path(self.temp.name) / repo.parent.name))
                result = self.run_role(repo, inputs)
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

    def spinnaker_overlay(self, repo, image="ghcr.io/spinnaker/gate:2025.3.2", cluster_authority=False):
        overlay = repo / "clusters/tier1/platform/spinnaker-test"
        overlay.mkdir(parents=True)
        services = ["clouddriver", "deck", "echo", "fiat", "front50", "gate", "orca", "rosco"]
        resources = [{
            "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": name},
            "spec": {"selector": {"matchLabels": {"app": name}}, "template": {
                "metadata": {"labels": {"app": name}}, "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [{"name": name, "image": image,
                                    "volumeMounts": [{"name": "runtime", "mountPath": "/opt/spinnaker/config/"}],
                                    "securityContext": {"allowPrivilegeEscalation": False}}],
                    "volumes": [{"name": "runtime", "secret": {"secretName": "spinnaker-runtime"}}],
                }}},
        } for name in services]
        resources.append({"apiVersion": "networking.k8s.io/v1", "kind": "Ingress",
                          "metadata": {"name": "spinnaker"}, "spec": {
                              "tls": [{"secretName": "spinnaker-tls", "hosts": ["spin.lab.test"]}],
                              "rules": [{"host": "spin.lab.test", "http": {"paths": []}}]}})
        if cluster_authority:
            resources.append({"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
                              "metadata": {"name": "demo-admin"}})
        (overlay / "resources.yml").write_text(yaml.safe_dump_all(resources))
        (overlay / "kustomization.yaml").write_text(yaml.safe_dump({
            "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
            "namespace": "spinnaker", "resources": ["resources.yml"],
        }))
        return overlay

    @unittest.skipUnless(NATIVE and (shutil.which("kubectl") or shutil.which("kustomize")),
                         "Requires native Ansible and Kustomize or kubectl")
    def test_native_kustomize_render_requires_complete_pinned_scoped_review(self):
        self.generate()
        repo = self.root / "verify-tier-1"
        overlay = self.spinnaker_overlay(repo)
        inputs = self.inputs(delivery_platform_controller="spinnaker", delivery_platform_install_harbor=False,
                             delivery_platform_spinnaker_host="spin.lab.test",
                             delivery_platform_spinnaker_overlay=str(overlay))
        result = self.run_role(repo, inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = Path(inputs["delivery_platform_output"])
        render = (output / "spinnaker-manifests.yml").read_bytes()
        self.assertEqual((output / "spinnaker.sha256").read_text().strip(), hashlib.sha256(render).hexdigest())
        resources = list(yaml.safe_load_all(render))
        self.assertEqual(sum(doc["kind"] == "Deployment" for doc in resources), 8)
        for image, authority in (("ghcr.io/spinnaker/gate:main-latest", False),
                                 ("ghcr.io/spinnaker/gate:2025.3.2", True)):
            shutil.rmtree(overlay)
            self.spinnaker_overlay(repo, image=image, cluster_authority=authority)
            result = self.run_role(repo, inputs)
            self.assertNotEqual(result.returncode, 0)
        # Rejection occurs before any Kubernetes API operation.
        shutil.rmtree(overlay)
        self.spinnaker_overlay(repo)
        result = self.run_role(repo, dict(inputs, delivery_platform_action="apply",
                                         delivery_platform_kubeconfig="/nonexistent/offline-test",
                                         delivery_platform_context="offline-test",
                                         delivery_platform_ca_path="/nonexistent/offline-ca",
                                         delivery_platform_spinnaker_review_sha256="0" * 64))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("TASK [delivery_platform : Check every existing credential", result.stdout)

    @unittest.skipUnless(NATIVE and shutil.which("kustomize"), "Requires native Kustomize, Ansible and Git")
    def test_pinned_official_spinnaker_kustomize_demo_is_not_accepted_as_production(self):
        self.generate()
        repo = self.root / "verify-tier-1"
        vendor = repo / "clusters/tier1/platform/spinnaker-upstream"
        vendor.mkdir(parents=True)
        revision = "d2eaa598c95d0a8e17736f2df61fa1fa9f738b53"
        for args in (["init", "--quiet"], ["remote", "add", "origin", "https://github.com/spinnaker/spinnaker.git"],
                     ["sparse-checkout", "set", "spinnaker-kustomize"],
                     ["fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", revision],
                     ["checkout", "--quiet", "--detach", "FETCH_HEAD"]):
            subprocess.run(["git", "-C", str(vendor), *args], capture_output=True, text=True,
                           timeout=180, check=True)
        overlay = vendor / "spinnaker-kustomize"
        native = subprocess.run(["kustomize", "build", str(overlay)], capture_output=True,
                                text=True, timeout=60, check=True)
        documents = list(yaml.safe_load_all(native.stdout))
        self.assertTrue(any(doc["kind"] == "Deployment" for doc in documents))
        self.assertIn("main-latest", native.stdout)
        inputs = self.inputs(delivery_platform_controller="spinnaker", delivery_platform_install_harbor=False,
                             delivery_platform_spinnaker_host="spin.lab.test",
                             delivery_platform_spinnaker_overlay=str(overlay))
        result = self.run_role(repo, inputs)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("TASK [delivery_platform : Apply the reviewed Spinnaker", result.stdout)


if __name__ == "__main__":
    unittest.main()
