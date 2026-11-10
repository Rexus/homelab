"""Explicit DNF source selection edits existing stanzas without contacting repositories."""

import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ANSIBLE = shutil.which(os.environ.get("ANSIBLE_PLAYBOOK", "ansible-playbook")) or shutil.which("ansible-playbook")
NATIVE = unittest.skipUnless(os.name != "nt" and ANSIBLE, "Requires Linux/WSL Ansible and community.general")
REPOSITORY = (
    "# Distribution-owned repository\n[{section}]\nname=Vendor packages\n"
    "baseurl=https://vendor.invalid/$releasever/$basearch/\n"
    "mirrorlist=https://mirrors.invalid/list\nmetalink=https://mirrors.invalid/meta\n"
    "gpgcheck=1\nrepo_gpgcheck=1\ngpgkey=file:///fixture/RPM-GPG-KEY-vendor\n"
    "sslverify=1\nenabled=1\npriority=20\n"
    "\n[unselected]\nbaseurl=https://other.invalid/packages\n"
    "mirrorlist=https://other.invalid/list\nmetalink=https://other.invalid/meta\n"
    "gpgcheck=0\nenabled=0\n"
)


class RepositorySources(TierRepositoryTestCase):
    def owners(self):
        self.generate("--repo", "shared")
        return (UPSTREAM / "shared", self.root / "verify-shared")

    def fixture(self, label):
        directory = Path(self.temp.name) / label
        repos = directory / "yum.repos.d"
        repos.mkdir(parents=True)
        for filename, section in (("vendor.repo", "baseos"), ("extra.repo", "extras"),
                                  ("untouched.repo", "vendor")):
            (repos / filename).write_text(REPOSITORY.format(section=section))
        (directory / "escape.repo").write_text(REPOSITORY.format(section="baseos"))
        (directory / "dnf.conf").write_text("[main]\nproxy=http://existing.invalid:3128\ngpgcheck=1\n")
        apt = directory / "apt"
        apt.mkdir()
        (apt / "80repositoryproxy").write_text("// Existing operator configuration\n")
        (directory / "ansible.cfg").write_text("[defaults]\nretry_files_enabled = false\n")
        values = dict(
            ansible_become=False, ansible_python_interpreter=sys.executable,
            ansible_remote_tmp=str(directory / "remote-temp"),
            repository_proxy_enabled=False, repository_proxy_manage_hosts_entry=False,
            repository_proxy_manage_dnf=True, repository_proxy_manage_apt=False,
            repository_proxy_remove_when_disabled=False,
            repository_proxy_dnf_conf_path=str(directory / "dnf.conf"),
            repository_proxy_dnf_repo_dir=str(repos), repository_proxy_dnf_sources=[],
            repository_proxy_apt_conf_dir=str(apt),
            repository_proxy_apt_conf_path=str(apt / "80repositoryproxy"),
        )
        return directory, values

    def snapshot(self, directory):
        paths = [directory / "dnf.conf", directory / "escape.repo",
                 directory / "apt/80repositoryproxy", *sorted((directory / "yum.repos.d").iterdir())]
        return {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns) for path in paths}

    def apply(self, owner, directory, values, success=True):
        play = directory / "play.yml"
        play.write_text(yaml.safe_dump([dict(
            hosts="localhost", connection="local", gather_facts=False, become=False, vars=values,
            tasks=[{"ansible.builtin.include_role": dict(name="baseline", tasks_from="repository_proxy")}],
        )], sort_keys=False))
        environment = dict(os.environ, ANSIBLE_CONFIG=str(directory / "ansible.cfg"),
                           ANSIBLE_ROLES_PATH=str(owner / "ansible/roles"), ANSIBLE_NOCOLOR="1",
                           ANSIBLE_LOCAL_TEMP=str(directory / "controller-temp"),
                           ANSIBLE_REMOTE_TEMP=str(directory / "remote-temp"), TMPDIR=str(directory))
        result = subprocess.run([ANSIBLE, "-i", "localhost,", str(play)], cwd=directory,
                                env=environment, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        return output

    def test_source_and_generated_defaults_require_explicit_source_selection(self):
        for owner in self.owners():
            with self.subTest(owner=owner):
                defaults = yaml.safe_load((owner / "ansible/roles/baseline/defaults/main.yml").read_text())
                self.assertEqual(defaults["repository_proxy_dnf_sources"], [])
                self.assertEqual(defaults["repository_proxy_dnf_repo_dir"], "/etc/yum.repos.d")

    @NATIVE
    def test_selected_sources_preserve_trust_other_sections_and_files_idempotently(self):
        for index, owner in enumerate(self.owners()):
            with self.subTest(owner=owner):
                directory, values = self.fixture(f"selected-{index}")
                before = self.snapshot(directory)
                values["repository_proxy_dnf_sources"] = [
                    dict(file="vendor.repo", section="baseos",
                         baseurl="https://approved.invalid/baseos/$releasever/$basearch/"),
                    dict(file="extra.repo", section="extras",
                         baseurl="https://approved.invalid/extras/$releasever/$basearch/"),
                ]
                self.apply(owner, directory, values)
                selected = set()
                for source in values["repository_proxy_dnf_sources"]:
                    path = directory / "yum.repos.d" / source["file"]
                    selected.add(path)
                    original = configparser.ConfigParser(interpolation=None)
                    original.read_string(before[path][0].decode())
                    actual = configparser.ConfigParser(interpolation=None)
                    actual.read(path)
                    expected = dict(original[source["section"]], baseurl=source["baseurl"])
                    for option in ("mirrorlist", "metalink"):
                        expected.pop(option)
                    self.assertEqual(dict(actual[source["section"]]), expected)
                    self.assertEqual(actual.sections(), original.sections())
                    self.assertEqual(dict(actual["unselected"]), dict(original["unselected"]))
                    self.assertEqual(path.read_text().split("\n[unselected]", 1)[1],
                                     before[path][0].decode().split("\n[unselected]", 1)[1])
                    self.assertIn("# Distribution-owned repository", path.read_text())
                after = self.snapshot(directory)
                for path in after.keys() - before.keys():
                    self.assertTrue(any(path.name.startswith(source.name + ".") and path.name.endswith("~")
                                        for source in selected), str(path))
                for path in before.keys() - selected:
                    self.assertEqual(after[path], before[path], str(path))
                self.assertRegex(self.apply(owner, directory, values), r"changed=0\b")
                self.assertEqual(self.snapshot(directory), after)

    @NATIVE
    def test_empty_and_default_source_lists_make_no_unrequested_changes(self):
        for index, owner in enumerate(self.owners()):
            for explicit in (True, False):
                with self.subTest(owner=owner, explicit=explicit):
                    directory, values = self.fixture(f"empty-{index}-{explicit}")
                    if not explicit:
                        values.pop("repository_proxy_dnf_sources")
                    before = self.snapshot(directory)
                    for _ in range(2):
                        self.assertRegex(self.apply(owner, directory, values), r"changed=0\b")
                        self.assertEqual(self.snapshot(directory), before)

    @NATIVE
    def test_invalid_sources_and_missing_files_or_sections_fail_before_writes(self):
        invalid = (
            dict(file="../escape.repo"), dict(file="vendor.conf"),
            dict(baseurl="https://operator:fixture@approved.invalid/packages"),
            dict(baseurl="https://operator@approved.invalid/packages"),
            dict(baseurl="http://approved.invalid/packages"), dict(file="missing.repo"),
            dict(baseurl="https:///packages"), dict(section="missing"),
        )
        for index, owner in enumerate(self.owners()):
            for case, override in enumerate(invalid):
                with self.subTest(owner=owner, override=override):
                    directory, values = self.fixture(f"invalid-{index}-{case}")
                    values["repository_proxy_dnf_sources"] = [dict(
                        dict(file="vendor.repo", section="baseos", baseurl="https://approved.invalid/packages"),
                        **override)]
                    before = self.snapshot(directory)
                    output = self.apply(owner, directory, values, success=False)
                    message = "credential-free HTTPS"
                    if override.get("file") == "missing.repo":
                        message = "must already exist"
                    elif override.get("section") == "missing":
                        message = "Section missing is missing from"
                    self.assertIn(message, output)
                    self.assertRegex(output, r"changed=0\b")
                    self.assertEqual(self.snapshot(directory), before)


if __name__ == "__main__":
    unittest.main()
