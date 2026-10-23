"""Native configuration merging in generated clusters, with no remote resources."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform"),
                     "Requires Terraform on Linux/WSL")
class KubernetesConfiguration(TierRepositoryTestCase):
    def test_generated_roots_merge_native_proxy_dns_time_and_mirrors(self):
        self.generate()
        cache = self.root / "provider-cache"
        cache.mkdir()
        environment = dict(os.environ, TF_PLUGIN_CACHE_DIR=str(cache))
        for tier in ("tier-0", "tier-1", "tier-2"):
            with self.subTest(tier=tier):
                root = self.root / f"verify-{tier}/terraform/deployments/kubernetes"
                source = UPSTREAM / tier / "terraform/deployments/kubernetes/tests"
                shutil.copytree(source, root / "tests")
                init = subprocess.run(
                    ["terraform", f"-chdir={root}", "init", "-backend=false",
                     "-input=false", "-lockfile=readonly", "-no-color"],
                    env=environment, capture_output=True, text=True,
                )
                self.assertEqual(init.returncode, 0, init.stderr)
                result = subprocess.run(
                    ["terraform", f"-chdir={root}", "test", "-json", "-verbose"],
                    env=environment, capture_output=True, text=True,
                )
                events = [json.loads(line) for line in result.stdout.splitlines()]
                # Verbose state contains disposable keys; never print it on failure.
                diagnostics = [event["diagnostic"]["summary"] for event in events
                               if event["type"] == "diagnostic"]
                self.assertEqual(result.returncode, 0, diagnostics)
                states = [event["test_state"] for event in events
                          if event["type"] == "test_state" and
                          event.get("@testrun") == "native_restricted_network_configuration"]
                self.assertEqual(len(states), 1)
                resources = states[0]["root_module"]["resources"]
                configs = [resource for resource in resources
                           if resource["type"] == "talos_machine_configuration"]
                self.assertEqual(len(configs), 4)
                for resource in configs:
                    documents = list(yaml.safe_load_all(resource["values"]["machine_configuration"]))
                    machine = next(doc["machine"] for doc in documents if "machine" in doc)
                    self.assertEqual(machine["env"]["https_proxy"], "http://cache.example.com:3128")
                    self.assertIn("10.96.0.0/12", machine["env"]["no_proxy"])
                    self.assertEqual(machine["network"]["nameservers"], ["192.0.2.53"])
                    self.assertEqual(machine["time"]["servers"], ["192.0.2.123"])
                    self.assertEqual(machine["network"]["hostname"], resource["index"])
                    self.assertEqual(machine["install"]["disk"], "/dev/sda")
                    mirror = next(doc for doc in documents if doc.get("kind") == "RegistryMirrorConfig")
                    self.assertEqual(mirror["name"], "registry.k8s.io")
                    self.assertEqual(mirror["endpoints"], [{"url": "https://registry.example.com"}])
                    self.assertTrue(mirror["skipFallback"])


if __name__ == "__main__":
    unittest.main()
