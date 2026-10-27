"""Exercise the NAS consumer contract with native Ansible assertions and real restic.

The roundtrip uses an existing tmpfs mount, never a live NAS or Kubernetes cluster.
"""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
RESTIC = os.environ.get("RESTIC_BINARY") or shutil.which("restic")
NATIVE = os.name != "nt" and shutil.which("ansible-playbook")


class RepositoryStorageInputs(unittest.TestCase):
    def test_fresh_file_example_and_figure_preserve_the_legacy_s3_default(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        example = yaml.safe_load((UPSTREAM / "tier-1/ansible/group_vars/delivery_platform.yml.example").read_text())
        self.assertEqual(defaults["delivery_platform_spinnaker_backup_backend"], "s3")
        self.assertEqual(example["delivery_platform_spinnaker_backup_backend"], "filesystem")
        guide = (UPSTREAM / "docs/deployment/stage-7-delivery/step-2b-spinnaker.md").read_text()
        diagram = guide.split("```mermaid", 1)[1].split("```", 1)[0]
        self.assertIn(example["delivery_platform_spinnaker_backup_filesystem_claim"], diagram)
        self.assertIn("Existing NAS / backup file area", diagram)
        self.assertNotIn("S3-compatible", diagram)


@unittest.skipUnless(NATIVE, "Requires native Ansible")
class RepositoryStoragePreflight(unittest.TestCase):
    def test_actual_ansible_assertions_reject_missing_unbound_local_or_disposable_storage(self):
        tasks = yaml.safe_load((ROLE / "tasks/spinnaker-backup-storage.yml").read_text())
        assertions = [task for task in tasks if "ansible.builtin.assert" in task]
        claim = {"metadata": {"name": "nas-repository", "uid": "claim-identity"},
                 "spec": {"volumeName": "nas-volume", "volumeMode": "Filesystem"},
                 "status": {"phase": "Bound"}}
        volume = {"metadata": {"name": "nas-volume"}, "status": {"phase": "Bound"}, "spec": {
            "persistentVolumeReclaimPolicy": "Retain", "volumeMode": "Filesystem",
            "claimRef": {"name": "nas-repository", "namespace": "spinnaker", "uid": "claim-identity"},
            "nfs": {"server": "nas.lab.test", "path": "/backups/spinnaker"}}}
        cases = [("nfs", [claim], [volume], True)]
        csi = copy.deepcopy(volume)
        csi["spec"].pop("nfs")
        csi["spec"]["csi"] = {"driver": "nfs.csi.k8s.io", "volumeHandle": "nas-repository"}
        cases.append(("nas-csi", [claim], [csi], True))
        cases.extend([("absent-claim", [], [volume], False), ("absent-volume", [claim], [], False)])
        for name, field, value in (("pending", "status", {"phase": "Pending"}),
                                   ("deleting", "metadata", dict(claim["metadata"], deletionTimestamp="now")),
                                   ("block", "spec", dict(claim["spec"], volumeMode="Block"))):
            changed = dict(claim, **{field: value})
            cases.append((name, [changed], [volume], False))
        for name, updates in (("delete-policy", {"persistentVolumeReclaimPolicy": "Delete"}),
                              ("wrong-binding", {"claimRef": dict(volume["spec"]["claimRef"], uid="other")}),
                              ("read-only", {"nfs": dict(volume["spec"]["nfs"], readOnly=True)})):
            changed = copy.deepcopy(volume)
            changed["spec"].update(updates)
            cases.append((name, [claim], [changed], False))
        local = copy.deepcopy(volume)
        local["spec"].pop("nfs")
        local["spec"]["hostPath"] = {"path": "/empty/local/fallback"}
        cases.append(("host-path", [claim], [local], False))
        with tempfile.TemporaryDirectory() as directory:
            playbook = Path(directory) / "preflight.yml"
            for name, claims, volumes, accepted in cases:
                with self.subTest(name=name):
                    playbook.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False,
                        "vars": {"delivery_platform_spinnaker_namespace": "spinnaker",
                                 "spinnaker_backup_claim": {"resources": claims},
                                 "spinnaker_backup_volume": {"resources": volumes}}, "tasks": assertions}]))
                    result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(playbook)],
                                            capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)


@unittest.skipUnless(os.name != "nt" and RESTIC and os.path.ismount("/dev/shm"),
                     "Requires pinned native restic and an existing writable tmpfs mount")
class FilesystemBackup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="spinnaker-backup-", dir="/dev/shm")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        work = tempfile.TemporaryDirectory(prefix="spinnaker-exports-")
        self.addCleanup(work.cleanup)
        self.work = Path(work.name)
        tools = self.work / "tools"
        tools.mkdir()
        (tools / "restic").symlink_to(Path(RESTIC).resolve())
        self.env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                        BACKUP_BACKEND="filesystem", BACKUP_FILESYSTEM_MOUNT="/dev/shm",
                        BACKUP_FILESYSTEM_MARKER="offline-nas-custody-identity-000001",
                        BACKUP_DIRECTORY=str(self.work / "staging"), BACKUP_RUN="run-1", RESTIC_HOST="spinnaker",
                        RESTIC_REPOSITORY=str(self.root), RESTIC_PASSWORD="offline-retained-password-32",
                        RESTIC_CACHE_DIR=str(self.work / "cache"))
        # Use a single child of the real mount, matching the production /repository/<name> layout.
        self.repository = self.root
        self.restic("init", "--repository-version", "2")
        self.marker = self.repository / ".spinnaker-backup-repository"
        self.marker.write_text(self.env["BACKUP_FILESYSTEM_MARKER"] + "\n")
        self.staged = self.work / "staging/run-1"
        self.staged.mkdir(parents=True)
        (self.staged / "mysql.sql.gz").write_bytes(b"offline SQL export")
        (self.staged / "redis.rdb").write_bytes(b"offline Redis export")

    def restic(self, *args):
        result = subprocess.run([RESTIC, *args], env=self.env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def backup(self, **overrides):
        return subprocess.run(["sh", str(ROLE / "files/spinnaker/backup-restic.sh")],
                              env=dict(self.env, **overrides), capture_output=True, text=True, timeout=120)

    def test_roundtrip_on_real_mount_preserves_repository_and_removes_only_successful_staging(self):
        result = self.backup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        restored = self.work / "restored"
        self.restic("restore", "latest", "--target", str(restored))
        self.assertEqual(next(restored.rglob("mysql.sql.gz")).read_bytes(), b"offline SQL export")
        self.assertEqual(next(restored.rglob("redis.rdb")).read_bytes(), b"offline Redis export")
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.marker.is_file())
        self.assertTrue((self.repository / "config").is_file())

    def test_missing_wrong_marker_password_or_incomplete_export_cannot_write(self):
        for denied in ({"BACKUP_FILESYSTEM_MARKER": "wrong-marker"}, {"RESTIC_PASSWORD": "wrong-password"},
                       {"BACKUP_BACKEND": "local"}):
            with self.subTest(denied=denied):
                result = self.backup(**denied)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((self.staged / "mysql.sql.gz").exists())
        self.marker.unlink()
        self.assertNotEqual(self.backup().returncode, 0)
        retained_marker = self.work / "marker"
        retained_marker.write_text(self.env["BACKUP_FILESYSTEM_MARKER"])
        self.marker.symlink_to(retained_marker)
        self.assertNotEqual(self.backup().returncode, 0)
        self.marker.unlink()
        self.marker.write_text(self.env["BACKUP_FILESYSTEM_MARKER"])
        (self.staged / "redis.rdb").unlink()
        self.assertNotEqual(self.backup().returncode, 0)
        self.assertEqual(json.loads(self.restic("snapshots", "--json").stdout) or [], [])

    def test_missing_mount_config_and_symlink_escape_never_initialize_or_fall_back(self):
        # Even a valid repository and marker inside an ordinary directory must fail the mount check.
        unmounted = self.work / "unmounted"
        local_repository = unmounted / "spinnaker"
        shutil.copytree(self.repository, local_repository)
        result = self.backup(BACKUP_FILESYSTEM_MOUNT=str(unmounted), RESTIC_REPOSITORY=str(local_repository))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NAS repository mount is absent", result.stderr)
        config = self.repository / "config"
        original = config.read_bytes()
        config.unlink()
        result = self.backup()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(config.exists(), "Filesystem jobs must never initialize missing repositories")
        config.write_bytes(original)
        missing = self.root.with_name(self.root.name + "-missing")
        self.assertNotEqual(self.backup(RESTIC_REPOSITORY=str(missing)).returncode, 0)
        self.assertFalse(missing.exists())
        alias = Path("/dev/shm") / (self.root.name + "-alias")
        alias.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(alias.unlink)
        self.assertNotEqual(self.backup(RESTIC_REPOSITORY=str(alias)).returncode, 0)
        self.assertTrue((self.staged / "mysql.sql.gz").is_file())
        self.assertEqual(json.loads(self.restic("snapshots", "--json").stdout) or [], [])


if __name__ == "__main__":
    unittest.main()
