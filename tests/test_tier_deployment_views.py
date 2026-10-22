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
            ("stage-1-logging/README.md", 0, "tier-0", "syslog", ["foundation_logging"]),
            ("stage-2-trust/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-2-trust/step-1b-usb-hsm.md", 0, "tier-0", "hsm", ["hsm_gateways"]),
            ("stage-3-identity/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-3-identity/README.md", 1, "tier-0", "kubernetes", ["talos_control_plane"]),
            ("stage-4-secrets/step-1b-vault-vm.md", 0, "tier-0", "vault", ["vault"]),
            ("stage-6-observability/step-1b-dedicated-vms.md", 0, "tier-1", "observability",
             ["observability"]),
            ("stage-5-delivery/README.md", 0, "tier-1", "kubernetes", ["talos_control_plane"]),
            ("stage-5-delivery/step-1b-source-control-vm.md", 0, "tier-1", "development",
             ["development_platform"]),
            ("stage-5-delivery/step-1c-podman-runner.md", 0, "tier-1", "podman-runner", ["podman_runner"]),
            ("stage-5-delivery/step-1d-image-based-linux.md", 0, "tier-0", "immutable-template",
             ["immutable_template_builders"]),
            ("stage-5-delivery/procedures/edge-proxy.md", 0, "tier-2", "edge", ["edge_load_balancers"]),
            ("stage-7-workloads/README.md", 1, "tier-2", "kubernetes", ["talos_control_plane"]),
            ("stage-7-workloads/README.md", 1, "tier-2", "lab", ["lab"]),
            ("foundation/step-3b-outbound-cache.md", 0, "tier-2", "cache", ["cache"]),
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

    def test_unimplemented_services_are_not_drawn_as_installed_products(self):
        cases = [
            ("stage-3-identity/README.md", "tier-0/clusters/tier0/infrastructure/cni"),
            ("stage-3-identity/README.md", "tier-0/clusters/tier0/applications/keycloak"),
            ("stage-4-secrets/README.md", "tier-0/clusters/tier0/applications/vault"),
            ("stage-4-secrets/README.md", "tier-0/clusters/tier0/applications/netbox"),
            ("stage-4-secrets/README.md", "tier-0/clusters/tier0/applications/headlamp"),
            ("stage-5-delivery/README.md", "tier-1/clusters/tier1/platform/source-control"),
            ("stage-6-observability/README.md", "tier-1/clusters/tier1/platform/observability"),
            ("stage-7-workloads/README.md", "tier-2/clusters/tier2"),
        ]
        for relative, starter in cases:
            document = DOCS / "deployment" / relative
            self.assertIn("Project integration", "\n".join(FENCES.findall(document.read_text())))
            config = yaml.safe_load((UPSTREAM / starter / "kustomization.yaml").read_text())
            self.assertFalse(config.get("resources"), starter)


if __name__ == "__main__":
    unittest.main()
