"""The maintained VMID plan matches starter allocations and generated references."""

import json
import re
import xml.etree.ElementTree as ET

import hcl2
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class VmidConventions(TierRepositoryTestCase):
    def test_starter_ids_match_categories_without_cluster_wide_collisions(self):
        linux_categories = {
            0: {"foundation": 3, "hsm": 3, "vault": 3, "cluster-endpoint": 4,
                "syslog": 5, "infrastructure-runner": 6},
            1: {"development": 3, "development-data": 3, "intake": 3,
                "podman-runner": 6, "observability": 5},
            2: {"edge": 4, "cache": 4, "lab": 3},
        }
        # Classify individual guests when one setup includes another functional role.
        role_categories = {(0, "foundation", "mon-1"): 5, (0, "hsm", "cadm-1"): 6}
        allocated = {}

        def reserve(vmid, location):
            self.assertIsInstance(vmid, int, location)
            self.assertGreaterEqual(vmid, 100, location)
            self.assertNotIn(vmid, allocated, f"{location} collides with {allocated.get(vmid)}")
            allocated[vmid] = location

        # Keep manual recovery access separate from every managed guest and optional example.
        reserve(601, "tier-0/manual/boot-1")

        for tier in range(3):
            inventory_source = (UPSTREAM / f"tier-{tier}/ansible/inventory/hosts.yml.example").read_text()
            inventory = yaml.safe_load(inventory_source)
            groups = inventory["all"]["children"]
            inventory_hosts = {host for group in groups.values()
                               for host in ((group or {}).get("hosts") or {})}
            builders = {host for group in ("immutable_template_builders", "template_refresh_builders")
                        for host in (groups.get(group, {}).get("hosts") or {})}
            hypervisors = set((groups.get("hypervisors") or {}).get("hosts") or {})
            for name in inventory_hosts - builders - hypervisors:
                self.assertTrue(3 <= len(name) <= 8, f"tier-{tier}: {name}")
                self.assertRegex(name, r"^[a-z][a-z0-9-]*-[0-9]+$")
            control_planes = set(groups["talos_control_plane"]["hosts"] or {})
            workers = set(groups["talos_workers"]["hosts"] or {})
            for path in sorted((UPSTREAM / f"tier-{tier}/terraform/deployments").glob("*/terraform.tfvars.example")):
                with path.open(encoding="utf-8") as stream:
                    values = hcl2.load(stream)
                setup = path.parent.name
                source = path.read_text(encoding="utf-8")

                def check_allocation(name, vmid):
                    location = f"tier-{tier}/{setup}/{name}"
                    reserve(vmid, location)
                    if setup in ("template-refresh", "immutable-template"):
                        self.assertTrue(9000 <= vmid <= 9999, location)
                        return
                    if setup == "kubernetes":
                        self.assertIn(name, control_planes | workers, location)
                        category = 1 if name in control_planes else 2
                    else:
                        category = role_categories.get((tier, setup, name), linux_categories[tier][setup])
                    group = 3 if tier == 2 and setup in ("lab", "kubernetes") else tier
                    self.assertNotEqual((vmid // 100) % 10, 0, location)
                    start = group * 1000 + category * 100
                    stop = start + 100
                    self.assertTrue(start <= vmid < stop, f"{location}: {vmid} outside {start}-{stop-1}")

                guests = {**values.get("vm_instances", {}), **values.get("lxc_instances", {}),
                          **values.get("nodes", {})}
                for name, guest in guests.items():
                    name = name.strip('"')  # python-hcl2 may retain quoted object-key delimiters.
                    self.assertIn(name, inventory_hosts, f"tier-{tier}/{setup}/{name}")
                    check_allocation(name, guest["vm_id"])

                # Commented optional guest examples also reserve IDs, not source-template references.
                optional_name = None
                optional_count = 0
                for line in source.splitlines():
                    heading = re.match(r'^\s*#\s+(?:"([a-z][a-z0-9-]+)"|([a-z][a-z0-9-]+))\s*=\s*\{\s*$', line)
                    if heading:
                        optional_name = heading[1] or heading[2]
                    vmid = re.match(r"^\s*#\s+vm_id\s*=\s*(\d+)", line)
                    if vmid:
                        self.assertIsNotNone(optional_name, f"{path}: optional VMID needs a named guest")
                        self.assertRegex(inventory_source, rf"(?m)^\s*(?:#\s*)?{re.escape(optional_name)}:\s*",
                                         f"{path}: missing optional inventory host {optional_name}")
                        check_allocation(optional_name, int(vmid[1]))
                        optional_count += 1
                    if re.match(r"^\s*#\s*}\s*$", line):
                        optional_name = None
                self.assertEqual(len(guests) + optional_count,
                                 len(re.findall(r"\bvm_id\s*=\s*\d+", source)),
                                 f"{path}: every active and optional guest allocation must be checked")
        catalog = yaml.safe_load((UPSTREAM / "tier-0/templates/proxmox.yml.example").read_text())
        for key, image in catalog["templates"].items():
            self.assertTrue(9000 <= image["vm_id"] <= 9999, key)
            reserve(image["vm_id"], f"templates/{key}")
        refresh = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/template_refresh.yml.example").read_text())
        for replacement in refresh["template_refresh_replacements"]:
            self.assertIn(replacement["staged_vm_id"], allocated)
            self.assertIn(replacement["target_vm_id"], allocated)
            self.assertNotEqual(replacement["staged_vm_id"], replacement["target_vm_id"])

    def test_tier_0_starters_use_the_approved_service_reservations(self):
        # Optional examples reserve space too; new starters must not consume boot-1's 601.
        allocations = {
            "kubernetes": ({"k8ctl-1": 101, "k8ctl-2": 102, "k8ctl-3": 103}, set()),
            "foundation": ({"ca-1": 311}, {301, 302, 511}),
            "vault": ({"vault-1": 321}, set()),
            "hsm": ({"hsm-1": 331, "hsm-2": 332}, {333, 621}),
            "cluster-endpoint": ({"api-gw-1": 401, "api-gw-2": 402}, set()),
            "syslog": ({"log-1": 501}, {502, 503}),
            "infrastructure-runner": ({"iac-1": 611}, set()),
        }
        for setup, (expected_guests, expected_optional) in allocations.items():
            path = UPSTREAM / f"tier-0/terraform/deployments/{setup}/terraform.tfvars.example"
            source = path.read_text(encoding="utf-8")
            values = hcl2.loads(source)
            guests = values.get("nodes", values.get("vm_instances", {}))
            with self.subTest(setup=setup):
                self.assertEqual({name.strip('"'): guest["vm_id"] for name, guest in guests.items()},
                                 expected_guests)
                optional = {int(match[1]) for match in
                            re.finditer(r"(?m)^\s*#\s+vm_id\s*=\s*(\d+)", source)}
                self.assertEqual(optional, expected_optional)

    def test_quick_reference_is_managed_and_reachable_from_reader_and_code_paths(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        relative = "02-conventions/vmid-convention.md"
        image = "02-conventions/vmid-convention.svg"
        renderer = "08-reference/diagrams/render-vmid.cjs"
        reference = (manual / relative).read_text(encoding="utf-8")
        self.assertIn("AUTO-DOCS - DO NOT EDIT", reference)
        self.assertIn("**`2203` = Tier 2, Kubernetes worker, instance 03**", reference)
        self.assertIn("## Categories", reference)
        self.assertIn("<a id=\"categories-and-tier-0-offset\"></a>", reference)
        self.assertIn("<a id=\"categories-and-tier-0-kubernetes-exception\"></a>", reference)
        self.assertIn("100 × C + NN", reference)
        self.assertNotIn("100 × (C + 1) + NN", reference)
        for row in ("| `0` | Reserved | `000-099` |",
                    "| `1` | Kubernetes control plane | `100-199` |",
                    "| `2` | Kubernetes workers | `200-299` |",
                    "| `3` | Identity, trust and core services | `300-399` |",
                    "| `6` | Administration and automation | `600-699` |",
                    "| `601` | Reserved for the manually created Tier 0 bootstrap host, `boot-1` |"):
            self.assertIn(row, reference)
        self.assertIn("three security tiers", reference)
        self.assertIn("category describes the guest's primary function", reference)
        self.assertIn("Category numbers do not rank importance or prescribe deployment order", reference)
        self.assertIn("retain its local VMIDs and state", reference)
        self.assertEqual((manual / image).read_bytes(), (UPSTREAM / "docs" / image).read_bytes())
        manifest = json.loads((repo / ".generated-files.json").read_text())
        self.assertEqual((manual / renderer).read_bytes(), (UPSTREAM / "docs" / renderer).read_bytes())
        for asset in (relative, image, renderer):
            self.assertIn(f"docs/auto-docs/{asset}", manifest["files"])
        for name in ("README.md", "docs/04-development/code-layout.md", "docs/03-deployment/foundation/README.md"):
            self.assertIn("vmid-convention.md", (UPSTREAM / name).read_text(), name)
        for tier in range(3):
            self.assertIn(relative, (self.root / f"verify-tier-{tier}/README.md").read_text())
        worksheet = repo / "platform-standards.md"
        self.assertIn(relative, worksheet.read_text())
        worksheet.write_text("# Project allocations\nKeep the existing local VMIDs.\n")
        self.generate("--refresh")
        self.assertIn("Keep the existing local VMIDs", worksheet.read_text())

    def test_visual_reference_has_the_same_categories_and_readable_format(self):
        path = UPSTREAM / "docs/02-conventions/vmid-convention.svg"
        diagram = ET.fromstring(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(float(diagram.attrib["width"]) / float(diagram.attrib["height"]), 4 / 3)
        text = " ".join(diagram.itertext())
        for label in ("T C NN", "Tier (T)", "Category (C)", "Kubernetes control plane",
                      "Kubernetes workers", "Identity, trust and core services", "Network / Edge",
                      "Observability / protected logging", "Administration and automation", "Other / Reserved", "2203",
                      "control planes 100–199", "workers 200–299", "601"):
            self.assertIn(label, text)
        self.assertIn("Reserved", text)
        self.assertNotIn("100–149", text)
        self.assertNotIn("150–199", text)
        self.assertIn("aria-labelledby", diagram.attrib)

    def test_refresh_keeps_existing_ids_inventory_and_state(self):
        self.generate()
        tier = self.root / 'verify-tier-0'
        variables = tier / 'terraform/deployments/syslog/terraform.tfvars'
        variables.write_text('vm_instances = { "log-1" = { vm_id = 401 } }\n')
        inventory = tier / 'ansible/inventory/hosts.yml'
        inventory.write_text('all:\n  children:\n    foundation_logging:\n      hosts:\n        log-1: {}\n')
        state = tier / '.terraform/state/syslog/prod/terraform.tfstate'
        state.parent.mkdir(parents=True)
        state.write_text('{"fixture": "original VMID 401 state"}\n')
        retained = {path: path.read_bytes() for path in (variables, inventory, state)}
        self.generate('--refresh')
        for path, expected in retained.items():
            self.assertEqual(path.read_bytes(), expected)
        current = hcl2.loads(variables.with_name('terraform.tfvars.example').read_text())
        guests = {name.strip('"'): guest for name, guest in current['vm_instances'].items()}
        self.assertEqual(guests['log-1']['vm_id'], 501)


if __name__ == "__main__":
    import unittest
    unittest.main()
