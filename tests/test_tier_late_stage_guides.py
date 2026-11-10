"""Execute late-stage guide examples without accessing infrastructure."""

import os
from pathlib import Path
import re
import shutil
import subprocess
from string import Template
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


def code_blocks(path, language):
    return re.findall(rf"(?ms)^```{language}\n(.*?)^```",
                      path.read_text(encoding="utf-8"))


class LateStageGuideExecution(TierRepositoryTestCase):
    def guide_trees(self):
        self.generate()
        return ((UPSTREAM / "docs/deployment", UPSTREAM),
                (self.root / "verify-architecture/docs/auto-docs/deployment", self.root))

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires native Ansible and Bash")
    def test_projection_command_resolves_receiver_inputs_and_limits_the_target(self):
        for docs, root in self.guide_trees():
            repo = root / ("tier-0" if root == UPSTREAM else "verify-tier-0")
            guide = docs / "stage-8-observability/step-4b-protected-log-search.md"
            command = next(block for block in code_blocks(guide, "bash")
                           if "ansible/playbooks/deployment/logging-export.yml" in block)
            command = "\n".join(line for line in command.splitlines()
                                if not line.startswith("read "))
            # Substitute a controller-only diagnostic play for the remote installer.
            # Keep the guide's actual input arguments and host limit unchanged.
            inputs = yaml.safe_load((repo / "ansible/group_vars/syslog.yml.example").read_text())
            probe = Path(self.temp.name) / "projection-input-probe.yml"
            probe.write_text(yaml.safe_dump([{
                "name": "Check receiver inputs without connecting",
                "hosts": "foundation_logging", "gather_facts": False,
                "tasks": [{"ansible.builtin.assert": {"that": [
                    "inventory_hostname == 'log-1'",
                    f"ansible_host == '{inputs['platform_host_ips']['log-1']}'",
                    "ansible_user == 'automation'",
                ]}}],
            }]), encoding="utf-8")
            command = command.replace("ansible/playbooks/deployment/logging-export.yml",
                                      f"'{probe}'")
            inventory = Path(self.temp.name) / "projection-inventory.yml"
            inventory_data = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())
            inventory_data["all"]["children"]["foundation_logging"]["hosts"]["log-2"] = {}
            inventory.write_text(yaml.safe_dump(inventory_data), encoding="utf-8")
            command = command.replace("ansible/inventory/hosts.yml", f"'{inventory}'")
            command = re.sub(r"@ansible/group_vars/([^\s]+\.yml)", r"@ansible/group_vars/\1.example",
                             command)
            result = subprocess.run(["bash", "-c", command], cwd=repo, capture_output=True, text=True,
                                    env=dict(os.environ, EXPORT_HOST="log-1"), timeout=60)
            with self.subTest(repo=repo):
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("log-1", result.stdout, result.stderr)
                self.assertNotIn("log-2", result.stdout)

    @unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "Requires Bash")
    def test_image_pipeline_uses_the_accepted_registry_without_gitlab_registry_variables(self):
        tools = Path(self.temp.name) / "tools"
        tools.mkdir()
        podman = tools / "podman"
        podman.write_text("#!/usr/bin/env bash\nset -eu\n"
                          'printf "%s\\n" "$*" >> "$PODMAN_LOG"\n'
                          'if [[ "$1" == login ]]; then cat >/dev/null; fi\n', encoding="utf-8")
        podman.chmod(0o755)
        for docs, _ in self.guide_trees():
            guide = docs / "stage-9-development/step-2b-podman-runner.md"
            pipeline = next(item for block in code_blocks(guide, "yaml")
                            if isinstance(item := yaml.safe_load(block), dict)
                            and "build_bootc_image" in item)
            for branch in ("main", "feature"):
                log = tools / "podman.log"
                log.write_text("", encoding="utf-8")
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith("CI_REGISTRY")}
                env.update(PATH=str(tools) + os.pathsep + env["PATH"], PODMAN_LOG=str(log),
                           REGISTRY_HOST="registry.test", REGISTRY_PROJECT="candidates",
                           REGISTRY_USER="robot", REGISTRY_PASSWORD="test-only-password",
                           CI_COMMIT_SHORT_SHA="abcd1234", CI_COMMIT_BRANCH=branch,
                           CI_DEFAULT_BRANCH="main", RH_REGISTRY_USER="")
                env["BOOTC_IMAGE"] = Template(pipeline["variables"]["BOOTC_IMAGE"]).substitute(env)
                result = subprocess.run(["bash", "-c", "\n".join(pipeline["build_bootc_image"]["script"])],
                                        env=env, capture_output=True, text=True, timeout=30)
                with self.subTest(guide=guide, branch=branch):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    calls = log.read_text(encoding="utf-8")
                    image = "registry.test/candidates/server-base"
                    self.assertIn("login registry.test -u robot --password-stdin", calls)
                    self.assertIn(f"build --pull=always -t {image}:abcd1234 .", calls)
                    self.assertIn(f"push {image}:abcd1234", calls)
                    self.assertEqual(f"push {image}:stable" in calls, branch == "main")
                    self.assertNotIn(env["REGISTRY_PASSWORD"], calls + result.stdout + result.stderr)
