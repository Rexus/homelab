"""Native restic tests on an isolated local mount; no live NAS acceptance claim."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined

from tier_repo_test_support import UPSTREAM


TEMPLATES = UPSTREAM / "tier-1/ansible/roles/development_data/templates"
RESTIC = os.environ.get("RESTIC_TEST_BINARY") or shutil.which("restic")
NATIVE = (os.name == "posix" and os.geteuid() == 0 and RESTIC
          and os.environ.get("DEVELOPMENT_DATA_BACKUP_MOUNT_TESTS") == "1")


@unittest.skipUnless(NATIVE, "Requires restic and root inside an explicitly isolated Linux mount namespace")
class DevelopmentDataFilesystemBackup(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gitlab-backup-", dir="/mnt")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.work.chmod(0o755)
        self.mount = self.work / "nas"
        self.mount.mkdir()
        self.command(["mount", "-t", "tmpfs", "-o", "size=64m", "development-data-test", str(self.mount)])
        self.addCleanup(lambda: self.command(["umount", "-l", str(self.mount)], check=False))
        self.repository = self.mount / "gitlab-db-1"
        self.repository.mkdir()
        self.marker = self.mount / ".development-data-backup-target"
        self.marker.write_text("unique-commissioned-backup-target-0001\n")
        self.config = self.work / "config"
        self.config.mkdir()
        (self.config / "backup.password").write_text("independent-restic-encryption-password")
        self.inputs = {
            "inventory_hostname": "gitlab-db-1", "data_component": "postgresql",
            "development_data_backup_transport": "filesystem",
            "development_data_backup_repository": {"gitlab-db-1": str(self.repository)},
            "development_data_backup_min_free_bytes": 1,
            "development_data_backup_filesystem": {"gitlab-db-1": {
                # Exercise the real guard on a private local mount; production inputs reject tmpfs.
                "mount": str(self.mount), "source": "development-data-test", "fstype": "tmpfs",
                "marker": self.marker.read_text().strip(), "uid": 0, "gid": 0}},
        }
        self.source = self.work / "source"
        self.source.mkdir()
        (self.source / "database").write_bytes(b"native GitLab cold copy fixture\n" * 1024)
        self.events = self.work / "service-events"
        self.ctl = self.work / "gitlab-ctl"
        self.ctl.write_text(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{self.events}"\n'
                            f'if [[ "$1" == stop && -f "{self.work}/detach" ]]; then\n'
                            f'  umount -l "{self.mount}"\n'
                            f'  mkdir -p "{self.repository}"\nfi\n')
        self.ctl.chmod(0o755)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        (self.bin / "restic").symlink_to(RESTIC)
        self.environment = {key: value for key, value in os.environ.items() if not key.startswith("RESTIC_")}
        self.environment.update(PATH=f"{self.bin}:{os.environ['PATH']}", RESTIC_CACHE_DIR=str(self.work / "cache"))
        self.render()

    def command(self, argv, check=True, **kwargs):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=60, **kwargs)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def render(self):
        environment = Environment(undefined=StrictUndefined)
        for name in ("backup.env", "backup.sh", "backup-filesystem.sh"):
            text = environment.from_string((TEMPLATES / f"{name}.j2").read_text()).render(**self.inputs)
            text = text.replace("/etc/development-data", str(self.config))
            text = text.replace("/run/development-data-backup.lock", str(self.work / "job.lock"))
            text = text.replace("/opt/gitlab/bin/gitlab-ctl", str(self.ctl))
            text = text.replace("/var/opt/gitlab /etc/gitlab", str(self.source))
            (self.config / name).write_text(text)
        self.command(["bash", "-n", str(self.config / "backup.sh")])

    def job(self, mode=None, success=True, prefix=()):
        return self.command([*prefix, "bash", str(self.config / "backup.sh"), *([mode] if mode else [])],
                            check=success, env=self.environment)

    def reject(self, mode="--initialize", prefix=()):
        result = self.job(mode, success=False, prefix=prefix)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_real_init_backup_restore_and_wrong_password_never_reinitializes(self):
        self.reject("--probe")
        self.assertEqual(list(self.repository.iterdir()), [])
        self.job("--initialize")
        config_digest = hashlib.sha256((self.repository / "config").read_bytes()).hexdigest()
        backed_up = self.job()
        self.assertIn("start requested after", backed_up.stdout)
        self.assertEqual(self.events.read_text().splitlines(), ["stop postgresql", "start postgresql"])
        restored = self.work / "restored"
        self.command([RESTIC, "-r", str(self.repository), "-p", str(self.config / "backup.password"),
                      "restore", "latest", "--target", str(restored)], env=self.environment)
        self.assertEqual((restored / self.source.relative_to("/") / "database").read_bytes(),
                         (self.source / "database").read_bytes())
        (self.config / "backup.password").write_text("wrong-independent-password")
        self.reject()
        self.assertEqual(config_digest, hashlib.sha256((self.repository / "config").read_bytes()).hexdigest())

    def test_absent_runtime_and_nonempty_damaged_repositories_never_initialize(self):
        self.reject("backup")
        self.assertFalse(self.events.exists())
        (self.repository / "orphan-data").write_text("preserve")
        self.reject()
        self.assertFalse((self.repository / "config").exists())
        self.assertEqual((self.repository / "orphan-data").read_text(), "preserve")

    def test_wrong_source_type_marker_and_space_fail_before_writes(self):
        contract = self.inputs["development_data_backup_filesystem"]["gitlab-db-1"]
        for key, value in (("source", "wrong-nas"), ("fstype", "nfs4"), ("marker", "wrong-marker")):
            with self.subTest(key=key):
                original = contract[key]
                contract[key] = value
                self.render()
                self.reject()
                self.assertEqual(list(self.repository.iterdir()), [])
                contract[key] = original
        self.inputs["development_data_backup_min_free_bytes"] = 1024 ** 4
        self.render()
        self.reject()
        self.assertEqual(list(self.repository.iterdir()), [])
        self.assertFalse(self.events.exists())

    def test_missing_mount_and_root_target_reject_local_fallback(self):
        self.command(["umount", str(self.mount)])
        self.repository.mkdir()
        self.marker.write_text("unique-commissioned-backup-target-0001")
        self.reject()
        self.assertEqual(list(self.repository.iterdir()), [])
        self.inputs["development_data_backup_filesystem"]["gitlab-db-1"]["mount"] = "/"
        self.render()
        self.reject()

    def test_marker_repository_parent_and_config_symlinks_rejected(self):
        for path in (self.marker, self.repository):
            with self.subTest(path=path):
                saved = path.with_name(path.name + "-original")
                path.rename(saved)
                path.symlink_to(saved)
                try:
                    self.reject()
                    self.assertFalse((self.repository / "config").exists())
                finally:
                    path.unlink()
                    saved.rename(path)
        (self.repository / "config").symlink_to(self.work / "outside")
        self.reject()
        self.assertFalse((self.work / "outside").exists())
        (self.repository / "config").unlink()
        alias = self.work / "alias"
        alias.symlink_to(self.mount)
        self.inputs["development_data_backup_filesystem"]["gitlab-db-1"]["mount"] = str(alias)
        self.inputs["development_data_backup_repository"]["gitlab-db-1"] = str(alias / self.repository.name)
        self.render()
        self.reject()

    def test_nested_repository_mount_is_not_the_commissioned_target(self):
        self.command(["mount", "-t", "tmpfs", "nested-repository", str(self.repository)])
        try:
            self.reject()
            self.assertEqual(list(self.repository.iterdir()), [])
        finally:
            self.command(["umount", str(self.repository)])

    def test_effective_uid_and_inaccessible_repository_fail_closed(self):
        contract = self.inputs["development_data_backup_filesystem"]["gitlab-db-1"]
        contract["uid"] = 65534
        self.render()
        self.reject()
        self.assertEqual(list(self.repository.iterdir()), [])
        self.repository.chmod(0)
        (self.work / "job.lock").chmod(0o666)
        try:
            rejected = self.reject(prefix=("setpriv", "--reuid=65534", "--regid=65534", "--clear-groups"))
            self.assertIn("Permission denied", rejected.stderr)
            self.assertNotIn("job.lock", rejected.stderr)
        finally:
            self.repository.chmod(0o755)
        self.assertFalse((self.repository / "config").exists())

    def test_mount_loss_after_stop_restarts_service_without_local_write(self):
        self.job("--initialize")
        (self.work / "detach").touch()
        self.reject("backup")
        self.assertEqual(self.events.read_text().splitlines(), ["stop postgresql", "start postgresql"])
        self.assertEqual(list(self.repository.iterdir()), [])

    def test_detach_during_restic_pins_writes_to_original_filesystem(self):
        self.job("--initialize")
        descriptor = os.open(self.repository, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, descriptor)
        (self.bin / "restic").unlink()
        (self.bin / "restic").write_text(
            f'#!/bin/bash\nif [[ "$1" == backup ]]; then\n'
            f'  umount -l "{self.mount}"\n  mkdir -p "{self.repository}"\nfi\n'
            f'exec "{RESTIC}" "$@"\n')
        (self.bin / "restic").chmod(0o755)
        self.reject("backup")
        self.assertEqual(list(self.repository.iterdir()), [])
        self.assertEqual(self.events.read_text().splitlines(), ["stop postgresql", "start postgresql"])
        snapshots = self.command([
            RESTIC, "-r", f"/proc/{os.getpid()}/fd/{descriptor}", "-p", str(self.config / "backup.password"),
            "snapshots", "--json"], env=self.environment)
        self.assertIn('"tags":["gitlab-postgresql"]', snapshots.stdout)

    def test_backup_destination_cannot_replace_live_data_path(self):
        self.source = self.repository / "live-data"
        self.render()
        rejected = self.reject()
        self.assertIn("overlaps live GitLab", rejected.stderr)
        self.assertEqual(list(self.repository.iterdir()), [])

    def test_real_enospc_restarts_source_and_preserves_repository(self):
        self.job("--initialize")
        config = (self.repository / "config").read_bytes()
        (self.source / "database").write_bytes(os.urandom(2 * 1024 * 1024))
        self.command(["mount", "-o", "remount,size=1m", str(self.mount)])
        result = self.reject("backup")
        self.assertIn("no space left on device", result.stdout + result.stderr)
        self.assertIn("start requested after", result.stdout)
        self.assertEqual(self.events.read_text().splitlines(), ["stop postgresql", "start postgresql"])
        self.assertEqual((self.repository / "config").read_bytes(), config)

    def test_interruptible_timeout_requests_source_restart(self):
        self.job("--initialize")
        (self.bin / "restic").unlink()
        (self.bin / "restic").write_text(
            '#!/bin/bash\nif [[ "$1" == backup ]]; then sleep 30; exit 1; fi\n'
            f'exec "{RESTIC}" "$@"\n')
        (self.bin / "restic").chmod(0o755)
        result = self.reject("backup", prefix=("timeout", "--signal=TERM", "--kill-after=5", "3"))
        self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
        self.assertEqual(self.events.read_text().splitlines(), ["stop postgresql", "start postgresql"])
        self.assertIn("start requested after", result.stdout)


if __name__ == "__main__":
    unittest.main()
