"""Receiver ownership, native configuration and real local mTLS/crash checks."""

import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import unittest

import yaml

from syslog_receiver_test_support import (
    BINARY, ROLE, certificates, command, records, render_config, send, wait_for_records,
)
from tier_repo_test_support import TierRepositoryTestCase


class ReceiverContract(TierRepositoryTestCase):
    def test_receiver_is_tier_zero_owned_and_generated_without_local_secrets(self):
        self.generate()
        generated = self.root / "verify-tier-0/ansible/roles/syslog_ng"
        for path in ROLE.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (generated / path.relative_to(ROLE)).read_bytes())
        for other in ("verify-shared", "verify-tier-1", "verify-tier-2"):
            self.assertFalse((self.root / other / "ansible/roles/syslog_ng").exists())
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertEqual(defaults["syslog_ng_sources"], [])
        self.assertEqual(defaults["syslog_ng_legacy_sources"], [])
        self.assertEqual(defaults["syslog_ng_data_uuid"], "")

    def test_safety_guards_and_native_modules_remain_explicit(self):
        preflight = (ROLE / "tasks/preflight.yml").read_text()
        self.assertIn("syslog_ng_data_facts[0].uuid == syslog_ng_data_uuid", preflight)
        self.assertIn("syslog_ng_root_facts[0].device", preflight)
        self.assertIn("syslog_ng_legacy_sources", preflight)
        tasks = "\n".join(path.read_text() for path in (ROLE / "tasks").glob("*.yml"))
        for forbidden in ("ansible.builtin.shell", "community.general.filesystem", "ansible.posix.mount",
                          "state: absent", "name: rsyslog", "recurse: true"):
            self.assertNotIn(forbidden, tasks)
        self.assertIn("community.crypto.x509_certificate_info", tasks)
        self.assertIn("community.crypto.openssl_privatekey_info", tasks)
        self.assertIn("ansible.posix.firewalld", tasks)
        self.assertIn("validate: /usr/sbin/syslog-ng --syntax-only --cfgfile %s", tasks)
        unit = (ROLE / "templates/receiver.service.j2").read_text()
        self.assertIn("ConditionPathIsMountPoint=", unit)
        self.assertIn("User={{ syslog_ng_user }}", unit)
        self.assertNotIn("Alias=syslog.service", unit)


@unittest.skipUnless(os.name != 'nt' and BINARY and shutil.which("openssl"),
                     "Set SYSLOG_NG_TEST_BINARY to run isolated native receiver tests on Linux")
class NativeReceiver(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="homelab-receiver-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "data/.state").mkdir(parents=True)
        certificates(self.directory)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.config = self.directory / "receiver.conf"
        self.config.write_text(render_config(self.directory, self.port))
        self.arguments = [BINARY, "--no-caps", "--module-path", os.environ.get(
            "SYSLOG_NG_TEST_MODULE_PATH", "/usr/lib64/syslog-ng"), "--cfgfile", str(self.config)]
        self.log = (self.directory / "process.log").open("a+")
        self.addCleanup(self.log.close)
        self.process = None
        self.addCleanup(self.stop)

    def start(self):
        command(*self.arguments, "--syntax-only")
        self.process = subprocess.Popen(self.arguments + ["--foreground", "--stderr",
            "--persist-file", str(self.directory / "data/.state/receiver.persist"),
            "--pidfile", str(self.directory / "pid"), "--control", str(self.directory / "control")],
            stdout=self.log, stderr=self.log)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail((self.directory / "process.log").read_text())
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.05)
        self.fail("Native receiver did not listen")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def test_mtls_raw_preservation_untrusted_clients_and_crash_restart(self):
        self.start()
        messages = [
            '<134>1 2026-10-17T08:00:00Z forged-host app 1 event - {"event":1,"text":"quotes \\\""}',
            '<134>Oct 17 08:00:01 forged-host app: legacy message',
            'malformed-but-retained "raw" message',
        ]
        send(self.directory, self.port, messages)
        found = wait_for_records(self.directory, 3)
        self.assertEqual([row["raw"] for row in found], messages)
        for row in found:
            self.assertEqual(row["source"], "producer")
            self.assertEqual(row["peer_cn"], "producer")
            self.assertEqual(row["peer_ip"], "127.0.0.1")
            self.assertTrue(row["received_at"])
        self.assertEqual(found[0]["message"], messages[0].split(' - ', 1)[1])
        for identity in (None, "impostor", "untrusted"):
            try:
                send(self.directory, self.port, ['forbidden'], identity=identity)
            except (ssl.SSLError, OSError):
                pass
        time.sleep(0.3)
        self.assertEqual(len(records(self.directory)), 3)
        self.process.kill()
        self.process.wait(timeout=5)
        self.start()
        send(self.directory, self.port, ["after-process-crash"])
        self.assertEqual(len(wait_for_records(self.directory, 4)), 4)
        self.stop()
        restored = self.directory / "restored"
        shutil.copytree(self.directory / "data/records", restored)
        self.assertEqual(sum(len(path.read_text().splitlines()) for path in restored.rglob("*.jsonl")), 4)

    def test_wrong_peer_address_is_rejected_and_udp_is_explicitly_unauthenticated(self):
        config = render_config(self.directory, self.port, [dict(name="legacy", address="127.0.0.1", tier=2)])
        # Keep TLS identity trusted, but deliberately assign it a different network origin.
        config = config.replace('netmask("127.0.0.1/32")', 'netmask("127.0.0.2/32")', 1)
        self.config.write_text(config)
        self.start()
        send(self.directory, self.port, ["wrong-origin"])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as source:
            source.sendto(b"legacy-device-event", ("127.0.0.1", self.port))
        found = wait_for_records(self.directory, 1)
        self.assertEqual(found[0]["source"], "legacy")
        self.assertEqual(found[0]["transport"], "udp")
        time.sleep(0.3)
        self.assertEqual(len(records(self.directory)), 1)

    @unittest.skipUnless(shutil.which('ansible-playbook'), 'Requires Ansible and community.crypto')
    def test_native_certificate_metadata_rejects_a_mismatched_server_key(self):
        tasks = yaml.safe_load((ROLE / 'tasks/tls.yml').read_text())
        # Exercise the actual metadata/assertion tasks, not privileged file installation.
        tasks = [task for task in tasks if 'ansible.builtin.copy' not in task]
        playbook = self.directory / 'certificate-check.yml'
        playbook.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
            vars=dict(syslog_ng_tls_cert_src=str(self.directory / 'tls/server.pem'),
                      syslog_ng_tls_ca_src=str(self.directory / 'tls/ca.pem'),
                      syslog_ng_tls_key_src=str(self.directory / 'tls/key.pem')), tasks=tasks)]))
        arguments = ['ansible-playbook', '-i', 'localhost,', str(playbook)]
        command(*arguments)
        (self.directory / 'tls/key.pem').write_bytes((self.directory / 'tls/producer.key').read_bytes())
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
