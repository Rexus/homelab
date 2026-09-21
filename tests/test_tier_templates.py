"""Template ownership, upgrade preservation, and local/CD command contracts."""

import json
import os
from pathlib import Path
import re
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


class TierTemplateLifecycle(TierRepositoryTestCase):
    def test_only_tier_zero_owns_template_inputs_and_jobs(self):
        self.generate()
        tier0 = self.root / "verify-tier-0"
        for setup in ("template-refresh", "immutable-template"):
            self.assertIn(setup, (tier0 / ".deployment-setups").read_text())
            self.assertTrue((tier0 / f"terraform/environments/{setup}/main.tf").exists())
            for tier in ("tier-1", "tier-2"):
                repo = self.root / f"verify-{tier}"
                self.assertNotIn(setup, (repo / ".deployment-setups").read_text())
                self.assertFalse((repo / f"terraform/environments/{setup}").exists())
                self.assertFalse((repo / "terraform/templates").exists())
                self.assertFalse((repo / "ci").exists())
        for source in (tier0 / "terraform/templates").glob("*.tf"):
            for module in re.findall(r'source\s*=\s*"(\.\./[^\"]+)"', source.read_text()):
                self.assertTrue((source.parent / module).is_dir(), (source, module))
        catalog = yaml.safe_load((tier0 / "templates/proxmox.yml.example").read_text())["templates"]
        self.assertEqual({entry["family"] for entry in catalog.values()}, {"alma", "rocky", "talos"})
        self.assertFalse((tier0 / "templates/proxmox.yml").exists())
        self.assertTrue((tier0 / "terraform/templates/.terraform.lock.hcl").exists())
        refresh = yaml.safe_load((tier0 / "ansible/playbooks/template-refresh.yml").read_text())
        replacement = refresh[1]["roles"][0]
        self.assertEqual(replacement["role"], "proxmox_template_replace")
        self.assertEqual(replacement["when"], "template_refresh_replace_enabled | default(false) | bool")
        groups = yaml.safe_load((tier0 / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
        self.assertIn("immutable_template_builders", groups)
        self.assertIn("template_refresh_builders", groups)
        self.assertTrue((tier0 / "packer/variables.auto.pkrvars.hcl.example").exists())
        shared = self.root / "verify-shared"
        self.assertFalse((shared / "packer/variables.auto.pkrvars.hcl.example").exists())
        self.assertTrue((tier0 / "terraform/modules/proxmox_templates/main.tf").is_file())
        self.assertTrue((tier0 / "scripts/proxmox-templates.sh").is_file())
        self.assertTrue((tier0 / "packer/templates/proxmox/talos-linux.pkr.hcl").is_file())
        self.assertFalse((shared / "terraform/modules/proxmox_templates").exists())
        self.assertFalse((shared / "scripts/proxmox-templates.sh").exists())
        self.assertFalse((shared / "packer").exists())
        pipeline_path = "ci/gitlab-templates.yml.example"
        pipeline = yaml.safe_load((tier0 / pipeline_path).read_text())
        self.assertNotIn("shared", str(pipeline))
        self.assertEqual(pipeline["template-plan"]["script"], ["bash scripts/proxmox-templates.sh plan"])
        self.assertEqual(pipeline["template-publish"]["when"], "manual")
        self.assertEqual(pipeline["template-plan"]["resource_group"],
                         pipeline["template-publish"]["resource_group"])
        self.assertIn(pipeline_path, json.loads((tier0 / ".generated-files.json").read_text())["owned"])

    def test_refresh_does_not_move_live_inputs_state_or_rewrite_owned_jobs(self):
        self.generate()
        preserved = {
            "verify-tier-0/.deployment-setups": "foundation\nvault\nhsm\n",
            "verify-tier-1/.deployment-setups": "edge\ntemplate-refresh\nimmutable-template\n",
            "verify-tier-1/.terraform/state/template-refresh/prod/terraform.tfstate": '{"serial": 7}\n',
            "verify-tier-1/terraform/environments/template-refresh/main.tf": "# Existing owner\n",
            "verify-tier-0/templates/proxmox.yml": "templates: {local: {vm_id: 9500}}\n",
            "verify-tier-0/ci/gitlab-templates.yml.example": "# Owned CI starter\n",
        }
        for path, content in preserved.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        result = self.generate("--refresh")
        self.assertIn("refresh does not move state", result.stdout)
        for path, content in preserved.items():
            self.assertEqual((self.root / path).read_text(), content)
        self.assertFalse((self.root / "verify-tier-0/.terraform").exists())

    @unittest.skipIf(os.name == "nt", "Bash wrapper checks run under Linux/WSL")
    def test_wrapper_scopes_state_and_requires_a_successful_saved_plan(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        commands = self.root / "commands"
        commands.mkdir()
        fake = commands / "terraform"
        fake.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['TEST_COMMAND_LOG'], 'a') as log:
    log.write(json.dumps({'args': sys.argv[1:], 'data': os.getenv('TF_DATA_DIR')}) + '\\n')
if os.getenv('FAIL_INIT') and 'init' in sys.argv:
    sys.exit(1)
if 'plan' in sys.argv:
    path = next(arg[5:] for arg in sys.argv if arg.startswith('-out='))
    pathlib.Path(path).write_text('test saved plan')
""")
        fake.chmod(0o755)
        log = self.root / "calls.jsonl"
        env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", TEST_COMMAND_LOG=str(log))
        for name in ("DEPLOYMENT_REPO_DIR", "TEMPLATE_STATE_PATH", "TEMPLATE_CATALOG_FILE"):
            env.pop(name, None)

        def run(action, cwd=repo, **overrides):
            return subprocess.run(["bash", str(repo / "scripts/proxmox-templates.sh"), action],
                                  cwd=cwd, env=dict(env, **overrides), capture_output=True, text=True)

        (self.root / "verify-shared").rename(self.root / "unavailable-shared")
        self.assertEqual(run("init").returncode, 0)
        catalog = repo / "templates/proxmox.yml"
        catalog.write_text("# Owned catalog\n")
        self.assertEqual(run("init").returncode, 0)
        self.assertEqual(catalog.read_text(), "# Owned catalog\n")
        self.assertNotEqual(run("apply").returncode, 0)
        for tier in ("tier-1", "tier-2"):
            self.assertNotEqual(run("init", self.root / f"verify-{tier}").returncode, 0)
        self.assertNotEqual(run("plan", TEMPLATE_STATE_PATH="relative.tfstate").returncode, 0)
        self.assertEqual(run("plan").returncode, 0)
        plan = repo / ".terraform/plans/proxmox-templates.tfplan"
        self.assertTrue(plan.exists())
        self.assertNotEqual(run("plan", TEMPLATE_STATE_PATH="relative.tfstate").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertEqual(run("plan").returncode, 0)
        self.assertNotEqual(run("plan", FAIL_INIT="1").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertNotEqual(run("apply").returncode, 0)
        self.assertEqual(run("plan").returncode, 0)
        self.assertEqual(run("apply").returncode, 0)
        self.assertFalse(plan.exists())
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        apply = next(call for call in calls if "apply" in call["args"])
        self.assertEqual(apply["args"][-1], str(plan))
        self.assertTrue(all(call["data"].startswith(str(repo)) for call in calls))
        init = next(call for call in calls if "init" in call["args"])
        self.assertIn(f"-backend-config=path={repo}/.terraform/state/proxmox-templates/terraform.tfstate",
                      init["args"])


if __name__ == "__main__":
    unittest.main()
