"""Exercise shared and tier-local network references without any providers or resources."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires Terraform in Linux/WSL")
class NetworkInputs(TierRepositoryTestCase):
    def test_generated_network_references_merge_without_moving_inventory(self):
        self.generate()
        profile = self.root / "verify-shared/config/platform.tfvars"
        shared_application = {"bridge": "shared-app", "vlan_id": 120,
                              "cidr_ipv4": "192.0.2.0/24", "gateway_ipv4": "192.0.2.1"}
        local_application = {"bridge": "tier-app", "cidr_ipv4": "192.0.2.0/25",
                             "gateway_ipv4": "192.0.2.126"}
        for tier, setup, private_keys in (
            ("tier-0", "foundation", {"identity", "cryptography"}),
            ("tier-1", "development", {"observability", "storage", "telemetry_gateway",
                                        "security_telemetry", "delivery_edge"}),
            ("tier-2", "lab", {"external_edge"}),
        ):
            repo = self.root / f"verify-{tier}"
            fixture = Path(self.temp.name) / f"networks-{tier}"
            fixture.mkdir()
            # Use the generated deployment's real input schema and inventory resolver.
            shutil.copyfile(repo / f"terraform/deployments/{setup}/variables.tf", fixture / "variables.tf")
            inventory = fixture / "hosts.yml"
            inventory.write_text('all:\n  children:\n    guests:\n      hosts:\n        test-1: {}\n')
            group_vars = fixture / "guests.yml"
            group_vars.write_text('platform_host_ips:\n  test-1: "192.0.2.10"\n')
            networks = "${merge(var.shared_network_zones, var.network_zones)}"
            module = {
                "source": str(repo / "terraform/modules/environment_guests"),
                "ansible_inventory_path": str(inventory),
                "ansible_group_vars_paths": [str(group_vars)],
                "default_platform_node_name": "test-platform",
                "network_zones": networks,
                "vm_instances": {"test-1": {"disk_size_gb": 30, "template_vm_id": 9100}},
            }
            lxc = dict(module, vm_instances={}, lxc_instances={
                "test-1": {"disk_size_gb": 8, "template_file_id": "local:vztmpl/test.tar.zst"}})
            config = {
                "module": {"vms": module, "lxcs": lxc},
                "output": {"networks": {"value": networks},
                           "vm": {"value": "${module.vms.vm_instances[\"test-1\"]}"},
                           "lxc": {"value": "${module.lxcs.lxc_instances[\"test-1\"]}"}},
            }
            (fixture / "main.tf.json").write_text(json.dumps(config))
            init = subprocess.run(["terraform", "init", "-backend=false", "-input=false"],
                                  cwd=fixture, capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            common = repo / "terraform/common.tfvars.example"
            overrides = fixture / "inputs.tfvars.json"
            shared = {"application": shared_application, "other_shared": shared_application}
            local = {"application": local_application, "private": local_application}
            cases = (
                ("inherited", {}, "app", None, "10.20.20.1", "24", {"application"} | private_keys),
                ("shared_change", {"shared_network_zones": shared}, "shared-app", 120,
                 "192.0.2.1", "24", set(shared) | private_keys),
                ("tier_override", {"shared_network_zones": shared, "network_zones": local},
                 "tier-app", None, "192.0.2.126", "25", set(shared) | set(local)),
                ("legacy_local", {"shared_network_zones": {}, "network_zones": local},
                 "tier-app", None, "192.0.2.126", "25", set(local)),
            )
            for name, values, bridge, vlan, gateway, prefix, keys in cases:
                with self.subTest(tier=tier, case=name):
                    overrides.write_text(json.dumps(values))
                    # This fixture only resolves data; there are no infrastructure resources.
                    result = subprocess.run([
                        "terraform", "apply", "-auto-approve", "-input=false", "-no-color",
                        f"-var-file={profile}", f"-var-file={common}", f"-var-file={overrides}",
                    ], cwd=fixture, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    output = json.loads(subprocess.check_output(
                        ["terraform", "output", "-json"], cwd=fixture, text=True))
                    self.assertEqual(set(output["networks"]["value"]), keys)
                    for kind in ("vm", "lxc"):
                        guest = output[kind]["value"]
                        self.assertEqual(guest["bridge"], bridge)
                        self.assertEqual(guest["vlan_id"], vlan)
                        self.assertEqual(guest["ipv4_gateway"], gateway)
                        self.assertEqual(guest["ipv4_address"], f"192.0.2.10/{prefix}")


if __name__ == "__main__":
    unittest.main()
