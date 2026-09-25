"""Talos resources, inputs, and state belong to Tier 0, not shared automation."""

import json
import os
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


class TierZeroTalos(TierRepositoryTestCase):
    def test_cluster_and_inventory_are_tier_owned(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        groups = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
        hosts = set(groups["talos_control_plane"]["hosts"]) | set(groups["talos_workers"]["hosts"])
        self.assertEqual(len(groups["talos_control_plane"]["hosts"]), 3)
        self.assertNotIn("talos", groups["guests"]["children"])
        self.assertEqual(set(yaml.safe_load((repo / "ansible/group_vars/talos.yml.example").read_text())
                             ["platform_host_ips"]), hosts)
        self.assertIn("all:!talos", (self.root / "verify-shared/ansible/playbooks/site.yml").read_text())
        root = repo / "terraform/deployments/kubernetes"
        self.assertTrue((root / ".terraform.lock.hcl").is_file())
        self.assertFalse((root / "tests").exists())
        self.assertFalse((repo / "bootstrap").exists())
        self.assertNotIn("kubernetes", (repo / ".deployment-setups").read_text().splitlines())
        self.assertFalse((repo / "terraform/deployments/talos").exists())
        main = (root / "main.tf").read_text()
        self.assertIn("../../../../verify-shared/config/guest-sizes.json", main)
        self.assertNotIn("shared/terraform", main)
        self.assertIn('prevent_destroy = true', (root / "machines.tf").read_text())
        self.assertTrue((repo / "scripts/kubernetes-cluster.sh").is_file())
        for tier in ("tier-1", "tier-2", "shared"):
            self.assertFalse((self.root / f"verify-{tier}/terraform/deployments/kubernetes").exists())

    @unittest.skipIf(os.name == "nt", "Bash wrapper checks run under Linux/WSL")
    def test_wrapper_preserves_inputs_and_requires_reviewed_plan(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        script = ["bash", "scripts/kubernetes-cluster.sh"]
        commands = self.root / "commands"
        commands.mkdir()
        fake = commands / "terraform"
        fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ["CALLS"], "a") as stream:
    stream.write(json.dumps({"args": sys.argv[1:], "data": os.environ["TF_DATA_DIR"]}) + "\\n")
for arg in sys.argv:
    if arg.startswith("-out="):
        pathlib.Path(arg[5:]).write_text("saved plan")
if os.environ.get("FAIL_PLAN") and "plan" in sys.argv:
    sys.exit(1)
if "output" in sys.argv:
    if os.environ.get("FAIL_EXPORT") and sys.argv[-1] == "kubeconfig":
        sys.exit(1)
    print('{"k8ctl-1": "test machine configuration"}' if "-json" in sys.argv else "test credential")
''')
        fake.chmod(0o755)
        log = self.root / "calls.jsonl"
        env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(log))

        def call(action, environment=env):
            return subprocess.run([*script, action], cwd=repo, env=environment,
                                  capture_output=True, text=True)

        self.assertNotEqual(call("apply").returncode, 0)
        self.assertFalse(log.exists())
        self.assertEqual(call("init").returncode, 0)
        inventory = repo / "ansible/inventory/hosts.yml"
        inventory.write_text("# Existing project inventory\n")
        self.assertEqual(call("init").returncode, 0)
        self.assertEqual(inventory.read_text(), "# Existing project inventory\n")
        alias = subprocess.run(["bash", "scripts/talos-cluster.sh", "init"], cwd=repo,
                               env=env, capture_output=True, text=True)
        self.assertEqual(alias.returncode, 0, alias.stdout + alias.stderr)
        self.assertEqual(inventory.read_text(), "# Existing project inventory\n")
        self.assertEqual(call("plan").returncode, 0)
        plan = repo / ".terraform/plans/talos.tfplan"
        self.assertTrue(plan.is_file())
        self.assertNotEqual(call("plan", dict(env, FAIL_PLAN="1")).returncode, 0)
        self.assertFalse(plan.exists())
        self.assertNotEqual(call("apply").returncode, 0)
        self.assertEqual(call("plan").returncode, 0)
        self.assertEqual(call("apply").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertNotEqual(call("credentials").returncode, 0)
        state = repo / ".terraform/state/talos/terraform.tfstate"
        state.write_text("fake state\n")
        self.assertEqual(call("credentials").returncode, 0)
        directory = repo / "secrets/talos"
        exported = {path: path.read_bytes() for path in directory.iterdir()}
        self.assertEqual(set(path.name for path in exported),
                         {"talosconfig", "kubeconfig", "machine-configurations.json"})
        for path in exported:
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertNotEqual(call("credentials", dict(env, FAIL_EXPORT="1")).returncode, 0)
        self.assertEqual({path: path.read_bytes() for path in directory.iterdir()}, exported)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        for record in calls:
            self.assertEqual(record["data"], str(repo / ".terraform/data/talos"))
            self.assertEqual(record["args"][0], f"-chdir={repo}/terraform/deployments/kubernetes")
        planning = next(record["args"] for record in calls if "plan" in record["args"])
        catalog = next(arg.removeprefix("-var-file=") for arg in planning if arg.startswith("-var-file="))
        self.assertEqual(os.path.realpath(catalog),
                         str(self.root / "verify-shared/templates/proxmox-catalog.tfvars"))
        initializing = next(record["args"] for record in calls if "init" in record["args"])
        self.assertIn(f"-backend-config=path={repo}/.terraform/state/talos/terraform.tfstate", initializing)


if __name__ == "__main__":
    unittest.main()
