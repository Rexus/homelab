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
        runtime = diagrams(DOCS / "deployment/stage-4-kubernetes/README.md")[1]
        self.assertIn("Apps ~~~ Reconcile ~~~ NodeServices", runtime)
        self.assertIn('subgraph Existing["Independent existing prerequisites"]', runtime)
        runner = diagrams(DOCS / "deployment/stage-9-development/step-2b-podman-runner.md")[0]
        self.assertIn('subgraph T1["Tier 1 / general build execution"]\n    direction LR', runner)
        self.assertIn("Runner -->|Scoped jobs / artifact publication| Existing", runner)

    def test_control_plane_and_edge_peers_stack_without_changing_instance_counts(self):
        cases = [
            ("stage-4-kubernetes/README.md", 0, "PVE", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-7-delivery/README.md", 0, "Nodes", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-7-delivery/procedures/edge-proxy.md", 0, "PVE", "A ~~~ B ~~~ C"),
            ("stage-10-lab-environments/public-https.md", 0, "PVE", "A ~~~ B ~~~ C"),
        ]
        for path, index, group, peers in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / "deployment" / path)[index]
                self.assertRegex(code, rf'subgraph {group}\["[^\n]+\n\s+direction TB')
                self.assertIn(peers, code)

    def test_controller_option_and_nodes_are_inside_the_runtime_they_extend(self):
        code = diagrams(DOCS / "deployment/stage-7-delivery/README.md")[0]
        self.assertRegex(code, r'subgraph PVE\["[^\n]+\n\s+direction LR\n\s+subgraph Added\[')
        self.assertIn("Added ~~~ Nodes", code)
        self.assertIn("A: Argo CD", code)
        self.assertIn("or B: Spinnaker", code)

    def test_execution_is_right_of_the_cluster_and_recovery_stays_outside_hosting(self):
        code = diagrams(DOCS / "deployment/stage-9-development/README.md")[-1]
        self.assertLess(code.index('subgraph T1['), code.index('subgraph T0['))
        self.assertLess(code.index('subgraph Execution['), code.index('subgraph Services['))
        self.assertIn("T1 ~~~ T0 ~~~ Recovery", code)
        self.assertIn("Runner <--> State", code)
        self.assertIn("Git -->|Accepted project jobs| T0", code)
        self.assertIn("iac-1 / gitlab-runner", code)

    def test_vault_operator_is_external_and_recovery_is_below_connected_runtime(self):
        code = diagrams(DOCS / "deployment/stage-6-secrets/step-1b-vault-vm.md")[0]
        self.assertIn("flowchart LR", code)
        self.assertLess(code.index('Operator["'), code.index('subgraph T0['))
        self.assertIn('subgraph T0["Tier 0 / Control"]\n    direction BT', code)
        self.assertLess(code.index('Recovery["'), code.index('subgraph PVE['))
        self.assertIn("Recovery -. Manual unseal / recovery transfer .-> PVE", code)
        self.assertIn("Operator -->|Verified TLS / authorized bootstrap| T0", code)

    def test_long_workflows_wrap_rows_without_changing_chronology(self):
        cases = [
            ("README.md", ("Base", "Intake", "Logs", "Identity", "Runtime", "Trust", "Control",
                           "Delivery", "Visibility", "Workloads", "Development"),
             ("Base", "Intake", "Logs", "Trust", "Runtime", "Identity", "Control", "Delivery", "Visibility", "Development", "Workloads")),
            ("stage-10-lab-environments/README.md", ("User", "Request", "Gate", "CI"),
             ("User", "Request", "CI", "Gate")),
        ]
        for path, placement, sequence in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / "deployment" / path)[0]
                self.assertIn(f"block-beta\n  columns {3 if path == 'README.md' else 5}", code)
                positions = [code.index(f'{name}["') for name in placement]
                self.assertEqual(positions, sorted(positions))
                for first, second in zip(sequence, sequence[1:]):
                    self.assertIn(f"{first} --> {second}", code)


if __name__ == "__main__":
    unittest.main()
