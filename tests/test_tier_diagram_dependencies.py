"""Declared dependency placement and compact peers; rendering is checked separately."""

import unittest

from test_tier_diagrams import diagrams
from tier_repo_test_support import UPSTREAM


DOCS = UPSTREAM / "docs"


class DiagramDependencies(unittest.TestCase):
    def test_authority_maps_place_foundational_peers_to_the_right(self):
        runtime = diagrams(DOCS / "architecture/compute/runtime.md")[0]
        self.assertLess(runtime.index('Cluster["'), runtime.index('Dedicated["'))
        delivery = diagrams(DOCS / "architecture/delivery/README.md")[0]
        for peers in (("Build", "Delivery", "Source"), ("Bootstrap", "Flux", "Gate")):
            positions = [delivery.index(f'{name}["') for name in peers]
            self.assertEqual(positions, sorted(positions))

    def test_controller_inputs_and_scoped_changes_keep_their_real_direction(self):
        code = diagrams(DOCS / "architecture/delivery/controllers.md")[0]
        for tier in (1, 0):
            self.assertRegex(code, rf'subgraph T{tier}\["[^\n]+\n    direction RL')
        for edge in ("Release -->|Approved inputs| D", "D -->|Scoped changes| Platform",
                     "Approved -->|Approved inputs| F", "F -->|Scoped changes| Control"):
            self.assertIn(edge, code)
        self.assertIn("T2 ~~~ T1 ~~~ T0", code)

    def test_cluster_foundation_and_runner_providers_keep_declared_order(self):
        runtime = diagrams(DOCS / "deployment/stage-3-identity/README.md")[2]
        self.assertIn("Base ~~~ Flux ~~~ Network", runtime)
        runner = diagrams(DOCS / "deployment/stage-5-delivery/step-1c-podman-runner.md")[0]
        self.assertIn('subgraph T1["Tier 1 / general build execution"]\n    direction LR', runner)
        self.assertIn("Runner -->|Scoped jobs / artifact publication| Existing", runner)

    def test_control_plane_and_edge_peers_stack_without_changing_instance_counts(self):
        cases = [
            ("stage-3-identity/README.md", 1, "PVE", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-5-delivery/README.md", 0, "Nodes", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-5-delivery/procedures/edge-proxy.md", 0, "PVE", "A ~~~ B ~~~ C"),
            ("stage-7-workloads/public-https.md", 0, "PVE", "A ~~~ B ~~~ C"),
        ]
        for path, index, group, peers in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / "deployment" / path)[index]
                self.assertRegex(code, rf'subgraph {group}\["[^\n]+\n\s+direction TB')
                self.assertIn(peers, code)

    def test_platform_starters_are_inside_the_runtime_they_extend(self):
        code = diagrams(DOCS / "deployment/stage-5-delivery/README.md")[0]
        self.assertRegex(code, r'subgraph Platform\["[^\n]+\n\s+direction LR\n\s+subgraph Apps\[')
        self.assertIn("Apps ~~~ Nodes", code)
        self.assertIn("Delivery ~~~ Git", code)

    def test_execution_is_right_of_the_cluster_and_bootstrap_stays_left(self):
        code = diagrams(DOCS / "deployment/stage-5-delivery/README.md")[1]
        self.assertLess(code.index('subgraph Entry['), code.index('subgraph ControlArea['))
        self.assertIn('subgraph ControlArea[" "]\n        direction LR', code)
        self.assertIn("Cluster ~~~ Management", code)
        self.assertIn('subgraph Integration["Project integration / not installed"]\n          direction TB', code)
        self.assertIn("Runner <--> State", code)
        self.assertIn("Runner -->|Approved lifecycle| PVE", code)

    def test_vault_operator_is_external_and_recovery_is_below_connected_runtime(self):
        code = diagrams(DOCS / "deployment/stage-4-secrets/step-1b-vault-vm.md")[0]
        self.assertIn("flowchart LR", code)
        self.assertLess(code.index('Operator["'), code.index('subgraph T0['))
        self.assertIn('subgraph T0["Tier 0 / Control"]\n    direction BT', code)
        self.assertLess(code.index('Recovery["'), code.index('subgraph PVE['))
        self.assertIn("Recovery -. Manual unseal / recovery transfer .-> PVE", code)
        self.assertIn("Operator -->|Verified TLS / authorized bootstrap| T0", code)

    def test_long_workflows_wrap_rows_without_changing_chronology(self):
        cases = [
            ("README.md", ("Base", "Logs", "Runtime", "Trust", "Control", "Delivery",
                           "Workloads", "Visibility"),
             ("Base", "Logs", "Trust", "Runtime", "Control", "Delivery", "Visibility", "Workloads")),
            ("stage-7-workloads/README.md", ("User", "Request", "Gate", "CI"),
             ("User", "Request", "CI", "Gate")),
        ]
        for path, placement, sequence in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / "deployment" / path)[0]
                self.assertIn("block-beta\n  columns 5", code)
                positions = [code.index(f'{name}["') for name in placement]
                self.assertEqual(positions, sorted(positions))
                for first, second in zip(sequence, sequence[1:]):
                    self.assertIn(f"{first} --> {second}", code)


if __name__ == "__main__":
    unittest.main()
