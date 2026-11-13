"""Native offline creation, identity guards and preservation of NAS backup storage."""

import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from backup_storage_api_support import BackupStorageAPI
from tier_repo_test_support import TierRepositoryTestCase


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "shared/ansible/roles/backup_repository_storage"
NATIVE = os.name != "nt" and shutil.which("ansible-playbook")


class BackupStorageGeneration(TierRepositoryTestCase):
    def test_shared_helper_is_available_in_generated_collections(self):
        self.generate()
        destination = self.root / 'verify-shared/ansible/roles/backup_repository_storage'
        for path in ROLE.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (destination / path.relative_to(ROLE)).read_bytes())

    def test_guard_expressions_are_scalars_not_yaml_mappings(self):
        for path in (ROLE / 'tasks').glob('*.yml'):
            for task in yaml.safe_load(path.read_text()):
                for expression in task.get('ansible.builtin.assert', {}).get('that', []):
                    self.assertIsInstance(expression, (str, bool), (path, expression))


@unittest.skipUnless(NATIVE, "Requires native Ansible and kubernetes.core")
class BackupRepositoryStorage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="backup-storage-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.values = dict(backup_repository_storage_action="render",
                          ansible_python_interpreter=sys.executable,
                          backup_repository_storage_output=str(self.work / "output"),
                          backup_repository_storage_owner="postgresql-file-backup/keycloak/keycloak-db",
                          backup_repository_storage_namespace="keycloak",
                          backup_repository_storage_claim="keycloak-db-backups",
                          backup_repository_storage_volume={"mode": "static_nfs", "server": "nas.lab.test",
                              "share": "/backups/keycloak", "size": "100Gi", "volume_handle": "nas-keycloak"})

    def run_play(self, values=None, tasks=None, plays=None):
        play = self.work / "play.yml"
        play.write_text(yaml.safe_dump(plays or [{"hosts": "localhost", "connection": "local",
            "gather_facts": False, "vars": {"ansible_python_interpreter": sys.executable} | (values or self.values),
            "tasks": tasks or [{"ansible.builtin.include_role": {"name": "backup_repository_storage"}}]}]))
        env = dict(os.environ, ANSIBLE_ROLES_PATH=os.pathsep.join([
            str(ROLE.parent), str(ROOT / "tier-0/ansible/roles"), str(ROOT / "tier-1/ansible/roles")]),
            ANSIBLE_LOCAL_TEMP=str(self.work / "ansible"), NO_PROXY="127.0.0.1,localhost",
            no_proxy="127.0.0.1,localhost")
        return subprocess.run(["ansible-playbook", "-i", "localhost,", str(play)], env=env,
                              capture_output=True, text=True, timeout=180)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def documents(self):
        path = self.work / "output/keycloak-keycloak-db-backups-storage.yml"
        return list(yaml.safe_load_all(path.read_text()))

    def api(self):
        api = BackupStorageAPI()
        self.addCleanup(api.close)
        config = self.work / "kubeconfig"
        config.write_text(yaml.safe_dump(api.kubeconfig()))
        self.values.update(backup_repository_storage_action="apply", backup_repository_storage_kubeconfig=str(config))
        return api

    def test_native_render_and_input_rejections_require_no_cluster(self):
        self.assert_ok(self.run_play())
        namespace, pv, claim = self.documents()
        self.assertEqual([namespace["kind"], pv["kind"], claim["kind"]],
                         ["Namespace", "PersistentVolume", "PersistentVolumeClaim"])
        self.assertEqual(pv["spec"]["persistentVolumeReclaimPolicy"], "Retain")
        self.assertEqual(pv["spec"]["claimRef"], {"namespace": "keycloak", "name": "keycloak-db-backups"})
        self.assertEqual(claim["spec"]["volumeName"], pv["metadata"]["name"])
        self.assertEqual(claim["spec"]["storageClassName"], "")
        self.assertEqual(pv["spec"]["csi"]["volumeAttributes"], {"server": "nas.lab.test", "share": "/backups/keycloak"})
        self.assertNotIn("ownerReferences", pv["metadata"])
        plays = []
        for field, value in [("mode", "arbitrary"), ("share", "/"), ("share", "/backups/../live"),
                             ("share", "/backups/"), ("size", "0Gi"), ("volume_handle", ""),
                             ("definition", {"kind": "ClusterRole"})]:
            values = copy.deepcopy(self.values)
            values["backup_repository_storage_volume"][field] = value
            plays.append(self.rejection_play(values, "preflight"))
        for field, value in [("namespace", "kube-system"), ("namespace", "default"),
                             ("owner", ""), ("claim", "../../other")]:
            values = copy.deepcopy(self.values)
            values["backup_repository_storage_" + field] = value
            plays.append(self.rejection_play(values, "preflight"))
        self.assert_ok(self.run_play(plays=plays))

    def test_route_changes_clear_previously_rendered_owned_storage_facts(self):
        self.assert_ok(self.run_play(tasks=[
            {"ansible.builtin.include_role": {"name": "backup_repository_storage"}},
            {"ansible.builtin.assert": {"that": ["backup_repository_storage_documents | length == 3",
                                                 "backup_repository_storage_render | length > 0"]}},
            {"ansible.builtin.include_role": {"name": "backup_repository_storage"},
             "vars": {"backup_repository_storage_volume": {"mode": "existing"}}},
            {"ansible.builtin.assert": {"that": ["backup_repository_storage_documents == []",
                                                 "backup_repository_storage_render == ''"]}},
        ]))

    @staticmethod
    def rejection_play(values, task_file):
        return {"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"ansible_python_interpreter": sys.executable} | values,
                "tasks": [{"block": [
                    {"ansible.builtin.include_role": {"name": "backup_repository_storage", "tasks_from": task_file}},
                    {"ansible.builtin.fail": {"msg": "UNEXPECTED_ACCEPTANCE"}}],
                    "rescue": [{"ansible.builtin.assert": {"that": [
                        "ansible_failed_result.msg | default('') != 'UNEXPECTED_ACCEPTANCE'"]}}]}]}

    def test_native_modules_create_only_owned_resources_and_do_not_patch_on_rerun(self):
        api = self.api()
        self.assert_ok(self.run_play())
        self.assertEqual([body["kind"] for _, _, body in api.mutations],
                         ["Namespace", "PersistentVolume", "PersistentVolumeClaim"])
        self.assertEqual({method for method, _, _ in api.mutations}, {"POST"})
        before = copy.deepcopy(api.objects)
        api.mutations.clear()
        self.assert_ok(self.run_play())
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)

    def test_existing_external_storage_is_never_adopted_or_rewritten(self):
        api = self.api()
        self.assert_ok(self.run_play(dict(self.values, backup_repository_storage_action="render")))
        for obj in self.documents():
            obj["metadata"].pop("annotations", None)
            api.put(obj)
        before = copy.deepcopy(api.objects)
        denied = self.run_play()
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("Existing PVC is not this owner's exact backup contract", denied.stdout)
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)
        self.assert_ok(self.run_play(dict(self.values, backup_repository_storage_volume={"mode": "existing"})))
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)

    def test_api_canonical_storage_quantities_preserve_the_exact_capacity_contract(self):
        api = self.api()
        self.values["backup_repository_storage_volume"]["size"] = "1024Gi"
        self.assert_ok(self.run_play(dict(self.values, backup_repository_storage_action="render")))
        namespace, pv, claim = self.documents()
        pv["spec"]["capacity"]["storage"] = "1Ti"
        claim["spec"]["resources"]["requests"]["storage"] = "1Ti"
        for obj in (namespace, pv, claim):
            api.put(obj)
        pv["spec"]["claimRef"]["uid"] = claim["metadata"]["uid"]
        pv["status"] = {"phase": "Bound"}
        before = copy.deepcopy(api.objects)
        self.assert_ok(self.run_play())
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)

        for quantity in ("2Ti", "1T"):
            for actual in (pv["spec"]["capacity"], claim["spec"]["resources"]["requests"]):
                with self.subTest(quantity=quantity, resource=actual):
                    actual["storage"] = quantity
                    rejected = self.run_play()
                    self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
                    self.assertEqual(api.mutations, [])
                    actual["storage"] = "1Ti"

    def test_missing_csi_is_actionable_before_writes_and_existing_namespaces_are_preserved(self):
        api = self.api()
        api.objects.clear()
        rejected = self.run_play()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Install/accept NFS CSI first", rejected.stdout)
        self.assertEqual(api.mutations, [])
        api.put({"apiVersion": "storage.k8s.io/v1", "kind": "CSIDriver",
                 "metadata": {"name": "nfs.csi.k8s.io"}, "spec": {}})
        namespace = {"apiVersion": "v1", "kind": "Namespace", "metadata": {
            "name": "keycloak", "labels": {"existing-owner": "accepted"}}}
        api.put(namespace)
        before = copy.deepcopy(namespace)
        self.assert_ok(self.run_play())
        self.assertEqual([body["kind"] for _, _, body in api.mutations], ["PersistentVolume", "PersistentVolumeClaim"])
        self.assertEqual(api.objects[("namespaces", "", "keycloak")], before)

    def test_matching_guards_reject_released_rebound_or_backend_data_storage(self):
        self.assert_ok(self.run_play())
        _, pv, claim = self.documents()
        claim["metadata"]["uid"] = "exact-claim"
        claim["status"] = {"phase": "Bound"}
        pv["spec"]["claimRef"]["uid"] = "exact-claim"
        pv["status"] = {"phase": "Bound"}
        values = self.values | {"backup_repository_storage_documents": self.documents(),
            "backup_repository_storage_existing_claim": {"resources": [claim]},
            "backup_repository_storage_existing_volumes": [pv]}
        tasks = [{"ansible.builtin.include_role": {"name": "backup_repository_storage", "tasks_from": "matching"}}]
        self.assert_ok(self.run_play(values, tasks))
        cases = []
        for resource, path, value in [
            ("claim", ["metadata", "namespace"], "other"),
            ("claim", ["metadata", "annotations", "backup.homelab/owner"], "different-owner"),
            ("claim", ["metadata", "deletionTimestamp"], "now"),
            ("claim", ["metadata", "labels"], {"cnpg.io/cluster": "keycloak-db"}),
            ("claim", ["spec", "volumeName"], "live-data"),
            ("claim", ["spec", "resources", "requests", "storage"], "200Gi"),
            ("pv", ["status", "phase"], "Released"),
            ("pv", ["metadata", "annotations", "backup.homelab/owner"], "different-owner"),
            ("pv", ["spec", "claimRef", "uid"], "previous-claim"),
            ("pv", ["spec", "claimRef", "namespace"], "other"),
            ("pv", ["spec", "persistentVolumeReclaimPolicy"], "Delete"),
            ("pv", ["spec", "csi", "readOnly"], True),
            ("pv", ["spec", "csi", "volumeHandle"], "different-export"),
        ]:
            changed = copy.deepcopy(values)
            obj = (changed["backup_repository_storage_existing_claim"]["resources"][0] if resource == "claim"
                   else changed["backup_repository_storage_existing_volumes"][0])
            for key in path[:-1]:
                obj = obj[key]
            obj[path[-1]] = value
            cases.append(self.rejection_play(changed, "matching"))
        self.assert_ok(self.run_play(plays=cases))

    def test_another_volume_cannot_alias_the_selected_export(self):
        api = self.api()
        self.assert_ok(self.run_play(dict(self.values, backup_repository_storage_action="render")))
        pv = self.documents()[1]
        pv["metadata"]["name"] = "other-owners-volume"
        pv["spec"]["csi"]["volumeHandle"] = "different-handle-same-export"
        api.put(pv)
        before = copy.deepcopy(api.objects)
        rejected = self.run_play()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("already represented by another PV", rejected.stdout)
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)

    def test_existing_claims_pass_native_consumer_qualification_without_ownership_transfer(self):
        api = self.api()
        self.assert_ok(self.run_play(dict(self.values, backup_repository_storage_action="render")))
        for obj in self.documents():
            obj["metadata"].pop("annotations", None)
            api.put(obj)
        pv = api.objects[("persistentvolumes", "", "backup-keycloak-keycloak-db-backups")]
        claim = api.objects[("persistentvolumeclaims", "keycloak", "keycloak-db-backups")]
        pv["status"] = {"phase": "Bound"}
        pv["spec"]["claimRef"]["uid"] = claim["metadata"]["uid"]
        before = copy.deepcopy(api.objects)
        postgres = {"postgresql_file_backup_kubeconfig": self.values["backup_repository_storage_kubeconfig"],
                    "postgresql_file_backup_target": {"namespace": "keycloak", "claim": "keycloak-db-backups",
                                                       "volume_handle": "nas-keycloak"}}
        self.assert_ok(self.run_play(postgres, [{"ansible.builtin.include_role": {
            "name": "postgresql_file_backup", "tasks_from": "storage"}}]))
        delivery = {"delivery_platform_kubeconfig": self.values["backup_repository_storage_kubeconfig"],
                    "delivery_platform_context": "offline", "delivery_platform_spinnaker_namespace": "keycloak",
                    "delivery_platform_spinnaker_backup_filesystem_claim": "keycloak-db-backups"}
        self.assert_ok(self.run_play(delivery, [{"ansible.builtin.include_role": {
            "name": "delivery_platform", "tasks_from": "spinnaker-backup-storage"}}]))
        self.assertEqual(api.mutations, [])
        self.assertEqual(api.objects, before)

    def test_native_consumers_render_the_same_bounded_storage_route(self):
        from test_tier_postgresql_file_backup import inputs

        values = inputs() | {"postgresql_file_backup_action": "render",
                             "postgresql_file_backup_output": str(self.work / "output")}
        values["postgresql_file_backup_target"]["storage"] = {
            key: value for key, value in self.values["backup_repository_storage_volume"].items() if key != "volume_handle"}
        self.assert_ok(self.run_play(values, [{"ansible.builtin.include_role": {"name": "postgresql_file_backup"}}]))
        pv = self.documents()[1]
        self.assertEqual(pv["spec"]["csi"]["volumeHandle"], values["postgresql_file_backup_target"]["volume_handle"])
        delivery = {"delivery_platform_output": str(self.work / "delivery"),
            "delivery_platform_kubeconfig": "", "delivery_platform_context": "", "delivery_platform_spinnaker_namespace": "spinnaker",
            "delivery_platform_spinnaker_backup_filesystem_claim": "spinnaker-nas-repository",
            "delivery_platform_spinnaker_backup_storage": self.values["backup_repository_storage_volume"]}
        self.assert_ok(self.run_play(delivery, [{"ansible.builtin.include_role": {
            "name": "delivery_platform", "tasks_from": "spinnaker-backup-provision"}}]))
        docs = list(yaml.safe_load_all((self.work / "delivery/spinnaker-spinnaker-nas-repository-storage.yml").read_text()))
        self.assertEqual(docs[2]["metadata"]["namespace"], "spinnaker")
        self.assertEqual(docs[1]["metadata"]["annotations"]["backup.homelab/owner"], "delivery-platform/spinnaker/spinnaker")


if __name__ == "__main__":
    unittest.main()
