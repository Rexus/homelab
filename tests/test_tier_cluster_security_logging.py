"""Native cluster log rendering, Talos patch validation and isolated mTLS/replay checks."""

import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest

import yaml

from syslog_receiver_test_support import certificates
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / "shared/ansible/roles/cluster_security_logging"
NATIVE = os.name != "nt" and bool(shutil.which("ansible-playbook"))
RENDER = NATIVE and bool(shutil.which("helm")) and os.getenv("HOMELAB_NATIVE_SECURITY_LOGGING_TESTS") == "1"
BINARY = os.getenv("FLUENT_BIT_TEST_BINARY")
TALOS = os.getenv("TALOSCTL_TEST_BINARY")
TALOS14 = os.getenv("TALOSCTL14_TEST_BINARY")


def settings(output, tier=0):
    return {
        "cluster_security_logging_action": "render",
        "cluster_security_logging_kubeconfig": "/nonexistent/never-contact-kubernetes",
        "cluster_security_logging_context": "never-contact-kubernetes",
        "cluster_security_logging_output": str(output),
        "cluster_security_logging_cluster": ["control", "platform", "workload"][tier],
        "cluster_security_logging_tier": tier,
        "cluster_security_logging_talos_schema": "v1.13",
        "cluster_security_logging_chart_version": "0.55.0",
        "cluster_security_logging_approved_repositories": ["https://fluent.github.io/helm-charts"],
        "cluster_security_logging_image_tag": "4.2.2",
        "cluster_security_logging_approved_image_repositories": ["cr.fluentbit.io/fluent/fluent-bit"],
        "cluster_security_logging_receiver": "127.0.0.1",
        "cluster_security_logging_receiver_name": "localhost",
        "cluster_security_logging_nodes": [{
            "name": ["k8ctl-1", "platform-k8ctl-1", "workload-k8ctl-1"][tier],
            "stream": "producer", "source_address": "127.0.0.1",
            "tls_secret": "node-tls", "tls_dn": "CN=producer", "control_plane": True,
        }],
    }


def run_role(directory, values, tier=0, repo=None):
    repo = repo or UPSTREAM / f"tier-{tier}"
    fixture = directory / "inputs.json"
    fixture.write_text(json.dumps(values))
    return subprocess.run(
        ["ansible-playbook", "-i", "localhost,", "playbooks/deployment/cluster-security-logging.yml",
         "-e", "@" + str(fixture)], cwd=repo / "ansible", capture_output=True, text=True, timeout=180,
        env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
    )


def port():
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return candidate.getsockname()[1]


class SecurityLogging(TierRepositoryTestCase):
    def test_generated_ownership_and_tier_input_node_names(self):
        self.generate()
        self.assertTrue((self.root / "verify-shared/ansible/roles/cluster_security_logging/tasks/main.yml").is_file())
        self.assertFalse((self.root / "verify-shared/ansible/inventory").exists())
        for tier in range(3):
            repo = self.root / f"verify-tier-{tier}"
            self.assertFalse((repo / "ansible/roles/cluster_security_logging").exists())
            self.assertTrue((repo / "ansible/playbooks/deployment/cluster-security-logging.yml").is_file())
            values = yaml.safe_load((repo / "ansible/group_vars/cluster_security_logging.yml.example").read_text())
            inventory = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())
            hosts = inventory["all"]["children"]["talos_control_plane"]["hosts"]
            self.assertEqual({n["name"] for n in values["cluster_security_logging_nodes"]}, set(hosts))
            self.assertEqual(values["cluster_security_logging_tier"], tier)
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertEqual(defaults["cluster_security_logging_nodes"], [])
        self.assertEqual(defaults["cluster_security_logging_cluster"], "")
        if RENDER:
            with tempfile.TemporaryDirectory(prefix="security-logging-generated-") as generated_temp:
                generated = Path(generated_temp)
                result = run_role(generated, settings(generated / "render"), repo=self.root / "verify-tier-0")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((generated / "render/security-log-producer-manifests.yml").is_file())

    @unittest.skipUnless(NATIVE, "Requires native Ansible, ansible.utils and netaddr")
    def test_preflight_rejects_missing_approval_and_unsafe_routes_before_installation(self):
        bad = [
            {"cluster_security_logging_chart_version": "latest"},
            {"cluster_security_logging_approved_repositories": []},
            {"cluster_security_logging_image_tag": "latest"},
            {"cluster_security_logging_approved_image_repositories": []},
            {"cluster_security_logging_queue_path": "/var/log"},
            {"cluster_security_logging_queue_mib_per_output": 0},
            {"cluster_security_logging_action": "apply"},
        ]
        node = settings(Path(self.temp.name))["cluster_security_logging_nodes"][0]
        for field in ("stream", "tls_secret"):
            other = dict(node, name="fixture-worker", stream="worker", tls_secret="worker-tls")
            other[field] = node[field]
            bad.append({"cluster_security_logging_nodes": [node, other]})
        bad.append({"cluster_security_logging_nodes": [dict(node, source_address=["127.0.0.1"])]})
        for index, overrides in enumerate(bad):
            with self.subTest(overrides=overrides):
                output = Path(self.temp.name) / f"reject-{index}"
                result = run_role(Path(self.temp.name), dict(settings(output), **overrides))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("assertion", result.stdout)
                self.assertFalse(output.exists())

    def test_api_operations_have_explicit_targets_and_secret_checks_are_private(self):
        for path in (ROLE / "tasks").glob("*.yml"):
            for task in yaml.safe_load(path.read_text()):
                self.assertNotIn("ansible.builtin.shell", task)
                self.assertNotIn("ansible.builtin.command", task)
                if "kubernetes.core.k8s_info" in task:
                    self.assertIs(task["kubernetes.core.k8s_info"]["validate_certs"], True)
                    self.assertIn("cluster_security_logging_kubeconfig", task["kubernetes.core.k8s_info"]["kubeconfig"])
                    if task["kubernetes.core.k8s_info"]["kind"] == "Secret":
                        self.assertIs(task["no_log"], True)


class TLSIntake:
    """Disposable local receiver: require a trusted client and an enrolled CN/origin."""

    def __init__(self, tls, listen_port):
        self.records = []
        self.peers = []
        self.stop = threading.Event()
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.load_cert_chain(tls / "server.pem", tls / "server.key")
        self.context.load_verify_locations(tls / "ca.pem")
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", listen_port))
        self.socket.listen()
        self.socket.settimeout(0.1)
        self.workers = []
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        while not self.stop.is_set():
            try:
                connection, address = self.socket.accept()
            except (TimeoutError, OSError):
                continue
            worker = threading.Thread(target=self.read, args=(connection, address), daemon=True)
            self.workers.append(worker)
            worker.start()

    def read(self, connection, address):
        try:
            connection.settimeout(1)
            with self.context.wrap_socket(connection, server_side=True) as encrypted:
                subject = dict(field for rdn in encrypted.getpeercert()["subject"] for field in rdn)
                if address[0] != "127.0.0.1" or subject.get("commonName") != "producer":
                    return
                self.peers.append(subject["commonName"])
                pending = b""
                while not self.stop.is_set():
                    try:
                        received = encrypted.recv(65536)
                    except TimeoutError:
                        continue
                    if not received:
                        break
                    pending += received
                    while b"\n" in pending:
                        record, pending = pending.split(b"\n", 1)
                        self.records.append(record.decode())
        except (ssl.SSLError, OSError):
            connection.close()

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=2)


@unittest.skipUnless(RENDER, "Set HOMELAB_NATIVE_SECURITY_LOGGING_TESTS=1 with Ansible, Helm and repository access")
class NativeSecurityLogging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cluster-security-logging-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        certificates(cls.directory)
        cls.values = settings(cls.directory / "render")
        cls.values["cluster_security_logging_manage_secrets"] = True
        cls.values["cluster_security_logging_secrets"] = {"security-logging/node-tls": {
            "ca.crt": (cls.directory / "tls/ca.pem").read_text(),
            "tls.crt": (cls.directory / "tls/producer.pem").read_text(),
            "tls.key": (cls.directory / "tls/producer.key").read_text(),
        }}
        result = run_role(cls.directory, cls.values)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        resources = list(yaml.safe_load_all((cls.directory / "render/security-log-producer-manifests.yml").read_text()))
        cls.resources = [r for r in resources if r]
        cls.config = next(r for r in cls.resources if r["kind"] == "ConfigMap")["data"]["fluent-bit.conf"]

    def setUp(self):
        self.test_temp = tempfile.TemporaryDirectory(prefix="cluster-log-process-")
        self.addCleanup(self.test_temp.cleanup)
        self.work = Path(self.test_temp.name)
        self.processes = []
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def test_pinned_chart_mounts_node_identity_queues_and_loopback_only(self):
        daemon = next(r for r in self.resources if r["kind"] == "DaemonSet")
        pod = daemon["spec"]["template"]["spec"]
        placement = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
        self.assertEqual(placement["nodeSelectorTerms"], [{"matchFields": [{
            "key": "metadata.name", "operator": "In", "values": ["k8ctl-1"],
        }]}])
        self.assertFalse(pod.get("nodeSelector"))
        self.assertTrue(pod["hostNetwork"])
        self.assertFalse(pod["automountServiceAccountToken"])
        mounts = {m["name"]: m for m in pod["containers"][0]["volumeMounts"]}
        self.assertTrue(mounts["varlog"]["readOnly"])
        self.assertTrue(mounts["collector-tls"]["readOnly"])
        secrets = [v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v]
        self.assertEqual(secrets, ["node-tls"])
        self.assertNotIn("ClusterRole", {r["kind"] for r in self.resources})
        self.assertIn("Listen 127.0.0.1", self.config)
        self.assertEqual(self.config.count("tls.verify_hostname On"), 3)
        self.assertEqual(self.config.count("storage.total_limit_size 134217728"), 3)
        self.assertNotIn("PRIVATE KEY", self.config)
        self.assertEqual((self.directory / "render/security-log-producer-manifests.yml").stat().st_mode & 0o777, 0o600)

    def test_all_tier_entrypoints_and_worker_configuration_use_shared_role(self):
        for tier in (1, 2):
            values = settings(self.work / f"tier-{tier}", tier)
            if tier == 2:
                values["cluster_security_logging_nodes"].append({
                    "name": "fixture-worker", "control_plane": False, "stream": "worker",
                    "tls_secret": "worker-tls", "tls_dn": "CN=worker", "source_address": "127.0.0.2",
                })
                values["cluster_security_logging_talos_schema"] = "v1.14"
            result = run_role(self.work, values, tier)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            catalog = yaml.safe_load((self.work / f"tier-{tier}/receiver-sources.yml").read_text())
            self.assertEqual(catalog["syslog_ng_sources"], [{
                "name": node["stream"], "address": node["source_address"],
                "tier": tier, "tls_dn": node["tls_dn"],
            } for node in values["cluster_security_logging_nodes"]])
            for node in values["cluster_security_logging_nodes"]:
                manifest = self.work / f"tier-{tier}/security-log-{node['stream']}-manifests.yml"
                daemon = next(r for r in yaml.safe_load_all(manifest.read_text()) if r and r["kind"] == "DaemonSet")
                pod = daemon["spec"]["template"]["spec"]
                secrets = [v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v]
                self.assertEqual(secrets, [node["tls_secret"]])
                placement = pod["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
                self.assertEqual(placement["nodeSelectorTerms"], [{"matchFields": [{
                    "key": "metadata.name", "operator": "In", "values": [node["name"]],
                }]}])
            if tier == 2:
                worker = (self.work / "tier-2/security-log-worker-values.yml").read_text()
                self.assertNotIn("Alias kubernetes-audit", yaml.safe_load(worker)["config"]["inputs"])
                policy = list(yaml.safe_load_all((self.work / "tier-2/talos-api-audit.patch.yml").read_text()))
                self.assertEqual([p["kind"] for p in policy], ["KubeAuditPolicyConfig", "KubeAPIServerConfig"])

    def test_mismatched_and_ca_client_material_is_rejected_before_helm(self):
        for field, source in (("tls.key", "server.key"), ("tls.crt", "impostor.pem"), ("tls.crt", "ca.pem")):
            with self.subTest(field=field, source=source):
                values = json.loads(json.dumps(self.values))
                values["cluster_security_logging_output"] = str(self.work / source)
                values["cluster_security_logging_secrets"]["security-logging/node-tls"][field] = (
                    self.directory / "tls" / source).read_text()
                result = run_role(self.work, values)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Install or converge the exact native Helm release", result.stdout)

    @unittest.skipUnless(TALOS, "Set TALOSCTL_TEST_BINARY for native offline Talos configuration validation")
    def test_generated_talos_patches_validate_with_matching_cli(self):
        self.validate_talos(TALOS, self.directory / "render")

    @unittest.skipUnless(TALOS14, "Set TALOSCTL14_TEST_BINARY for native Talos 1.14 document validation")
    def test_newer_talos_document_patches_validate_with_matching_cli(self):
        values = settings(self.work / "v1.14")
        values["cluster_security_logging_talos_schema"] = "v1.14"
        result = run_role(self.work, values)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.validate_talos(TALOS14, self.work / "v1.14")

    def validate_talos(self, binary, artifacts):
        subprocess.run([binary, "gen", "config", "log-test", "https://192.0.2.10:6443",
                        "--output-dir", str(self.work), "--with-docs=false", "--with-examples=false"],
                       capture_output=True, text=True, check=True)
        for kind in ("controlplane", "worker"):
            arguments = [binary, "machineconfig", "patch", str(self.work / f"{kind}.yaml"),
                         "--patch", "@" + str(artifacts / "talos-system-logging.patch.yml")]
            if kind == "controlplane":
                arguments += ["--patch", "@" + str(artifacts / "talos-api-audit.patch.yml")]
            merged = self.work / f"{kind}-logging.yaml"
            subprocess.run(arguments + ["--output", str(merged)], capture_output=True, text=True, check=True)
            result = subprocess.run([binary, "validate", "--config", str(merged), "--mode", "metal"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def process_config(self, receiver_port, expected_name="localhost"):
        for folder in ("log/containers", "log/audit/kube", "buffers"):
            (self.work / folder).mkdir(parents=True, exist_ok=True)
        config = self.config.replace("/var/log", str(self.work / "log"))
        config = config.replace("/buffers", str(self.work / "buffers"))
        config = config.replace("/collector-tls/ca.crt", str(self.directory / "tls/ca.pem"))
        config = config.replace("/collector-tls/tls.crt", str(self.directory / "tls/producer.pem"))
        config = config.replace("/collector-tls/tls.key", str(self.directory / "tls/producer.key"))
        self.input_port = port()
        config = config.replace("Port 6050", f"Port {self.input_port}")
        config = config.replace("Port 6514", f"Port {receiver_port}")
        config = config.replace("HTTP_Port 2020", f"HTTP_Port {port()}")
        config = config.replace("tls.vhost localhost", f"tls.vhost {expected_name}")
        self.config_file = self.work / "fluent-bit.conf"
        self.config_file.write_text(config)

    def start(self):
        output = (self.work / f"process-{len(self.processes)}.log").open("w")
        self.addCleanup(output.close)
        process = subprocess.Popen([BINARY, "-c", str(self.config_file)], stdout=output, stderr=output)
        self.processes.append(process)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail("Native Fluent Bit exited: " + (self.work / f"process-{len(self.processes)-1}.log").read_text())
            try:
                with socket.create_connection(("127.0.0.1", self.input_port), timeout=0.2):
                    return process
            except OSError:
                time.sleep(0.05)
        self.fail("Native Fluent Bit did not open the loopback input")

    def send(self, message):
        with socket.create_connection(("127.0.0.1", self.input_port), timeout=2) as connection:
            connection.sendall(message.encode() + b"\n")

    def wait_records(self, intake, count):
        deadline = time.monotonic() + 12
        while len(intake.records) < count and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertGreaterEqual(len(intake.records), count, "\n".join(p.read_text() for p in self.work.glob("process*.log")))

    @unittest.skipUnless(BINARY, "Set FLUENT_BIT_TEST_BINARY for native config and local mTLS process checks")
    def test_native_config_and_mtls_preserve_all_three_raw_input_paths(self):
        receiver_port = port()
        self.process_config(receiver_port)
        audit = '{"auditID":"audit-canary","verb":"get","objectRef":{"resource":"secrets"}}'
        pod = "2026-10-26T08:00:00Z stdout F pod-canary"
        system = '{"msg":"system-canary","nested":{"retain":true}}'
        (self.work / "log/audit/kube/kube-apiserver.log").write_text(audit + "\n")
        (self.work / "log/containers/app_default_app-abc.log").write_text(pod + "\n")
        checked = subprocess.run([BINARY, "--dry-run", "-c", str(self.config_file)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        intake = TLSIntake(self.directory / "tls", receiver_port)
        self.addCleanup(intake.close)
        self.start()
        self.send(system)
        self.wait_records(intake, 3)
        for raw in (audit, pod, system):
            self.assertTrue(any(record.endswith(raw) for record in intake.records), intake.records)
        self.assertTrue(all(re.match(r"^<\d+>1 ", r) for r in intake.records), intake.records)
        self.assertEqual(set(intake.peers), {"producer"})
        self.assertTrue(any("source_file=" in r and "app_default_app" in r for r in intake.records))

    @unittest.skipUnless(BINARY, "Set FLUENT_BIT_TEST_BINARY for native hostname verification checks")
    def test_wrong_receiver_hostname_fails_closed(self):
        self.assert_receiver_rejected("wrong-receiver.invalid", "ca.pem")

    @unittest.skipUnless(BINARY, "Set FLUENT_BIT_TEST_BINARY for native trust-anchor verification checks")
    def test_wrong_receiver_ca_fails_closed(self):
        self.assert_receiver_rejected("localhost", "untrusted.pem")

    def assert_receiver_rejected(self, expected_name, ca_file):
        receiver_port = port()
        self.process_config(receiver_port, expected_name)
        config = self.config_file.read_text().replace(str(self.directory / "tls/ca.pem"), str(self.directory / "tls" / ca_file))
        self.config_file.write_text(config)
        intake = TLSIntake(self.directory / "tls", receiver_port)
        self.addCleanup(intake.close)
        self.start()
        self.send("must-not-arrive")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            logs = "\n".join(p.read_text() for p in self.work.glob("process*.log"))
            if "certificate" in logs.lower() or "hostname" in logs.lower():
                break
            time.sleep(0.05)
        self.assertRegex(logs.lower(), "certificate|hostname")
        self.assertEqual(intake.records, [])

    @unittest.skipUnless(BINARY, "Set FLUENT_BIT_TEST_BINARY for native persistent queue replay checks")
    def test_outage_queue_replays_after_collector_process_crash(self):
        receiver_port = port()
        self.process_config(receiver_port)
        process = self.start()
        self.send("queued-before-crash")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if "failed to flush chunk" in (self.work / "process-0.log").read_text():
                break
            time.sleep(0.05)
        else:
            self.fail("The queued record did not reach a failed output attempt")
        process.kill()
        process.wait(timeout=5)
        intake = TLSIntake(self.directory / "tls", receiver_port)
        self.addCleanup(intake.close)
        self.start()
        self.wait_records(intake, 1)
        self.assertTrue(any(r.endswith("queued-before-crash") for r in intake.records), intake.records)


if __name__ == "__main__":
    unittest.main()
