"""Downstream guide commands must retain the manual cluster's credential export."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest


UPSTREAM = Path(__file__).resolve().parents[1]
GUIDES = (
    "stage-4-kubernetes/procedures/basic-platform.md",
    "stage-4-kubernetes/procedures/flux-sops.md",
    "stage-5-identity/procedures/keycloak.md",
)


@unittest.skipUnless(shutil.which("bash"), "Requires Bash to exercise the documented exports")
class ManualClusterHandoff(unittest.TestCase):
    def exports(self, guide):
        text = (UPSTREAM / "docs/deployment" / guide).read_text(encoding="utf-8")
        blocks = re.findall(r"(?ms)^```bash\n(.*?)^```", text)
        lines = [line for block in blocks for line in block.splitlines()
                 if line.startswith("export KUBECONFIG=")]
        self.assertTrue(lines, f"No documented kubeconfig export in {guide}")
        return lines

    def run_export(self, line, existing):
        environment = os.environ.copy()
        environment.pop("KUBECONFIG", None)
        if existing is not None:
            environment["KUBECONFIG"] = existing
        result = subprocess.run(
            [shutil.which("bash"), "-eu", "-c", line + '\nprintf "%s" "$KUBECONFIG"'],
            cwd=UPSTREAM, env=environment, capture_output=True, text=True, check=True,
        )
        return result.stdout

    def test_existing_manual_cluster_credentials_survive_each_guide(self):
        existing = "/protected/manual-control/kubeconfig"
        for guide in GUIDES:
            for line in self.exports(guide):
                with self.subTest(guide=guide):
                    self.assertEqual(self.run_export(line, existing), existing)

    def test_terraform_export_remains_the_default_for_an_unset_environment(self):
        for guide in GUIDES:
            for line in self.exports(guide):
                with self.subTest(guide=guide):
                    output = self.run_export(line, None)
                    self.assertTrue(output.endswith("/secrets/talos/kubeconfig"), output)


if __name__ == "__main__":
    unittest.main()
