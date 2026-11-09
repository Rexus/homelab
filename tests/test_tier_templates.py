"""Template ownership, upgrade preservation, and local/CD command contracts."""

import json
import os
from pathlib import Path
import re
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


class TierTemplateLifecycle(TierRepositoryTestCase):
    def test_only_tier_zero_owns_template_inputs_and_jobs(self):
        self.generate()
        tier0 = self.root / "verify-tier-0"
        for setup in ("template-refresh", "immutable-template"):
            self.assertIn(setup, (tier0 / ".deployment-setups").read_text())
            self.assertTrue((tier0 / f"terraform/deployments/{setup}/main.tf").exists())
            for tier in ("tier-1", "tier-2"):
                repo = self.root / f"verify-{tier}"
                self.assertNotIn(setup, (repo / ".deployment-setups").read_text())
                self.assertFalse((repo / f"terraform/deployments/{setup}").exists())
                self.assertFalse((repo / "terraform/deployments/templates").exists())
                self.assertFalse((repo / "ci").exists())
        for source in (tier0 / "terraform/deployments/templates").glob("*.tf"):
            for module in re.findall(r'source\s*=\s*"(\.\./[^\"]+)"', source.read_text()):
                self.assertTrue((source.parent / module).is_dir(), (source, module))
        inputs = yaml.safe_load((tier0 / "templates/proxmox.yml.example").read_text())
        catalog = {key: dict(inputs["all"], **entry) for key, entry in inputs["templates"].items()}
        self.assertEqual({entry["family"] for entry in catalog.values()}, {"redhat", "talos", "debian"})
        self.assertEqual({entry["distribution"] for entry in catalog.values()}, {"alma", "rocky", "talos", "debian"})
        self.assertTrue(all("node_name" not in entry for entry in inputs["templates"].values()))
        self.assertTrue(all(entry["node_name"] == "pve01" and entry["bridge"] == "vmbr0"
                            for entry in catalog.values()))
        self.assertFalse((tier0 / "templates/proxmox.yml").exists())
        talos = next(entry for entry in catalog.values() if entry["family"] == "talos")
        self.assertEqual((talos["bios"], talos["machine"], talos["vlan_id"]), ("ovmf", "q35", 10))
        self.assertNotIn("scsi_hardware", talos)
        self.assertNotIn("qemu_agent", talos)
        self.assertTrue((tier0 / "terraform/deployments/templates/.terraform.lock.hcl").exists())
        entry = tier0 / "ansible/playbooks/template-refresh.yml"
        recipe = yaml.safe_load(entry.read_text())[0]["ansible.builtin.import_playbook"]
        refresh = yaml.safe_load((entry.parent / recipe).read_text())
        replacement = refresh[1]["roles"][0]
        self.assertEqual(replacement["role"], "proxmox_template_replace")
        self.assertEqual(replacement["when"], "template_refresh_replace_enabled | default(false) | bool")
        groups = yaml.safe_load((tier0 / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
        self.assertIn("immutable_template_builders", groups)
        self.assertIn("template_refresh_builders", groups)
        self.assertTrue((tier0 / "packer/variables.auto.pkrvars.hcl.example").exists())
        shared = self.root / "verify-shared"
        self.assertFalse((shared / "packer/variables.auto.pkrvars.hcl.example").exists())
        self.assertTrue((tier0 / "terraform/modules/proxmox_templates/main.tf").is_file())
        self.assertTrue((tier0 / "scripts/proxmox-templates.sh").is_file())
        self.assertTrue((tier0 / "ansible/vars/proxmox-api.yml").is_file())
        self.assertTrue((tier0 / "ansible/playbooks/maintenance/template-policy.yml").is_file())
        self.assertTrue((tier0 / "ansible/roles/proxmox_template_policy/tasks/template.yml").is_file())
        self.assertTrue((tier0 / "packer/templates/proxmox/talos-linux.pkr.hcl").is_file())
        self.assertFalse((shared / "terraform/modules/proxmox_templates").exists())
        self.assertFalse((shared / "scripts/proxmox-templates.sh").exists())
        self.assertFalse((shared / "packer").exists())
        pipeline_path = "ci/gitlab-templates.yml.example"
        pipeline = yaml.safe_load((tier0 / pipeline_path).read_text())
        self.assertNotIn("shared", str(pipeline))
        self.assertEqual(pipeline["template-plan"]["script"], ["bash scripts/proxmox-templates.sh plan"])
        self.assertEqual(pipeline["template-publish"]["when"], "manual")
        self.assertEqual(pipeline["template-plan"]["resource_group"],
                         pipeline["template-publish"]["resource_group"])
        self.assertIn(pipeline_path, json.loads((tier0 / ".generated-files.json").read_text())["owned"])

    def test_refresh_does_not_move_live_inputs_state_or_rewrite_owned_jobs(self):
        self.generate()
        preserved = {
            "verify-tier-0/.deployment-setups": "foundation\nvault\nhsm\n",
            "verify-tier-1/.deployment-setups": "edge\ntemplate-refresh\nimmutable-template\n",
            "verify-tier-1/.terraform/state/template-refresh/prod/terraform.tfstate": '{"serial": 7}\n',
            "verify-tier-1/terraform/deployments/template-refresh/main.tf": "# Existing owner\n",
            "verify-tier-0/templates/proxmox.yml": "templates: {local: {vm_id: 9500}}\n",
            "verify-tier-0/ci/gitlab-templates.yml.example": "# Owned CI starter\n",
        }
        for path, content in preserved.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        result = self.generate("--refresh")
        self.assertIn("refresh does not move state", result.stdout)
        for path, content in preserved.items():
            self.assertEqual((self.root / path).read_text(), content)
        self.assertFalse((self.root / "verify-tier-0/.terraform").exists())

    @unittest.skipIf(os.name == "nt", "Bash wrapper checks run under Linux/WSL")
    def test_wrapper_scopes_state_and_requires_a_successful_saved_plan(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        commands = self.root / "commands"
        commands.mkdir()
        fake = commands / "terraform"
        fake.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['TEST_COMMAND_LOG'], 'a') as log:
    log.write(json.dumps({'tool': pathlib.Path(sys.argv[0]).name, 'args': sys.argv[1:], 'data': os.getenv('TF_DATA_DIR'),
                         'endpoint': os.getenv('PROXMOX_VE_ENDPOINT'),
                         'token': os.getenv('PROXMOX_VE_API_TOKEN')}) + '\\n')
if os.getenv('FAIL_INIT') and 'init' in sys.argv:
    sys.exit(1)
if os.getenv('FAIL_APPLY') and 'apply' in sys.argv:
    sys.exit(42)
if 'plan' in sys.argv:
    path = next(arg[5:] for arg in sys.argv if arg.startswith('-out='))
    pathlib.Path(path).write_text('test saved plan')
    if os.getenv('MUTATE_PLAN_INPUT'):
        with open(os.environ['TEST_TEMPLATE_CATALOG'], 'a') as catalog:
            catalog.write('# changed during planning\\n')
    if os.getenv('FAIL_PLAN'):
        sys.exit(7)
if pathlib.Path(sys.argv[0]).name == 'terraform' and 'apply' in sys.argv and '-refresh-only' not in sys.argv:
    if os.getenv('MUTATE_APPLY_INPUT'):
        with open(os.environ['TEST_TEMPLATE_CATALOG'], 'a') as catalog:
            catalog.write('# changed during publication\\n')
        pathlib.Path(os.environ['TEST_TEMPLATE_STATE']).write_text('applied state preserved')
if 'output' in sys.argv:
    if 'template_candidates' in sys.argv:
        print(json.dumps({'rocky-build-1': {'vm_id': 110, 'title': 'rocky-10-tmpl',
                         'node_name': 'pve01', 'family': 'redhat', 'tags': ['el10', 'rocky']}}))
    else:
        print('{}')
if pathlib.Path(sys.argv[0]).name == 'ansible-doc':
    print(json.dumps({name: {'doc': {'module': name}} for name in sys.argv[1:]
                      if name.startswith('community.proxmox.')}))
if pathlib.Path(sys.argv[0]).name == 'ansible-playbook' and os.getenv('FAIL_POLICY'):
    sys.exit(2)
""")
        fake.chmod(0o755)
        for tool in ('ansible-doc', 'ansible-playbook'):
            (commands / tool).symlink_to(fake)
        log = self.root / "calls.jsonl"
        env = {name: value for name, value in os.environ.items()
               if not name.startswith(('PROXMOX_', 'TEMPLATE_', 'TF_VAR_', 'TF_CLI_ARGS', 'FAIL_', 'MUTATE_'))
               and name not in ('DEPLOYMENT_REPO_DIR', 'PM_VE_INSECURE')}
        env.update(PATH=f"{commands}:{os.environ['PATH']}", TEST_COMMAND_LOG=str(log),
                   TEMPLATE_RUNTIME_MODE='check')

        def run(action, *arguments, cwd=repo, **overrides):
            return subprocess.run(["bash", str(repo / "scripts/proxmox-templates.sh"), action, *arguments],
                                  cwd=cwd, env=dict(env, **overrides), capture_output=True, text=True)

        (self.root / "verify-shared").rename(self.root / "unavailable-shared")
        self.assertEqual(run("init").returncode, 0)
        catalog = repo / "templates/proxmox.yml"
        catalog.write_text("# Owned catalog\n")
        state = repo / ".terraform/state/proxmox-templates/terraform.tfstate"
        env.update(TEST_TEMPLATE_CATALOG=str(catalog), TEST_TEMPLATE_STATE=str(state))
        self.assertEqual(run("init").returncode, 0)
        self.assertEqual(catalog.read_text(), "# Owned catalog\n")
        self.assertNotEqual(run("apply").returncode, 0)
        for tier in ("tier-1", "tier-2"):
            self.assertNotEqual(run("init", cwd=self.root / f"verify-{tier}").returncode, 0)
        self.assertNotEqual(run("plan", TEMPLATE_STATE_PATH="relative.tfstate").returncode, 0)
        self.assertEqual(run("plan").returncode, 0)
        plan = repo / ".terraform/plans/proxmox-templates.tfplan"
        context = plan.with_suffix(plan.suffix + '.context')
        self.assertTrue(plan.exists())
        self.assertTrue(context.exists())
        self.assertNotEqual(run("plan", TEMPLATE_STATE_PATH="relative.tfstate").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertEqual(run("plan").returncode, 0)
        self.assertNotEqual(run("plan", FAIL_INIT="1").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertNotEqual(run("apply").returncode, 0)
        self.assertEqual(run("plan").returncode, 0)
        self.assertEqual(run("apply").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertFalse(context.exists())
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        apply = next(call for call in calls if "apply" in call["args"])
        self.assertEqual(apply["args"][-1], str(plan))
        self.assertIn("-parallelism=1", apply["args"])
        policy = next(index for index, call in enumerate(calls) if call['tool'] == 'ansible-playbook')
        refresh = next(index for index, call in enumerate(calls) if '-refresh-only' in call['args'])
        self.assertLess(policy, refresh)
        self.assertTrue(all(call["data"].startswith(str(repo)) for call in calls))
        init = next(call for call in calls if "init" in call["args"])
        self.assertIn(f"-backend-config=path={repo}/.terraform/state/proxmox-templates/terraform.tfstate",
                      init["args"])

        profile = self.root / 'reviewed profile.tfvars'
        profile.write_text('proxmox_storage_classes = {}\n')
        state.write_text('original state preserved')

        def prepare_context():
            result = run('plan', '--platform-file', str(profile))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(plan.exists())
            self.assertTrue(context.exists())

        # Rejection must precede every Terraform and Ansible invocation, preserving state.
        files = {'catalog': catalog, 'platform profile': profile,
                 'root configuration': repo / 'terraform/deployments/templates/main.tf',
                 'module configuration': repo / 'terraform/modules/proxmox_templates/main.tf',
                 'saved plan bytes': plan}
        for name, path in files.items():
            with self.subTest(changed_plan_input=name):
                prepare_context()
                original = path.read_bytes()
                before = log.read_bytes()
                try:
                    path.write_bytes(original + b'\n# changed after review\n')
                    rejected = run('apply', '--platform-file', str(profile))
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn('execution target changed', rejected.stderr)
                    self.assertEqual(log.read_bytes(), before)
                    self.assertEqual(state.read_text(), 'original state preserved')
                finally:
                    path.write_bytes(original)
        for name, changes in {
            'endpoint': {'PROXMOX_VE_ENDPOINT': 'https://other.invalid:8006/'},
            'backend': {'TEMPLATE_STATE_PATH': str(self.root / 'other.tfstate')},
            'TF_VAR placement': {'TF_VAR_default_platform_node_name': 'other-node'},
            'CLI arguments': {'TF_CLI_ARGS_apply': '-parallelism=2'},
        }.items():
            with self.subTest(changed_plan_input=name):
                prepare_context()
                before = log.read_bytes()
                rejected = run('apply', '--platform-file', str(profile), **changes)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn('execution target changed', rejected.stderr)
                self.assertEqual(log.read_bytes(), before)
                self.assertEqual(state.read_text(), 'original state preserved')

        with self.subTest(plan_context='missing companion'):
            prepare_context()
            context.unlink()
            before = log.read_bytes()
            rejected = run('apply', '--platform-file', str(profile))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('Missing saved template input context', rejected.stderr)
            self.assertEqual(log.read_bytes(), before)

        for name, changes in {'failed planning': {'FAIL_PLAN': '1'},
                              'edit during planning': {'MUTATE_PLAN_INPUT': '1'}}.items():
            with self.subTest(plan_context=name):
                prepare_context()
                rejected = run('plan', '--platform-file', str(profile), **changes)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(plan.exists())
                self.assertFalse(context.exists())
                self.assertEqual(state.read_text(), 'original state preserved')
                before = log.read_bytes()
                self.assertNotEqual(run('apply', '--platform-file', str(profile)).returncode, 0)
                self.assertEqual(log.read_bytes(), before)

        # Shared is optional at bootstrap; when present it changes only after complete publication.
        (self.root / "unavailable-shared").rename(self.root / "verify-shared")
        consumer_catalog = self.root / "verify-shared/templates/proxmox-catalog.tfvars"
        original_consumer_catalog = consumer_catalog.read_bytes()

        with self.subTest(plan_context='edit during publication'):
            prepare_context()
            original = catalog.read_bytes()
            before = len(log.read_text().splitlines())
            try:
                rejected = run('apply', '--platform-file', str(profile), MUTATE_APPLY_INPUT='1')
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn('Keep the applied state', rejected.stderr)
                later = [json.loads(line) for line in log.read_text().splitlines()[before:]]
                self.assertEqual(sum('apply' in call['args'] for call in later), 1)
                self.assertFalse(any('-refresh-only' in call['args'] for call in later))
                self.assertFalse(any('template_candidates' in call['args'] for call in later))
                self.assertEqual(state.read_text(), 'applied state preserved')
                self.assertEqual(consumer_catalog.read_bytes(), original_consumer_catalog)
                self.assertFalse(plan.exists())
                self.assertFalse(context.exists())
            finally:
                catalog.write_bytes(original)

        # Failed publication consumes the plan but never discards already-recorded imports.
        state.write_text("preserved import state")
        self.assertEqual(run("import").returncode, 0)
        failed = run("apply", FAIL_APPLY="1")
        self.assertEqual(failed.returncode, 42, failed.stderr)
        self.assertEqual(consumer_catalog.read_bytes(), original_consumer_catalog)
        self.assertIn("Keep the existing state", failed.stderr)
        self.assertFalse(plan.exists())
        self.assertFalse(context.exists())
        self.assertEqual(state.read_text(), "preserved import state")
        self.assertNotEqual(run("apply").returncode, 0)
        self.assertEqual(run("import").returncode, 0)
        self.assertEqual(run("apply").returncode, 0)
        self.assertIn('rocky-10-tmpl', consumer_catalog.read_text())
        self.assertIn('default_linux_vm_template_id = null', consumer_catalog.read_text())
        applied_consumer_catalog = consumer_catalog.read_bytes()

        # A policy failure cannot be reported as a complete publication or trigger a state refresh.
        self.assertEqual(run('plan').returncode, 0)
        before = len(log.read_text().splitlines())
        failed = run('apply', FAIL_POLICY='1')
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('template policy verification failed', failed.stderr)
        self.assertEqual(consumer_catalog.read_bytes(), applied_consumer_catalog)
        later = [json.loads(line) for line in log.read_text().splitlines()[before:]]
        self.assertFalse(any('-refresh-only' in call['args'] for call in later))
        self.assertFalse(plan.exists())
        before = len(log.read_text().splitlines())
        self.assertEqual(run('verify', '--template', 'rocky-build-1').returncode, 0)
        later = [json.loads(line) for line in log.read_text().splitlines()[before:]]
        self.assertFalse(any('apply' in call['args'] for call in later))

        # Local files are explicit, literal inputs; no source/export/token concatenation is required.
        local_env = repo / ".env.local"
        local_env.write_text("PROXMOX_API_URL=https://fixture.invalid:8006/\r\n"
                             "PROXMOX_API_TOKEN_ID='test@pve!template'\r\n"
                             "PROXMOX_API_TOKEN_SECRET=fixture-not-a-secret\r\n")
        self.assertEqual(run("import", "--env-file", ".env.local").returncode, 0)
        last = json.loads(log.read_text().splitlines()[-1])
        self.assertEqual(last["endpoint"], "https://fixture.invalid:8006/")
        self.assertEqual(last["token"], "test@pve!template=fixture-not-a-secret")
        self.assertIn("-var=adopt_existing=true", last["args"])
        self.assertFalse(any("import" == arg or "apply" == arg for arg in last["args"]))
        self.assertNotEqual(run("plan", "--env-file", "missing").returncode, 0)
        self.assertFalse(plan.exists())
        self.assertNotEqual(run("plan", "--env-file").returncode, 0)
        local_env.write_text("PROXMOX_VE_INSECURE=true\n")
        result = run("plan", "--env-file", ".env.local")
        self.assertIn("Refusing Proxmox TLS bypass", result.stderr)
        self.assertFalse(plan.exists())
        marker = repo / "should-not-exist"
        local_env.write_text(f"PROXMOX_API_TOKEN_SECRET=$(touch {marker})\n")
        run("plan", "--env-file", ".env.local")
        self.assertFalse(marker.exists())
        local_env.write_text("repo_root=/untrusted\n")
        self.assertNotEqual(run("plan", "--env-file", ".env.local").returncode, 0)
        local_env.write_text("PROXMOX_API_URL=https://fixture.invalid:8006/\n")
        self.assertNotEqual(run("plan", "--env-file", ".env.local",
                                PROXMOX_VE_ENDPOINT="https://other.invalid/").returncode, 0)
        profile = self.root / "profile with spaces.tfvars"
        profile.write_text("proxmox_storage_classes = {}\n")
        self.assertEqual(run("plan", "--platform-file", str(profile)).returncode, 0)
        last = json.loads(log.read_text().splitlines()[-1])
        self.assertIn(f"-var-file={profile}", last["args"])

        # Catalog failure follows publication but cannot destroy either state or local selections.
        consumer_catalog.write_text('default_linux_vm_template_id = null\nproxmox_template_catalog = {\n')
        broken_catalog = consumer_catalog.read_bytes()
        failed = run('apply', '--platform-file', str(profile))
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('Shared catalog update failed', failed.stderr)
        self.assertEqual(consumer_catalog.read_bytes(), broken_catalog)
        self.assertEqual(state.read_text(), 'preserved import state')
        self.assertFalse(plan.exists())
        consumer_catalog.write_bytes(applied_consumer_catalog)
        self.assertEqual(run('plan').returncode, 0)
        self.assertEqual(run('apply').returncode, 0)


if __name__ == "__main__":
    unittest.main()
