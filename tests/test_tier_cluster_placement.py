"""Cluster placement contracts without contacting Proxmox."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


class ClusterPlacement(TierRepositoryTestCase):
    def test_every_generated_root_forwards_template_source_node(self):
        self.generate()
        count = 0
        for tier in ("tier-0", "tier-1", "tier-2"):
            repo = self.root / f"verify-{tier}"
            for setup in (repo / ".deployment-setups").read_text().splitlines():
                root = repo / "terraform/environments" / setup
                main = (root / "main.tf").read_text()
                variables = (root / "variables.tf").read_text()
                self.assertRegex(main, r"template_node_name\s*=\s*each.value.template_node_name")
                self.assertIn('variable "proxmox_template_catalog"', variables)
                self.assertRegex(main, r"proxmox_template_catalog\s*=\s*var.proxmox_template_catalog")
                count += 1
        self.assertEqual(count, 11)
        vm = (self.root / "verify-shared/terraform/modules/vm/main.tf").read_text()
        self.assertIn("ignore_changes = [node_name]", vm)
        self.assertIn("node_name = var.template_node_name", vm)
        lxc = (self.root / "verify-shared/terraform/modules/lxc/main.tf").read_text()
        self.assertNotIn("ignore_changes", lxc)

    @unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires Terraform on Linux/WSL")
    def test_template_source_resolution_is_independent_of_target_and_output_tags(self):
        self.generate()
        fixture = self.root / "placement-inputs"
        fixture.mkdir()
        inventory = fixture / "hosts.yml"
        group_vars = fixture / "all.yml"
        inventory.write_text(yaml.safe_dump({"all": {"children": {"guests": {"hosts": {"vm-1": {}}}}}}))
        group_vars.write_text(yaml.safe_dump({"platform_host_ips": {"vm-1": "dhcp"}}))
        module = {
            "source": str(self.root / "verify-shared/terraform/modules/environment_guests"),
            "ansible_inventory_path": str(inventory),
            "ansible_group_vars_paths": [str(group_vars)],
            "default_platform_node_name": "pve02",
            "default_vm_template_id": 110,
            "network_zones": {"application": {"bridge": "services", "cidr_ipv4": "192.0.2.0/24"}},
            "proxmox_template_catalog": {
                "110": {"title": "Linux source", "family": "alma", "node_name": "pve01", "tags": ["source"]},
                "120": {"title": "Alternate Linux", "family": "rocky", "node_name": "pve03", "tags": ["alternate"]},
                "130": {"title": "Local Linux", "family": "alma", "tags": ["local"]},
                "9100": {"title": "Builder output", "family": "alma", "node_name": "output-node", "tags": ["output"]},
                "9102": {"title": "Talos candidate", "family": "talos"},
            },
        }
        # Builder tags describe the future image, never the source clone's node.
        cases = (
            ({}, "pve01", "pve02", ["source"]),
            ({"template_catalog_id": 9100}, "pve01", "pve02", ["output"]),
            ({"template_vm_id": 120, "proxmox_node_name": "pve04"}, "pve03", "pve04", ["alternate"]),
            ({"template_vm_id": 130}, None, "pve02", ["local"]),
            ({"template_vm_id": 140}, None, "pve02", []),
        )
        for index, (overrides, source, target, tags) in enumerate(cases):
            with self.subTest(overrides=overrides):
                module["vm_instances"] = {"vm-1": {"disk_size_gb": 32, **overrides}}
                config = {"module": {"inventory": module},
                          "output": {"resolved": {"value": "${module.inventory.vm_instances}"}}}
                (fixture / "main.tf.json").write_text(json.dumps(config))
                if index == 0:
                    self.run_terraform(fixture, "init", "-backend=false", "-input=false")
                self.run_terraform(fixture, "apply", "-auto-approve", "-input=false")
                output = self.run_terraform(fixture, "output", "-json", "resolved")
                resolved = json.loads(output)["vm-1"]
                self.assertEqual(resolved["template_node_name"], source)
                self.assertEqual(resolved["node_name"], target)
                self.assertEqual(resolved["tags"], tags)
                template_id = str(overrides.get("template_vm_id", 110))
                title = module["proxmox_template_catalog"].get(template_id, {}).get("title")
                self.assertEqual(resolved["template_title"], title)

        module["vm_instances"] = {"vm-1": {"disk_size_gb": 32}}
        module["linux_vm_template_catalog"] = {"110": {"node_name": "legacy-node", "tags": ["legacy"]}}
        (fixture / "main.tf.json").write_text(json.dumps(config))
        self.run_terraform(fixture, "apply", "-auto-approve", "-input=false")
        resolved = json.loads(self.run_terraform(fixture, "output", "-json", "resolved"))["vm-1"]
        self.assertEqual(resolved["template_node_name"], "legacy-node")
        self.assertEqual(resolved["tags"], ["legacy"])

        for template_id, message in ((None, "Select an approved Linux template ID"),
                                     (9102, "Talos templates need Talos machine configuration")):
            module["default_vm_template_id"] = template_id
            (fixture / "main.tf.json").write_text(json.dumps(config))
            result = subprocess.run(["terraform", f"-chdir={fixture}", "plan", "-input=false", "-no-color"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(message, result.stdout + result.stderr)

    def run_terraform(self, fixture, *args):
        result = subprocess.run(["terraform", f"-chdir={fixture}", *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout


if __name__ == "__main__":
    unittest.main()
