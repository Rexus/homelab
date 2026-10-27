"""Independent private API gateways: input gates, reproducible rendering and native parsers."""

import copy
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


TIER = UPSTREAM / "tier-0"
ROLE = TIER / "ansible/roles/cluster_endpoint"
SHARED = UPSTREAM / "shared/ansible/roles/shared"
NATIVE = os.name != "nt" and bool(shutil.which("ansible-playbook"))
HAPROXY = os.getenv("HOMELAB_HAPROXY") or shutil.which("haproxy")
KEEPALIVED = os.getenv("HOMELAB_KEEPALIVED") or shutil.which("keepalived")


def inputs():
    values = yaml.safe_load((TIER / "ansible/group_vars/cluster_endpoint.yml.example").read_text())
    values["cluster_endpoint_fault_domains_validated"] = True
    values["cluster_endpoint_network_gates_validated"] = True
    return values


def render_haproxy(values):
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    environment = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, keep_trailing_newline=True)
    return environment.from_string((ROLE / "templates/haproxy.cfg.j2").read_text()).render(defaults | values)


def render_keepalived(values, host):
    environment = jinja2.Environment(undefined=jinja2.StrictUndefined, trim_blocks=True, keep_trailing_newline=True)
    environment.filters["regex_replace"] = lambda value, pattern, replacement: re.sub(pattern, replacement, value)
    return environment.from_string((SHARED / "templates/keepalived.conf.j2").read_text()).render(
        inventory_hostname=host,
        groups={"cluster_endpoint": list(values["platform_host_ips"])},
        platform_host_ips=values["platform_host_ips"],
        shared_keepalived_group="cluster_endpoint",
        shared_keepalived_interface=values["cluster_endpoint_interface"],
        shared_keepalived_instances=values["cluster_endpoint_endpoints"],
        shared_keepalived_instance_name_prefix="cluster_api_",
        shared_keepalived_scripts=[{"name": "chk_cluster_api_haproxy",
                                    "path": "/usr/bin/systemctl is-active --quiet haproxy"}],
        shared_keepalived_default_track_scripts=["chk_cluster_api_haproxy"],
    )


def run_preflight(directory, values, members=None, tasks=None, roles=None):
    inventory = directory / "hosts.yml"
    inventory.write_text(yaml.safe_dump({"all": {"vars": {"ansible_connection": "local"}, "children": {
        "cluster_endpoint": {"hosts": {host: {} for host in (members or ["api-gw-1", "api-gw-2"])}}
    }}}))
    variables = directory / "inputs.json"
    variables.write_text(json.dumps(values))
    playbook = directory / "check.yml"
    playbook.write_text(yaml.safe_dump([{"hosts": "cluster_endpoint", "gather_facts": False,
                                       "any_errors_fatal": True, "tasks": tasks or [{
                                           "ansible.builtin.include_role": {
                                               "name": "cluster_endpoint", "tasks_from": "preflight"}}]}]))
    return subprocess.run(
        ["ansible-playbook", "-i", str(inventory), str(playbook), "-e", "@" + str(variables)],
        cwd=TIER / "ansible", capture_output=True, text=True, timeout=90,
        env=dict(os.environ, ANSIBLE_CONFIG=str(TIER / "ansible/ansible.cfg"),
                 ANSIBLE_ROLES_PATH=os.pathsep.join([str(path) for path in
                                                   ([roles] if roles else []) + [ROLE.parent, SHARED.parent]]),
                 ANSIBLE_LOCAL_TEMP=str(directory / "controller"),
                 ANSIBLE_REMOTE_TEMP=str(directory / "remote")),
    )


class ClusterEndpoint(TierRepositoryTestCase):
    def test_el_gateway_keeps_selinux_with_native_persistent_permission(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        permissions = [task['ansible.posix.seboolean'] for task in tasks if 'ansible.posix.seboolean' in task]
        self.assertEqual(permissions, [{'name': 'haproxy_connect_any', 'state': True, 'persistent': True}])
        self.assertFalse(any('ansible.posix.selinux' in task for task in tasks))

    def test_generated_pair_inputs_and_role_preserve_tier_ownership(self):
        self.generate()
        role_files = [path.relative_to(ROLE) for path in ROLE.rglob("*") if path.is_file()]
        generated = self.root / "verify-tier-0"
        for relative in role_files:
            self.assertEqual((ROLE / relative).read_text(),
                             (generated / "ansible/roles/cluster_endpoint" / relative).read_text())
        for tier in (1, 2):
            self.assertFalse((self.root / f"verify-tier-{tier}/ansible/roles/cluster_endpoint").exists())
        groups = yaml.safe_load((generated / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
        self.assertEqual(set(groups["cluster_endpoint"]["hosts"]), {"api-gw-1", "api-gw-2"})
        self.assertIn("cluster_endpoint", groups["guests"]["children"])
        values = inputs()
        talos = yaml.safe_load((TIER / "ansible/group_vars/talos.yml.example").read_text())
        self.assertEqual(values["cluster_endpoint_endpoints"][0]["control_planes"], talos["platform_host_ips"])
        self.assertTrue(set(values["platform_host_ips"]).isdisjoint(talos["platform_host_ips"]))
        example = yaml.safe_load((TIER / "ansible/group_vars/cluster_endpoint.yml.example").read_text())
        self.assertFalse(example["cluster_endpoint_fault_domains_validated"])
        self.assertFalse(example["cluster_endpoint_network_gates_validated"])
        local = generated / "ansible/group_vars/cluster_endpoint.yml"
        local.write_text("# Private operator-owned inputs\n")
        self.generate("--refresh")
        self.assertEqual(local.read_text(), "# Private operator-owned inputs\n")
        for tier in range(3):
            for lock in (UPSTREAM / f"tier-{tier}/terraform/deployments").glob("*/.terraform.lock.hcl"):
                target = self.root / f"verify-tier-{tier}" / lock.relative_to(UPSTREAM / f"tier-{tier}")
                self.assertEqual(lock.read_text(), target.read_text(), str(target))

    def test_recipe_reuses_shared_without_public_edge_or_cluster_dependencies(self):
        plays = yaml.safe_load((TIER / "ansible/playbooks/deployment/cluster-endpoint.yml").read_text())
        self.assertFalse(plays[0]["gather_facts"])
        self.assertTrue(plays[0]["any_errors_fatal"])
        self.assertEqual(plays[1]["serial"], 1)
        self.assertEqual(plays[1]["roles"], ["baseline", "cluster_endpoint"])
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        includes = [task for task in tasks if "ansible.builtin.include_role" in task]
        keepalived = next(task for task in tasks if "block" in task)
        includes.extend(keepalived["block"])
        self.assertEqual([task["ansible.builtin.include_role"] for task in includes], [
            {"name": "shared", "tasks_from": name} for name in ("packages", "sysctl", "keepalived")])
        self.assertEqual(keepalived["module_defaults"]["ansible.builtin.template"]["validate"],
                         "/usr/sbin/keepalived --config-test -f %s")
        template = next(task for task in tasks if "ansible.builtin.template" in task)
        self.assertEqual(template["ansible.builtin.template"]["validate"], "/usr/sbin/haproxy -c -f %s")
        for path in ROLE.rglob("*.yml"):
            text = path.read_text()
            for unwanted in ("edge_load_balancer", "kubernetes.core.", "ansible.builtin.shell", "50000"):
                self.assertNotIn(unwanted, text)

    def test_render_is_deterministic_and_endpoints_never_share_backends(self):
        values = inputs()
        first = render_haproxy(values)
        self.assertIn("bind 10.10.10.62:6443", first)
        self.assertEqual(len(re.findall(r"^  server ", first, re.MULTILINE)), 3)
        self.assertNotRegex(first, r"50000|\bssl\b|\bcrt\b|send-proxy|0\.0\.0\.0|\*:")
        values["cluster_endpoint_endpoints"].append({
            "name": "platform", "tier": 1, "vip_cidr": "10.10.10.63/24", "virtual_router_id": 41,
            "control_planes": {"platform-k8ctl-1": "10.20.13.10"},
        })
        rendered = render_haproxy(values)
        control, platform = rendered.split("frontend api_platform")
        self.assertNotIn("10.20.13.10", control)
        self.assertNotIn("10.10.13.10", platform)
        values["cluster_endpoint_endpoints"].reverse()
        for endpoint in values["cluster_endpoint_endpoints"]:
            endpoint["control_planes"] = dict(reversed(list(endpoint["control_planes"].items())))
        self.assertEqual(rendered, render_haproxy(values))
        one = render_keepalived(values, "api-gw-1")
        two = render_keepalived(values, "api-gw-2")
        self.assertIn("priority 110", one)
        self.assertIn("priority 100", two)
        self.assertIn("unicast_src_ip 10.10.10.60", one)
        self.assertIn("unicast_src_ip 10.10.10.61", two)
        self.assertEqual(one.count("state BACKUP"), 2)
        self.assertEqual(one.count("chk_cluster_api_haproxy"), 3)

    def test_gateway_addresses_and_vips_do_not_collide_with_active_tier_zero_examples(self):
        values = inputs()
        allocated = set(values["platform_host_ips"].values())
        allocated.update(endpoint["vip_cidr"].split("/")[0] for endpoint in values["cluster_endpoint_endpoints"])
        for path in (TIER / "ansible/group_vars").glob("*.example"):
            if path.name == "cluster_endpoint.yml.example":
                continue
            other = (yaml.safe_load(path.read_text()) or {}).get("platform_host_ips", {})
            self.assertFalse(allocated.intersection(other.values()), str(path))


@unittest.skipUnless(NATIVE, "Requires Ansible on Linux/WSL with ansible.utils and netaddr")
class NativeClusterEndpoint(unittest.TestCase):
    def test_deployment_recipe_passes_native_syntax_check(self):
        result = subprocess.run(
            ["ansible-playbook", "--syntax-check", "-i", str(TIER / "ansible/inventory/hosts.yml.example"),
             str(TIER / "ansible/playbooks/deployment/cluster-endpoint.yml")],
            cwd=TIER / "ansible", capture_output=True, text=True, timeout=30,
            env=dict(os.environ, ANSIBLE_CONFIG=str(TIER / "ansible/ansible.cfg")),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_private_and_cross_tier_address_maps_pass_without_cluster_inventory(self):
        values = inputs()
        with tempfile.TemporaryDirectory(prefix="cluster-endpoint-") as name:
            directory = Path(name)
            for tier in (0, 1, 2):
                if tier:
                    values["cluster_endpoint_endpoints"].append({
                        "name": f"tier{tier}", "tier": tier, "vip_cidr": f"10.10.10.{62 + tier}/24",
                        "virtual_router_id": 40 + tier, "control_planes": {"other-control": f"10.{20 + tier}.13.10"},
                    })
                result = run_preflight(directory, values)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotRegex(result.stdout, r"changed=[1-9]")

    def test_preflight_rejects_unapproved_colliding_or_unsafe_endpoints(self):
        valid = inputs()
        cases = [
            {"cluster_endpoint_fault_domains_validated": False},
            {"cluster_endpoint_network_gates_validated": False},
            {"cluster_endpoint_fault_domains": {"api-gw-1": "pve01", "api-gw-2": "pve01"}},
            {"platform_host_ips": {"api-gw-1": "10.10.10.60", "api-gw-2": "dhcp"}},
            {"cluster_endpoint_interface": "eth0\ninterface eth1"},
        ]
        for change in (
            {"vip_cidr": "0.0.0.0/24"}, {"vip_cidr": "8.8.8.8/24"},
            {"vip_cidr": "10.10.10.60/24"}, {"vip_cidr": "10.11.10.62/24"},
            {"virtual_router_id": 256}, {"control_planes": {}},
            {"control_planes": {"bad": "api.example.com"}},
            {"control_planes": {"bad": "10.10.13.10:50000"}},
            {"control_planes": {"bad": "10.10.10.62"}},
            {"control_planes": {"bad": "8.8.8.8"}},
            {"track_scripts": []},
        ):
            cases.append({"cluster_endpoint_endpoints": [valid["cluster_endpoint_endpoints"][0] | change]})
        for change in ({"vip_cidr": "10.10.10.62/25", "virtual_router_id": 41},
                       {"vip_cidr": "10.10.10.63/24", "virtual_router_id": 40}):
            other = valid["cluster_endpoint_endpoints"][0] | {"name": "platform", "tier": 1} | change
            cases.append({"cluster_endpoint_endpoints": valid["cluster_endpoint_endpoints"] + [other]})
        with tempfile.TemporaryDirectory(prefix="cluster-endpoint-refusal-") as name:
            for overrides in cases:
                with self.subTest(overrides=overrides):
                    result = run_preflight(Path(name), valid | overrides)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("assertion", result.stdout)
            result = run_preflight(Path(name), valid, members=["api-gw-1"])
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_template_validation_failure_preserves_installed_configuration(self):
        values = inputs()
        task = copy.deepcopy(next(task for task in yaml.safe_load((ROLE / "tasks/main.yml").read_text())
                                  if "block" in task))
        # Exercise actual include/module-default inheritance without root privileges or daemon changes.
        task["module_defaults"]["ansible.builtin.template"]["validate"] = "/bin/false %s"
        with tempfile.TemporaryDirectory(prefix="cluster-endpoint-validation-") as name:
            directory = Path(name)
            destination = directory / "keepalived.conf"
            destination.write_text("existing configuration\n")
            values["cluster_endpoint_keepalived_config_path"] = str(destination)
            values["cluster_endpoint_group"] = "cluster_endpoint"
            # Preserve Shared's tasks/templates; adapt only file ownership for an unprivileged fixture.
            fixture = directory / "roles/shared"
            (fixture / "tasks").mkdir(parents=True)
            (fixture / "templates").mkdir()
            shared_tasks = yaml.safe_load((SHARED / "tasks/keepalived.yml").read_text())
            for shared_task in shared_tasks:
                if "ansible.builtin.template" in shared_task:
                    shared_task["ansible.builtin.template"].pop("owner")
                    shared_task["ansible.builtin.template"].pop("group")
            (fixture / "tasks/keepalived.yml").write_text(yaml.safe_dump(shared_tasks))
            shutil.copyfile(SHARED / "templates/keepalived.conf.j2", fixture / "templates/keepalived.conf.j2")
            result = run_preflight(directory, values, tasks=[task], roles=fixture.parent)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("failed to validate", result.stdout + result.stderr)
            self.assertEqual(destination.read_text(), "existing configuration\n")


class NativeConfiguration(unittest.TestCase):
    @unittest.skipUnless(HAPROXY, "Requires HAProxy or HOMELAB_HAPROXY")
    def test_haproxy_accepts_rendered_tcp_configuration(self):
        with tempfile.TemporaryDirectory(prefix="cluster-api-haproxy-") as name:
            configuration = Path(name) / "haproxy.cfg"
            # A standalone validator may lack the package-created haproxy account.
            content = render_haproxy(inputs()).replace("user haproxy", f"user {getpass.getuser()}")
            content = re.sub(r"^  group haproxy\n", "", content, flags=re.MULTILINE)
            configuration.write_text(content)
            result = subprocess.run([HAPROXY, "-c", "-f", str(configuration)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(KEEPALIVED, "Requires Keepalived or HOMELAB_KEEPALIVED")
    def test_keepalived_accepts_both_shared_peer_configurations(self):
        with tempfile.TemporaryDirectory(prefix="cluster-api-keepalived-") as name:
            configuration = Path(name) / "keepalived.conf"
            for host in inputs()["platform_host_ips"]:
                # The parser runs unprivileged; production runs as root on the managed gateway.
                content = render_keepalived(inputs(), host).replace(
                    "script_user root", f"script_user {getpass.getuser()}")
                configuration.write_text(content)
                result = subprocess.run([KEEPALIVED, "--config-test", "-f", str(configuration)],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ReleaseReproducibility(unittest.TestCase):
    def test_terraform_deployment_roots_ship_nonempty_provider_locks(self):
        roots = sorted(path.parent for tier in range(3) for path in
                       (UPSTREAM / f"tier-{tier}/terraform/deployments").glob("*/versions.tf"))
        self.assertTrue(roots)
        missing = [str(root.relative_to(UPSTREAM)).replace(os.sep, "/") for root in roots
                   if not (root / ".terraform.lock.hcl").is_file()]
        self.assertFalse(missing, "Missing release provider locks:\n" + "\n".join(missing))
        for root in roots:
            self.assertTrue((root / ".terraform.lock.hcl").read_text().strip(), str(root))


if __name__ == "__main__":
    unittest.main()
