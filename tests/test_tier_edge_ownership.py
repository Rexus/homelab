"""Public edge ownership stays separate from build supply and privileged access."""

import json

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class EdgeOwnership(TierRepositoryTestCase):
    def test_source_and_generated_edge_inputs_belong_to_tier_two(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            tier_one = collection / f"{prefix}tier-1"
            tier_two = collection / f"{prefix}tier-2"
            first = set((tier_one / ".deployment-setups").read_text().splitlines())
            second = set((tier_two / ".deployment-setups").read_text().splitlines())
            self.assertTrue({"edge", "cache"}.isdisjoint(first))
            self.assertTrue({"edge", "cache"}.issubset(second))
            one_groups = yaml.safe_load((tier_one / "ansible/inventory/hosts.yml.example").read_text())
            two_groups = yaml.safe_load((tier_two / "ansible/inventory/hosts.yml.example").read_text())
            one_groups = one_groups["all"]["children"]
            two_groups = two_groups["all"]["children"]
            self.assertNotIn("edge_load_balancers", one_groups)
            self.assertNotIn("cache", one_groups)
            self.assertEqual(set(two_groups["edge_load_balancers"]["hosts"]),
                             {"edge-lb-1", "edge-lb-2", "edge-lb-3"})
            self.assertEqual(set(two_groups["cache"]["hosts"]), {"cache-1", "cache-2"})
            for setup in ("edge", "cache"):
                self.assertFalse((tier_one / f"terraform/deployments/{setup}").exists())
                self.assertTrue((tier_two / f"terraform/deployments/{setup}/main.tf").is_file())
                self.assertTrue((tier_two / f"ansible/playbooks/maintenance/{setup}.yml").is_file())
            self.assertIn("  delivery_edge = {", (tier_one / "terraform/common.tfvars.example").read_text())
            self.assertNotIn("  external_edge = {", (tier_one / "terraform/common.tfvars.example").read_text())
            self.assertIn("  external_edge = {", (tier_two / "terraform/common.tfvars.example").read_text())
            runner = (tier_one / "terraform/deployments/podman-runner/terraform.tfvars.example").read_text()
            self.assertIn('network_zone_key = "delivery_edge"', runner)
            self.assertNotIn('network_zone_key = "external_edge"', runner)
            runner_vars = yaml.safe_load((tier_one / "ansible/group_vars/podman_runner.yml.example").read_text())
            self.assertEqual(runner_vars["platform_host_ips"]["runner-1"], "10.30.31.30")

    def test_signing_frontend_is_cohosted_and_stays_in_tier_zero(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            tier_zero = collection / f"{prefix}tier-0"
            inventory = yaml.safe_load((tier_zero / "ansible/inventory/hosts.yml.example").read_text())
            self.assertNotIn("cryptography_load_balancers", inventory["all"]["children"])
            ingress = yaml.safe_load((tier_zero / "ansible/playbooks/ingress.yml").read_text())
            self.assertEqual(ingress[0]["hosts"], "hsm_gateways")
            self.assertEqual(ingress[0]["roles"][0]["role"], "hsm_proxy_ingress")
            self.assertIn("hsm_proxy_ingress_enabled", ingress[0]["roles"][0]["when"])
            self.assertTrue((tier_zero / "ansible/roles/hsm_proxy_ingress/tasks/main.yml").is_file())
            for tier in ("tier-1", "tier-2"):
                repo = collection / f"{prefix}{tier}"
                self.assertFalse((repo / "ansible/playbooks/ingress.yml").exists())
                self.assertFalse((repo / "ansible/roles/hsm_proxy_ingress").exists())
            public = (collection / f"{prefix}tier-2/ansible/group_vars/edge.yml.example").read_text()
            self.assertNotIn("vault_https", public)
            self.assertNotIn("internal_mgmt", public)

    def test_refresh_reports_migration_without_transferring_live_inputs_or_state(self):
        self.generate()
        preserved = {
            "verify-tier-1/.deployment-setups": "edge\ncache\ndevelopment\n",
            "verify-tier-2/.deployment-setups": "lab\n",
            "verify-tier-1/terraform/deployments/edge/main.tf": "# Local legacy edge resources\n",
            "verify-tier-1/terraform/deployments/cache/main.tf": "# Local legacy cache resources\n",
            "verify-tier-1/ansible/playbooks/ingress.yml": "# Previous local signing integration\n",
            "verify-tier-1/ansible/inventory/hosts.yml": "all: {hosts: {edge-lb-1: {}}}\n",
            "verify-tier-1/ansible/group_vars/edge.yml": "platform_host_ips: {edge-lb-1: 192.0.2.10}\n",
            "verify-tier-1/.terraform/state/edge/prod/terraform.tfstate": '{"lineage":"edge-old"}\n',
            "verify-tier-1/.terraform/state/cache/prod/terraform.tfstate": '{"lineage":"cache-old"}\n',
            "verify-tier-2/ansible/inventory/hosts.yml": "all: {hosts: {lab-local: {}}}\n",
            "verify-tier-2/terraform/common.tfvars": "# Local network choices\n",
            "verify-tier-2/docs/architecture/README.md": "# Local selected design\n",
            "verify-tier-0/ansible/playbooks/ingress.yml": "# Local previous private frontend integration\n",
        }
        for relative, content in preserved.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Model a previous collection without the newly introduced Tier 2 root.
        repo = self.root / "verify-tier-2"
        new_root = repo / "terraform/deployments/edge/main.tf"
        new_root.unlink()
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"].pop("terraform/deployments/edge/main.tf")
        manifest_path.write_text(json.dumps(manifest))
        dry_run = self.generate("--refresh", "--dry-run")
        self.assertIn("Edge ownership upgrade", dry_run.stdout)
        self.assertFalse(new_root.exists())
        refreshed = self.generate("--refresh")
        self.assertIn("Edge ownership upgrade", refreshed.stdout)
        self.assertTrue(new_root.is_file())
        for relative, content in preserved.items():
            self.assertEqual((self.root / relative).read_text(), content, relative)
        self.assertFalse((repo / ".terraform/state/edge").exists())
        self.assertFalse((repo / ".terraform/state/cache").exists())


if __name__ == "__main__":
    import unittest
    unittest.main()
