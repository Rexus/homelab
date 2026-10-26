"""Native configuration merging in generated clusters, with no remote resources."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


TALOSCTL = os.environ.get("HOMELAB_TALOSCTL") or shutil.which("talosctl")


@unittest.skipUnless(os.name != "nt" and shutil.which("terraform") and TALOSCTL,
                     "Requires Terraform and Talos 1.13 (HOMELAB_TALOSCTL) on Linux/WSL")
class KubernetesConfiguration(TierRepositoryTestCase):
    def test_generated_roots_merge_native_proxy_dns_time_and_mirrors(self):
        self.generate()
        cache = os.environ.get("TF_PLUGIN_CACHE_DIR", str(self.root / "provider-cache"))
        os.makedirs(cache, exist_ok=True)
        environment = dict(os.environ, TF_PLUGIN_CACHE_DIR=str(cache))
        version = subprocess.run([TALOSCTL, "version", "--client", "--short"],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("Talos v1.13.", version.stdout)
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
                outputs = states[0]["outputs"]["machine_configurations"]["value"]
                self.assertEqual(set(outputs), {resource["index"] for resource in configs})
                for resource in configs:
                    # Validate the real provider's complete output, never a hand-built substitute.
                    configuration = outputs[resource["index"]]
                    self.assertTrue(configuration == resource["values"]["machine_configuration"],
                                    "Published output must match the real provider configuration")
                    config_file = root / f"{resource['index']}.native-validation.yaml"
                    config_file.touch(mode=0o600)
                    config_file.write_text(configuration)
                    validation = subprocess.run(
                        [TALOSCTL, "validate", "--config", str(config_file), "--mode", "metal", "--strict"],
                        capture_output=True, text=True, timeout=60,
                    )
                    self.assertEqual(validation.returncode, 0,
                                     f"{tier}/{resource['index']}: native Talos validation failed; "
                                     "output withheld because configurations contain disposable keys")
                    documents = list(yaml.safe_load_all(configuration))
                    machine = next(doc["machine"] for doc in documents if "machine" in doc)
                    self.assertEqual(machine["env"]["https_proxy"], "http://cache.example.com:3128")
                    self.assertIn("10.96.0.0/12", machine["env"]["no_proxy"])
                    self.assertEqual(machine["network"]["nameservers"], ["192.0.2.53"])
                    self.assertEqual(machine["time"]["servers"], ["192.0.2.123"])
                    self.assertNotIn("hostname", machine["network"])
                    hostnames = [doc for doc in documents if doc.get("kind") == "HostnameConfig"]
                    self.assertEqual(len(hostnames), 1)
                    self.assertEqual(hostnames[0]["hostname"], resource["index"])
                    self.assertEqual(hostnames[0].get("auto", "off"), "off")
                    self.assertEqual(machine["install"]["disk"], "/dev/sda")
                    mirror = next(doc for doc in documents if doc.get("kind") == "RegistryMirrorConfig")
                    self.assertEqual(mirror["name"], "registry.k8s.io")
                    self.assertEqual(mirror["endpoints"], [{"url": "https://registry.example.com"}])
                    self.assertTrue(mirror["skipFallback"])


if __name__ == "__main__":
    unittest.main()
