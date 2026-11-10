"""Cache CIDR validation declares its controller dependencies before guest changes."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class CacheDependencies(TierRepositoryTestCase):
    def repositories(self):
        self.generate()
        return (UPSTREAM / "tier-2", self.root / "verify-tier-2")

    def test_cache_precheck_selects_the_filter_and_controller_python_requirements(self):
        for owner in self.repositories():
            settings = yaml.safe_load((owner / "ansible/playbooks/control-node.yml").read_text())[0]["vars"]
            selected = settings["control_node_setup_collection_names"]["cache"]
            self.assertIn("ansible.utils", selected, str(owner))
            dependency = settings["control_node_collection_catalog"]["ansible.utils"]
            for family in ("RedHat", "Debian"):
                self.assertIn("python3-netaddr", dependency["os_packages"][family])
            self.assertIn("netaddr>=0.10.1", (owner / "ansible/requirements.txt").read_text())
            policy = yaml.safe_load((owner / "ansible/group_vars/cache.yml.example").read_text())
            self.assertIn("galaxy.ansible.com", policy["cache_squid_allowed_domains"], str(owner))

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Linux Ansible")
    def test_missing_ipaddr_collection_is_prepared_or_rejected_before_guest_tasks(self):
        fixture = Path(self.temp.name) / "cache-precheck"
        tools = fixture / "bin"
        tools.mkdir(parents=True)
        log = fixture / "galaxy.jsonl"
        shim = tools / "ansible-galaxy"
        shim.write_text(
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            "with open(os.environ['CACHE_GALAXY_LOG'], 'a') as log:\n"
            "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:3] == ['collection', 'list']:\n"
            "    if sys.argv[3] != 'ansible.utils':\n"
            "        print(sys.argv[3] + ' 10.2.0')\n"
            "elif sys.argv[1:3] == ['collection', 'install']:\n"
            "    print('Collection was installed successfully')\n"
            "else:\n"
            "    sys.exit('Unexpected collection operation')\n", encoding="utf-8")
        shim.chmod(0o700)
        environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                           CACHE_GALAXY_LOG=str(log), ANSIBLE_NOCOLOR="1")
        prefix = [
            "Resolve required collections for selected setup",
            "Check required Ansible collections",
            "Track missing Ansible collections",
            "Build OS package list for missing Ansible collections",
        ]
        for owner in self.repositories():
            shared = owner.parent / ("verify-shared" if owner.name.startswith("verify-") else "shared")
            play = yaml.safe_load((shared / "ansible/playbooks/control-node.yml").read_text())[0]
            settings = yaml.safe_load((owner / "ansible/playbooks/control-node.yml").read_text())[0]["vars"]
            tasks = {task["name"]: task for task in play["tasks"]}
            for mode in ("auto", "check"):
                log.write_text("", encoding="utf-8")
                selected = [deepcopy(tasks[name]) for name in prefix]
                selected.append({"ansible.builtin.assert": {"that": [
                    "control_node_missing_collections | map(attribute='name') | list == ['ansible.utils']",
                    "'python3-netaddr' in control_node_collection_packages",
                ]}})
                if mode == "auto":
                    selected.append(deepcopy(tasks[
                        "Install missing or incompatible Ansible collections with native Galaxy ranges"]))
                else:
                    selected.append(deepcopy(tasks["Require preinstalled collections in check mode"]))
                variables = dict(play["vars"], **settings,
                                 control_node_setup="cache", ansible_os_family="RedHat",
                                 control_node_collections_mode=mode)
                probe = fixture / "probe.yml"
                probe.write_text(yaml.safe_dump([dict(hosts="localhost", connection="local",
                                                     gather_facts=False, vars=variables,
                                                     tasks=selected)], sort_keys=False), encoding="utf-8")
                result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(probe)],
                                        cwd=owner, env=environment, capture_output=True, text=True,
                                        timeout=60)
                output = result.stdout + result.stderr
                with self.subTest(owner=owner, mode=mode):
                    self.assertEqual(result.returncode == 0, mode == "auto", output)
                    calls = [json.loads(line) for line in log.read_text().splitlines()]
                    if mode == "auto":
                        self.assertIn(["collection", "install", "--no-cache",
                                       "ansible.utils:>=6.0.0,<7.0.0"], calls)
                    else:
                        self.assertIn("Missing collections: ansible.utils", output)
                        self.assertIn("check mode never downloads dependencies", output)
                        self.assertTrue(all(call[:2] == ["collection", "list"] for call in calls))
