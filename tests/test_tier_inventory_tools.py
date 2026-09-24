"""Resolve generated inputs with real local tools, without provisioning hosts."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

UPSTREAM = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform") and shutil.which("ansible-playbook"),
                     "Requires Terraform and Ansible on Linux/WSL")
class InventoryToolContract(unittest.TestCase):
    def test_both_tools_resolve_each_tiers_inventory(self):
        with tempfile.TemporaryDirectory(prefix="tier-inventory-") as temporary:
            root = Path(temporary)
            subprocess.run([sys.executable, str(UPSTREAM / "scripts/tier-repos/generate.py"),
                            "--root", str(root), "--prefix", "verify"],
                           check=True, capture_output=True, text=True)
            root = root / "verify-iac"
            catalog = root / "verify-shared/templates/proxmox-catalog.tfvars"
            catalog.write_text('''default_linux_vm_template_id = 110
proxmox_template_catalog = {
  "110" = { title = "Approved Linux", family = "alma", node_name = "template-host", tags = ["alma"] }
}
''')
            for tier, setup, host in (("tier-0", "foundation", "idm-1"),
                                      ("tier-1", "edge", "edge-lb-1"), ("tier-2", "lab", "lab-1")):
                with self.subTest(tier=tier):
                    repo = root / f"verify-{tier}"
                    subprocess.run(["bash", "../verify-shared/scripts/init-local-files.sh",
                                    "--setup", setup, "--env", "test"],
                                   cwd=repo, check=True, capture_output=True, text=True)
                    vars_paths = [repo / f"ansible/group_vars/{name}.yml"
                                  for name in ("all", setup, "all.test", f"{setup}.test")]
                    merged = {}
                    for path in vars_paths:
                        merged.update(yaml.safe_load(path.read_text()))
                    fixture = root / f"resolve-{tier}"
                    fixture.mkdir()
                    module = {
                        "source": str(repo / "terraform/modules/environment_guests"),
                        "ansible_inventory_path": str(repo / "ansible/inventory/hosts.yml"),
                        "ansible_group_vars_paths": [str(path) for path in vars_paths],
                        "default_platform_node_name": "test-platform",
                        "default_vm_template_id": "${var.default_linux_vm_template_id}",
                        "proxmox_template_catalog": "${var.proxmox_template_catalog}",
                        "network_zones": {"application": {"bridge": "isolated-test",
                                          "cidr_ipv4": "192.0.2.0/24", "gateway_ipv4": "192.0.2.1"}},
                        "vm_instances": {host: {"disk_size_gb": 30}},
                    }
                    config = {"variable": {"default_linux_vm_template_id": {"type": "number"},
                                           "proxmox_template_catalog": {"type": "any"}},
                              "module": {"inventory": module},
                              "output": {"resolved": {"value": "${module.inventory.vm_instances}"}}}
                    (fixture / "main.tf.json").write_text(json.dumps(config))
                    for args in (("init", "-backend=false", "-input=false"),
                                 ("apply", "-auto-approve", "-input=false", f"-var-file={catalog}")):
                        result = subprocess.run(["terraform", f"-chdir={fixture}", *args],
                                                capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    output = subprocess.check_output(
                        ["terraform", f"-chdir={fixture}", "output", "-json", "resolved"], text=True)
                    resolved = json.loads(output)[host]
                    self.assertEqual(resolved["template_title"], "Approved Linux")
                    self.assertEqual(resolved["template_node_name"], "template-host")
                    self.assertEqual(resolved["tags"], ["alma"])
                    self.assertEqual(resolved["ipv4_address"], merged["platform_host_ips"][host] + "/24")
                    expected = str(fixture / "expected.json")
                    Path(expected).write_text(json.dumps({"expected_name": resolved["name"],
                                                         "expected_ip": merged["platform_host_ips"][host]}))
                    play = fixture / "verify.yml"
                    play.write_text(yaml.safe_dump([{
                        "name": "Verify generated inventory identity without connecting to hosts",
                        "hosts": host, "gather_facts": False,
                        "tasks": [{"ansible.builtin.assert": {"that": [
                            "ansible_host == expected_ip", "platform_hostname == expected_name"]}}],
                    }]))
                    command = ["ansible-playbook", "-i", str(repo / "ansible/inventory/hosts.yml"), str(play)]
                    for path in [*vars_paths, Path(expected)]:
                        command.extend(["-e", f"@{path}"])
                    env = dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"))
                    result = subprocess.run(command, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
