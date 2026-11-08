"""Read-only SDN discovery, verified TLS, and generated guest network resolution."""

import contextlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import threading
import unittest
from unittest import mock

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

spec = importlib.util.spec_from_file_location("proxmox_sdn", UPSTREAM / "shared/scripts/proxmox-sdn.py")
sdn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdn)


class SubnetDiscovery(unittest.TestCase):
    def test_one_ipv4_subnet_and_valid_gateway_are_required(self):
        valid = {"cidr": "192.0.2.0/24", "gateway": "192.0.2.1"}
        self.assertEqual(sdn.resolve_subnet([{"cidr": "2001:db8::/64"}, valid]),
                         {"cidr_ipv4": "192.0.2.0/24", "gateway_ipv4": "192.0.2.1"})
        for records in ([], [valid, valid], [{"cidr": "broken"}],
                        [{"cidr": "192.0.2.0/24"}],
                        [dict(valid, gateway="192.0.2.255")],
                        [dict(valid, gateway="192.0.3.1")]):
            with self.subTest(records=records), self.assertRaises(sdn.LookupError):
                sdn.resolve_subnet(records)

    def test_credentials_are_environment_only_and_conflicts_are_rejected(self):
        native = {"PROXMOX_VE_ENDPOINT": "https://pve.example.test/",
                  "PROXMOX_VE_API_TOKEN": "automation@pve!test=fixture-secret"}
        self.assertEqual(sdn.credentials(native),
                         ("https://pve.example.test", "automation@pve!test=fixture-secret"))
        aliases = {"TF_VAR_proxmox_api_url": "https://pve.example.test",
                   "TF_VAR_proxmox_api_token_id": "automation@pve!test",
                   "TF_VAR_proxmox_api_token_secret": "fixture-secret"}
        self.assertEqual(sdn.credentials(aliases), sdn.credentials(native))
        for override in ({"PROXMOX_API_URL": "https://different.example.test"},
                         {"PROXMOX_VE_INSECURE": "true"},
                         {"PROXMOX_VE_ENDPOINT": "http://pve.example.test"},
                         {"PROXMOX_VE_ENDPOINT": "https://user:password@pve.example.test"}):
            with self.subTest(override=override), self.assertRaises(sdn.LookupError):
                sdn.credentials(dict(native, **override))

    def test_failures_do_not_echo_credentials_or_api_response_bodies(self):
        environ = {"PROXMOX_VE_ENDPOINT": "https://pve.example.test",
                   "PROXMOX_VE_API_TOKEN": "automation@pve!test=private-token"}
        error = sdn.urllib.error.HTTPError("https://pve.example.test", 403, "private-token", {}, None)
        with mock.patch.object(sdn.urllib.request.OpenerDirector, "open", side_effect=error):
            with self.assertRaisesRegex(sdn.LookupError, "HTTP 403") as failure:
                sdn.lookup("ident", environ)
        self.assertNotIn("private-token", str(failure.exception))
        for vnet in ("../ident", "identity-long", "control/ident", None):
            with self.subTest(vnet=vnet), self.assertRaises(sdn.LookupError):
                sdn.lookup(vnet, environ)

    def test_transport_errors_identify_the_failure_without_echoing_private_details(self):
        environ = {"PROXMOX_VE_ENDPOINT": "https://pve.example.test",
                   "PROXMOX_VE_API_TOKEN": "automation@pve!test=private-token"}
        failures = ((ssl.SSLCertVerificationError(1, "private-token"), "certificate verification failed"),
                    (socket.gaierror(-2, "private-token"), "cannot resolve the API hostname"),
                    (TimeoutError("private-token"), "connection timed out"),
                    (ConnectionRefusedError("private-token"), "connection refused"),
                    (ssl.SSLError(1, "private-token"), "TLS handshake failed"))
        for reason, expected in failures:
            with self.subTest(reason=type(reason).__name__):
                error = sdn.urllib.error.URLError(reason)
                with mock.patch.object(sdn.urllib.request.OpenerDirector, "open", side_effect=error):
                    with self.assertRaisesRegex(sdn.LookupError, expected) as failure:
                        sdn.lookup("edge", environ)
                self.assertNotIn("private-token", str(failure.exception))


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform") and shutil.which("openssl"),
                     "Requires Terraform and OpenSSL in Linux/WSL")
class GeneratedSdnLookup(TierRepositoryTestCase):
    @contextlib.contextmanager
    def api(self):
        directory = Path(self.temp.name) / "tls"
        directory.mkdir(exist_ok=True)
        cert, key = directory / "ca.pem", directory / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", str(key), "-out", str(cert), "-days", "1",
                        "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost"],
                       check=True, capture_output=True)
        records = [{"cidr": "192.0.2.0/25", "gateway": "192.0.2.126"}]
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get("Authorization")))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"data": records}).encode())

            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        environ = {name: value for name, value in os.environ.items()
                   if not name.startswith(("PROXMOX_", "PM_VE_", "TF_VAR_proxmox_"))}
        environ.update(PROXMOX_VE_ENDPOINT=f"https://localhost:{server.server_port}/",
                       PROXMOX_VE_API_TOKEN="automation@pve!test=fixture-secret", SSL_CERT_FILE=str(cert))
        try:
            yield environ, records, requests
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_generated_linux_vms_and_containers_resolve_applied_subnet(self):
        self.generate()
        with self.api() as (environ, records, requests):
            for tier in ("tier-0", "tier-1", "tier-2"):
                repo = self.root / f"verify-{tier}"
                fixture = repo / "terraform/deployments/sdn-fixture"
                fixture.mkdir()
                (fixture / "hosts.yml").write_text("all:\n  children:\n    test:\n      hosts:\n        test-1: {}\n")
                (fixture / "ips.yml").write_text('platform_host_ips:\n  test-1: "192.0.2.10"\n')
                inputs = {"source": "../../modules/environment_guests",
                          "default_platform_node_name": "pve-test", "default_vm_template_id": 9100,
                          "ansible_inventory_path": str(fixture / "hosts.yml"),
                          "ansible_group_vars_paths": [str(fixture / "ips.yml")],
                          "network_zones": {"application": {"bridge": "app", "sdn_lookup": True},
                                            "unused": {"bridge": "unused", "sdn_lookup": True}},
                          "vm_instances": {"test-1": {"disk_size_gb": 30}}}
                container = dict(inputs, vm_instances={}, lxc_instances={
                    "test-1": {"disk_size_gb": 8, "template_file_id": "local:vztmpl/test.tar.zst"}})
                config = {"module": {"vm": inputs, "lxc": container},
                          "output": {"vm": {"value": '${module.vm.vm_instances["test-1"]}'},
                                     "lxc": {"value": '${module.lxc.lxc_instances["test-1"]}'}}}
                (fixture / "main.tf.json").write_text(json.dumps(config))
                init = subprocess.run(["terraform", "init", "-backend=false", "-input=false"],
                                      cwd=fixture, env=environ, capture_output=True, text=True)
                self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
                before = len(requests)
                result = subprocess.run(["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
                                        cwd=fixture, env=environ, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = json.loads(subprocess.check_output(["terraform", "output", "-json"], cwd=fixture))
                for kind in ("vm", "lxc"):
                    guest = output[kind]["value"]
                    self.assertEqual((guest["bridge"], guest["vlan_id"], guest["ipv4_address"],
                                      guest["ipv4_gateway"]), ("app", None, "192.0.2.10/25", "192.0.2.126"))
                self.assertEqual(len(requests) - before, 2)
                state = (fixture / "terraform.tfstate").read_text()
                self.assertNotIn("fixture-secret", state)
                self.assertTrue(all(path == "/api2/json/cluster/sdn/vnets/app/subnets?running=1"
                                    for path, _auth in requests))
                self.assertTrue(all(auth == "PVEAPIToken=automation@pve!test=fixture-secret"
                                    for _path, auth in requests))
                # A changed subnet cannot silently move an inventory address into another network.
                records[0]["cidr"] = "192.0.2.128/25"
                records[0]["gateway"] = "192.0.2.129"
                failed = subprocess.run(["terraform", "plan", "-input=false", "-no-color"],
                                        cwd=fixture, env=environ, capture_output=True, text=True)
                self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
                self.assertIn("Inventory IPs must be usable", failed.stdout + failed.stderr)
                records[0].update(cidr="192.0.2.0/25", gateway="192.0.2.126")

    def test_untrusted_tls_is_rejected_before_any_request(self):
        with self.api() as (environ, _records, requests):
            environ.pop("SSL_CERT_FILE")
            result = subprocess.run(["python3", str(UPSTREAM / "shared/scripts/proxmox-sdn.py")],
                                    input='{"vnet":"app"}', env=environ, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("verified HTTPS", result.stderr)
            self.assertNotIn("fixture-secret", result.stderr)
            self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
