"""The operator path exposes prerequisites, review gates and known integration gaps."""

import re
import shutil
import subprocess
import sys
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class OperatorJourney(TierRepositoryTestCase):
    def test_first_host_handoff_does_not_skip_logging_or_network_commissioning(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            foundation = (docs / "deployment/foundation/README.md").read_text()
            self.assertIn("unifi-zones.md#bring-up-the-network", foundation)
            host = (docs / "deployment/foundation/procedures/proxmox.md").read_text()
            handoff = next(line for line in host.splitlines() if line.startswith("| 8."))
            self.assertIn("stage-2-logging/README.md", handoff)
            self.assertNotIn("freeipa.md", handoff)
            network = (docs / "deployment/foundation/procedures/unifi-zones.md").read_text()
            for expected in ("## Bring up the network", "switch alone is not", "controller",
                             "native/untagged", "control_cluster"):
                self.assertIn(expected.lower(), network.lower())
            for relative in ("README.md", "receiver.md"):
                logging = (docs / "deployment/stage-2-logging" / relative).read_text()
                self.assertIn("software-pki.md#decisions-and-recovery-kit", logging)
                self.assertIn("client-auth", logging)
                self.assertIn("independent producer authority", logging)

    def test_service_walkthroughs_initialize_plan_review_then_deploy(self):
        self.generate()
        guides = (
            ("stage-1-software-intake/proxy-cache.md", "cache", ""),
            ("stage-7-delivery/procedures/edge-proxy.md", "edge", ""),
            ("stage-6-secrets/step-1b-vault-vm.md", "vault", ""),
            ("stage-5-identity/procedures/freeipa.md", "foundation", ""),
            ("stage-9-development/step-1b-source-control-vm.md", "development", " --env test"),
            ("stage-9-development/step-2b-podman-runner.md", "podman-runner", " --env test"),
            ("stage-9-development/step-2c-image-based-linux.md", "immutable-template", " --env test"),
        )
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            for relative, setup, environment in guides:
                content = (docs / "deployment" / relative).read_text()
                lines = [line.strip() for line in content.splitlines()]
                init = f"bash scripts/init-local-files.sh --setup {setup}{environment}"
                apply = f"bash scripts/deploy.sh {setup}{environment}"
                # Identity now provisions once, then explicitly pauses/resumes its CA recipe.
                provision = apply + " --terraform-only" if setup == "foundation" else apply
                positions = [lines.index(command) for command in (init, apply + " --plan-only", provision)]
                self.assertEqual(positions, sorted(positions), relative)
                for block in re.findall(r"```bash\n(.*?)```", content, re.DOTALL):
                    self.assertFalse(apply + " --plan-only" in block and apply + "\n" in block, relative)
            vault = (docs / "deployment/stage-6-secrets/step-1b-vault-vm.md").read_text()
            self.assertLess(vault.index("export VAULT_ADDR VAULT_CACERT"), vault.index("vault status"))
            self.assertLess(vault.index("vault login"), vault.index("vault audit enable"))
            identity = (docs / "deployment/stage-5-identity/procedures/freeipa.md").read_text()
            self.assertIn("same context/state used for the issuer", identity)

    def test_hidden_follow_up_covers_every_branch_without_entering_generated_docs(self):
        self.generate()
        checklist = (UPSTREAM / ".ai/operator-walkthrough.md").read_text()
        for option in (UPSTREAM / "docs/deployment").rglob("step-*.md"):
            self.assertIn(option.relative_to(UPSTREAM).as_posix(), checklist)
        for expected in ("P1: Logging integration", "P1: Recovery procedures", "P2: Household/team procedures",
                         "## Repeat cadence", "no live gateway"):
            self.assertIn(expected, checklist)
        access = (UPSTREAM / "docs/administration/access-lifecycle.md").read_text()
        for heading in ("## Household devices", "## Team roles", "## Join and leave"):
            self.assertIn(heading, access)
        self.assertIn("../docs/administration/access-lifecycle.md", checklist)
        for repo in self.root.iterdir():
            self.assertFalse((repo / ".ai/operator-walkthrough.md").exists())
            self.assertIn(".venv/", (repo / ".gitignore").read_text())

    @unittest.skipUnless(shutil.which("bash"), "Requires Bash")
    def test_environment_initialization_is_not_misrepresented_as_resource_allocation(self):
        self.generate()
        tier = self.root / "verify-tier-2"
        result = subprocess.run(["bash", "scripts/init-local-files.sh", "--setup", "edge", "--env", "test"],
                                cwd=tier, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        variables = tier / "ansible/group_vars"
        base = yaml.safe_load((variables / "edge.yml").read_text())
        test = yaml.safe_load((variables / "edge.test.yml").read_text())
        self.assertEqual(base["platform_host_ips"], test["platform_host_ips"])
        self.assertFalse((tier / "terraform/deployments/edge/terraform.test.tfvars").exists())
        guide = (UPSTREAM / "docs/reference/repository-scripts.md").read_text()
        for expected in ("## Environment isolation", "does not allocate independent resources",
                         "Never apply a second state", "VIPs, VRRP IDs, MACs"):
            self.assertIn(expected, guide)

    def test_missing_generator_dependency_points_to_the_safe_setup_path(self):
        result = subprocess.run([sys.executable, "-E", "-S", str(UPSTREAM / "scripts/tier-repos/generate.py"),
                                 "--dry-run", "--root", str(self.parent)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PyYAML is required", result.stderr)
        self.assertIn("generated-repositories.md#purpose-and-prerequisites", result.stderr)
        self.assertFalse(self.parent.exists())

    def test_first_guest_restore_follows_template_publication_and_allows_existing_backup_services(self):
        self.generate("--repo", "architecture")
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            foundation = (docs / "deployment/foundation/README.md").read_text()
            step2, step3 = foundation.split("## Step 2:", 1)[1].split("## Step 3:", 1)
            self.assertIn("test their recovery before provisioning", step2)
            self.assertIn("first disposable clone in Step 3", step2)
            self.assertIn("Back up and restore a disposable clone", step3)
            backup = (docs / "administration/compute/backup-restore.md").read_text()
            self.assertIn("installing PBS is not mandatory", backup)
            criteria = backup.split("## Done criteria", 1)[1].split("## Read more", 1)[0]
            self.assertNotIn("PBS is reachable", criteria)
            self.assertIn("selected backup destination", criteria)

    def test_named_test_guides_edit_the_files_that_override_base_settings(self):
        self.generate("--repo", "architecture")
        guides = (("step-1b-source-control-vm.md", "development", "development"),
                  ("step-2b-podman-runner.md", "podman-runner", "podman_runner"),
                  ("step-2c-image-based-linux.md", "immutable-template", "immutable_template"))
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            for relative, setup, stem in guides:
                content = (docs / "deployment/stage-9-development" / relative).read_text()
                plan = content.index(f"bash scripts/deploy.sh {setup} --env test --plan-only")
                for path in (f"terraform/deployments/{setup}/terraform.test.tfvars",
                             f"ansible/group_vars/{stem}.test.yml"):
                    self.assertLess(content.index(path), plan)
                self.assertIn("override", content)

    def test_fresh_readme_uses_logging_and_keeps_environment_isolation_adjacent(self):
        self.generate()
        for tier in ("tier-0", "tier-1", "tier-2"):
            readme = (self.root / f"verify-{tier}/README.md").read_text()
            quick = readme.split("## Linux VM quick start", 1)[1].split("## Repository structure", 1)[0]
            self.assertIn("#environment-isolation", quick)
            self.assertNotIn("--env test --plan-only", quick)
            self.assertIn("Some setups require storage or TLS preparation", quick)
            if tier == "tier-0":
                self.assertIn("--setup syslog", quick)
                self.assertIn("deploy.sh syslog --plan-only", quick)

    def test_tls_exceptions_are_visible_before_linux_api_use(self):
        guide = (UPSTREAM / "docs/deployment/foundation/procedures/api-access.md").read_text()
        if any(re.search(r"insecure\s*=\s*true", source.read_text())
               for tier in range(3)
               for source in (UPSTREAM / f"tier-{tier}/terraform/deployments").glob("*/providers.tf")):
            self.assertIn("## TLS gate", guide)
            self.assertIn("not an accepted production default", guide)
            checklist = (UPSTREAM / ".ai/operator-walkthrough.md").read_text()
            self.assertIn("P1: Secure provider defaults", checklist)

    def test_bootstrap_tls_and_pki_cutover_are_reachable_in_generated_guides(self):
        self.generate()
        relative = "administration/compute/proxmox-tls.md"
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            guide = (docs / relative).read_text()
            for heading in ("## Step 1: Trust the bootstrap CA", "## Step 2: Adopt the platform PKI",
                            "## Step 3: Remove exceptions and verify callers", "## Renewal and recovery"):
                self.assertIn(heading, guide)
            self.assertIn("insecure = false", guide)
            self.assertIn("unset PROXMOX_VE_INSECURE PM_VE_INSECURE", guide)
            self.assertIn("SHA-256 fingerprint", guide)
            self.assertIn("untrusted CA and a wrong hostname are rejected", guide)
            self.assertIn("state as before", guide)
            entry = (docs / "deployment/foundation/procedures/api-access.md").read_text()
            self.assertIn(relative, entry)
            trust = (docs / "deployment/stage-3-trust/README.md").read_text()
            self.assertIn(relative + "#step-2-adopt-the-platform-pki", trust)
