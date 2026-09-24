"""Offline checks for generation, ownership, and refresh behavior."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generate import TIERS
from generated_files import RepositoryWriter


class GeneratedRepositories(TierRepositoryTestCase):
    def test_dry_run_and_repo_selection(self):
        self.generate("--dry-run")
        self.assertFalse(self.parent.exists())
        self.generate("--repo", "tier-2", "--repo", "tier-2")
        self.assertEqual([path.name for path in self.root.iterdir()], ["verify-tier-2"])
        self.assertEqual([path.name for path in self.parent.iterdir()], ["verify-iac"])
        self.assertFalse((self.root / ".git").exists())

    def test_default_collection_is_beside_kit_not_current_directory(self):
        result = subprocess.run(
            [sys.executable, str(UPSTREAM / "scripts/tier-repos/generate.py"),
             "--dry-run", "--repo", "tier-2"], cwd=self.temp.name,
            capture_output=True, text=True, check=True,
        )
        self.assertIn(f"Collection: {UPSTREAM.parent / 'homelab-iac'}", result.stdout)

    def test_inventory_is_split_and_templates_resolve(self):
        self.generate()
        inventories = {}
        for tier in TIERS:
            repo = self.root / f"verify-{tier}"
            inventory = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())
            inventories[tier] = {host for group in inventory["all"]["children"].values()
                                 for host in (group or {}).get("hosts", {})}
            for source in (repo / "terraform/environments").rglob("*.tf"):
                for module in re.findall(r'source\s*=\s*"(\.\./[^\"]+)"', source.read_text()):
                    self.assertTrue((source.parent / module).is_dir(), (source, module))
            for values in (repo / "ansible/group_vars").glob("*.example"):
                ips = yaml.safe_load(values.read_text()).get("platform_host_ips", {})
                self.assertTrue(set(ips).issubset(inventories[tier]), values)
            for config in (repo / "clusters").rglob("kustomization.yaml"):
                for resource in yaml.safe_load(config.read_text())["resources"]:
                    self.assertTrue((config.parent / resource / "kustomization.yaml").is_file())
        all_hosts = set().union(*inventories.values())
        self.assertEqual(sum(map(len, inventories.values())), len(all_hosts))
        self.assertIn("idm-1", inventories["tier-0"])
        self.assertIn("edge-lb-1", inventories["tier-1"])
        self.assertIn("lab-1", inventories["tier-2"])
        shared = self.root / "verify-shared"
        self.assertTrue((self.root / "verify-tier-0/ansible/playbooks/foundation.yml").is_file())
        self.assertTrue((self.root / "verify-tier-1/ansible/roles/cache_proxy/templates/squid.conf.j2").is_file())
        self.assertTrue((shared / "ansible/roles/baseline/tasks/main.yml").is_file())
        self.assertFalse((shared / "ansible/inventory").exists())
        self.assertFalse((shared / "ansible/group_vars").exists())
        for repo in self.root.iterdir():
            self.assertFalse(list(repo.rglob("terraform.tfvars")))
            self.assertFalse(list(repo.rglob(".env.local")))
            self.assertFalse(list(repo.rglob("terraform.tfstate")))
            for document in repo.rglob("*.md"):
                for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                    target = target.split("#")[0]
                    if not target or ":" in target:
                        continue
                    self.assertTrue((document.parent / target).exists(), (document, target))

    def test_refresh_preserves_edits_inputs_and_cluster_definitions(self):
        self.generate()
        shared = self.root / "verify-shared"
        changed = shared / "ansible/playbooks/site.yml"
        changed.write_text("# Local playbook changes\n", encoding="utf-8")
        owned = self.root / "verify-tier-0/clusters/tier0/applications/kustomization.yaml"
        owned.write_text("resources: [owned-service]\n", encoding="utf-8")
        live = self.root / "verify-tier-0/ansible/inventory/hosts.yml"
        live.write_text("all: {hosts: {owned-host: {}}}\n", encoding="utf-8")
        custom = self.root / "verify-tier-0/terraform/environments/custom/main.tf"
        custom.parent.mkdir()
        custom.write_text("# User-developed infrastructure\n", encoding="utf-8")
        deleted = [self.root / "verify-tier-2/ansible/playbooks/lab.yml",
                   self.root / "verify-tier-0/clusters/tier0/infrastructure/cni/kustomization.yaml"]
        for path in deleted:
            path.unlink()
        updates = [(self.root / "verify-tier-1", "ansible/group_vars/edge.yml.example"),
                   (self.root / "verify-architecture", "docs/auto-docs/architecture/overview.md")]
        expected = {}
        for repo, relative in updates:
            file = repo / relative
            expected[file] = file.read_bytes()
            file.write_bytes(b"# Previous upstream version\n")
            manifest_path = repo / ".generated-files.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"][relative] = hashlib.sha256(file.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
        self.generate("--refresh")
        self.assertEqual(changed.read_text(), "# Local playbook changes\n")
        self.assertEqual(owned.read_text(), "resources: [owned-service]\n")
        self.assertIn("owned-host", live.read_text())
        self.assertEqual(custom.read_text(), "# User-developed infrastructure\n")
        for path in deleted:
            self.assertFalse(path.exists(), path)
        for path, contents in expected.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_hash_manifest_refresh_and_unmarked_file_preservation(self):
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(self.root)
            writer.write("generated.tf", "# original\n")
            writer.finish()
            writer = RepositoryWriter(self.root, refresh=True)
            writer.write("generated.tf", "# refreshed\n")
            writer.finish()
            self.assertEqual((self.root / "generated.tf").read_text(), "# refreshed\n")
            (self.root / "untracked.tf").write_text("# owned\n")
            writer = RepositoryWriter(self.root, refresh=True)
            writer.write("untracked.tf", "# replacement\n")
            writer.finish()
            self.assertEqual((self.root / "untracked.tf").read_text(), "# owned\n")
            writer = RepositoryWriter(self.root, refresh=True)
            writer.write("untracked.tf", "# owned\n")
            writer.finish()
            self.assertNotIn("untracked.tf", writer.hashes)
            writer = RepositoryWriter(self.root, refresh=True)
            writer.write("untracked.tf", "# future upstream change\n")
            writer.finish()
            self.assertEqual((self.root / "untracked.tf").read_text(), "# owned\n")

    @unittest.skipIf(os.name == "nt", "Bash wrapper checks run under Linux/WSL")
    def test_wrappers_use_tier_inputs_playbooks_and_shared_helpers(self):
        self.generate()
        commands = self.root / "commands"
        commands.mkdir()
        log = self.root / "calls.jsonl"
        fake = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ['TEST_COMMAND_LOG'], 'a') as log:
    log.write(json.dumps({'tool': os.path.basename(sys.argv[0]), 'args': sys.argv[1:],
                         'cwd': os.getcwd(), 'data': os.getenv('TF_DATA_DIR'),
                         'config': os.getenv('ANSIBLE_CONFIG'),
                         'roles': os.getenv('ANSIBLE_ROLES_PATH')}) + '\\n')
"""
        for command in ("ansible-playbook", "terraform"):
            path = commands / command
            path.write_text(fake)
            path.chmod(0o755)
        env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", TEST_COMMAND_LOG=str(log))
        env.pop("DEPLOYMENT_REPO_DIR", None)
        for tier, setup in (("tier-0", "hsm"), ("tier-1", "edge"), ("tier-2", "lab")):
            repo = self.root / f"verify-{tier}"
            init = ["bash", "../verify-shared/scripts/init-local-files.sh"]
            subprocess.run([*init, "--env", "test"], cwd=repo,
                           check=True, capture_output=True, text=True, env=env)
            invalid = subprocess.run([*init, "--setup", "not-owned"], cwd=repo, capture_output=True, env=env)
            self.assertNotEqual(invalid.returncode, 0)
            extra = repo / "extra.yml"
            extra.write_text("platform_hostname_prefix: check\n")
            result = subprocess.run(
                ["bash", "../verify-shared/scripts/deploy.sh", setup, "--env", "test",
                 "--ansible-vars", str(extra), "--auto-approve"],
                cwd=repo, capture_output=True, text=True, env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        shortcut = subprocess.run(
            ["bash", str(self.root / "verify-tier-2/scripts/deploy.sh"), "lab", "--ansible-only"],
            cwd=self.temp.name, capture_output=True, text=True, env=env)
        self.assertEqual(shortcut.returncode, 0, shortcut.stdout + shortcut.stderr)
        misplaced = subprocess.run(
            ["bash", str(self.root / "verify-shared/scripts/init-local-files.sh")],
            cwd=self.root, capture_output=True, text=True, env=env)
        self.assertNotEqual(misplaced.returncode, 0)
        self.assertIn("tier repository root", misplaced.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        plans = [call for call in calls if call["tool"] == "terraform" and call["args"][0] == "plan"]
        self.assertEqual(len(plans), 3)
        for plan in plans:
            repo = Path(plan["cwd"]).parents[2]
            catalog_arg = f"-var-file={self.root}/verify-shared/templates/proxmox-catalog.tfvars"
            common_arg = f"-var-file={repo}/terraform/common.tfvars"
            self.assertLess(plan["args"].index(catalog_arg), plan["args"].index(common_arg))
            self.assertTrue(plan["data"].startswith(str(repo / ".terraform/data")))
            self.assertIn(f"-var=ansible_inventory_path={repo}/ansible/inventory/hosts.yml", plan["args"])
            arg = next(arg for arg in plan["args"] if arg.startswith("-var=ansible_group_vars_paths="))
            variables = json.loads(arg.split("=", 2)[2])
            setup = Path(plan["cwd"]).name
            stem = setup.replace("-", "_")
            self.assertEqual(variables, [str(repo / f"ansible/group_vars/{name}.yml")
                                        for name in ("all", stem, "all.test", f"{stem}.test")]
                             + [str(repo / "extra.yml")])
            play = next(call for call in calls if call["tool"] == "ansible-playbook"
                        and call["args"][-1].endswith(f"/{setup}.yml"))
            self.assertEqual(play["args"][-1], str(repo / f"ansible/playbooks/{setup}.yml"))
            self.assertEqual([arg[1:] for arg in play["args"] if arg.startswith("@")], variables)
            self.assertEqual(play["config"], str(repo / "ansible/ansible.cfg"))
            self.assertEqual(play["roles"].split(":")[:2],
                             [str(repo / "ansible/roles"), str(self.root / "verify-shared/ansible/roles")])
        self.assertFalse(any("ingress.yml" in str(call["args"]) for call in calls))
        (self.root / "verify-shared/scripts/deploy.sh").unlink()
        result = subprocess.run(["bash", str(self.root / "verify-tier-0/scripts/deploy.sh"), "hsm"],
                                capture_output=True, text=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing shared automation", result.stderr)


if __name__ == "__main__":
    unittest.main()
