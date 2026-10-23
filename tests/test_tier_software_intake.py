"""Controlled update intake stays separate from artifact approval and administration."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class SoftwareIntake(TierRepositoryTestCase):
    def test_source_and_generated_docs_explain_transport_ownership_and_supply(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            design = (docs / "architecture/delivery/software-intake.md").read_text()
            for expected in ("## Connected proxy design", "## Supply choices", "## Transport and integrity",
                             "client-initiated requests", "one common policy", "not supplied",
                             "Tier 0 authorizes and executes its updates", "Internal HTTP mirror",
                             "Tier 1 owns authoritative shared mirrors", "independent of the cache"):
                self.assertIn(expected, design)
            self.assertNotIn("```bash", design)
            for source in ("architecture/delivery/README.md", "architecture/delivery/artifact-supply.md",
                           "deployment/foundation/README.md", "administration/compute/update-access.md"):
                self.assertIn("software-intake.md", (docs / source).read_text(), source)
            guide = (docs / "deployment/stage-1-software-intake/proxy-cache.md").read_text()
            for expected in ("**Working repository:** `<prefix>-tier-2`", "not cached",
                             "no unrestricted", "direct WAN bypass fails", "not a cache hit",
                             "No cache-to-Tier-0 management rule"):
                self.assertIn(expected, guide)

    def test_capability_is_outside_foundation_and_grows_into_later_oci_supply(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            deployment = docs / "deployment"
            self.assertFalse((deployment / "foundation/step-3b-outbound-cache.md").exists())
            capability = (deployment / "stage-1-software-intake/README.md").read_text()
            for step in range(1, 4):
                self.assertIn(f"## Step {step}:", capability)
            for expected in ("cache-1", "cache-2", "proxy-cache.md", "**IaC:**", "Harbor",
                             "works independently of later hosted", "not installed by this path"):
                self.assertIn(expected, capability)
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
                           "platform_host_ips": {"localhost": "192.0.2.1"}})
            preflight = yaml.safe_load((role / "tasks/preflight.yml").read_text())[0]
            cases = (("empty", [], False, False), ("blank", [" ", ""], False, False),
                     ("approved", [".example.com", ".repo.example.com"], False, True),
                     ("empty-render", [], True, True))
            for name, domains, render_only, succeeds in cases:
                with self.subTest(owner=label, policy=name):
                    output = fixture / f"{label}-{name}.conf"
                    tasks = [] if render_only else [preflight]
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
                        self.assertIn("acl allowed_update_domains dstdomain .example.com\n", config)
                        self.assertNotIn(".repo.example.com", config)
                        self.assertIn("http_access allow localnet allowed_update_domains", config)
                        self.assertLess(config.index("http_access deny CONNECT !SSL_ports"),
                                        config.index("http_access allow localnet allowed_update_domains"))
                    else:
                        self.assertNotIn("http_access allow localnet", config)
