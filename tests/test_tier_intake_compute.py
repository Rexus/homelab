"""Tier 1 owns optional software-intake compute, inventory and state."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


DEPLOYMENT = Path("terraform/deployments/intake")


class IntakeCompute(TierRepositoryTestCase):
    def test_source_and_generated_setup_keep_inventory_catalog_and_disks_tier_local(self):
        self.generate()
        sizes = json.loads((UPSTREAM / "shared/config/guest-sizes.json").read_text())
        self.assertEqual(sizes["vm"]["small-mem"]["memory"], 8192)
        for owner in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(owner=owner.name):
                self.assertIn("intake", (owner / ".deployment-setups").read_text().splitlines())
                groups = yaml.safe_load((owner / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
                self.assertEqual(set(groups["software_intake"]["hosts"]), {"intake-1"})
                self.assertIn("software_intake", groups["guests"]["children"])
                inputs = yaml.safe_load((owner / "ansible/group_vars/intake.yml.example").read_text())
                self.assertEqual(inputs["platform_host_ips"], {"intake-1": "10.30.31.40"})
                root = owner / DEPLOYMENT
                example = (root / "terraform.tfvars.example").read_text()
                for pattern in (r'vm_id\s*=\s*1221\b', r'size\s*=\s*"small-mem"',
                                r'disk_size_gb\s*=\s*40\b', r'size_gb\s*=\s*200\b',
                                r'interface\s*=\s*"scsi1"', r'network_zone_key\s*=\s*"delivery_edge"'):
                    self.assertRegex(example, pattern)
                self.assertNotRegex(example, r'(?m)^\s*template_vm_id\s*=')
                self.assertIn('source = "../../modules/environment_guests"', (root / "main.tf").read_text())
                self.assertRegex((root / "main.tf").read_text(), r'extra_disks\s*=\s*each.value.extra_disks')
                self.assertTrue((root / ".terraform.lock.hcl").is_file())
                precheck = yaml.safe_load((owner / "ansible/playbooks/control-node.yml").read_text())[0]
                self.assertEqual(precheck["vars"]["control_node_setup_collection_names"]["intake"],
                                 ["community.general", "ansible.posix", "community.crypto", "ansible.utils"])

    @unittest.skipIf(os.name == "nt", "Generated Bash commands run under Linux/WSL")
    def test_generated_init_selects_intake_and_rejects_the_wrong_owner(self):
        self.generate()
        tier = self.root / "verify-tier-1"
        environment = os.environ.copy()
        environment.pop("DEPLOYMENT_REPO_DIR", None)
        for owner in (self.root / "verify-tier-0", self.root / "verify-tier-2"):
            rejected = subprocess.run(["bash", "scripts/init-local-files.sh", "--setup", "intake"],
                                      cwd=owner, env=environment, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(str(tier), rejected.stderr)
            self.assertFalse((owner / "ansible/group_vars/intake.yml").exists())
        initialized = subprocess.run(["bash", "scripts/init-local-files.sh", "--setup", "intake"],
                                     cwd=tier, env=environment, capture_output=True, text=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        self.assertEqual((tier / "ansible/group_vars/intake.yml").read_bytes(),
                         (tier / "ansible/group_vars/intake.yml.example").read_bytes())
        self.assertEqual((tier / DEPLOYMENT / "terraform.tfvars").read_bytes(),
                         (tier / DEPLOYMENT / "terraform.tfvars.example").read_bytes())
        self.assertFalse((tier / DEPLOYMENT / ".terraform").exists())
        inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml").read_text())
        self.assertIn("intake-1", inventory["all"]["children"]["software_intake"]["hosts"])

        # Capture dispatcher arguments without executing prechecks, SSH or the service installer.
        tools = self.parent / "dispatch-tools"
        tools.mkdir()
        log = tools / "ansible.jsonl"
        executable = tools / "ansible-playbook"
        executable.write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                              "with open(os.environ['INTAKE_DISPATCH_LOG'], 'a') as output:\n"
                              "    output.write(json.dumps(sys.argv[1:]) + '\\n')\n")
        executable.chmod(0o755)
        environment.update(PATH=str(tools) + os.pathsep + environment["PATH"], INTAKE_DISPATCH_LOG=str(log))
        deployed = subprocess.run(["bash", "scripts/deploy.sh", "intake", "--ansible-only"],
                                   cwd=tier, env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(deployed.returncode, 0, deployed.stdout + deployed.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(calls[-1][-1], str(tier / "ansible/playbooks/intake.yml"))
        self.assertIn("@" + str(tier / "ansible/group_vars/intake.yml"), calls[-1])
        recipe = yaml.safe_load((tier / "ansible/playbooks/intake.yml").read_text())
        self.assertEqual(recipe[0]["ansible.builtin.import_playbook"], "deployment/intake.yml")

    @unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires native Terraform >=1.7")
    def test_native_mocked_source_vm_uses_catalog_network_and_data_disk(self):
        source = self.parent / "source"
        shutil.copytree(UPSTREAM / "tier-1" / DEPLOYMENT, source / "tier-1" / DEPLOYMENT)
        for module in ("vm", "lxc", "environment_guests"):
            shutil.copytree(UPSTREAM / "tier-1/terraform/modules" / module,
                            source / "tier-1/terraform/modules" / module)
        (source / "shared/config").mkdir(parents=True)
        shutil.copy2(UPSTREAM / "shared/config/guest-sizes.json", source / "shared/config/guest-sizes.json")
        self.check_native_vm(source / "tier-1")

    @unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires native Terraform >=1.7")
    def test_native_mocked_generated_vm_uses_catalog_network_and_data_disk(self):
        self.generate()
        self.check_native_vm(self.root / "verify-tier-1")

    def check_native_vm(self, owner):
        root = owner / DEPLOYMENT
        fixtures = root / "tests"
        fixtures.mkdir()
        inventory = root / "hosts.fixture.yml"
        inventory.write_bytes((UPSTREAM / "tier-1/ansible/inventory/hosts.yml.example").read_bytes())
        ips = root / "ips.fixture.yml"
        ips.write_bytes((UPSTREAM / "tier-1/ansible/group_vars/intake.yml.example").read_bytes())
        inputs = {
            "proxmox_api_url": "https://pve.example.invalid:8006/",
            "proxmox_api_token_id": "fixture@pve!provision",
            "proxmox_api_token_secret": "disposable-fixture-value",
            "default_platform_node_name": "guest-node",
            "default_linux_vm_template_id": 9101,
            "proxmox_template_catalog": {"9101": {"title": "approved-linux", "family": "el",
                                                   "node_name": "template-node", "tags": ["el10"]}},
            "proxmox_storage_classes": {"local": {"vm_disk": "fixture-zfs", "cloud_init_drive": "fixture-init"}},
            "ansible_inventory_path": str(inventory),
            "ansible_group_vars_paths": [str(ips)],
            "network_zones": {"delivery_edge": {"bridge": "vmbr0", "vlan_id": 321,
                                                  "cidr_ipv4": "10.30.31.0/24",
                                                  "gateway_ipv4": "10.30.31.1"}},
        }
        variables = root / "intake.fixture.tfvars.json"
        variables.write_text(json.dumps(inputs))
        (fixtures / "intake.tftest.hcl").write_text('''mock_provider "proxmox" {}
run "intake_compute" {
  command = apply
  assert {
    condition = length(module.environment.vm_instances) == 1 && length(module.environment.lxc_instances) == 0
    error_message = "Intake must provision exactly one VM and no containers."
  }
  assert {
    condition = module.environment.vm_instances["intake-1"].template_vm_id == 9101
    error_message = "The consumer must resolve the shared default Linux template."
  }
}
run "explicit_overrides" {
  command = apply
  variables {
    vm_instances = {
      "intake-1" = {
        vm_id = 1221
        size = "small-mem"
        storage_class = "local"
        disk_size_gb = 40
        network_zone_key = "delivery_edge"
        full_clone = false
        firmware = {
          bios = "ovmf"
          machine = "q35"
          scsi_hardware = "virtio-scsi-pci"
          efi_pre_enrolled_keys = true
        }
        initialization_datastore_id = "fixture-override-init"
        nic_firewall = false
        started = false
        stop_on_destroy = true
        extra_disks = [{interface = "scsi1", size_gb = 200, storage_class = "local"}]
      }
    }
  }
}
''')
        environment = dict(os.environ, TF_DATA_DIR=str(root / "terraform-data"))
        initialized = subprocess.run(["terraform", f"-chdir={root}", "init", "-backend=false",
                                       "-input=false", "-lockfile=readonly", "-no-color"],
                                      env=environment, capture_output=True, text=True, timeout=120)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        validation = subprocess.run(["terraform", f"-chdir={root}", "validate", "-json"],
                                     env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        tested = subprocess.run(["terraform", f"-chdir={root}", "test", "-json", "-verbose",
                                 "-var-file=terraform.tfvars.example", f"-var-file={variables}"],
                                env=environment, capture_output=True, text=True, timeout=120)
        events = [json.loads(line) for line in tested.stdout.splitlines() if line.strip()]
        diagnostics = [event["diagnostic"]["summary"] for event in events
                       if event.get("type") == "diagnostic"]
        self.assertEqual(tested.returncode, 0, diagnostics)
        states = [event["test_state"] for event in events if event.get("type") == "test_state"]
        self.assertEqual(len(states), 2, diagnostics)
        self.check_guest_state(states[0], override=False)
        self.check_guest_state(states[1], override=True)

    def check_guest_state(self, state, override):
        resources = []

        def collect(module):
            resources.extend(module.get("resources", []))
            for child in module.get("child_modules", []):
                collect(child)

        collect(state["root_module"])
        guests = [r["values"] for r in resources if r["type"] == "proxmox_virtual_environment_vm"]
        self.assertEqual(len(guests), 1)
        vm = guests[0]
        self.assertEqual((vm["name"], vm["vm_id"], vm["node_name"]), ("intake-1", 1221, "guest-node"))
        self.assertEqual(vm["memory"][0]["dedicated"], 8192)
        self.assertEqual(vm["clone"][0]["vm_id"], 9101)
        self.assertEqual(vm["clone"][0]["node_name"], "template-node")
        self.assertEqual(vm["clone"][0]["full"], not override)
        self.assertEqual(vm["bios"], "ovmf")
        self.assertEqual(vm["machine"], "q35")
        self.assertEqual(vm["scsi_hardware"], "virtio-scsi-pci" if override else "virtio-scsi-single")
        self.assertEqual(vm["boot_order"], ["scsi0"])
        self.assertEqual(len(vm["efi_disk"]), 1)
        self.assertEqual(vm["efi_disk"][0]["type"], "4m")
        self.assertEqual(vm["efi_disk"][0]["datastore_id"], "fixture-zfs")
        self.assertEqual(vm["efi_disk"][0]["pre_enrolled_keys"], override)
        self.assertEqual(vm["started"], not override)
        if override:
            self.assertTrue(vm["stop_on_destroy"])
        self.assertEqual({disk["interface"]: disk["size"] for disk in vm["disk"]},
                         {"scsi0": 40, "scsi1": 200})
        self.assertTrue(all(disk["datastore_id"] == "fixture-zfs" for disk in vm["disk"]))
        self.assertTrue(all(disk["iothread"] == (not override) for disk in vm["disk"]))
        self.assertEqual((vm["network_device"][0]["bridge"], vm["network_device"][0]["vlan_id"]),
                         ("vmbr0", 321))
        self.assertEqual(vm["network_device"][0]["firewall"], not override)
        self.assertEqual(vm["initialization"][0]["datastore_id"],
                         "fixture-override-init" if override else "fixture-init")
        self.assertEqual(vm["initialization"][0]["user_account"][0]["username"], "automation")
        network = vm["initialization"][0]["ip_config"][0]["ipv4"][0]
        self.assertEqual(network["address"], "10.30.31.40/24")
        self.assertEqual(network["gateway"], "10.30.31.1")
        if not override:
            self.check_starter_diagram(vm)

    def check_starter_diagram(self, vm):
        guide = UPSTREAM / "docs/deployment/stage-1-software-intake/verified-intake.md"
        diagrams = re.findall(r"```mermaid\n(.*?)\n```", guide.read_text(), re.DOTALL)
        identity = f"{vm['name']} / VMID {vm['vm_id']:g}"
        drawings = [diagram for diagram in diagrams if identity in diagram and "scsi0" in diagram]
        self.assertEqual(len(drawings), 1, "A provisioning view must map the resolved starter VM and disks")
        for disk in vm["disk"]:
            expected = rf"{re.escape(disk['interface'])}\s*/\s*{disk['size']:g}\s*(?:GB|GiB)\b"
            self.assertRegex(drawings[0], expected)


if __name__ == "__main__":
    unittest.main()
