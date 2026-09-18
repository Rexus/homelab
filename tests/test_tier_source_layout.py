"""Source ownership must remain visible and match the generated repositories."""

import configparser
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generated_files import RepositoryWriter
from payload import TIERS, copy_payload, validate_layout


class SourceLayout(TierRepositoryTestCase):
    def test_source_payloads_match_generated_paths_and_inputs(self):
        validate_layout(UPSTREAM)
        self.generate()
        for name in ("shared", *TIERS):
            source = UPSTREAM / name
            generated = self.root / f"verify-{name}"
            manifest = json.loads((generated / ".generated-files.json").read_text())
            for relative in set(manifest["files"]) | set(manifest["owned"]):
                if relative in ("README.md", ".gitignore", ".gitattributes", "LICENSE"):
                    continue
                expected = (source / relative).read_text(encoding="utf-8")
                expected = re.sub(r"(?<=\.\./)shared(?=[/\"'\s]|$)", "verify-shared", expected)
                expected = expected.replace("check out shared beside", "check out verify-shared beside")
                self.assertEqual((generated / relative).read_text(encoding="utf-8"), expected, relative)
            for path in source.rglob("*.tf"):
                for module in re.findall(r'source\s*=\s*"(\.\./[^"]+)"', path.read_text()):
                    self.assertTrue((path.parent / module).is_dir(), (path, module))
            if name == "shared":
                self.assertFalse((source / "ansible/inventory").exists())
                continue
            config = configparser.ConfigParser()
            config.read(source / "ansible/ansible.cfg")
            self.assertTrue((source / "ansible" / config["defaults"]["roles_path"]).is_dir())
            relative = "ansible/inventory/hosts.yml.example"
            self.assertEqual(yaml.safe_load((source / relative).read_text()),
                             yaml.safe_load((generated / relative).read_text()))
        for old in ("ansible/inventory/hosts.yml.example", "terraform/common.tfvars.example",
                    "scripts/deploy.sh", "scripts/init-local-files.sh"):
            self.assertFalse((UPSTREAM / old).exists(), old)

    def test_payload_copy_excludes_live_files_state_overrides_and_test_fixtures(self):
        upstream = Path(self.temp.name) / "source"
        root = upstream / "tier-2"
        files = {
            ".deployment-setups": "lab\n",
            "env.local.example": "# example\n",
            "terraform/environments/lab/main.tf": "# source\n",
            "terraform/environments/lab/.terraform.lock.hcl": "# lock\n",
            "terraform/environments/lab/terraform.tfvars.example": "# example\n",
            "ansible/inventory/hosts.yml.example": "all: {}\n",
            "ansible/inventory/hosts.yml": "SECRET\n",
            "ansible/group_vars/all.yml": "SECRET\n",
            "ansible/host_vars/host.yml": "SECRET\n",
            "terraform/common.tfvars": "SECRET\n",
            "terraform/environments/lab/override.tf": "SECRET\n",
            "terraform/environments/lab/local_override.tf": "SECRET\n",
            "terraform/environments/lab/terraform.tfstate": "SECRET\n",
            "terraform/environments/lab/.terraform/main.tf": "SECRET\n",
            "terraform/modules/sample/tests/main.tf": "SECRET\n",
            "templates/proxmox.yml": "SECRET\n",
            "templates/artifacts/image.qcow2": "SECRET\n",
            ".env.local": "SECRET\n",
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(self.root)
            copy_payload(writer, upstream, "tier-2", "verify")
            writer.finish()
        for relative, content in files.items():
            self.assertEqual((self.root / relative).exists(), content != "SECRET\n", relative)

    def test_validation_rejects_missing_unregistered_and_cross_tier_inputs(self):
        self.generate()
        for name in TIERS:
            (self.root / f"verify-{name}").rename(self.root / name)
        validate_layout(self.root)
        setup_list = self.root / "tier-2/.deployment-setups"
        setup_list.write_text("missing\n")
        with self.assertRaisesRegex(ValueError, "Missing setup source"):
            validate_layout(self.root)
        setup_list.write_text("lab\n")
        extra = self.root / "tier-2/terraform/environments/unregistered/main.tf"
        extra.parent.mkdir()
        extra.write_text("# unregistered\n")
        with self.assertRaisesRegex(ValueError, "Terraform roots disagree"):
            validate_layout(self.root)
        extra.unlink()
        ips = self.root / "tier-2/ansible/group_vars/lab.yml.example"
        ips.write_text("platform_host_ips: {idm-1: 192.0.2.1}\n")
        with self.assertRaisesRegex(ValueError, "Host IPs outside"):
            validate_layout(self.root)

    @unittest.skipIf(os.name == "nt", "Source Bash commands run under Linux/WSL")
    def test_source_shortcuts_initialize_only_the_owning_tier(self):
        self.generate()
        for name in ("shared", *TIERS):
            (self.root / f"verify-{name}").rename(self.root / name)
        env = dict(os.environ)
        env.pop("DEPLOYMENT_REPO_DIR", None)
        for tier in TIERS:
            root = self.root / tier
            for path in (UPSTREAM / tier / "scripts").glob("*.sh"):
                shutil.copyfile(path, root / "scripts" / path.name)
            result = subprocess.run(["bash", "scripts/init-local-files.sh", "--env", "test"],
                                    cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            setups = (root / ".deployment-setups").read_text().splitlines()
            local = list((root / "terraform/environments").glob("*/terraform.tfvars"))
            self.assertEqual({path.parent.name for path in local}, set(setups))
            self.assertTrue((root / "ansible/inventory/hosts.yml").is_file())
            self.assertTrue((root / "ansible/group_vars/all.test.yml").is_file())
            invalid = subprocess.run(["bash", "scripts/deploy.sh", "not-owned", "--plan-only"],
                                     cwd=root, env=env, capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
        script = self.root / "shared/scripts/init-local-files.sh"
        for cwd in (self.root, self.root / "shared"):
            result = subprocess.run(["bash", str(script)], cwd=cwd, env=env,
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tier repository root", result.stderr)


if __name__ == "__main__":
    unittest.main()
