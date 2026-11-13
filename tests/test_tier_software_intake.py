"""Controlled update intake stays separate from artifact approval and administration."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class SoftwareIntake(TierRepositoryTestCase):
    @unittest.skipIf(os.name == "nt", "Generated Bash commands run under Linux/WSL")
    def test_first_command_names_owner_and_wrong_tier_creates_no_inputs(self):
        self.generate()
        tier0 = self.root / "verify-tier-0"
        tier2 = self.root / "verify-tier-2"
        environment = os.environ.copy()
        environment.pop("DEPLOYMENT_REPO_DIR", None)
        rejected = subprocess.run(["bash", "scripts/init-local-files.sh", "--setup", "cache"],
                                  cwd=tier0, env=environment, capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(f"owning repository: {tier2}", rejected.stderr)
        self.assertFalse((tier0 / ".env.local").exists())
        self.assertFalse((tier0 / "ansible/inventory/hosts.yml").exists())

        guide = (self.root / "verify-architecture/docs/auto-docs/03-deployment/"
                 "stage-1-software-intake/README.md").read_text()
        commands = re.search(r"```bash\n(.*?)```", guide, re.DOTALL).group(1)
        self.assertRegex(guide, r"Run from \*\*`verify-tier-2/`\*\*[^\n]*\n\n```bash\n"
                               r"bash scripts/init-local-files\.sh --setup cache\n")
        initialized = subprocess.run(["bash", "-e", "-c", commands], cwd=tier2, env=environment,
                                     capture_output=True, text=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        self.assertTrue((tier2 / "terraform/deployments/cache/terraform.tfvars").is_file())
        self.assertTrue((tier2 / "ansible/inventory/hosts.yml").is_file())
        self.assertFalse((tier0 / "ansible/inventory/hosts.yml").exists())
        self.assertRegex(guide, r"Edit in \*\*`verify-shared/`\*\*[.:]")
        self.assertIn("config/platform.tfvars", guide)
        self.assertNotIn("../homelab-shared/", guide)

    def test_source_and_generated_docs_explain_transport_ownership_and_supply(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            prefix = "<prefix>" if docs == UPSTREAM / "docs" else "verify"
            design = " ".join((docs / "01-architecture/07-software-intake/README.md").read_text().split())
            for expected in ("## Connected proxy design", "## Supply choices", "## Transport and integrity",
                             "requests target the proxy interface", "one common policy", "not supplied",
                             "Tier 0 authorizes and executes its updates", "Internal HTTP mirror",
                             "Tier 1 owns authoritative shared mirrors", "independent of the cache"):
                self.assertIn(expected, design)
            self.assertNotIn("```bash", design)
            for source in ("01-architecture/10-delivery/README.md", "01-architecture/10-delivery/01-artifact-supply.md",
                           "05-operations/02-software-intake/host-updates.md"):
                self.assertIn("software-intake/", (docs / source).read_text(), source)
            self.assertIn("../stage-1-software-intake/README.md",
                          (docs / "03-deployment/foundation/README.md").read_text())
            guide = (docs / "08-reference/proxy-cache.md").read_text()
            for expected in (f"**Working repository:** `{prefix}-tier-2`", "not cached",
                             "no unrestricted", "direct WAN bypass fails", "not a cache hit",
                             "No cache-to-Tier-0 management rule"):
                self.assertIn(expected, guide)

    def test_capability_is_outside_foundation_and_grows_into_later_oci_supply(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            deployment = docs / "03-deployment"
            self.assertFalse((deployment / "foundation/step-3b-outbound-cache.md").exists())
            capability = (deployment / "stage-1-software-intake/README.md").read_text()
            for step in range(1, 4):
                self.assertIn(f"## Step {step}:", capability)
            for expected in ("cache-1", "cache-2", "proxy-cache.md", "**IaC:**", "Harbor",
                             "complete without PKI or a hosted registry", "Harbor belongs to Stage 7"):
                self.assertIn(expected, capability)
            self.assertIn("../stage-3-trust/README.md#15b-verified-repository-and-artifact-publication-optional", capability)
            foundation = (deployment / "foundation/README.md").read_text()
            self.assertIn("../stage-1-software-intake/README.md", foundation)
            self.assertNotIn("step-3b-outbound-cache.md", foundation)
            registry = (deployment / "stage-7-delivery/procedures/registry.md").read_text()
            self.assertIn("../../stage-1-software-intake/README.md#extend-the-capability-later", registry)
            self.assertIn("not a replacement", registry)
            index = (deployment / "README.md").read_text()
            for connection in ("Base --> Intake", "Intake --> Logs", "Logs --> Trust"):
                self.assertIn(connection, index)
            self.assertIn("Software intake", (self.root / "verify-tier-2/docs/deployment/README.md").read_text())

    @unittest.skipUnless(shutil.which("ansible-playbook"), "Ansible is required for native policy checks")
    def test_native_preflight_and_render_fail_closed_in_source_and_generated_roles(self):
        self.generate()
        fixture = Path(self.temp.name) / "native-policy"
        fixture.mkdir()
        inventory = fixture / "hosts.ini"
        inventory.write_text("[cache]\nlocalhost ansible_connection=local\n")
        environment = os.environ.copy()
        environment["ANSIBLE_LOCAL_TEMP"] = str(fixture / "controller-temp")
        for label, owner in (("source", UPSTREAM / "tier-2"), ("generated", self.root / "verify-tier-2")):
            role = owner / "ansible/roles/cache_proxy"
            inputs = yaml.safe_load((role / "defaults/main.yml").read_text())
            inputs.update({"ansible_os_family": "Debian", "cache_keepalived_vip_cidr": "192.0.2.10/24",
                           "platform_host_ips": {"localhost": "192.0.2.1"},
                           "cache_squid_allowed_cidrs": ["192.0.2.0/24"]})
            preflight = yaml.safe_load((role / "tasks/preflight.yml").read_text())[:-1]
            cases = (("empty", [], False, False), ("blank", [" ", ""], False, False),
                     ("approved", [".example.com", ".repo.example.com"], False, True),
                     ("empty-render", [], True, True))
            for name, domains, render_only, succeeds in cases:
                with self.subTest(owner=label, policy=name):
                    output = fixture / f"{label}-{name}.conf"
                    tasks = [] if render_only else list(preflight)
                    tasks.append({"ansible.builtin.template": {
                        "src": str(role / "templates/squid.conf.j2"), "dest": str(output), "mode": "0600"}})
                    play = fixture / f"{label}-{name}.yml"
                    play.write_text(yaml.safe_dump([{
                        "hosts": "cache", "gather_facts": False,
                        "vars": {**inputs, "cache_squid_allowed_domains": domains}, "tasks": tasks}]))
                    result = subprocess.run(["ansible-playbook", "-i", str(inventory), str(play)],
                                            capture_output=True, text=True, env=environment, timeout=120)
                    self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)
                    if not succeeds:
                        self.assertIn("non-empty software-source domains", result.stdout)
                        self.assertFalse(output.exists())
                        continue
                    config = output.read_text()
                    self.assertNotIn("http_access allow localnet\n", config)
                    self.assertIn("http_access deny all", config)
                    if domains:
                        self.assertIn("acl allowed_update_domains dstdomain -n .example.com\n", config)
                        self.assertNotIn(".repo.example.com", config)
                        self.assertIn("http_access allow localnet allowed_update_domains", config)
                        self.assertLess(config.index("http_access deny CONNECT !SSL_ports"),
                                        config.index("http_access allow localnet allowed_update_domains"))
                    else:
                        self.assertNotIn("http_access allow localnet", config)
