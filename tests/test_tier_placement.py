"""Initial placement accepts per-guest nodes and rejects missing destinations clearly."""

import json
import os
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires native Terraform in Linux/WSL")
class GuestPlacement(TierRepositoryTestCase):
    def test_generated_root_and_resolver_accept_overrides_defaults_and_legacy_inputs(self):
        self.generate()
        for tier, setup in (("tier-0", "foundation"), ("tier-1", "development"), ("tier-2", "cache")):
            with self.subTest(tier=tier):
                repo = self.root / f"verify-{tier}"
                fixture = repo / "terraform/deployments/placement-test"
                fixture.mkdir()
                root = (repo / f"terraform/deployments/{setup}/main.tf").read_text()
                (fixture / "main.tf").write_text(root.split('module "environment"')[0])
                (fixture / "hosts.yml").write_text("all:\n  children:\n    test:\n      hosts:\n"
                                                 "        vm-1: {}\n        container-1: {}\n")
                (fixture / "ips.yml").write_text("platform_host_ips:\n  vm-1: 192.0.2.10\n"
                                               "  container-1: 192.0.2.11\n")
                inputs = {
                    "source": "../../modules/environment_guests",
                    "default_platform_node_name": "${local.effective_default_platform_node_name}",
                    "default_vm_template_id": 9101,
                    "network_zones": {"application": {"bridge": "vmbr0", "cidr_ipv4": "192.0.2.0/24",
                                                       "gateway_ipv4": "192.0.2.1"}},
                    "ansible_inventory_path": str(fixture / "hosts.yml"),
                    "ansible_group_vars_paths": [str(fixture / "ips.yml")],
                    "vm_instances": {"vm-1": {"disk_size_gb": 20, "proxmox_node_name": "vm-node"}},
                    "lxc_instances": {"container-1": {"disk_size_gb": 8, "proxmox_node_name": "container-node",
                                                        "template_file_id": "local:vztmpl/test.tar.zst"}},
                }
                config = {"variable": {name: {"type": "string", "default": None}
                                       for name in ("default_platform_node_name", "default_proxmox_node_name")},
                          "module": {"environment": inputs},
                          "output": {"vm": {"value": '${module.environment.vm_instances["vm-1"].node_name}'},
                                     "lxc": {"value": '${module.environment.lxc_instances["container-1"].node_name}'}}}
                path = fixture / "main.tf.json"
                path.write_text(json.dumps(config))

                def run(*args):
                    return subprocess.run(["terraform", f"-chdir={fixture}", *args], capture_output=True, text=True)

                initialized = run("init", "-backend=false", "-input=false", "-no-color")
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                applied = run("apply", "-auto-approve", "-input=false", "-no-color")
                self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
                outputs = json.loads(run("output", "-json").stdout)
                self.assertEqual(outputs["vm"]["value"], "vm-node")
                self.assertEqual(outputs["lxc"]["value"], "container-node")

                inputs["vm_instances"]["vm-1"].pop("proxmox_node_name")
                inputs["lxc_instances"]["container-1"].pop("proxmox_node_name")
                path.write_text(json.dumps(config))
                missing = run("plan", "-input=false", "-no-color")
                self.assertNotEqual(missing.returncode, 0)
                self.assertIn("Set default_platform_node_name in Shared", missing.stdout + missing.stderr)
                self.assertIn("vm-1", missing.stdout + missing.stderr)
                self.assertIn("container-1", missing.stdout + missing.stderr)
                self.assertNotIn('Call to function "coalesce" failed', missing.stdout + missing.stderr)

                for args, expected in ((["-var=default_platform_node_name=site-node"], "site-node"),
                                       (["-var=default_proxmox_node_name=legacy-node"], "legacy-node"),
                                       (["-var=default_platform_node_name=site-node",
                                         "-var=default_proxmox_node_name=legacy-node"], "site-node")):
                    applied = run("apply", "-auto-approve", "-input=false", "-no-color", *args)
                    self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
                    outputs = json.loads(run("output", "-json").stdout)
                    self.assertEqual(outputs["vm"]["value"], expected)
                    self.assertEqual(outputs["lxc"]["value"], expected)


if __name__ == "__main__":
    unittest.main()
