"""Tier-specific code stays with its owner; only common mechanics are shared."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from payload import TIERS


class AnsibleOwnership(TierRepositoryTestCase):
    def test_identity_authority_is_a_vm_pair_and_broker_is_in_talos(self):
        self.generate()
        for repo in (UPSTREAM / "tier-0", self.root / "verify-tier-0"):
            groups = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
            self.assertEqual(set(groups["identity_primary"]["hosts"]), {"idm-1"})
            self.assertEqual(set(groups["identity_replicas"]["hosts"]), {"idm-2"})
            apps = repo / "clusters/tier0/applications"
            resources = yaml.safe_load((apps / "kustomization.yaml").read_text())["resources"]
            self.assertIn("keycloak", resources)
            self.assertNotIn("freeipa", resources)
            self.assertFalse((apps / "freeipa/kustomization.yaml").exists())
            self.assertTrue((apps / "keycloak/kustomization.yaml").is_file())

    def test_only_common_code_is_shared(self):
        self.generate()
        shared = self.root / "verify-shared"
        self.assertEqual({p.name for p in (shared / "ansible/roles").iterdir()}, {"baseline", "shared"})
        self.assertEqual({p.name for p in (shared / "ansible/playbooks").iterdir()},
                         {"control-node.yml", "site.yml"})
        self.assertEqual({p.name for p in (shared / "terraform/modules").iterdir()},
                         {"environment_guests", "vm", "lxc"})
        common = yaml.safe_load((shared / "ansible/playbooks/control-node.yml").read_text())[0]
        catalog = common["vars"]["control_node_base_collection_catalog"]
        expected_roles = {
            "tier-0": {"immutable_template", "proxmox_host", "proxmox_template_replace", "template_refresh", "vault"},
            "tier-1": {"cache_proxy", "edge_load_balancer", "gitlab_container", "hsm_proxy_ingress", "podman_runner"},
            "tier-2": set(),
        }
        for tier in TIERS:
            repo = self.root / f"verify-{tier}"
            roles = repo / "ansible/roles"
            self.assertEqual({p.name for p in roles.iterdir()} if roles.exists() else set(), expected_roles[tier])
            entry = repo / "ansible/playbooks/control-node.yml"
            profile = yaml.safe_load(entry.read_text())[0]
            self.assertEqual((entry.parent / profile["ansible.builtin.import_playbook"]).resolve(),
                             shared / "ansible/playbooks/control-node.yml")
            variables = profile["vars"]
            available = set(catalog) | set(variables.get("control_node_collection_catalog", {}))
            for setup in (repo / ".deployment-setups").read_text().splitlines():
                self.assertTrue((repo / f"ansible/playbooks/{setup}.yml").is_file())
                required = variables["control_node_setup_collection_names"][setup]
                self.assertTrue(set(required).issubset(available), (tier, setup))
        self.assertNotIn("freeipa", (shared / "ansible/requirements.yml").read_text())
        self.assertIn("freeipa", (self.root / "verify-tier-0/ansible/requirements.yml").read_text())

    def test_refresh_preserves_retired_shared_code_and_reports_upgrade(self):
        self.generate()
        retained = {
            "verify-shared/ansible/playbooks/foundation.yml": "# Local foundation changes\n",
            "verify-shared/scripts/proxmox-templates.sh": "# Previous publisher\n",
            "verify-tier-0/ansible/roles/vault/tasks/main.yml": "# Local role changes\n",
        }
        for relative, content in retained.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        result = self.generate("--refresh")
        self.assertIn("Legacy tier-owned automation preserved in shared", result.stdout)
        for relative, content in retained.items():
            self.assertEqual((self.root / relative).read_text(), content)
        self.assertTrue((self.root / "verify-tier-0/scripts/proxmox-templates.sh").is_file())

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Ansible on Linux/WSL")
    def test_native_import_resolves_tier_collection_requirements(self):
        self.generate()
        common_path = self.root / "verify-shared/ansible/playbooks/control-node.yml"
        common = yaml.safe_load(common_path.read_text())
        # Exercise the real import and filters without installing packages or contacting hosts.
        common[0]["tasks"] = common[0]["tasks"][1:3] + [{
            "name": "Check resolved collection names",
            "ansible.builtin.assert": {"that": [
                "control_node_required_collections | map(attribute='name') | sort == expected_collections | sort"
            ]},
        }]
        common_path.write_text(yaml.safe_dump(common))
        for tier, setup, expected in (
            ("tier-0", "foundation", ["community.general", "ansible.posix", "freeipa.ansible_freeipa"]),
            ("tier-0", "template-refresh", []),
            ("tier-1", "edge", ["community.general", "ansible.posix"]),
            ("tier-2", "lab", ["community.general", "ansible.posix"]),
        ):
            repo = self.root / f"verify-{tier}"
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", "ansible/playbooks/control-node.yml", "-e",
                 json.dumps({"control_node_setup": setup, "expected_collections": expected})],
                cwd=repo, env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, f"{tier}/{setup}\n{result.stdout}{result.stderr}")

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Ansible on Linux/WSL")
    def test_source_and_generated_playbooks_resolve_roles_without_running_hosts(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            for tier in TIERS:
                repo = collection / f"{prefix}{tier}"
                env = dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"))
                env.pop("ANSIBLE_ROLES_PATH", None)
                inventory = self.root / f"{prefix}{tier}-inventory.yml"
                shutil.copyfile(repo / "ansible/inventory/hosts.yml.example", inventory)
                for playbook in (repo / "ansible/playbooks").glob("*.yml"):
                    result = subprocess.run(
                        ["ansible-playbook", "--syntax-check", "-i", str(inventory), str(playbook)],
                        cwd=repo, env=env, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, f"{playbook}\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
