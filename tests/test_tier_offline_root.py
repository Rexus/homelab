"""Exercise the portable offline root contract, native crypto and fail-closed guards.

Linux tests use explicit command fixtures for physical media inspection, never production
guard-bypass flags. Native ceremonies use an isolated network namespace and unmodified clca.
Set ORCA_TEST_CLCA_ARCHIVE to the official pinned archive to enable native bundle/roundtrip tests.
"""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import tarfile
import tempfile
import time
import unittest

from tier_repo_test_support import TierRepositoryTestCase

UPSTREAM = Path(__file__).resolve().parents[1]
REVISION = "d560135cf4bbdc1916fa4c5545012085b96d4a21"
ARCHIVE_HASH = "a0ca869c3f639b88690db5d6bc23db9ee3ed7b229428cafff01b3b30295353b6"
SCRIPT = UPSTREAM / "tier-0/scripts/offline-root.sh"
TEMPLATES = UPSTREAM / "tier-0/templates/offline-root"
ARCHIVE = Path(os.environ.get("ORCA_TEST_CLCA_ARCHIVE", UPSTREAM / ".tmp/orca-source/clca.tar.gz"))


class OfflineRootRepositoryExport(TierRepositoryTestCase):
    def test_tier_zero_exports_wrapper_and_public_example_without_root_state(self):
        self.generate("--repo", "tier-0")
        generated = self.root / "verify-tier-0"
        self.assertEqual((generated / "scripts/offline-root.sh").read_text(), SCRIPT.read_text())
        for name in ("orca.conf.example", "clca.cfg.example", "openssl.cnf.example"):
            self.assertTrue((generated / f"templates/offline-root/{name}").is_file())
        self.assertFalse((generated / "templates/offline-root/orca.conf").exists())
        self.assertFalse((generated / "templates/offline-root/private").exists())


@unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "Requires Linux Bash")
class OfflineRootWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="orca-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "tier"
        (self.repo / "scripts").mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.repo / "scripts/offline-root.sh")
        shutil.copytree(TEMPLATES, self.repo / "templates/offline-root")
        self.work = self.root / "work"
        self.work.mkdir()
        self.instance = self.work / "root"
        self.transfer = self.root / "transfer"
        self.transfer.mkdir()
        self.backup = self.root / "backup"
        self.backup.mkdir()
        self.tools = self.work / "tools"
        self.commands = self.root / "fixture-bin"
        self.commands.mkdir()
        self.settings = self.root / "fixture.json"
        self.fixture = {"work": str(self.work), "transfer": str(self.transfer),
                        "backup": str(self.backup), "online": False, "encrypted": True,
                        "same_disk": False, "archive": str(ARCHIVE)}
        self.save_fixture()
        # These executables exist only in the test subprocess PATH. The production wrapper
        # contains no fixture mode and still invokes its normal network/media inspection.
        fixture_program = self.commands / "fixture"
        fixture_program.write_text("#!/usr/bin/python3\n" + '''
import json, pathlib, shutil, sys
data = json.loads(pathlib.Path(__file__).resolve().parents[1].joinpath('fixture.json').read_text())
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
if name == 'curl':
    assert 'https://codeload.github.com/openxpki/clca/tar.gz/''' + REVISION + '''' in args
    shutil.copyfile(data['archive'], args[args.index('-o') + 1])
elif name == 'ip':
    mode = data['online']
    if 'link' in args:
        if mode is True or mode == 'link': print('2: eth0: <BROADCAST,UP> mtu 1500 state UP')
        else: print('1: lo: <LOOPBACK,UP> mtu 65536 state UNKNOWN')
    elif '-4' in args and (mode is True or mode == 'route4'): print('default via 192.0.2.1 dev eth0')
    elif '-6' in args and mode == 'route6': print('default via 2001:db8::1 dev eth0')
elif name == 'findmnt':
    path = args[-1]
    owner = next((key for key in ('work', 'transfer', 'backup') if path.startswith(data[key])), None)
    if owner is None: sys.exit(1)
    if 'SOURCE' in args: print('/dev/mapper/orca-' + owner)
    elif 'TARGET' in args: print(data[owner])
    elif 'MAJ:MIN' in args: print({'work': '253:1', 'transfer': '253:2', 'backup': '253:3'}[owner])
    else: sys.exit(1)
elif name == 'lsblk':
    owner = args[-1].split('-')[-1]
    if args[args.index('-o') + 1] == 'TYPE':
        print('crypt' if data['encrypted'] else 'part')
        print('disk')
    else:
        disk = '8:0' if data['same_disk'] else {'work': '8:0', 'transfer': '8:16', 'backup': '8:32'}[owner]
        print(disk + ' disk')
else: sys.exit(1)
''')
        fixture_program.chmod(0o755)
        for name in ("ip", "findmnt", "lsblk", "curl"):
            (self.commands / name).symlink_to(fixture_program)
        self.env = dict(os.environ, PATH=f"{self.commands}:{os.environ['PATH']}")
        self.run_action("init", repo=self.repo)
        self.config = self.repo / "templates/offline-root/orca.conf"
        self.set_config(ORCA_INSTANCE=self.instance, ORCA_TOOLS=self.tools,
                        ORCA_TRANSFER=self.transfer, ORCA_BACKUP=self.backup,
                        ORCA_ORGANIZATION="Fixture Organization", ORCA_COMMON_NAME="Fixture Offline Root",
                        ORCA_PUBLICATION_URL="http://pki.example.internal/download",
                        ORCA_BACKUP_RECIPIENT="age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq")

    def save_fixture(self):
        self.settings.write_text(json.dumps(self.fixture))

    def set_config(self, **settings):
        content = self.config.read_text()
        for key, value in settings.items():
            content, count = re.subn(rf"^{key}=.*$", lambda _: f'{key}="{value}"', content, flags=re.M)
            self.assertEqual(count, 1, key)
        self.config.write_text(content)

    def run_action(self, *args, repo=None, success=True, env=None, input=None, namespace=False):
        repo = repo or self.repo
        command = ["bash", str(repo / "scripts/offline-root.sh"), *map(str, args)]
        if namespace:
            command = ["unshare", "-Urn", *command]
        result = subprocess.run(command, cwd=repo, env=env or self.env, input=input,
                                capture_output=True, text=True, timeout=45)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def bundle_kit(self):
        if not ARCHIVE.is_file():
            self.skipTest("Provide the pinned official archive with ORCA_TEST_CLCA_ARCHIVE")
        self.assertEqual(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), ARCHIVE_HASH)
        self.repo_before_kit = self.repo
        kit = self.root / "kit"
        self.run_action("bundle", kit)
        self.repo = kit
        self.config = kit / "templates/offline-root/orca.conf"
        return kit

    def test_init_preserves_existing_local_config_exactly(self):
        before = self.config.read_bytes()
        self.run_action("init")
        self.assertEqual(self.config.read_bytes(), before)

    def test_config_is_literal_and_rejects_unknown_flags_and_mismatched_pin(self):
        self.set_config(ORCA_CLCA_REVISION="a" * 40)
        result = self.run_action("bundle", self.root / "bad-kit", success=False)
        self.assertIn("Source revision mismatch", result.stderr)
        self.set_config(ORCA_CLCA_REVISION=REVISION)
        with self.config.open("a") as handle:
            handle.write("ORCA_ALLOW_ONLINE=true\n")
        self.assertIn("Unknown configuration field", self.run_action("create", success=False).stderr)
        source = SCRIPT.read_text()
        self.assertNotRegex(source, r"ORCA_(SKIP|ALLOW|TEST|IGNORE|FIXTURE|DISABLE)_")
        self.assertNotIn('source "$INPUTS"', source)

    def test_ambient_config_cannot_override_file(self):
        env = dict(self.env, ORCA_INSTANCE="/do-not-use-this", ORCA_CLCA_REVISION="wrong")
        result = self.run_action("status", env=env)
        self.assertIn(str(self.instance), result.stdout)
        self.assertNotIn("do-not-use", result.stdout)

    def test_online_mutation_is_rejected_before_tools_or_root_state_created(self):
        for mode in ("link", "route4", "route6"):
            self.fixture["online"] = mode
            self.save_fixture()
            for action in ("prepare", "create", "crl", "backup", "maintain"):
                with self.subTest(action=action, mode=mode):
                    result = self.run_action(action, success=False)
                    self.assertIn("non-loopback links", result.stderr)
                    self.assertFalse(self.instance.exists())
                    self.assertFalse(self.tools.exists())

    def test_unencrypted_or_shared_physical_media_rejected(self):
        self.fixture["encrypted"] = False
        self.save_fixture()
        self.assertIn("encrypted block volume", self.run_action("prepare", success=False).stderr)
        self.fixture.update(encrypted=True, same_disk=True)
        self.save_fixture()
        self.assertIn("share a physical disk", self.run_action("prepare", success=False).stderr)
        self.assertFalse(self.instance.exists())

    def test_bundle_has_only_public_policy_tools_and_pinned_source(self):
        self.instance.mkdir()
        (self.instance / "private").mkdir()
        (self.instance / "private/cakey.pem").write_text("DO NOT COPY ROOT STATE")
        kit = self.bundle_kit()
        self.assertTrue((kit / "clca/bin/clca").is_file())
        self.assertTrue((kit / "clca/lib").is_dir())
        self.assertTrue((kit / "clca/LICENSE").is_file())
        self.assertIn(REVISION, (kit / "source.txt").read_text())
        self.assertNotIn(str(self.repo_before_kit), self.config.read_text())
        for path in kit.rglob("*"):
            self.assertNotIn(path.name, ("private", "cakey.pem", "index.txt", "cacert.pem"))
            if path.is_file():
                self.assertNotIn(b"DO NOT COPY ROOT STATE", path.read_bytes())
        self.run_action("prepare", success=False)  # retained unprepared state must not be initialized
        self.assertFalse((self.instance / "etc").exists())

    def test_tampered_archive_or_local_checkout_is_rejected(self):
        if not ARCHIVE.is_file():
            self.skipTest("Provide ORCA_TEST_CLCA_ARCHIVE")
        archive = self.root / "corrupt.tar.gz"
        archive.write_bytes(ARCHIVE.read_bytes() + b"tamper")
        self.fixture["archive"] = str(archive)
        self.save_fixture()
        result = self.run_action("bundle", self.root / "bad-kit", success=False)
        self.assertIn("archive checksum mismatch", result.stderr)
        self.assertFalse((self.root / "bad-kit").exists())
        checkout = self.root / "wrong-checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "fixture"], check=True)
        self.set_config(ORCA_CLCA_SOURCE=checkout)
        self.assertIn("Local clca revision mismatch", self.run_action("bundle", self.root / "bad-kit", success=False).stderr)

    def test_prepare_is_idempotent_keyless_and_preserves_policy(self):
        self.bundle_kit()
        self.run_action("prepare")
        before = (self.instance / "etc/openssl.cnf").read_bytes()
        self.run_action("prepare")
        self.assertEqual((self.instance / "etc/openssl.cnf").read_bytes(), before)
        self.assertFalse((self.instance / "private").exists())
        self.assertFalse((self.instance / "ca").exists())
        self.set_config(ORCA_COMMON_NAME="Different Identity")
        self.assertIn("binding differs", self.run_action("prepare", success=False).stderr)
        self.assertEqual((self.instance / "etc/openssl.cnf").read_bytes(), before)

    def test_prepare_restores_missing_tools_without_changing_existing_instance_bytes(self):
        self.bundle_kit()
        self.run_action("prepare")
        (self.instance / "private").mkdir()
        (self.instance / "private/cakey.pem").write_bytes(b"retained encrypted key fixture\n")
        (self.instance / "ca").mkdir()
        (self.instance / "ca/index.txt").write_bytes(b"retained issuance database fixture\n")
        (self.instance / ".orca-created").touch()
        retained = {path.relative_to(self.instance): path.read_bytes()
                    for path in self.instance.rglob("*") if path.is_file()}
        tools = {path.relative_to(self.tools): path.read_bytes()
                 for path in self.tools.rglob("*") if path.is_file()}
        shutil.rmtree(self.tools)
        self.run_action("prepare")
        self.assertEqual({path.relative_to(self.instance): path.read_bytes()
                          for path in self.instance.rglob("*") if path.is_file()}, retained)
        self.assertEqual({path.relative_to(self.tools): path.read_bytes()
                          for path in self.tools.rglob("*") if path.is_file()}, tools)

    def test_prepare_checks_retained_binding_and_policy_before_restoring_missing_tools(self):
        self.bundle_kit()
        self.run_action("prepare")
        shutil.rmtree(self.tools)
        self.set_config(ORCA_COMMON_NAME="Different Identity")
        self.assertIn("binding differs", self.run_action("prepare", success=False).stderr)
        self.assertFalse(self.tools.exists())
        self.set_config(ORCA_COMMON_NAME="Fixture Offline Root")
        policy = self.instance / "etc/openssl.cnf"
        policy.write_text(policy.read_text() + "# changed retained policy\n")
        self.assertIn("Retained CA policy has changed", self.run_action("prepare", success=False).stderr)
        self.assertFalse(self.tools.exists())

    def test_changed_kit_and_native_tools_are_rejected(self):
        self.bundle_kit()
        policy = self.repo / "templates/offline-root/openssl.cnf.example"
        policy.write_text(policy.read_text() + "# tamper\n")
        self.assertIn("Kit integrity check failed", self.run_action("prepare", success=False).stderr)
        self.assertFalse(self.instance.exists())

    def test_installed_native_tools_cannot_change_after_preparation(self):
        self.bundle_kit()
        self.run_action("prepare")
        tool = self.tools / "bin/clca"
        tool.write_text(tool.read_text() + "# modified installed payload\n")
        retained = tool.read_bytes()
        self.assertIn("clca checksum mismatch", self.run_action("prepare", success=False).stderr)
        self.assertEqual(tool.read_bytes(), retained)
        self.assertIn("clca checksum mismatch", self.run_action("create", success=False).stderr)
        self.assertFalse((self.instance / "private").exists())

    def test_creation_never_repeats_existing_key_state_or_partial_attempt(self):
        self.bundle_kit()
        self.run_action("prepare")
        for name in ("private", "ca", "certs", "crl", ".orca-create-started"):
            path = self.instance / name
            path.mkdir() if not name.startswith(".") else path.touch()
            result = self.run_action("create", success=False)
            self.assertIn("create will never repeat initialization", result.stderr)
            path.rmdir() if path.is_dir() else path.unlink()

    def test_partial_ceremony_cannot_be_reinitialized_or_accepted_as_backup(self):
        if not shutil.which("age"):
            self.skipTest("Requires native age")
        self.bundle_kit()
        self.run_action("prepare")
        (self.instance / ".orca-create-started").write_text("creation started\n")
        (self.instance / ".orca-pending").write_text("create interrupted\n")
        (self.instance / "private").mkdir()
        (self.instance / "private/cakey.pem").write_text("partial encrypted key\n")
        (self.instance / "ca").mkdir()
        (self.instance / "ca/index.txt").write_text("")
        self.assertIn("never repeat initialization", self.run_action("create", success=False).stderr)
        # A crash inside native initialize may already have rewritten the absolute policy paths.
        with (self.instance / "etc/openssl.cnf").open("a") as handle:
            handle.write("# partially rewritten by interrupted initialization\n")
        self.assertIn("Incomplete operation recorded", self.run_action("backup", success=False).stderr)
        report = self.run_action("status").stdout
        self.assertIn("INCOMPLETE operation", report)
        self.assertIn("create interrupted", report)
        self.assertFalse(list(self.backup.iterdir()))

    def test_whole_operation_lock_blocks_another_writer(self):
        import fcntl
        self.bundle_kit()
        lock = self.work / ".orca-root.lock"
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn("Another ceremony", self.run_action("prepare", success=False).stderr)
        self.assertFalse(self.instance.exists())

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "Requires an unprivileged caller")
    def test_poweroff_requires_local_root_before_attempting_any_key_operation(self):
        self.bundle_kit()
        self.run_action("prepare")
        report = self.run_action("maintain", "--poweroff", success=False)
        self.assertIn("as root on the ceremony system", report.stderr)
        self.assertFalse((self.instance / ".orca-pending").exists())
        self.assertFalse(list(self.transfer.iterdir()))
        self.assertFalse(list(self.backup.iterdir()))

    def run_ceremony(self, args, answers, success=True):
        import pty
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.repo)
            os.execvpe("unshare", ["unshare", "-Urn", "bash", str(self.repo / "scripts/offline-root.sh"), *args],
                      self.native_env)
        output = b""
        cursor = 0
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([fd], [], [], 0.1)
                if ready:
                    try:
                        data = os.read(fd, 65536)
                    except OSError:
                        break
                    if not data:
                        break
                    output += data
                    if answers and answers[0][0].encode() in output[cursor:]:
                        _, answer = answers.pop(0)
                        os.write(fd, (answer + "\n").encode())
                        cursor = len(output)
            else:
                os.kill(pid, 9)
                self.fail("Ceremony timeout: " + output.decode(errors="replace"))
            _, status = os.waitpid(pid, 0)
            if success:
                self.assertEqual(os.waitstatus_to_exitcode(status), 0, output.decode(errors="replace"))
            else:
                self.assertNotEqual(os.waitstatus_to_exitcode(status), 0, output.decode(errors="replace"))
            self.assertFalse(answers, "Unseen prompts: " + str(answers))
            return output.decode(errors="replace")
        finally:
            os.close(fd)

    def test_native_clca_root_sign_crl_encrypted_archive_and_restore_roundtrip(self):
        if not all(shutil.which(tool) for tool in ("age", "age-keygen", "unshare", "openssl")):
            self.skipTest("Requires native age/OpenSSL and network namespaces")
        if subprocess.run(["unshare", "-Urn", "true"], capture_output=True).returncode:
            self.skipTest("Network namespaces unavailable")
        identity = self.root / "backup-identity"
        result = subprocess.run(["age-keygen", "-o", str(identity)], capture_output=True, text=True, check=True)
        self.set_config(ORCA_BACKUP_RECIPIENT=result.stderr.split("Public key: ")[1].strip())
        self.bundle_kit()
        # Native ip inspects a real disconnected namespace; only physical-media queries are fixtures.
        (self.commands / "ip").unlink()
        self.native_env = self.env
        self.run_action("prepare", namespace=True)
        self.run_ceremony(["create"], [
            ("Type exactly:", "Fixture Offline Root"),
            ("Enter PEM pass phrase:", "test ceremony passphrase"),
            ("Verifying - Enter PEM pass phrase:", "test ceremony passphrase"),
            ("Enter passphrase:", "test ceremony passphrase"),
        ])
        self.assertIn("ENCRYPTED PRIVATE KEY", (self.instance / "private/cakey.pem").read_text())
        cert_der = subprocess.check_output(["openssl", "x509", "-in", str(self.instance / "ca/cacert.pem"), "-outform", "DER"])
        self.set_config(ORCA_ROOT_FINGERPRINT=hashlib.sha256(cert_der).hexdigest())
        self.assertIn("never repeat initialization", self.run_action("create", namespace=True, success=False).stderr)
        self.set_config(ORCA_ROOT_FINGERPRINT="0" * 64)
        for action in ("crl", "backup"):
            self.assertIn("independently verified ORCA_ROOT_FINGERPRINT", self.run_action(action, namespace=True, success=False).stderr)
        self.assertIn("absent/different", self.run_action("status").stdout)
        self.set_config(ORCA_ROOT_FINGERPRINT=hashlib.sha256(cert_der).hexdigest())
        csr = self.transfer / "issuer.csr"
        subprocess.run(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=Fixture Issuer",
                        "-keyout", str(self.root / "issuer.key"), "-out", str(csr)], capture_output=True, check=True)
        pub = subprocess.check_output(["openssl", "req", "-in", str(csr), "-pubkey", "-noout"])
        der = subprocess.run(["openssl", "pkey", "-pubin", "-outform", "DER"], input=pub, capture_output=True, check=True).stdout
        key_hash = hashlib.sha256(der).hexdigest()
        self.assertIn("fingerprint mismatch", self.run_action("sign", csr, "0" * 64, namespace=True, success=False).stderr)
        self.run_ceremony(["sign", str(csr), key_hash], [
            ("Type exactly:", f"SIGN {key_hash} WITH Fixture Offline Root"),
            ("Enter passphrase:", "test ceremony passphrase"),
        ])
        self.assertIn("already processed", self.run_action("sign", csr, key_hash, namespace=True, success=False).stderr)
        report = self.run_ceremony(["maintain"], [("Enter passphrase:", "test ceremony passphrase")])
        self.assertIn("CRL maintenance complete", report)
        receipt, = self.transfer.glob("public-*/ceremony-receipt.txt")
        self.assertIn("publication=pending", receipt.read_text())
        self.assertIn(hashlib.sha256(cert_der).hexdigest(), receipt.read_text())
        self.assertTrue(list(self.backup.glob("*.age.receipt")))
        before = (self.instance / "ca/index.txt").read_bytes()
        encrypted, = self.backup.glob("*.age")
        self.assertTrue(encrypted.read_bytes().startswith(b"age-encryption.org/v1"))
        restored = subprocess.run(["age", "--decrypt", "--identity", str(identity), str(encrypted)],
                                  capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(restored), mode="r:gz") as archive:
            self.assertEqual(archive.extractfile("./ca/index.txt").read(), before)
            for path in ("./private/cakey.pem", "./etc/openssl.cnf", "./etc/clca.cfg", "./ca/serial", "./ca/crlnumber.txt"):
                self.assertTrue(archive.getmember(path).isfile(), path)
            self.assertTrue(any(name.endswith(".crl") for name in archive.getnames()))
        self.assertTrue((self.instance / f"history/{encrypted.name}.sha256").is_file())
        cert, = self.instance.glob("history/issuer-*.pem")
        text = subprocess.check_output(["openssl", "x509", "-in", str(cert), "-noout", "-text"], text=True)
        self.assertIn("CA:TRUE, pathlen:0", text)
        self.assertIn("http://pki.example.internal/download/root.crl", text)
        for file in self.transfer.rglob("*"):
            if file.is_file():
                self.assertNotIn(b"PRIVATE KEY", file.read_bytes())
        self.assertFalse(list(self.work.glob(".orca-backup-*")))
        self.assertFalse(list(self.transfer.glob("*.tar*")))
        # Restore the complete native archive at its original mount binding and prove the
        # recovered key/database can issue a new, verifiable CRL without regenerating keys.
        key_before = (self.instance / "private/cakey.pem").read_bytes()
        shutil.rmtree(self.instance)
        shutil.rmtree(self.tools)
        self.instance.mkdir()
        with tarfile.open(fileobj=io.BytesIO(restored), mode="r:gz") as archive:
            archive.extractall(self.instance, filter="data")
        self.run_action("prepare", namespace=True)
        self.assertEqual((self.instance / "private/cakey.pem").read_bytes(), key_before)
        self.assertEqual((self.instance / "ca/index.txt").read_bytes(), before)
        # Backup failure after signing must never produce success/receipt or request shutdown.
        failed_age = self.commands / "age"
        failed_age.write_text("#!/bin/sh\nexit 1\n")
        failed_age.chmod(0o755)
        time.sleep(1.1)
        receipts_before = list(self.transfer.glob("public-*/ceremony-receipt.txt"))
        failure = self.run_ceremony(["maintain"], [("Enter passphrase:", "test ceremony passphrase")], success=False)
        self.assertNotIn("CRL maintenance complete", failure)
        self.assertEqual(list(self.transfer.glob("public-*/ceremony-receipt.txt")), receipts_before)
        self.assertFalse(list(self.work.glob(".orca-backup-*")))
        failed_age.unlink()

        # Rejected options are caught before a new signing operation.
        counter_before = (self.instance / "ca/crlnumber.txt").read_bytes()
        self.assertIn("Usage: maintain", self.run_action("maintain", "--download-updates", namespace=True,
                                                        success=False).stderr)
        self.assertEqual((self.instance / "ca/crlnumber.txt").read_bytes(), counter_before)
        time.sleep(1.1)  # native clca names CRLs with one-second granularity
        self.run_ceremony(["crl"], [("Enter passphrase:", "test ceremony passphrase")])
        self.assertEqual((self.instance / "private/cakey.pem").read_bytes(), key_before)
        self.assertEqual((self.instance / "ca/index.txt").read_bytes(), before)
        # Match older OpenSSL's zero-status signature failure: no export/backup may accept it.
        verifier = self.commands / "openssl"
        verifier.write_text('#!/bin/bash\nif [[ "$1" == crl && " $* " == *" -verify "* ]]; then\n'
                            '  echo "verify failure" >&2; exit 0\nfi\nexec /usr/bin/openssl "$@"\n')
        verifier.chmod(0o755)
        time.sleep(1.1)
        exports_before = list(self.transfer.iterdir())
        report = self.run_ceremony(["maintain"], [("Enter passphrase:", "test ceremony passphrase")], success=False)
        self.assertIn("CRL signature verification failed", report)
        self.assertEqual(list(self.transfer.iterdir()), exports_before)
        self.assertTrue((self.instance / ".orca-pending").is_file())


if __name__ == "__main__":
    unittest.main()
