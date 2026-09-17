"""Workspace-local fixtures shared by repository generator checks."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

UPSTREAM = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(UPSTREAM / "scripts/tier-repos"))


class TierRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        temp_root = UPSTREAM / ".tmp"
        temp_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="tier-repos-", dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / "workspace with spaces"
        self.root = self.parent / "verify-iac"

    def generate(self, *args):
        return subprocess.run(
            [sys.executable, str(UPSTREAM / "scripts/tier-repos/generate.py"),
             "--root", str(self.parent), "--prefix", "verify", *args],
            capture_output=True, text=True, check=True,
        )
