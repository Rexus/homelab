"""Optional Stage 6 capacity reuses foundation provisioning and connection inputs."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


def activate_monitor(repo):
    path = repo / "terraform/deployments/foundation/terraform.tfvars"
    content = path.read_text(encoding="utf-8")
    block = re.search(r'(?ms)^  # "mon-1" = \{\n.*?^  # \}', content)
    if block is None:
        raise AssertionError("Missing commented Stage 6 monitor block")
    content = content[:block.start()] + re.sub(r"(?m)^  # ?", "  ", block[0]) + content[block.end():]
    path.write_text(content, encoding="utf-8")
    path = repo / "ansible/group_vars/foundation.yml"
    content = path.read_text(encoding="utf-8").replace("  # mon-1:", "  mon-1:")
    path.write_text(content, encoding="utf-8")
    path = repo / "ansible/inventory/hosts.yml"
    inventory = yaml.safe_load(path.read_text(encoding="utf-8"))
    inventory["all"]["children"]["infrastructure_monitoring"]["hosts"] = {"mon-1": {}}
    path.write_text(yaml.safe_dump(inventory), encoding="utf-8")


class MonitoringProvisioning(TierRepositoryTestCase):
    def prepare(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        for relative in ("terraform/deployments/foundation/terraform.tfvars",
                         "ansible/group_vars/all.yml", "ansible/group_vars/foundation.yml",
                         "ansible/inventory/hosts.yml"):
            target = repo / relative
            shutil.copyfile(str(target) + ".example", target)
        return repo

    def test_starters_leave_monitor_disabled_and_keep_existing_foundation_hosts(self):
        repo = self.prepare()
        original = yaml.safe_load((repo / "ansible/group_vars/foundation.yml").read_text())
        inventory = yaml.safe_load((repo / "ansible/inventory/hosts.yml").read_text())
        self.assertEqual(inventory["all"]["children"]["infrastructure_monitoring"]["hosts"], {})
        self.assertNotIn("mon-1", original["platform_host_ips"])
        self.assertFalse(re.search(r'(?m)^\s*"mon-1"\s*=',
                                   (repo / "terraform/deployments/foundation/terraform.tfvars").read_text()))
        activate_monitor(repo)
        enabled = yaml.safe_load((repo / "ansible/group_vars/foundation.yml").read_text())
        self.assertEqual(enabled["platform_host_ips"],
                         dict(original["platform_host_ips"], **{"mon-1": "10.10.10.60"}))

    @unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires native Terraform")
    def test_native_mock_plan_adds_only_monitor_to_the_same_foundation_root(self):
        repo = self.prepare()
        root = repo / "terraform/deployments/foundation"
        tests = root / "tests"
        tests.mkdir()
        test_file = tests / "monitor.tftest.hcl"
        settings = '''
mock_provider "proxmox" {}
mock_provider "external" {}
variables {
  default_platform_node_name = "test-platform"
  default_linux_vm_template_id = 9101
  proxmox_storage_classes = {local = {vm_disk = "test-vm-storage"}}
  proxmox_template_catalog = {
    "9101" = {title = "Approved EL image", family = "rocky"}
    "9103" = {title = "Approved CA image", family = "debian"}
  }
  ansible_group_vars_paths = ["../../../ansible/group_vars/all.yml", "../../../ansible/group_vars/foundation.yml"]
  network_zones = {
    management = {bridge = "vmbr0", cidr_ipv4 = "10.10.10.0/24", gateway_ipv4 = "10.10.10.1"}
    identity = {bridge = "ident", cidr_ipv4 = "10.10.12.0/24", gateway_ipv4 = "10.10.12.1"}
    cryptography = {bridge = "crypto", cidr_ipv4 = "10.20.21.0/24", gateway_ipv4 = "10.20.21.1"}
  }
}
'''
        test_file.write_text(settings + '''
run "before_stage_six" {
  command = plan
  assert {
    condition = toset(keys(module.vms)) == toset(["ca-1", "idm-1", "idm-2"])
    error_message = "The default must not create an early monitor or lose foundation guests."
  }
}
''', encoding="utf-8")
        environment = dict(os.environ, CHECKPOINT_DISABLE="1", TF_IN_AUTOMATION="1")
        for args in (("init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color"),
                     ("test", "-no-color")):
            result = subprocess.run(["terraform", f"-chdir={root}", *args], capture_output=True,
                                    text=True, env=environment, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        activate_monitor(repo)
        test_file.write_text(settings + '''
run "stage_six_enabled" {
  command = plan
  assert {
    condition = toset(keys(module.vms)) == toset(["ca-1", "idm-1", "idm-2", "mon-1"])
    error_message = "Only the optional monitor may join the existing foundation addresses."
  }
  assert {
    condition = (
      module.environment.vm_instances["mon-1"].vm_id == 411 &&
      module.environment.vm_instances["mon-1"].network_zone_key == "management" &&
      module.environment.vm_instances["mon-1"].ipv4_address == "10.10.10.60/24" &&
      module.environment.vm_instances["mon-1"].disk_size_gb == 40 &&
      module.environment.vm_instances["mon-1"].template_vm_id == 9101
    )
    error_message = "The monitor must resolve its real management IP, disk and Linux template."
  }
}
''', encoding="utf-8")
        result = subprocess.run(["terraform", f"-chdir={root}", "test", "-no-color"],
                                capture_output=True, text=True, env=environment, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
    def test_documented_shared_baseline_selects_only_the_monitor(self):
        repo = self.prepare()
        activate_monitor(repo)
        guide = self.root / "verify-architecture/docs/auto-docs/deployment/stage-6-secrets/monitoring.md"
        command = next(block for block in re.findall(r"(?ms)^```bash\n(.*?)^```", guide.read_text())
                       if "-shared/ansible/playbooks/site.yml" in block)
        result = subprocess.run(["bash", "-c", command.rstrip() + " --list-hosts"], cwd=repo,
                                capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, ANSIBLE_SSH_EXECUTABLE="/bin/false"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("mon-1", result.stdout)
        self.assertNotIn("idm-1", result.stdout)
        self.assertNotIn("ca-1", result.stdout)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
    def test_documented_monitor_and_audit_inputs_resolve_managed_and_external_hosts(self):
        repo = self.prepare()
        activate_monitor(repo)
        docs = self.root / "verify-architecture/docs/auto-docs/deployment/stage-6-secrets"
        for relative, host_variable in (("monitoring.md", "MONITOR_HOST"),
                                        ("procedures/netbox-audit.md", "AUDIT_HOST")):
            blocks = re.findall(r"(?ms)^```bash\n(.*?)^```", (docs / relative).read_text())
            command = next(block for block in blocks if f"${host_variable}" in block or
                           f"${{{host_variable}" in block)
            command = "\n".join(line for line in command.splitlines() if not line.startswith("read "))
            # Use the real guide input sequence, but replace the remote installer with a local assertion.
            playbook = re.search(r"ansible/playbooks/deployment/[a-z-]+\.yml", command)[0]
            for input_file in re.findall(r"@([a-zA-Z0-9_/.]+\.yml)", command):
                if not (repo / input_file).exists():
                    (repo / input_file).write_text("{}\n", encoding="utf-8")
            command = command.replace("--ask-vault-pass", "")
            for external in (False, True):
                probe = Path(self.temp.name) / "monitor-input-probe.yml"
                probe.write_text(yaml.safe_dump([{
                    "hosts": "infrastructure_monitoring", "gather_facts": False,
                    "tasks": [{"ansible.builtin.assert": {"that": [
                        "ansible_host == '" + ("192.0.2.60" if external else "10.10.10.60") + "'",
                    ]}}],
                }]), encoding="utf-8")
                invocation = command.replace(playbook, f"'{probe}'")
                if external:
                    override = Path(self.temp.name) / "external-monitor.yml"
                    override.write_text("ansible_host: 192.0.2.60\n", encoding="utf-8")
                    invocation += f" -e '@{override}'"
                result = subprocess.run(["bash", "-c", invocation], cwd=repo, capture_output=True,
                                        text=True, env=dict(os.environ, **{host_variable: "mon-1"}), timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("mon-1", result.stdout, result.stderr)
