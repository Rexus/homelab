"""Architecture abstractions and deployment pictures retain their source contracts."""

import re
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


DOCS = UPSTREAM / "docs"
FENCES = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
LINKS = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def inventory_groups(tier):
    path = UPSTREAM / tier / "ansible/inventory/hosts.yml.example"
    return yaml.safe_load(path.read_text())["all"]["children"]


def guest_names(groups):
    return {name for group in groups.values() for name in (group.get("hosts") or {})}


class DeploymentViews(unittest.TestCase):
    def test_architecture_diagrams_use_roles_not_site_guest_keys(self):
        names = set().union(*(guest_names(inventory_groups(f"tier-{tier}")) for tier in range(3)))
        for document in (DOCS / "architecture").rglob("*.md"):
            for code in FENCES.findall(document.read_text()):
                for name in names:
                    self.assertNotRegex(code, rf"(?<![\w-]){re.escape(name)}(?![\w-])", str(document))

    def test_every_deployment_diagram_declares_scope_and_traceable_links(self):
        checked = 0
        for document in (DOCS / "deployment").rglob("*.md"):
            content = document.read_text()
            for fence in FENCES.finditer(content):
                caption = content[fence.end():].lstrip().split("\n\n", 1)[0]
                self.assertRegex(caption, r"^\*\*(?:IaC|Manual|Integration|Workflow):\*\*", str(document))
                paths = LINKS.findall(caption)
                self.assertTrue(paths, str(document))
                for path in paths:
                    if not path.startswith(("https://", "http://", "#")):
                        self.assertTrue((document.parent / path.split("#", 1)[0]).exists(), path)
                if caption.startswith(("**IaC:**", "**Integration:**")):
                    self.assertTrue(any(re.search(r"/(?:tier-[012]|shared)/", path) for path in paths),
                                    str(document))
                checked += 1
        self.assertGreaterEqual(checked, 30)

    def test_deployment_resource_views_account_for_the_selected_starter_hosts(self):
        # Each row expands an actual input/inventory selection, not a second guest catalogue.
        cases = [
            ("stage-2-logging/README.md", 0, "tier-0", "syslog", ["foundation_logging"]),
            ("stage-3-trust/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-3-trust/step-1b-usb-hsm.md", 0, "tier-0", "hsm", ["hsm_gateways"]),
            ("stage-5-identity/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-4-kubernetes/README.md", 0, "tier-0", "kubernetes", ["talos_control_plane"]),
            ("stage-6-secrets/step-1b-vault-vm.md", 0, "tier-0", "vault", ["vault"]),
            ("stage-8-observability/step-1b-dedicated-vms.md", 0, "tier-1", "observability",
             ["observability"]),
            ("stage-7-delivery/README.md", 0, "tier-1", "kubernetes", ["talos_control_plane"]),
            ("stage-9-development/step-1b-source-control-vm.md", 0, "tier-1", "development",
             ["development_platform"]),
            ("stage-9-development/step-2b-podman-runner.md", 0, "tier-1", "podman-runner", ["podman_runner"]),
            ("stage-9-development/step-2c-image-based-linux.md", 0, "tier-0", "immutable-template",
             ["immutable_template_builders"]),
            ("stage-7-delivery/procedures/edge-proxy.md", 0, "tier-2", "edge", ["edge_load_balancers"]),
            ("stage-10-lab-environments/README.md", 1, "tier-2", "kubernetes", ["talos_control_plane"]),
            ("stage-10-lab-environments/README.md", 1, "tier-2", "lab", ["lab"]),
            ("stage-10-lab-environments/README.md", 1, "tier-0", "infrastructure-runner", ["infrastructure_runner"]),
            ("stage-1-software-intake/README.md", 0, "tier-2", "cache", ["cache"]),
        ]
        selections = {}
        for relative, index, tier, setup, selected in cases:
            with self.subTest(document=relative, setup=setup):
                code = FENCES.findall((DOCS / "deployment" / relative).read_text())[index]
                groups = inventory_groups(tier)
                hosts = guest_names({name: groups[name] for name in selected})
                selections.setdefault((relative, index), set()).update(hosts)
                inputs = (UPSTREAM / tier / f"terraform/deployments/{setup}/terraform.tfvars.example").read_text()
                self.assertTrue(hosts)
                for name in hosts:
                    self.assertRegex(inputs, rf'(?m)^\s*(?:"{re.escape(name)}"|{re.escape(name)})\s*=\s*\{{')
                    self.assertEqual(len(re.findall(rf"(?<![\w-]){re.escape(name)}(?![\w-])", code)), 1,
                                     f"{relative}: one depicted instance per guest key: {name}")
                self.assertIn("Proxmox", code)
                self.assertIn(f"Tier {tier[-1]}", code)
        all_hosts = set().union(*(guest_names(inventory_groups(f"tier-{tier}")) for tier in range(3)))
        for (relative, index), selected in selections.items():
            code = FENCES.findall((DOCS / "deployment" / relative).read_text())[index]
            drawn = {name for name in all_hosts if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", code)}
            self.assertEqual(drawn, selected, relative)

    def test_application_installers_are_not_confused_with_owned_gitops_starters(self):
        cases = [
            ("stage-4-kubernetes", "tier-0", "cluster-platform", "infrastructure/cni"),
            ("stage-5-identity", "tier-0", "control-applications", "applications/keycloak"),
            ("stage-6-secrets", "tier-0", "control-applications", "applications/vault"),
            ("stage-7-delivery", "tier-1", "delivery-platform", "platform/artifact-registry"),
            ("stage-8-observability", "tier-1", "observability-platform", "platform/observability"),
            ("stage-9-development", "tier-1", "development-platform", "platform/source-control"),
            ("stage-10-lab-environments", "tier-2", "lab-environment", ""),
        ]
        for stage, tier, recipe, relative in cases:
            stage_docs = "\n".join(path.read_text() for path in (DOCS / "deployment" / stage).rglob('*.md'))
            self.assertIn(f"ansible/playbooks/deployment/{recipe}.yml", stage_docs, stage)
            self.assertTrue((UPSTREAM / tier / f"ansible/playbooks/deployment/{recipe}.yml").is_file())
            starter = UPSTREAM / tier / f"clusters/tier{tier[-1]}" / relative
            config = yaml.safe_load((starter / "kustomization.yaml").read_text())
            self.assertFalse(config.get("resources"), starter)

    def test_cluster_logging_picture_matches_tier_owned_node_streams(self):
        inputs = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/cluster_security_logging.yml.example").read_text())
        document = (DOCS / "deployment/stage-4-kubernetes/README.md").read_text()
        picture = FENCES.findall(document)[2]
        nodes = inputs["cluster_security_logging_nodes"]
        self.assertEqual({node["name"] for node in nodes},
                         set(inventory_groups("tier-0")["talos_control_plane"]["hosts"]))
        for node in nodes:
            self.assertEqual(picture.count(f'security-log-{node["stream"]}'), 1)
        for expected in ("Existing log-1", "not replicated", "mTLS"):
            self.assertIn(expected, picture)

    def test_observability_pictures_account_for_selected_native_releases_and_counts(self):
        from test_tier_observability_platform import ROLE, platform_inputs, render_template
        inputs = platform_inputs()
        releases = yaml.safe_load(render_template(ROLE, 'releases.yml.j2', inputs))
        document = (DOCS / 'deployment/stage-8-observability/README.md').read_text()
        pictures = FENCES.findall(document)
        for release in releases:
            self.assertIn(release['name'], pictures[0], release['name'])
        expected_counts = {
            'otel-gateway': ('observability_gateway_replicas', 'replicas'),
            'data-prepper': ('observability_prepper_replicas', 'replicas'),
            'opensearch': ('observability_search_replicas', 'members'),
        }
        for name, (key, unit) in expected_counts.items():
            self.assertIn(f'{name} / {inputs[key]} {unit}', pictures[1])
        self.assertIn('Allowlisted metric bridge', pictures[2])


if __name__ == "__main__":
    unittest.main()
