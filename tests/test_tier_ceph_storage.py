"""Ceph RBD ownership guards and real native chart renders without cluster access."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml


UPSTREAM = Path(__file__).resolve().parents[1]
ROLE = UPSTREAM / "shared/ansible/roles/cluster_platform"
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
NATIVE = os.name != "nt" and bool(shutil.which("ansible-playbook"))
CHARTS = NATIVE and bool(shutil.which("helm")) and os.getenv("HOMELAB_NATIVE_CHART_TESTS") == "1"
DIGEST = "@sha256:" + "0" * 64  # Deliberately unusable test pins, never deployed.


def inputs(output):
    images = {
        "nodeplugin": {
            "plugin": ("quay.io/cephcsi/cephcsi", "v3.17.1"),
            "registrar": ("registry.k8s.io/sig-storage/csi-node-driver-registrar", "v2.16.0"),
        },
        "provisioner": {
            "provisioner": ("registry.k8s.io/sig-storage/csi-provisioner", "v6.3.0"),
            "attacher": ("registry.k8s.io/sig-storage/csi-attacher", "v4.11.0"),
            "resizer": ("registry.k8s.io/sig-storage/csi-resizer", "v2.0.0"),
            "snapshotter": ("registry.k8s.io/sig-storage/csi-snapshotter", "v8.6.0"),
        },
    }
    return dict(
        cluster_platform_action="render", cluster_platform_output=str(output),
        cluster_platform_kubeconfig="/nonexistent/never-contact-kubernetes",
        cluster_platform_context="never-contact-kubernetes", cluster_platform_components=["storage"],
        cluster_platform_versions={"storage": "3.17.1"},
        cluster_platform_approved_repositories=["https://ceph.github.io/csi-charts"],
        cluster_platform_expected_nodes=["consumer-1"], cluster_platform_storage_provider="ceph_rbd",
        cluster_platform_storage_class="ceph-block-test", cluster_platform_ceph_rbd_prerequisites_accepted=True,
        cluster_platform_talos_ceph_rbd_ready=True, cluster_platform_ceph_rbd_images_approved=True,
        cluster_platform_ceph_rbd_fsid="12345678-1234-1234-1234-123456789abc",
        cluster_platform_ceph_rbd_monitors=["mon.lab.test:6789", "[2001:db8::1]:3300"],
        cluster_platform_ceph_rbd_pool="kubernetes-test", cluster_platform_ceph_rbd_user_id="tier-test",
        cluster_platform_values={"storage": {
            group: {name: {"image": {"repository": repo, "tag": tag + DIGEST}}
                    for name, (repo, tag) in entries.items()} for group, entries in images.items()
        }},
    )


class CephStorage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="homelab-ceph-test-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "rendered"

    def run_play(self, variables, tier="tier-0", tasks=None, entrypoint=False):
        repo = UPSTREAM / tier / "ansible"
        fixture = Path(self.temp.name) / "inputs.json"
        fixture.write_text(json.dumps(variables))
        playbook = repo / "playbooks/deployment/cluster-platform.yml"
        if not entrypoint:
            playbook = Path(self.temp.name) / "verify.yml"
            playbook.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"ansible_python_interpreter": "{{ ansible_playbook_python }}"},
                "tasks": tasks if tasks is not None else [
                    {"ansible.builtin.import_role": {"name": "cluster_platform"}},
                ],
            }]))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook), "-e", "@" + str(fixture)],
            cwd=repo, capture_output=True, text=True,
            env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible.cfg"),
                     CONTROL_NODE_COLLECTIONS_MODE="check",
                     ANSIBLE_ROLES_PATH=str(UPSTREAM / "shared/ansible/roles"),
                     ANSIBLE_LOCAL_TEMP=str(Path(self.temp.name) / "ansible-local")),
        )

    def test_template_references_scoped_secret_and_retains_rbd_data(self):
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters["to_json"] = json.dumps
        selected = yaml.safe_load(env.from_string((ROLE / "templates/ceph-rbd.yml.j2").read_text()).render(
            **dict(DEFAULTS, **inputs(self.output))))
        storage_class = selected["after"][0]
        self.assertEqual(storage_class["provisioner"], "rbd.csi.ceph.com")
        self.assertEqual(storage_class["reclaimPolicy"], "Retain")
        self.assertTrue(storage_class["allowVolumeExpansion"])
        self.assertNotIn("annotations", storage_class["metadata"])
        self.assertEqual(storage_class["parameters"]["mounter"], "rbd")
        for operation in ("provisioner", "controller-expand", "node-stage"):
            self.assertEqual(storage_class["parameters"][f"csi.storage.k8s.io/{operation}-secret-name"], "csi-rbd-secret")
            self.assertEqual(storage_class["parameters"][f"csi.storage.k8s.io/{operation}-secret-namespace"], "ceph-csi-rbd")
        self.assertEqual(selected["required_secrets"], [{"name": "csi-rbd-secret", "keys": ["userID", "userKey"]}])
        self.assertEqual(selected["values"]["secret"], {"create": False})

    def test_all_tier_examples_offer_ceph_without_changing_existing_default(self):
        for tier in range(3):
            example = yaml.safe_load((UPSTREAM / f"tier-{tier}/ansible/group_vars/cluster_platform.yml.example").read_text())
            self.assertEqual(example["cluster_platform_storage_provider"], "existing")
            self.assertFalse(example["cluster_platform_ceph_rbd_images_approved"])
            self.assertFalse(example["cluster_platform_talos_ceph_rbd_ready"])
            self.assertIn("snapshotter", example["cluster_platform_values"]["storage"]["provisioner"])

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_bad_inputs_and_unsafe_overrides_fail_before_chart_or_cluster_work(self):
        failures = [
            {"cluster_platform_versions": {"storage": "latest"}},
            {"cluster_platform_approved_repositories": []},
            {"cluster_platform_ceph_rbd_prerequisites_accepted": False},
            {"cluster_platform_talos_ceph_rbd_ready": False},
            {"cluster_platform_ceph_rbd_images_approved": False},
            {"cluster_platform_ceph_rbd_fsid": "not-a-fsid"},
            {"cluster_platform_ceph_rbd_monitors": ["mon.lab.test:99999"]},
            {"cluster_platform_ceph_rbd_monitors": "mon.lab.test:6789"},
            {"cluster_platform_ceph_rbd_user_id": "admin"},
            {"cluster_platform_ceph_rbd_image_features": ["fast-diff"]},
        ]
        for override in ({"kubeletDir": "/wrong"}, {"cephLogDirHostPath": "/var/log/ceph"},
                         {"driverName": "other.csi.ceph.com"}, {"secret": {"create": True}},
                         {"csiConfig": []}, {"nodeplugin": {"plugin": {"image": {"tag": "canary"}}}}):
            values = copy.deepcopy(inputs(self.output)["cluster_platform_values"])
            for key, value in override.items():
                if key == "nodeplugin":
                    values["storage"][key]["plugin"]["image"]["tag"] = "canary"
                else:
                    values["storage"][key] = value
            failures.append({"cluster_platform_values": values})
        for override in failures:
            with self.subTest(override=override):
                result = self.run_play(dict(inputs(self.output), **override))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('"evaluated_to": false', result.stdout, result.stdout + result.stderr)
                self.assertFalse(self.output.exists(), result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_assembly_keeps_secrets_private_and_rejects_wrong_scoped_identity(self):
        variables = inputs(self.output)
        variables.update(cluster_platform_manage_secrets=True, cluster_platform_secrets={
            "ceph-csi-rbd/csi-rbd-secret": {"userID": "tier-test", "userKey": "PRIVATE-TEST-SENTINEL"},
        })
        tasks = [
            {"ansible.builtin.import_role": {"name": "cluster_platform", "tasks_from": "preflight"}},
            {"ansible.builtin.set_fact": {"cluster_platform_releases": []}},
            {"ansible.builtin.import_role": {"name": "cluster_platform", "tasks_from": "assemble"},
             "vars": {"cluster_platform_component": "storage"}},
            {"ansible.builtin.import_role": {"name": "cluster_platform", "tasks_from": "ceph-rbd-values"}},
            {"ansible.builtin.assert": {"that": [
                "cluster_platform_releases[0].name == 'ceph-csi-rbd'",
                "cluster_platform_releases[0].health[0].name == 'ceph-csi-rbd-provisioner'",
                "'PRIVATE-TEST-SENTINEL' not in (cluster_platform_releases | to_json)",
            ]}},
        ]
        result = self.run_play(variables, tasks=tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("PRIVATE-TEST-SENTINEL", result.stdout + result.stderr)
        variables["cluster_platform_secrets"]["ceph-csi-rbd/csi-rbd-secret"]["userID"] = "admin"
        result = self.run_play(variables, tasks=tasks)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PRIVATE-TEST-SENTINEL", result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_existing_storage_needs_no_chart_pin_or_ceph_credentials(self):
        result = self.run_play({
            "cluster_platform_action": "render", "cluster_platform_components": ["storage"],
            "cluster_platform_storage_provider": "existing", "cluster_platform_storage_class": "accepted-csi",
            "cluster_platform_existing_storage_accepted": True, "cluster_platform_output": str(self.output),
        })
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_node_registration_gate_rejects_absent_or_wrong_driver(self):
        gate = next(task for task in yaml.safe_load((ROLE / "tasks/storage.yml").read_text()) if "until" in task)
        predicates = "(" + ") and (".join(gate["until"]) + ")"
        tasks = []
        for resources, accepted in (([], False), ([{"spec": {"drivers": []}}], False),
                                    ([{"spec": {"drivers": [{"name": "nfs.csi.k8s.io"}]}}], False),
                                    ([{"spec": {"drivers": [{"name": "rbd.csi.ceph.com"}]}}], True)):
            tasks.append({
                "ansible.builtin.assert": {"that": [predicates if accepted else "not (" + predicates + ")"]},
                "vars": {"cluster_platform_csi_node": {"resources": resources}},
            })
        result = self.run_play({}, tasks=tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(CHARTS, "Set HOMELAB_NATIVE_CHART_TESTS=1 with Ansible, Helm and chart access")
    def test_nfs_chart_still_renders_with_original_contract(self):
        variables = inputs(self.output)
        variables.update(cluster_platform_storage_provider="nfs", cluster_platform_versions={"storage": "4.11.0"},
                         cluster_platform_values={}, cluster_platform_nfs_prerequisites_accepted=True,
                         cluster_platform_nfs_server="nas.lab.test", cluster_platform_nfs_share="/exports/test",
                         cluster_platform_approved_repositories=[DEFAULTS["cluster_platform_catalog"]["storage"]["repository"]])
        result = self.run_play(variables, entrypoint=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        storage_class = yaml.safe_load((self.output / "csi-driver-nfs-after.yml").read_text())
        self.assertEqual(storage_class["provisioner"], "nfs.csi.k8s.io")
        self.assertEqual(storage_class["reclaimPolicy"], "Retain")

    @unittest.skipUnless(CHARTS, "Set HOMELAB_NATIVE_CHART_TESTS=1 with Ansible, Helm and chart access")
    def test_native_chart_renders_for_each_tier_without_api_or_credential_leak(self):
        for tier in range(3):
            with self.subTest(tier=tier):
                variables = inputs(self.output)
                variables.update(cluster_platform_manage_secrets=True, cluster_platform_secrets={
                    "ceph-csi-rbd/csi-rbd-secret": {"userID": "tier-test", "userKey": "PRIVATE-TEST-SENTINEL"},
                })
                result = self.run_play(variables, f"tier-{tier}", entrypoint=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("PRIVATE-TEST-SENTINEL", result.stdout + result.stderr)
                resources = list(yaml.safe_load_all((self.output / "ceph-csi-rbd-manifests.yml").read_text()))
                for expected in DEFAULTS["cluster_platform_ceph_rbd_chart"]["health"]:
                    self.assertTrue(any(r and r["kind"] == expected["kind"] and
                                        r["metadata"]["name"] == expected["name"] for r in resources), expected)
                self.assertFalse(any(r and r["kind"] in ("Secret", "StorageClass", "CephCluster") for r in resources))
                for resource in resources:
                    if resource and resource["kind"] in ("Deployment", "DaemonSet"):
                        pod = resource["spec"]["template"]["spec"]
                        for container in pod.get("containers", []) + pod.get("initContainers", []):
                            self.assertTrue(container["image"].endswith(DIGEST), container["image"])
                        if resource["kind"] == "DaemonSet":
                            paths = {v["hostPath"]["path"] for v in pod["volumes"] if "hostPath" in v}
                            self.assertIn("/var/lib/ceph-csi", paths)
                            self.assertIn("/var/lib/kubelet/plugins/rbd.csi.ceph.com", paths)
                            self.assertNotIn("/etc/selinux", paths)
                for path in self.output.iterdir():
                    self.assertNotIn("PRIVATE-TEST-SENTINEL", path.read_text())
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
