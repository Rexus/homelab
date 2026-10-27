"""Offline release contracts: locks, runtime payloads, CI isolation and guest IP allocations."""

from collections import defaultdict
from copy import deepcopy
from ipaddress import ip_address
import re
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


TIERS = ("tier-0", "tier-1", "tier-2")
ROLE_SUFFIXES = {".py", ".hcl", ".sh", ".js", ".cnf", ".conf", ".yml", ".yaml", ".j2"}


class ReleaseInputs(unittest.TestCase):
    def test_every_terraform_deployment_root_has_a_nonempty_provider_lock(self):
        roots = sorted(path.parent for tier in TIERS for path in
                       (UPSTREAM / tier / "terraform/deployments").glob("*/main.tf"))
        self.assertTrue(roots, "No deployment roots were discovered")
        missing = [root.relative_to(UPSTREAM).as_posix() for root in roots
                   if not (root / ".terraform.lock.hcl").is_file()]
        self.assertFalse(missing, "Missing provider locks:\n" + "\n".join(missing))
        for root in roots:
            with self.subTest(root=root.relative_to(UPSTREAM).as_posix()):
                self.assertTrue((root / ".terraform.lock.hcl").read_text(encoding="utf-8").strip())

    def test_static_example_addresses_have_one_logical_guest_owner(self):
        owners = defaultdict(lambda: defaultdict(list))
        for tier in TIERS:
            for path in sorted((UPSTREAM / tier / "ansible/group_vars").glob("*.yml.example")):
                settings = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                for host, value in settings.get("platform_host_ips", {}).items():
                    if not isinstance(value, str):
                        continue
                    try:
                        address = str(ip_address(value))
                    except ValueError:
                        continue
                    owners[address][(tier, host)].append(path.relative_to(UPSTREAM).as_posix())
        self.assertTrue(owners, "No static example guest addresses were discovered")
        collisions = []
        for address, allocations in sorted(owners.items()):
            if len(allocations) > 1:
                details = [f"{tier}/{host} ({', '.join(paths)})"
                           for (tier, host), paths in sorted(allocations.items())]
                collisions.append(f"{address}: " + "; ".join(details))
        self.assertFalse(collisions, "Unrelated example guests share addresses:\n" + "\n".join(collisions))


class ScannerIsolation(unittest.TestCase):
    @staticmethod
    def effective_job(pipeline, name):
        # Model only documented boolean default/variable inheritance, not the full CI compiler.
        job = deepcopy(pipeline[name])
        inherit = job.get("inherit", {})
        if inherit.get("default", True):
            for keyword, value in pipeline.get("default", {}).items():
                job.setdefault(keyword, deepcopy(value))
        variables = deepcopy(pipeline.get("variables", {})) if inherit.get("variables", True) else {}
        variables.update(job.get("variables", {}))
        job["variables"] = variables
        return job

    def test_scanner_explicitly_disables_both_inheritance_channels(self):
        job = yaml.safe_load((UPSTREAM / "shared/ci/gitlab-secrets.yml.example").read_text())["secret-scan"]
        self.assertEqual(job.get("inherit"), {"default": False, "variables": False})

    def test_scanner_stays_isolated_when_included_with_tier_zero_defaults(self):
        scanner = yaml.safe_load((UPSTREAM / "shared/ci/gitlab-secrets.yml.example").read_text())
        for starter in ("gitlab-iac.yml.example", "gitlab-templates.yml.example"):
            with self.subTest(starter=starter):
                pipeline = yaml.safe_load((UPSTREAM / "tier-0/ci" / starter).read_text())
                self.assertTrue(pipeline["default"]["before_script"])
                self.assertTrue(pipeline["default"]["tags"][0].startswith("tier0-"))
                pipeline["default"].setdefault("id_tokens", {"VAULT_ID_TOKEN": {"aud": "$VAULT_ADDR"}})
                pipeline["default"]["artifacts"] = {"paths": ["terraform.tfstate"]}
                pipeline["variables"] = {"VAULT_ADDR": "https://vault.test", "GIT_DEPTH": "1",
                                         "IAC_TRUST_CI_CONTROL_PLANE": "true"}
                pipeline.update(deepcopy(scanner))
                pipeline["fixture-control"] = {"script": ["true"]}

                control = self.effective_job(pipeline, "fixture-control")
                self.assertEqual(control["id_tokens"], pipeline["default"]["id_tokens"])
                self.assertEqual(control["before_script"], pipeline["default"]["before_script"])
                self.assertEqual(control["variables"], pipeline["variables"])
                self.assertEqual(control["tags"], pipeline["default"]["tags"])

                job = self.effective_job(pipeline, "secret-scan")
                self.assertEqual(job["variables"], {"GIT_DEPTH": "0"})
                self.assertEqual(job["tags"], ["tier1-build"])
                self.assertEqual(job["image"], scanner["secret-scan"]["image"])
                self.assertFalse(job["allow_failure"])
                for keyword in ("id_tokens", "before_script", "artifacts", "secrets", "extends"):
                    self.assertNotIn(keyword, job)


class ReleasePayload(TierRepositoryTestCase):
    def test_delivery_navigation_points_to_the_supplied_native_reference(self):
        self.generate("--repo", "architecture")
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            for relative in ("README.md", "procedures/platform-cluster.md"):
                with self.subTest(docs=str(docs), relative=relative):
                    content = (docs / "deployment/stage-7-delivery" / relative).read_text()
                    self.assertIn("step-2b-spinnaker.md#installation-decision", content)
                    self.assertNotRegex(" ".join(content.split()), r"Spinnaker (still )?requires a complete")

    def test_generation_preserves_all_tier_role_runtime_files_and_provider_locks(self):
        self.generate()
        role_programs = []
        provider_locks = []
        for tier in TIERS:
            source = UPSTREAM / tier
            generated = self.root / f"verify-{tier}"
            role_root = source / "ansible/roles"
            programs = []
            for path in role_root.rglob("*"):
                if not path.is_file():
                    continue
                # Role-local tests and hidden source directories are never deployment payloads.
                if any(part.startswith(".") or part == "tests"
                       for part in path.relative_to(role_root).parts[:-1]):
                    self.assertFalse((generated / path.relative_to(source)).exists())
                    continue
                if path.suffix in ROLE_SUFFIXES or path.name.startswith(("LICENSE", "NOTICE")):
                    programs.append(path)
            locks = list((source / "terraform/deployments").glob("*/.terraform.lock.hcl"))
            role_programs.extend(programs)
            provider_locks.extend(locks)
            for path in sorted(programs + locks):
                relative = path.relative_to(source)
                with self.subTest(path=f"{tier}/{relative.as_posix()}"):
                    target = generated / relative
                    self.assertTrue(target.is_file(), f"Generator omitted {tier}/{relative.as_posix()}")
                    expected = re.sub(r"(?<=\.\./)shared(?=[/\"'\s]|$)", "verify-shared",
                                      path.read_text(encoding="utf-8"))
                    expected = expected.replace("check out shared beside", "check out verify-shared beside")
                    self.assertEqual(target.read_text(encoding="utf-8"), expected)
            # Runtime-file support belongs to roles, never to operational inventory or host vars.
            self.assertFalse((generated / "ansible/inventory/hosts.yml").exists())
            for directory in ("inventory", "host_vars", "group_vars"):
                for suffix in (".py", ".hcl", ".sh", ".js", ".cnf", ".conf"):
                    self.assertEqual(list((generated / "ansible" / directory).rglob(f"*{suffix}")), [])
        self.assertTrue(role_programs, "No tier-owned runtime files were discovered")
        self.assertTrue(provider_locks, "No provider locks were discovered")


if __name__ == "__main__":
    unittest.main()
