"""Focused dedicated-VM contracts; synthetic inputs, no guests or credentials."""

import base64
import configparser
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "tier-1/ansible/roles/observability_vm"
TF = ROOT / "tier-1/terraform/deployments/observability"
ANSIBLE = os.environ.get("ANSIBLE_PLAYBOOK") or shutil.which("ansible-playbook")


class ObservabilityVMTests(unittest.TestCase):
    def setUp(self):
        self.values = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.values.update(yaml.safe_load(
            (ROOT / "tier-1/ansible/group_vars/observability.yml.example").read_text()))
        secret = "synthetic_test_password_0123456789"
        for key in ("metrics", "reader", "prepper", "prepper_core"):
            self.values[f"observability_vm_{key}_auth"] = {"username": key, "password": secret}
        for key in ("prepper_search_password", "dashboards_search_password", "oidc_grafana_secret",
                    "oidc_dashboards_secret", "grafana_admin_password", "grafana_secret_key"):
            self.values[f"observability_vm_{key}"] = secret
        self.values.update(inventory_hostname="otel-1", observability_vm_service="collector",
                           observability_vm_admin_staging={"path": "/tmp/synthetic-admin"},
                           observability_vm_netdata_admin_allow_from=["10.20.10.*"],
                           observability_vm_netdata_child_key="11111111-2222-4333-8444-555555555555",
                           observability_vm_netdata_peer_key="21111111-2222-4333-8444-555555555555")
        self.values["observability_vm_images"] = {
            key: f"registry.example.org/{key}@sha256:" + "a" * 64
            for key in self.values["observability_vm_images"]
        }
        self.values["observability_vm_log_scopes"] += [{
            "name": "approved-security", "kind": "projection", "port": 4401,
            "client_ca_src": "/synthetic/projection-ca.crt", "reader_backend_roles": ["security-readers"],
        }]
        self.env = Environment(loader=FileSystemLoader(ROLE / "templates"),
                               undefined=StrictUndefined, trim_blocks=True)
        self.env.filters.update(
            to_json=json.dumps,
            regex_replace=lambda value, pattern, replacement: re.sub(pattern, replacement, value),
            b64encode=lambda value: base64.b64encode(value.encode()).decode(),
            extract=lambda value, mapping: mapping[value],
        )
        self.env.globals["lookup"] = lambda *_: "SYNTHETIC CA"

    def render(self, name, **changes):
        return self.env.get_template(name).render(self.values | changes)

    def test_all_yaml_and_task_includes_parse(self):
        for path in ROLE.rglob("*.yml"):
            with self.subTest(path=path.name):
                content = yaml.safe_load(path.read_text())
                self.assertIsNotNone(content)
                if path.parent.name == "tasks":
                    for task in content:
                        for action in ("ansible.builtin.include_tasks", "ansible.builtin.import_tasks"):
                            if action in task:
                                self.assertTrue((path.parent / task[action]).is_file())

    def test_collector_dual_writes_and_scope_isolation(self):
        config = yaml.safe_load(self.render("collector.yml.j2"))
        self.assertEqual(config["service"]["pipelines"]["metrics"]["exporters"],
                         ["otlphttp/metric-1", "otlphttp/metric-2"])
        for exporter in config["exporters"].values():
            self.assertEqual(exporter["sending_queue"]["storage"], "file_storage")
            self.assertEqual(exporter["retry_on_failure"]["max_elapsed_time"], "0s")
            self.assertEqual(exporter["tls"]["ca_file"], "/tls/ca.crt")
        self.assertNotIn("traces/approved-security", config["service"]["pipelines"])
        anchors = [receiver["protocols"]["grpc"]["tls"]["client_ca_file"]
                   for name, receiver in config["receivers"].items() if name.startswith("otlp")]
        self.assertEqual(len(anchors), len(set(anchors)))

    def test_prepper_ports_match_collector_and_indices_are_scoped(self):
        collector = yaml.safe_load(self.render("collector.yml.j2"))
        prepper = yaml.safe_load(self.render("prepper.yml.j2"))
        self.assertEqual(len(prepper), 3)
        for name, pipeline in prepper.items():
            source = next(iter(pipeline["source"].values()))
            self.assertTrue(source["ssl"])
            self.assertIn("http_basic", source["authentication"])
            self.assertTrue(collector["exporters"][f"otlp/{name}"]["endpoint"].endswith(f':{source["port"]}'))
            sink = pipeline["sink"][0]["opensearch"]
            self.assertFalse(sink["insecure"])
            self.assertEqual(sink["number_of_replicas"], 1)
            self.assertEqual(len(sink["hosts"]), 3)
            self.assertIn(name, sink["index"])
        core = yaml.safe_load(self.render("prepper-core.yml.j2"))
        self.assertTrue(core["ssl"])
        self.assertIn("http_basic", core["authentication"])

    def test_read_router_does_not_route_writes_or_silently_promote(self):
        config = yaml.safe_load(self.render("query.yml.j2"))
        self.assertNotIn("unauthorized_user", config)
        user = config["users"][0]
        self.assertNotIn("default_url", user)
        route = user["url_map"][0]
        self.assertEqual(len(route["url_prefix"]), 1)
        for path in ("/api/v1/import/prometheus", "/api/v1/admin/tsdb/delete_series", "/write"):
            self.assertFalse(any(re.fullmatch(pattern, path) for pattern in route["src_paths"]))

    def test_search_bootstrap_is_explicit_and_tls_checks_are_enabled(self):
        for bootstrap in (False, True):
            config = yaml.safe_load(self.render("search.yml.j2", inventory_hostname="search-1",
                                               observability_vm_search_bootstrap=bootstrap))
            self.assertEqual("cluster.initial_cluster_manager_nodes" in config, bootstrap)
            self.assertEqual(config["node.name"], "search-1")
            self.assertEqual(len(config["discovery.seed_hosts"]), 3)
            self.assertTrue(config["plugins.security.ssl.transport.enforce_hostname_verification"])
            self.assertTrue(config["plugins.security.ssl.http.enabled"])
            self.assertFalse(config["plugins.security.allow_default_init_securityindex"])

    def test_frontends_use_verified_tls_and_read_only_sso(self):
        dashboards = yaml.safe_load(self.render("dashboards.yml.j2"))
        self.assertEqual(dashboards["opensearch.ssl.verificationMode"], "full")
        self.assertEqual(dashboards["opensearch_security.auth.type"], "openid")
        self.assertEqual(dashboards["opensearch_security.readonly_mode.roles"], ["kibana_user"])
        grafana = configparser.ConfigParser(interpolation=None)
        grafana.read_string(self.render("grafana.ini.j2"))
        self.assertEqual(grafana["database"]["path"], "/data/grafana.db")
        self.assertEqual(grafana["users"]["auto_assign_org_role"], "Viewer")
        self.assertEqual(grafana["auth.generic_oauth"]["tls_skip_verify_insecure"], "false")
        datasource = yaml.safe_load(self.render("datasource.yml.j2"))["datasources"][0]
        self.assertTrue(datasource["url"].endswith(":8427"))
        self.assertFalse(datasource["editable"])

    def test_quadlets_cover_every_product_and_keep_secrets_out_of_units(self):
        for service in self.values["observability_vm_images"]:
            if service == "netdata":
                continue  # Netdata uses its own host-access and native privilege-drop contract.
            with self.subTest(service=service):
                unit = self.render("service.container.j2", observability_vm_service=service)
                self.assertIn("User=1000:1000", unit)
                self.assertIn("RequiresMountsFor=/srv/observability", unit)
                self.assertIn("WantedBy=multi-user.target", unit)
                self.assertNotIn(self.values["observability_vm_metrics_auth"]["password"], unit)
                self.assertIn("@sha256:", unit)
                environment = self.render("service.env.j2", observability_vm_service=service)
                self.assertNotIn('="', environment)  # Podman env files preserve literal quotes.
        admin = self.render("search-security.container.j2")
        self.assertNotIn("WantedBy", admin)
        self.assertNotIn("-nhnv", admin)
        self.assertIn("Type=oneshot", admin)

    def test_netdata_installs_two_parents_and_five_children_with_private_diagnostics(self):
        hosts = (self.values["observability_vm_gateway_hosts"] + self.values["observability_vm_metrics_hosts"]
                 + self.values["observability_vm_search_hosts"])
        parents = []
        for host in hosts:
            with self.subTest(host=host):
                config = configparser.ConfigParser(interpolation=None)
                config.read_string(self.render("netdata.conf.j2", inventory_hostname=host))
                stream = configparser.ConfigParser(interpolation=None)
                stream.read_string(self.render("netdata-stream.conf.j2", inventory_hostname=host))
                self.assertEqual(config["global"]["hostname"], host)
                binding = config["web"]["bind to"]
                address = self.values["platform_host_ips"][host]
                self.assertIn(f"{address}:20000=dashboard^SSL=force", binding)
                self.assertEqual(config["web"]["allow dashboard from"], f"localhost {address} 10.20.10.*")
                self.assertEqual(config["web"]["allow management from"], "localhost")
                self.assertEqual(config["web"]["allow netdata.conf from"], "localhost")
                self.assertEqual(config["plugins"]["enable running new plugins"], "no")
                self.assertEqual(config["plugins"]["proc"], "yes")
                self.assertEqual(config["db"]["mode"], "dbengine")
                self.assertEqual(stream["stream"]["ssl skip certificate verification"], "no")
                self.assertEqual(stream["stream"]["CAfile"], "/etc/netdata/private/ca.crt")
                if host in self.values["observability_vm_gateway_hosts"]:
                    parents.append(host)
                    self.assertIn(f"{address}:19999=streaming^SSL=force", binding)
                    self.assertEqual(len(stream["stream"]["destination"].split()), 1)
                    peer = next(item for item in self.values["observability_vm_gateway_hosts"] if item != host)
                    self.assertEqual(stream["stream"]["destination"],
                                     f'{self.values["observability_vm_endpoints"][peer]}:19999:SSL')
                    self.assertEqual(stream["stream"]["api key"], self.values["observability_vm_netdata_peer_key"])
                    self.assertEqual(config["db"]["dbengine tier 0 retention size"], "8192MiB")
                    child = stream[self.values["observability_vm_netdata_child_key"]]
                    self.assertEqual(len(child["allow from"].split()), 5)
                    self.assertEqual(child["enable replication"], "yes")
                else:
                    self.assertNotIn("=streaming", binding)
                    self.assertEqual(len(stream["stream"]["destination"].split()), 2)
                    self.assertEqual(stream["stream"]["api key"], self.values["observability_vm_netdata_child_key"])
                    self.assertEqual(config["db"]["dbengine tier 0 retention size"], "256MiB")
                    self.assertEqual(stream.sections(), ["stream"])
        self.assertEqual(parents, ["otel-1", "otel-2"])

    def test_netdata_quadlet_preserves_history_identity_and_guest_only_host_access(self):
        for host, memory in (("otel-1", "2G"), ("metric-1", "512M")):
            unit = self.render("netdata.container.j2", inventory_hostname=host)
            self.assertIn("Entrypoint=/usr/sbin/netdata", unit)
            self.assertIn("Exec=-D -u netdata -s /host", unit)
            self.assertNotIn("User=1000", unit)
            self.assertIn("/srv/observability/netdata/cache:/var/cache/netdata", unit)
            self.assertIn("/srv/observability/netdata/lib:/var/lib/netdata", unit)
            self.assertIn("Volume=/proc:/host/proc:ro", unit)
            self.assertIn("Volume=/sys:/host/sys:ro", unit)
            self.assertNotIn("docker.sock", unit)
            self.assertNotIn("podman.sock", unit)
            self.assertNotIn("SYS_ADMIN", unit)
            self.assertIn(f"MemoryMax={memory}", unit)
        cloud = configparser.ConfigParser()
        cloud.read_string(self.render("netdata-cloud.conf.j2"))
        self.assertEqual(cloud["global"]["enabled"], "no")

    def test_netdata_is_installed_and_started_on_the_normal_seven_guest_path(self):
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        self.assertTrue(any(task.get("ansible.builtin.import_tasks") == "netdata.yml" for task in tasks))
        plays = yaml.safe_load((ROOT / "tier-1/ansible/playbooks/deployment/telemetry-hosts.yml").read_text())
        starts = [(index, task) for index, play in enumerate(plays) for task in play.get("tasks", [])
                  if task.get("ansible.builtin.import_role", {}).get("tasks_from") == "netdata-start.yml"]
        self.assertEqual(len(starts), 2)
        self.assertIn("inventory_hostname in observability_vm_gateway_hosts", starts[0][1]["when"])
        self.assertIn("inventory_hostname not in observability_vm_gateway_hosts", starts[1][1]["when"])
        backend = next(index for index, play in enumerate(plays) if play.get("name") ==
                       "Start persistent backends before gateways")
        self.assertLess(starts[0][0], starts[1][0])
        self.assertLess(starts[1][0], backend)

    def test_netdata_metric_bridge_has_one_owner_and_the_existing_native_prometheus_contract(self):
        for host in self.values["observability_vm_gateway_hosts"]:
            config = yaml.safe_load(self.render("collector.yml.j2", inventory_hostname=host))
            receiver = config["receivers"].get("prometheus/netdata")
            if host == "otel-2":
                self.assertIsNone(receiver)
                continue
            scrape, = receiver["config"]["scrape_configs"]
            self.assertEqual(scrape["scheme"], "https")
            self.assertEqual(scrape["metrics_path"], "/api/v1/allmetrics")
            self.assertEqual(scrape["params"], {"format": ["prometheus"], "help": ["no"], "allhosts": ["yes"]})
            self.assertEqual(scrape["tls_config"], {"ca_file": "/tls/ca.crt"})
            self.assertEqual(scrape["metric_relabel_configs"], [{"source_labels": ["__name__"],
                             "regex": "netdata_system_cpu_percentage_average", "action": "keep"}])
            self.assertIn("prometheus/netdata", config["service"]["pipelines"]["metrics"]["receivers"])
        config = yaml.safe_load(self.render("collector.yml.j2", observability_vm_netdata_scrape_metrics=[]))
        self.assertNotIn("prometheus/netdata", config["receivers"])

    def test_native_otel_parser_accepts_the_single_netdata_bridge(self):
        binary = os.environ.get("OTELCOL_BINARY")
        if not binary:
            self.skipTest("Set OTELCOL_BINARY to the pinned contrib binary")
        with tempfile.TemporaryDirectory() as temporary:
            for host in self.values["observability_vm_gateway_hosts"]:
                path = Path(temporary) / f"{host}.yaml"
                path.write_text(self.render("collector.yml.j2", inventory_hostname=host))
                result = subprocess.run([binary, "validate", "--config", str(path)], capture_output=True,
                                        text=True, timeout=30, env=os.environ | {
                                            "VM_USERNAME": "test", "VM_PASSWORD": "test",
                                            "DP_USERNAME": "test", "DP_PASSWORD": "test"})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_netdata_configuration_reader_when_available(self):
        binary = os.environ.get("NETDATA_BINARY")
        if not binary:
            self.skipTest("Set NETDATA_BINARY to the approved native Netdata binary")
        with tempfile.TemporaryDirectory() as temporary:
            for host in ("otel-1", "otel-2", "metric-1"):
                for template, section, key, expected in (
                    ("netdata.conf.j2", "global", "hostname", host),
                    ("netdata-stream.conf.j2", "stream", "enabled", "yes"),
                    ("netdata-cloud.conf.j2", "global", "enabled", "no"),
                ):
                    path = Path(temporary) / "native.conf"
                    path.write_text(self.render(template, inventory_hostname=host))
                    result = subprocess.run([binary, "-c", str(path), "-W", "get", section, key, "MISSING"],
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)

    def test_every_vm_disk_is_attached_and_matches_the_stable_guest_selector(self):
        inputs = (TF / "terraform.tfvars.example").read_text()
        hosts = re.findall(r'"((?:otel|metric|search)-[123])"\s*=\s*\{(.*?)\n  \}', inputs, re.S)
        self.assertEqual(len(hosts), 7)
        for host, definition in hosts:
            with self.subTest(host=host):
                self.assertRegex(definition, r'extra_disks\s*=\s*\[\{ interface = "scsi1"')
        main = (TF / "main.tf").read_text()
        self.assertRegex(main, r'extra_disks\s*=\s*each.value.extra_disks')
        self.assertTrue(self.values["observability_vm_data_device"].endswith("drive-scsi1"))
        tasks = (ROLE / "tasks/main.yml").read_text()
        self.assertIn("name: data_volume", tasks)
        self.assertIn("data_volume_expected_uuid:", tasks)
        volume = next(task for task in yaml.safe_load(tasks)
                      if task.get("ansible.builtin.include_role", {}).get("name") == "data_volume")
        label = volume["vars"]["data_volume_label"]
        self.assertLessEqual(len(label), 11)


@unittest.skipUnless(ANSIBLE and os.name == "posix", "Requires native Linux Ansible and community.crypto")
class NativeSearchKeyTests(unittest.TestCase):
    def test_pkcs1_node_and_admin_keys_preserve_identity_idempotence_and_rotation(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        action = "community.crypto.openssl_privatekey_convert"
        node = next(task for task in yaml.safe_load((ROLE / "tasks/certificates.yml").read_text())
                    if action in task)
        security = yaml.safe_load((ROLE / "tasks/search-security.yml").read_text())
        admin = next(task for parent in security for task in parent.get("block", []) if action in task)
        with tempfile.TemporaryDirectory(prefix="observability-key-test-") as temporary:
            directory = Path(temporary)
            config = directory / "config"
            (config / "tls").mkdir(parents=True)
            staging = directory / "admin"
            staging.mkdir()
            source = directory / "provider-key.pem"
            inventory = directory / "inventory.yml"
            inventory.write_text(yaml.safe_dump({"all": {"hosts": {"search-1": {
                "ansible_connection": "local", "ansible_python_interpreter": sys.executable,
            }}}}))
            tasks = []
            for name, original in (("node", node), ("admin", admin)):
                task = dict(original)
                task[action] = original[action] | {"owner": str(os.getuid()), "group": str(os.getgid())}
                task["register"] = f"converted_{name}"
                tasks.append(task)
                tasks.append(task | {"name": f"Repeat {name} conversion", "register": f"repeated_{name}"})
            tasks.append({"name": "Require idempotent repeat conversions", "ansible.builtin.assert": {
                "that": ["not repeated_node.changed", "not repeated_admin.changed"],
            }})
            playbook = directory / "convert.yml"
            playbook.write_text(yaml.safe_dump([{
                "hosts": "all", "gather_facts": False, "vars": {
                    "observability_vm_config_path": str(config),
                    "observability_vm_search_hosts": ["search-1"],
                    "observability_vm_tls": {"search-1": {"key_src": str(source)}},
                    "observability_vm_search_admin_tls": {"key_src": str(source)},
                    "observability_vm_admin_staging": {"path": str(staging)},
                }, "tasks": tasks,
            }], sort_keys=False))
            environment = os.environ | {"ANSIBLE_LOCAL_TEMP": str(directory / "ansible-local")}
            # The second fixture rotates an already-converted key at the same runtime paths.
            for rotation in range(2):
                with self.subTest(rotation=rotation):
                    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    original = key.private_bytes(serialization.Encoding.PEM,
                                                serialization.PrivateFormat.TraditionalOpenSSL,
                                                serialization.NoEncryption())
                    source.write_bytes(original)
                    result = subprocess.run([ANSIBLE, "-i", str(inventory), str(playbook)],
                                            capture_output=True, text=True, env=environment, timeout=120)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(source.read_bytes(), original)
                    for output, mode in ((config / "tls/tls.key", 0o640), (staging / "tls.key", 0o600)):
                        converted = output.read_bytes()
                        self.assertTrue(converted.startswith(b"-----BEGIN PRIVATE KEY-----"))
                        actual = serialization.load_pem_private_key(converted, password=None)
                        self.assertEqual(actual.private_numbers(), key.private_numbers())
                        self.assertEqual(stat.S_IMODE(output.stat().st_mode), mode)


if __name__ == "__main__":
    unittest.main()
