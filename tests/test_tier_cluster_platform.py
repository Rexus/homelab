"""Tier-owned platform contracts, native readiness predicates and real Helm renders."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / "shared/ansible/roles/cluster_platform"
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
# Test fixtures only; production pins remain explicit operator inputs.
PINS = {
    "cilium": "1.18.0", "storage": "4.11.0", "cert_manager": "1.18.2",
    "ingress": "37.1.1", "cloudnative_pg": "0.26.0", "barman_cloud": "0.8.1", "flux": "2.16.4",
}
NATIVE = os.name != "nt" and bool(shutil.which("ansible-playbook"))
CHARTS = NATIVE and bool(shutil.which("helm")) and os.getenv("HOMELAB_NATIVE_CHART_TESTS") == "1"


def inputs(output):
    return {
        "cluster_platform_action": "render",
        "cluster_platform_output": str(output),
        "cluster_platform_kubeconfig": "/nonexistent/never-contact-kubernetes",
        "cluster_platform_context": "never-contact-kubernetes",
        "cluster_platform_versions": PINS,
        "cluster_platform_approved_repositories": [c["repository"] for c in DEFAULTS["cluster_platform_catalog"].values()],
        "cluster_platform_talos_cilium_ready": True,
        "cluster_platform_expected_nodes": ["k8ctl-1", "k8ctl-2", "k8ctl-3"],
        "cluster_platform_storage_provider": "nfs",
        "cluster_platform_storage_class": "nfs-test",
        "cluster_platform_nfs_prerequisites_accepted": True,
        "cluster_platform_nfs_server": "nas.lab.test",
        "cluster_platform_nfs_share": "/exports/platform",
        "cluster_platform_database_enabled": True,
        "cluster_platform_database_image": "ghcr.io/cloudnative-pg/postgresql:17.6@sha256:" + "0" * 64,
        "cluster_platform_database_image_approved": True,
        "cluster_platform_issuer_spec": {
            "acme": {
                "server": "https://qualified-acme.lab.test/directory", "email": "operator@lab.test",
                "privateKeySecretRef": {"name": "platform-acme-account"},
                "solvers": [{"http01": {"ingress": {"ingressClassName": "traefik"}}}],
            },
        },
        "cluster_platform_certificate_dns_names": ["tls.lab.test"],
        "cluster_platform_flux_source_approved": True,
        "cluster_platform_flux_url": "https://bootstrap.lab.test/control.git",
        "cluster_platform_flux_commit": "a" * 40,
        "cluster_platform_flux_path": "./clusters/tier0",
        "cluster_platform_flux_canary_sha256": hashlib.sha256(b"platform-sops-ok").hexdigest(),
    }


class ClusterPlatform(TierRepositoryTestCase):
    def run_role(self, variables, repo=None):
        repo = repo or UPSTREAM / "tier-0"
        fixture = Path(self.temp.name) / "platform-inputs.json"
        fixture.write_text(json.dumps(variables))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", "playbooks/deployment/cluster-platform.yml", "-e", "@" + str(fixture)],
            cwd=repo / "ansible", capture_output=True, text=True,
            env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"),
                     ANSIBLE_LOCAL_TEMP=str(Path(self.temp.name) / "ansible-local")),
        )

    def test_generated_execution_is_shared_but_inputs_stay_with_cluster_owner(self):
        self.generate()
        tier = self.root / "verify-tier-0"
        for relative in (
            "ansible/playbooks/deployment/cluster-platform.yml",
            "ansible/group_vars/cluster_platform.yml.example",
            "ansible/group_vars/cluster_platform_secrets.yml.example",
        ):
            self.assertTrue((tier / relative).is_file(), relative)
        shared = self.root / 'verify-shared/ansible/roles/cluster_platform'
        self.assertTrue((shared / 'tasks/main.yml').is_file())
        self.assertTrue((shared / 'templates/flux.yml.j2').is_file())
        self.assertFalse((tier / 'ansible/roles/cluster_platform').exists())
        self.assertFalse((self.root / "verify-shared/ansible/inventory").exists())
        self.assertEqual(DEFAULTS["cluster_platform_flux_path"], "")
        self.assertEqual(DEFAULTS["cluster_platform_expected_nodes"], [])

    def test_native_execution_delegates_and_all_api_calls_use_target_and_tls(self):
        product = yaml.safe_load((ROLE / "tasks/product.yml").read_text())
        delegation = next(t for t in product if "ansible.builtin.include_role" in t)
        self.assertEqual(delegation["ansible.builtin.include_role"]["name"], "kubernetes_applications")
        self.assertEqual(delegation["vars"]["kube_apps_context"], "{{ cluster_platform_context }}")
        for path in (ROLE / "tasks").glob("*.yml"):
            for task in yaml.safe_load(path.read_text()):
                self.assertFalse({"ansible.builtin.shell", "ansible.builtin.command", "kubernetes.core.helm"} & task.keys())
                if "kubernetes.core.k8s_info" in task:
                    call = task["kubernetes.core.k8s_info"]
                    self.assertIs(call["validate_certs"], True)
                    self.assertIn("cluster_platform_kubeconfig", call["kubeconfig"])
                    self.assertIn("cluster_platform_context", call["context"])

    @unittest.skipUnless(NATIVE, "Requires native Ansible and kubernetes.core on Linux/WSL")
    def test_invalid_inputs_fail_before_any_chart_or_cluster_work(self):
        failures = [
            {"cluster_platform_versions": {}},
            {"cluster_platform_versions": dict(PINS, cilium="latest")},
            {"cluster_platform_approved_repositories": []},
            {"cluster_platform_talos_cilium_ready": False},
            {"cluster_platform_nfs_prerequisites_accepted": False},
            {"cluster_platform_flux_commit": "main"},
            {"cluster_platform_flux_source_approved": False},
            {"cluster_platform_issuer_spec": {"ca": {"secretName": "forbidden-ca-key"}}},
            {"cluster_platform_database_image": "ghcr.io/cloudnative-pg/postgresql@sha256:" + "0" * 64},
            {"cluster_platform_values": {"cilium": {"cgroup": {"autoMount": {"enabled": True}}}}},
        ]
        for i, overrides in enumerate(failures):
            with self.subTest(overrides=overrides):
                output = Path(self.temp.name) / f"rejected-{i}"
                result = self.run_role(dict(inputs(output), **overrides))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("assertion", result.stdout)
                self.assertFalse(output.exists(), result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible predicate evaluation on Linux/WSL")
    def test_health_predicates_reject_absent_stale_and_zero_workloads(self):
        gate = yaml.safe_load((ROLE / "tasks/health.yml").read_text())[0]
        predicates = gate["until"]
        healthy = {
            "metadata": {"generation": 2}, "spec": {"replicas": 1},
            "status": {"observedGeneration": 2, "replicas": 1, "updatedReplicas": 1, "availableReplicas": 1},
        }
        cases = [
            ("absent", "Deployment", None, False, {}),
            ("ready", "Deployment", healthy, True, {}),
            ("stale", "Deployment", dict(healthy, status=dict(healthy["status"], observedGeneration=1)), False, {}),
            ("scaled-zero", "Deployment", dict(healthy, spec={"replicas": 0}, status={}), False, {}),
            ("old-pods", "Deployment", dict(healthy, status=dict(healthy["status"], replicas=2)), False, {}),
            ("empty-ds", "DaemonSet", {"metadata": {"generation": 1}, "status": {}}, False, {}),
            ("stale-certificate", "Certificate", {
                "metadata": {"generation": 2},
                "status": {"conditions": [{"type": "Ready", "status": "True", "observedGeneration": 1}]},
            }, False, {"condition": "Ready"}),
            ("stale-flux", "Kustomization", {
                "metadata": {"generation": 2},
                "status": {"observedGeneration": 1, "conditions": [{"type": "Ready", "status": "True"}],
                           "lastAppliedRevision": "sha1:" + "a" * 40},
            }, False, {"condition": "Ready", "revision": "a" * 40}),
        ]
        tasks = []
        for name, kind, resource, expected, extra in cases:
            tasks.append({
                "name": name,
                "ansible.builtin.assert": {"that": ["(" + ") and (".join(predicates) + ")" if expected else
                                                         "not ((" + ") and (".join(predicates) + "))"]},
                "vars": dict(gate["vars"], cluster_platform_observed={"resources": [resource] if resource else []},
                             cluster_platform_health=dict(kind=kind, **extra)),
            })
        fixture = Path(self.temp.name) / "health.yml"
        fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False, "tasks": tasks}]))
        result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(fixture)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(CHARTS, "Set HOMELAB_NATIVE_CHART_TESTS=1 with native Ansible, Helm and repository access")
    def test_real_pinned_charts_render_without_cluster_source_and_generated(self):
        self.generate()
        # Keep privacy assertions on a POSIX filesystem, including when the checkout is on drvfs.
        render_temp = tempfile.TemporaryDirectory(prefix="homelab-platform-render-")
        self.addCleanup(render_temp.cleanup)
        for i, repo in enumerate((UPSTREAM / "tier-0", self.root / "verify-tier-0")):
            with self.subTest(repo=str(repo)):
                output = Path(render_temp.name) / f"native-{i}"
                result = self.run_role(inputs(output), repo)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                rendered = {}
                for component, chart in DEFAULTS["cluster_platform_catalog"].items():
                    path = output / f"{chart['name']}-manifests.yml"
                    resources = [r for r in yaml.safe_load_all(path.read_text()) if r]
                    rendered[component] = resources
                    for health in chart["health"]:
                        self.assertTrue(any(r["kind"] == health["kind"] and r["metadata"]["name"] == health["name"]
                                            for r in resources) or health["name"] == "coredns", health)
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                cilium = next(r for r in rendered["cilium"] if r["kind"] == "DaemonSet" and r["metadata"]["name"] == "cilium")
                pod = cilium["spec"]["template"]["spec"]
                self.assertFalse(any(c["name"] in ["mount-cgroup", "mount-bpf-fs"] for c in pod["initContainers"]))
                for container in pod["containers"] + pod["initContainers"]:
                    self.assertNotIn("SYS_MODULE", container.get("securityContext", {}).get("capabilities", {}).get("add", []))
                nfs = yaml.safe_load((output / "csi-driver-nfs-after.yml").read_text())
                self.assertEqual(nfs["reclaimPolicy"], "Retain")
                self.assertNotIn("storageclass.kubernetes.io/is-default-class", nfs["metadata"].get("annotations", {}))
                ingress = next(r for r in rendered["ingress"] if r["kind"] == "Service" and r["metadata"]["name"] == "traefik")
                self.assertEqual(ingress["spec"]["type"], "NodePort")
                self.assertEqual({p["nodePort"] for p in ingress["spec"]["ports"]}, {30080, 30443})
                self.assertTrue(any(r['kind'] == 'CustomResourceDefinition' and
                                    r['metadata']['name'] == 'serverstransports.traefik.io'
                                    for r in rendered['ingress']))
                flux = list(yaml.safe_load_all((output / "flux2-after.yml").read_text()))
                self.assertEqual(flux[0]["spec"]["ref"], {"commit": "a" * 40})
                self.assertEqual(flux[1]["spec"]["decryption"]["secretRef"], {"name": "sops-age"})
                database = list(yaml.safe_load_all((output / "cloudnative-pg-after.yml").read_text()))[1]
                self.assertEqual(database["spec"]["storage"]["storageClass"], "nfs-test")
                self.assertFalse(database["spec"]["enableSuperuserAccess"])


if __name__ == "__main__":
    unittest.main()
