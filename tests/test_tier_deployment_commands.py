"""Keep the compact command index tied to executable setup and recipe owners."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


SHEET = UPSTREAM / "docs/05-operations/deployment-commands.md"
BASH = os.environ.get("BASH_BINARY")
if not BASH and os.name == "nt" and (git := shutil.which("git")):
    candidate = Path(git).resolve().parents[1] / "bin/bash.exe"
    if candidate.is_file():
        BASH = str(candidate)
BASH = BASH or shutil.which("bash")


def table_rows(text, heading):
    section = text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    return [[cell.strip() for cell in line.strip("|").split("|")]
            for line in section.splitlines() if line.startswith("| ")][2:]


class DeploymentCommands(unittest.TestCase):
    def test_linux_rows_cover_every_registered_owner_and_real_inputs(self):
        content = SHEET.read_text(encoding="utf-8")
        rows = table_rows(content, "Linux setups")
        expected = {(str(tier), setup) for tier in range(3)
                    for setup in (UPSTREAM / f"tier-{tier}/.deployment-setups").read_text().splitlines()}
        actual = set()
        wrapper = (UPSTREAM / "shared/scripts/deploy.sh").read_text()
        prefix = "bash scripts/deploy.sh "
        for label, tier, inputs, terraform, ansible in rows:
            setup = re.search(r": `([a-z-]+)`$", label)[1]
            owner = UPSTREAM / f"tier-{tier}"
            actual.add((tier, setup))
            self.assertIn((tier, setup), expected)
            self.assertTrue((owner / f"terraform/deployments/{setup}/terraform.tfvars.example").is_file())
            self.assertIn(f"`{setup.replace('-', '_')}.yml`", inputs)
            for filename in re.findall(r"`([a-z_-]+\.yml)`", inputs):
                self.assertTrue((owner / f"ansible/group_vars/{filename}.example").is_file(), filename)
            entry = yaml.safe_load((owner / f"ansible/playbooks/{setup}.yml").read_text())
            for play in entry:
                self.assertTrue((owner / "ansible/playbooks" / play["ansible.builtin.import_playbook"]).is_file())
            for command in re.findall(r"`([^`]+)`", terraform + " " + ansible):
                if command in {"csr", "complete"}:
                    continue
                self.assertTrue(command.startswith(prefix), command)
                arguments = command.removeprefix(prefix)
                self.assertEqual(arguments.split()[0], setup)
                for flag in re.findall(r"--[a-z-]+", arguments):
                    self.assertIn(f"{flag})", wrapper, command)
        self.assertEqual(actual, expected)

    def test_native_catalog_rows_resolve_recipes_inputs_and_action_variables(self):
        content = SHEET.read_text(encoding="utf-8")
        rows = table_rows(content, "Native application recipes and GitOps")
        recipes = set()
        for _, tiers, recipe, inputs, action in rows:
            filename = re.fullmatch(r"`([a-z-]+\.yml)`", recipe)[1]
            recipes.add(filename)
            variable = re.search(r"`([a-z_]+)`", action)[1]
            for tier in re.findall(r"[012]", tiers):
                owner = UPSTREAM / f"tier-{tier}"
                play = owner / "ansible/playbooks/deployment" / filename
                plays = yaml.safe_load(play.read_text())
                roles = [task["ansible.builtin.include_role"]["name"]
                         for item in plays for task in item.get("tasks", [])
                         if "ansible.builtin.include_role" in task]
                defaults = [root / "ansible/roles" / role / "defaults/main.yml"
                            for role in roles for root in (owner, UPSTREAM / "shared")]
                self.assertTrue(any(variable in yaml.safe_load(path.read_text())
                                    for path in defaults if path.is_file()), (filename, variable))
                for input_file in re.findall(r"`([a-z_]+\.yml)`", inputs):
                    self.assertTrue((owner / f"ansible/group_vars/{input_file}.example").is_file(), input_file)
        catalog = (UPSTREAM / "docs/05-operations/01-hosting/ansible-recipes.md").read_text()
        native = catalog.split("Cluster applications use separate native recipes", 1)[1]
        native = native.split("Tier 0's", 1)[0]
        self.assertTrue(set(re.findall(r"deployment/([a-z-]+\.yml)", native)) <= recipes)

    def test_special_roots_and_explicit_overrides_have_source_owners(self):
        content = SHEET.read_text(encoding="utf-8")
        for tier in range(3):
            for root in (UPSTREAM / f"tier-{tier}/terraform/deployments").iterdir():
                if (root / "main.tf").is_file():
                    self.assertIn(f"`{root.name}`", content, str(root))
        for setup, recipe, inputs in re.findall(
                r"bash scripts/deploy.sh ([a-z-]+) --ansible-only --playbook ([a-z/-]+\.yml) "
                r"--ansible-vars (ansible/group_vars/[a-z_-]+\.yml)", content):
            owners = [UPSTREAM / f"tier-{tier}" for tier in range(3)
                      if setup in (UPSTREAM / f"tier-{tier}/.deployment-setups").read_text().splitlines()]
            self.assertEqual(len(owners), 1)
            self.assertTrue((owners[0] / "ansible/playbooks" / recipe).is_file(), recipe)
            self.assertTrue((owners[0] / (inputs + ".example")).is_file(), inputs)

    def test_tables_keep_inline_commands_and_consistent_columns(self):
        table = []
        for line in SHEET.read_text(encoding="utf-8").splitlines() + [""]:
            if line.startswith("|"):
                self.assertNotIn("```", line)
                table.append(line)
            elif table:
                self.assertEqual(len({row.count("|") for row in table}), 1)
                table = []

    @unittest.skipUnless(BASH, "Requires Bash for fenced-command syntax checks")
    def test_bash_fences_parse_without_executing_commands(self):
        content = SHEET.read_text(encoding="utf-8")
        blocks = list(re.finditer(r"(?ms)^```bash\n(.*?)^```\s*$", content))
        self.assertTrue(blocks)
        for block in blocks:
            line = content.count("\n", 0, block.start()) + 1
            with self.subTest(line=line):
                result = subprocess.run(
                    [BASH, "--noprofile", "--norc", "-n"], input=block[1],
                    capture_output=True, text=True, timeout=10, cwd=UPSTREAM,
                )
                self.assertEqual(result.returncode, 0, f"{SHEET}:{line}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
