"""Host identity selection and enrollment guards never mutate the execution host.

Native fixtures retain the role's validation, stat, slurp and copy tasks. Only /etc
paths and copy ownership are redirected; the hostname write is replaced by a debug
sentinel. Real hostname changes and directory enrollment remain live acceptance work.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / "shared/ansible/roles/baseline"
ANSIBLE = os.environ.get("ANSIBLE_PLAYBOOK") or shutil.which("ansible-playbook")
NATIVE = unittest.skipUnless(os.name != "nt" and ANSIBLE, "Requires Linux/WSL Ansible")
WRITE_SENTINEL = "Fixture reached the intercepted hostname write"


class HostIdentity(TierRepositoryTestCase):
    def test_generated_role_keeps_safe_defaults_and_preflight_before_baseline_mutations(self):
        self.generate("--repo", "shared")
        generated = self.root / "verify-shared/ansible/roles/baseline"
        for path in ("defaults/main.yml", "tasks/main.yml", "tasks/hostname.yml"):
            self.assertEqual((ROLE / path).read_bytes(), (generated / path).read_bytes())
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertIs(defaults["baseline_manage_hostname"], False)
        self.assertEqual(defaults["baseline_hostname"], "{{ platform_fqdn }}")
        main = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        self.assertEqual(main[0]["ansible.builtin.include_tasks"], "hostname.yml")
        self.assertNotIn("when", main[0])
        hostname = yaml.safe_load((ROLE / "tasks/hostname.yml").read_text())
        block = hostname[-1]["block"]
        self.assertEqual(block[-1]["ansible.builtin.hostname"],
                         {"name": "{{ baseline_hostname }}", "use": "systemd"})
        copy = block[-2]["ansible.builtin.copy"]
        self.assertEqual(yaml.safe_load(copy["content"]), {"preserve_hostname": True})
        self.assertEqual(copy["dest"], "/etc/cloud/cloud.cfg.d/99-baseline-hostname.cfg")

    def fixture(self):
        directory = Path(self.temp.name) / "identity"
        directory.mkdir()
        role = directory / "roles/baseline"
        shutil.copytree(ROLE, role)
        main = yaml.safe_load((role / "tasks/main.yml").read_text())
        self.assertEqual(main[0]["ansible.builtin.include_tasks"], "hostname.yml")
        # Keep the actual first include, excluding unrelated package/sysctl work.
        (role / "tasks/main.yml").write_text(yaml.safe_dump(main[:1], sort_keys=False))
        self.etc = directory / "etc"
        self.etc.mkdir()
        self.cloud = self.etc / "cloud/cloud.cfg.d"
        self.cloud.mkdir(parents=True)
        self.preserve = self.cloud / "99-baseline-hostname.cfg"
        tasks = yaml.safe_load((role / "tasks/hostname.yml").read_text())

        def fixture_path(path):
            self.assertTrue(path.startswith("/etc/"), path)
            return str(self.etc / path.removeprefix("/etc/"))

        def redirect(tasks):
            for task in tasks:
                if "block" in task:
                    redirect(task["block"])
                    continue
                modules = [key for key in task if key.startswith("ansible.")]
                self.assertEqual(len(modules), 1, task)
                module = modules[0]
                self.assertIn(module, {"ansible.builtin.assert", "ansible.builtin.stat",
                                       "ansible.builtin.slurp", "ansible.builtin.copy",
                                       "ansible.builtin.hostname"})
                args = task[module]
                if module == "ansible.builtin.hostname":
                    self.assertEqual(args, {"name": "{{ baseline_hostname }}", "use": "systemd"})
                    del task[module]
                    task["ansible.builtin.debug"] = {"msg": WRITE_SENTINEL}
                elif module == "ansible.builtin.stat":
                    self.assertFalse(args["get_checksum"])
                    self.assertFalse(args["get_mime"])
                    self.assertFalse(args["get_attributes"])
                    if "loop" in task:
                        task["loop"] = [fixture_path(path) for path in task["loop"]]
                        self.assertEqual(args["path"], "{{ item }}")
                    else:
                        args["path"] = fixture_path(args["path"])
                elif module == "ansible.builtin.slurp":
                    self.assertEqual(args["src"], "/etc/hostname")
                    args["src"] = fixture_path(args["src"])
                elif module == "ansible.builtin.copy":
                    args["dest"] = fixture_path(args["dest"])
                    args.pop("owner")
                    args.pop("group")

        redirect(tasks)
        (role / "tasks/hostname.yml").write_text(yaml.safe_dump(tasks, sort_keys=False))
        (directory / "ansible.cfg").write_text("[defaults]\nretry_files_enabled = false\n")
        return directory

    def run_identity(self, directory, cases, *, fresh=False, expected_success=True):
        plays = []
        for index, (inputs, assertions) in enumerate(cases):
            case = directory / f"inputs-{index}.yml"
            case.write_text(yaml.safe_dump(dict(ansible_become=False,
                ansible_connection="local", ansible_python_interpreter=sys.executable,
                ansible_remote_tmp=str(directory / "remote-temp"), **inputs), sort_keys=False))
            files = [str(case)]
            if fresh:
                files.insert(0, str(UPSTREAM / "tier-0/ansible/group_vars/all.yml.example"))
            plays.append(dict(hosts="fixture-1", gather_facts=False, vars_files=files, tasks=[
                {"ansible.builtin.include_role": {"name": "baseline", "public": True}},
                {"ansible.builtin.assert": {"that": assertions or ["true"]}},
            ]))
        play = directory / "play.yml"
        play.write_text(yaml.safe_dump(plays, sort_keys=False))
        environment = dict(os.environ, ANSIBLE_CONFIG=str(directory / "ansible.cfg"),
            ANSIBLE_ROLES_PATH=str(directory / "roles"), ANSIBLE_NOCOLOR="1",
            ANSIBLE_LOCAL_TEMP=str(directory / "controller-temp"))
        result = subprocess.run([ANSIBLE, "-i", "fixture-1,", str(play)], env=environment,
                                capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, expected_success, output)
        return output

    @NATIVE
    def test_native_fresh_inputs_select_namespaces_without_hostname_writes(self):
        directory = self.fixture()
        cases = []
        for role, domain in ((None, "internal.example.com"), ("standalone", "internal.example.com"),
                             ("member", "corp.example.com"), ("authority", "corp.example.com")):
            inputs = {"baseline_manage_hostname": False}
            if role is not None:
                inputs["platform_domain_role"] = role
            cases.append((inputs, [f"platform_host_domain == '{domain}'",
                                   f"baseline_hostname == 'fixture-1.{domain}'"]))
        output = self.run_identity(directory, cases, fresh=True)
        self.assertNotIn(WRITE_SENTINEL, output)
        self.assertFalse(self.preserve.exists())
        self.assertRegex(output, r"changed=0\b")

    @NATIVE
    def test_native_proxy_excludes_both_namespaces_and_legacy_inputs_remain_valid(self):
        directory = self.fixture()
        cases = []
        for inputs, expected in (
            ({}, []),
            ({"platform_domain": "legacy.example.com"},
             ["legacy.example.com", ".legacy.example.com"]),
            ({"platform_internal_domain": "example.internal", "platform_domain": "corp.example.com"},
             ["example.internal", "corp.example.com", ".example.internal", ".corp.example.com"]),
            ({"platform_internal_domain": "example.internal", "platform_domain": "example.internal"},
             ["example.internal", ".example.internal"]),
        ):
            cases.append((inputs, [f"shell_proxy_no_proxy_domain_entries == {json.dumps(expected)}",
                                   "not baseline_manage_hostname | bool"]))
        output = self.run_identity(directory, cases)
        self.assertNotIn(WRITE_SENTINEL, output)
        self.assertFalse(self.preserve.exists())

    @NATIVE
    def test_native_invalid_identity_inputs_refuse_before_any_fixture_mutation(self):
        directory = self.fixture()
        for inputs in (
            {"platform_domain_role": "joined"},
            {"platform_domain_role": None},
            {"platform_internal_domain": ""},
            {"platform_internal_domain": "internal.example.local"},
            {"platform_internal_domain": "EXAMPLE.LOCAL"},
            {"platform_internal_domain": "bad_domain.internal"},
            {"platform_internal_domain": " example.internal"},
            {"platform_internal_domain": "example.internal."},
            {"platform_internal_domain": "example.internal\n"},
            {"platform_internal_domain": "-invalid.internal"},
            {"platform_internal_domain": "a" * 64 + ".internal"},
            {"platform_internal_domain": None},
            {"platform_domain_role": "member"},
            {"platform_domain_role": "member", "platform_internal_domain": "example.internal"},
            {"platform_domain_role": "authority", "platform_domain": "example.local"},
        ):
            with self.subTest(inputs=inputs):
                output = self.run_identity(directory, [(dict(inputs, baseline_manage_hostname=False), [])],
                                           expected_success=False)
                self.assertIn("Validate", output)
                self.assertNotIn(WRITE_SENTINEL, output)
                self.assertFalse(self.preserve.exists())

    @NATIVE
    def test_native_management_rejects_unsupported_targets_and_unsafe_hostnames(self):
        directory = self.fixture()
        base = dict(platform_internal_domain="example.internal", platform_fqdn="fixture-1.example.internal",
                    baseline_manage_hostname=True, ansible_os_family="RedHat", ansible_service_mgr="systemd")
        for inputs in ({"ansible_os_family": "Windows"}, {"ansible_service_mgr": "openrc"},
                       {"baseline_hostname": "bad_name.example.internal"},
                       {"baseline_hostname": "fixture-1.example.local"},
                       {"baseline_hostname": "a" * 63 + ".example.internal"}):
            with self.subTest(inputs=inputs):
                output = self.run_identity(directory, [(base | inputs, [])], expected_success=False)
                self.assertNotIn(WRITE_SENTINEL, output)
                self.assertFalse(self.preserve.exists())

    @NATIVE
    def test_native_enrollment_material_blocks_renames_even_if_role_is_standalone(self):
        directory = self.fixture()
        base = dict(platform_internal_domain="example.internal", platform_domain_role="standalone",
                    platform_fqdn="fixture-1.example.internal", baseline_manage_hostname=True,
                    ansible_os_family="RedHat", ansible_service_mgr="systemd")
        static = self.etc / "hostname"
        for material in ("krb5.keytab", "ipa/default.conf"):
            with self.subTest(material=material):
                path = self.etc / material
                path.parent.mkdir(exist_ok=True)
                path.write_text("Enrollment fixture contents must never appear in output\n")
                static.write_text("fixture-1.corp.example.com\n")
                output = self.run_identity(directory, [(base, [])], expected_success=False)
                self.assertIn("Refuse to rename", output)
                self.assertIn("baseline_manage_hostname=false", output)
                self.assertNotIn("Enrollment fixture contents", output)
                self.assertNotIn(WRITE_SENTINEL, output)
                self.assertFalse(self.preserve.exists())
                static.unlink()
                output = self.run_identity(directory, [(base, [])], expected_success=False)
                self.assertIn("Restore the existing static hostname", output)
                self.assertNotIn(WRITE_SENTINEL, output)
                self.assertFalse(self.preserve.exists())
                path.unlink()
                # A temporarily missing keytab target must not bypass the enrollment guard.
                path.symlink_to("missing-enrollment-file")
                static.write_text("fixture-1.corp.example.com\n")
                output = self.run_identity(directory, [(base, [])], expected_success=False)
                self.assertIn("Refuse to rename", output)
                self.assertNotIn(WRITE_SENTINEL, output)
                self.assertFalse(self.preserve.exists())
                path.unlink()

    @NATIVE
    def test_native_commissioning_and_same_enrolled_name_preserve_cloud_init_idempotently(self):
        directory = self.fixture()
        inputs = dict(platform_domain="corp.example.com", platform_domain_role="authority",
                      platform_fqdn="fixture-1.corp.example.com", baseline_manage_hostname=True,
                      ansible_os_family="Debian", ansible_service_mgr="systemd")
        # An authority without existing enrollment may commission its initial FQDN.
        output = self.run_identity(directory, [(inputs, [])])
        self.assertIn(WRITE_SENTINEL, output)
        self.assertEqual(yaml.safe_load(self.preserve.read_text()), {"preserve_hostname": True})
        (self.etc / "krb5.keytab").write_bytes(b"enrollment fixture")
        (self.etc / "hostname").write_text(inputs["platform_fqdn"] + "\n")
        output = self.run_identity(directory, [(inputs, [])])
        self.assertIn(WRITE_SENTINEL, output)
        self.assertRegex(output, r"changed=0\b")
        # Hosts without Cloud-init do not gain an invented configuration directory.
        self.preserve.unlink()
        self.cloud.rmdir()
        output = self.run_identity(directory, [(inputs, [])])
        self.assertIn(WRITE_SENTINEL, output)
        self.assertFalse(self.cloud.exists())


if __name__ == "__main__":
    unittest.main()
