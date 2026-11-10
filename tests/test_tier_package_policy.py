"""Package policy configures verification/failure handling, never package updates.

Native APT fixtures use only loopback HTTP and disposable state/configuration.
Repository-specific exceptions are deliberately demonstrated, not hidden by main defaults.
"""

from contextlib import contextmanager
import configparser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = os.environ.get("ANSIBLE_PLAYBOOK") or shutil.which("ansible-playbook")


@contextmanager
def repository_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/unavailable/"):
                self.send_error(503, "Temporary repository failure")
                return
            if self.path.endswith("/Release"):
                now = datetime.now(timezone.utc)
                expires = now + timedelta(days=-1 if self.path.startswith("/expired/") else 1)
                data = (
                    "Origin: Package policy fixture\nSuite: stable\nCodename: stable\n"
                    f"Date: {now.strftime('%a, %d %b %Y %H:%M:%S +0000')}\n"
                    f"Valid-Until: {expires.strftime('%a, %d %b %Y %H:%M:%S +0000')}\n"
                    "Architectures: amd64\nComponents: main\nSHA256:\n"
                    " e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                    " 0 main/binary-amd64/Packages\n"
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


@unittest.skipIf(os.name == "nt", "Native package-policy checks run under Linux/WSL")
@unittest.skipUnless(ANSIBLE, "ansible-playbook is required")
class PackagePolicy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="package-policy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roles = self.root / "roles"
        for name, source in (
            ("baseline", ROOT / "shared/ansible/roles/baseline"),
            ("proxmox_host", ROOT / "tier-0/ansible/roles/proxmox_host"),
        ):
            target = self.roles / name
            shutil.copytree(source, target)
            # Exercise the actual tasks as an unprivileged user on temporary files.
            # Only root ownership is omitted; paths, conditions, templates and modules stay intact.
            for path in (target / "tasks").glob("*.yml"):
                tasks = yaml.safe_load(path.read_text())
                for task in tasks:
                    for module in ("ansible.builtin.file", "ansible.builtin.template"):
                        if module in task:
                            task[module].pop("owner", None)
                            task[module].pop("group", None)
                path.write_text(yaml.safe_dump(tasks, sort_keys=False))
        # Keep the actual main-entry policy include and its condition in role context.
        # No fixture can execute the unrelated full baseline or host sysctl tasks.
        main = self.roles / "baseline/tasks/main.yml"
        policy = [task for task in yaml.safe_load(main.read_text())
                  if task.get("ansible.builtin.include_tasks") == "package_policy.yml"]
        self.assertEqual(len(policy), 1, "The full baseline must include package policy independently")
        main.write_text(yaml.safe_dump(policy, sort_keys=False))
        self.apt_dir = self.root / "apt.conf.d"
        self.apt_dir.mkdir()
        self.policy = self.apt_dir / "90package-policy"
        self.dnf = self.root / "dnf.conf"
        self.dnf.write_text("[main]\n# Preserve distribution settings.\nkeepcache=True\n")
        self.apt_python = os.environ.get("APT_PYTHON", "/usr/bin/python3")
        config = self.root / "ansible.cfg"
        config.write_text("[defaults]\nretry_files_enabled = false\n")
        self.environment = os.environ.copy()
        self.environment.update({
            "ANSIBLE_ROLES_PATH": str(self.roles),
            "ANSIBLE_LOCAL_TEMP": str(self.root / "controller-temp"),
            "ANSIBLE_NOCOLOR": "1",
            "ANSIBLE_CONFIG": str(config),
        })

    def play(self, entry, family):
        role = {"name": "proxmox_host" if entry == "proxmox" else "baseline"}
        if entry not in ("proxmox", "baseline", "bootstrap"):
            role["tasks_from"] = entry
        tasks = [{"ansible.builtin.import_role": role}]
        if entry == "bootstrap":
            source = ROOT / "tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml"
            imports = yaml.safe_load(source.read_text())[1]["tasks"]
            tasks = [task for task in imports if task.get("ansible.builtin.import_role", {}).get(
                "tasks_from") in ("package_policy", "repository_proxy")]
            self.assertEqual(len(tasks), 2, "Bootstrap must import policy and proxy configuration separately")
        inputs = {
            "ansible_os_family": family,
            "ansible_python_interpreter": sys.executable,
            "baseline_manage_repository_proxy": entry != "baseline",
            "baseline_manage_shell_proxy": False,
            "baseline_manage_timezone": False,
            "bootstrap_software_intake_mode": "mirror",
            "repository_proxy_enabled": False,
            "package_policy_apt_conf_dir": str(self.apt_dir),
            "package_policy_apt_conf_path": str(self.policy),
            "package_policy_dnf_conf_path": str(self.dnf),
            "repository_proxy_manage_hosts_entry": False,
            "repository_proxy_manage_apt": False,
            "repository_proxy_manage_dnf": False,
            "proxmox_host_manage_datacenter_proxy": False,
            "proxmox_host_manage_apt_proxy": False,
        }
        path = self.root / f"{entry}-{family}.yml"
        path.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": inputs, "tasks": tasks,
        }], sort_keys=False))
        return path

    def apply(self, entry="bootstrap", family="Debian"):
        result = subprocess.run(
            [ANSIBLE, "-i", "localhost,", str(self.play(entry, family))],
            capture_output=True, text=True, env=self.environment, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def apt(self, source, strict=True, command="update"):
        etc = self.root / "apt-etc"
        etc.mkdir(exist_ok=True)
        sources = etc / "sources.list"
        sources.write_text(source + "\n")
        parts = self.apt_dir if strict else self.root / "no-policy"
        parts.mkdir(exist_ok=True)
        lists = self.root / "lists"
        (lists / "partial").mkdir(parents=True, exist_ok=True)
        config = self.root / "apt-test.conf"
        config.write_text(
            f'Dir::Etc "{etc}";\nDir::Etc::Parts "{parts}";\nDir::Etc::main "/dev/null";\n'
            'Dir::Etc::sourceparts "-";\n'
            f'Dir::State::lists "{lists}";\nDir::State::status "/dev/null";\n'
            f'Dir::Cache "{self.root / "cache"}";\n'
            'Debug::NoLocking "true";\nAcquire::Languages "none";\n'
            'APT::Architecture "amd64";\nAPT::Architectures { "amd64"; };\n'
            'Acquire::Retries "0";\nAcquire::http::Timeout "2";\n'
            'Acquire::http::Proxy "DIRECT";\n'
        )
        environment = self.environment | {"APT_CONFIG": str(config)}
        if command == "library":
            args = [self.apt_python, "-c", "\n".join([
                "import apt",
                "cache = apt.Cache(memonly=True)",
                "try:",
                "    cache.update(raise_on_error=True)",
                "except apt.cache.FetchFailedException:",
                "    print('FetchFailedException')",
                "else:",
                "    raise AssertionError('Incomplete refresh unexpectedly succeeded')",
            ])]
        else:
            args = ["apt-config", "dump"] if command == "dump" else ["apt-get", "update"]
        return subprocess.run(args, env=environment, capture_output=True, text=True, timeout=30)

    def test_bootstrap_mirror_and_proxmox_apply_the_same_policy_without_proxy(self):
        # Bootstrap explicitly imports only package policy and proxy tasks, not the full baseline.
        self.apply()
        original = self.policy.read_text()
        self.assertFalse((self.apt_dir / "80repositoryproxy").exists())
        self.assertRegex(self.apply().stdout, r"changed=0\b")
        self.policy.unlink()
        pve_proxy = self.apt_dir / "76pveproxy"
        pve_proxy.write_text('// GUI-owned proxy setting\nAcquire::http::Proxy "http://example:3128";\n')
        before = pve_proxy.read_bytes()
        # Proxmox does not gather facts; the role supplies its Debian family explicitly.
        self.apply("proxmox", "")
        self.assertEqual(self.policy.read_text(), original)
        self.assertEqual(pve_proxy.read_bytes(), before)

    def test_dnf_policy_preserves_unrelated_settings_and_vendor_repository_overrides(self):
        vendor = self.root / "vendor.repo"
        vendor.write_text(
            "[example]\nbaseurl=https://repo.example.org\n"
            "gpgcheck=False\nsslverify=False\nskip_if_unavailable=True\n"
        )
        before = vendor.read_bytes()
        self.apply("baseline", family="RedHat")
        config = configparser.ConfigParser()
        config.read(self.dnf)
        for option in ("gpgcheck", "localpkg_gpgcheck", "sslverify", "proxy_sslverify"):
            self.assertTrue(config.getboolean("main", option))
        self.assertFalse(config.getboolean("main", "skip_if_unavailable"))
        self.assertTrue(config.getboolean("main", "keepcache"))
        self.assertNotIn("repo_gpgcheck", config["main"])
        self.assertEqual(vendor.read_bytes(), before)
        # DNF gives these repository settings precedence; strict main defaults are not enforcement.
        repository = configparser.ConfigParser()
        repository.read(vendor)
        self.assertFalse(repository.getboolean("example", "gpgcheck"))
        self.assertFalse(repository.getboolean("example", "sslverify"))
        self.assertTrue(repository.getboolean("example", "skip_if_unavailable"))
        self.assertRegex(self.apply("baseline", family="RedHat").stdout, r"changed=0\b")

    def test_redhat_bootstrap_mirror_applies_policy_without_configuring_proxy(self):
        self.apply("bootstrap", "RedHat")
        config = configparser.ConfigParser()
        config.read(self.dnf)
        self.assertTrue(config.getboolean("main", "gpgcheck"))
        self.assertFalse(config.getboolean("main", "skip_if_unavailable"))
        self.assertNotIn("proxy", config["main"])

    @unittest.skipUnless(shutil.which("apt-get") and shutil.which("apt-config"), "APT is required")
    def test_native_apt_rejects_transient_refresh_failure_instead_of_warning_success(self):
        self.apply()
        with repository_server() as endpoint:
            source = f"deb {endpoint}/unavailable stable main"
            permissive = self.apt(source, strict=False)
            self.assertEqual(permissive.returncode, 0, permissive.stdout + permissive.stderr)
            self.assertIn("Failed to fetch", permissive.stderr)
            strict = self.apt(source)
            self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
            self.assertIn("Failed to fetch", strict.stderr)

    @unittest.skipUnless(shutil.which("apt-get") and shutil.which("apt-config"), "APT is required")
    def test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception(self):
        self.apply()
        with repository_server() as endpoint:
            unsigned = self.apt(f"deb {endpoint}/unsigned stable main")
            self.assertNotEqual(unsigned.returncode, 0, unsigned.stdout + unsigned.stderr)
            self.assertIn("not signed", unsigned.stderr)
            # trusted=yes is a real source-level bypass, even with strict manager defaults.
            trusted = self.apt(f"deb [trusted=yes] {endpoint}/unsigned stable main")
            self.assertEqual(trusted.returncode, 0, trusted.stdout + trusted.stderr)
            expired = self.apt(f"deb [trusted=yes] {endpoint}/expired stable main")
            self.assertNotEqual(expired.returncode, 0, expired.stdout + expired.stderr)
            self.assertIn("expired", expired.stderr)
        parsed = self.apt("", command="dump")
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        for option in ("Verify-Peer", "Verify-Host"):
            self.assertIn(f'Acquire::https::{option} "true";', parsed.stdout)

    @unittest.skipUnless(shutil.which("apt-get"), "APT is required")
    def test_native_python_apt_raises_on_incomplete_refresh(self):
        available = subprocess.run([self.apt_python, "-c", "import apt"], capture_output=True)
        if available.returncode:
            self.skipTest("python-apt is required for the native APT library check")
        self.apply()
        with repository_server() as endpoint:
            result = self.apt(f"deb {endpoint}/unavailable stable main", command="library")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("FetchFailedException", result.stdout)

    def test_ansible_216_parses_all_entry_points(self):
        compatible = os.environ.get("ANSIBLE216_PLAYBOOK")
        if not compatible:
            self.skipTest("Set ANSIBLE216_PLAYBOOK to run the Ansible 2.16 parser")
        version = subprocess.run([compatible, "--version"], capture_output=True, text=True, timeout=20)
        self.assertRegex(version.stdout, r"core 2\.16\.")
        for entry in ("baseline", "bootstrap", "proxmox"):
            result = subprocess.run(
                [compatible, "-i", "localhost,", "--syntax-check", str(self.play(entry, "Debian"))],
                env=self.environment, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
