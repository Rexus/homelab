"""Exercise saved-plan and trusted-CI boundaries with disposable command doubles."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipIf(os.name == "nt", "Requires native Bash and Linux file permissions")
class CiExecution(TierRepositoryTestCase):
    def executable(self, name, content):
        target = self.commands / name
        target.write_text(content)
        target.chmod(0o755)

    def setUp(self):
        super().setUp()
        self.commands = Path(self.temp.name) / "commands"
        self.commands.mkdir()
        self.log = self.commands / "calls.jsonl"
        self.environment = dict(os.environ, PATH=f"{self.commands}:{os.environ['PATH']}",
                                TEST_CI_LOG=str(self.log))
        for name in ("DEPLOYMENT_REPO_DIR", "SHARED_REPO_DIR", "TF_DATA_DIR",
                     "PROXMOX_VE_INSECURE", "PM_VE_INSECURE"):
            self.environment.pop(name, None)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_saved_plan_is_private_context_bound_invalidated_and_consumed(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        for stem in ("inventory/hosts", "group_vars/all", "group_vars/foundation"):
            shutil.copyfile(repo / f"ansible/{stem}.yml.example", repo / f"ansible/{stem}.yml")
        for stem in ("all", "foundation"):
            (repo / f"ansible/group_vars/{stem}.test.yml").write_text("{}\n")
        root = repo / "terraform/deployments/foundation"
        shutil.copyfile(root / "terraform.tfvars.example", root / "terraform.tfvars")
        self.executable("ansible-playbook", "#!/bin/sh\nexit 0\n")
        self.executable("terraform", """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['TEST_CI_LOG'], 'a') as output:
    output.write(json.dumps(args) + '\\n')
if args[0] == 'plan':
    if os.environ.get('TEST_FAIL_PLAN') == 'true':
        sys.exit(1)
    for arg in args:
        if arg.startswith('-out='):
            pathlib.Path(arg[5:]).write_text('disposable saved plan')
""")
        env = dict(self.environment, PROXMOX_API_URL="https://pve.invalid:8006/",
                   PROXMOX_API_TOKEN_ID="test@pve!fixture", PROXMOX_API_TOKEN_SECRET="fixture-only")

        def run(*args, overrides=None):
            return subprocess.run(["bash", "scripts/deploy.sh", "foundation", "--terraform-only", *args],
                                  cwd=repo, env=dict(env, **(overrides or {})), capture_output=True, text=True)

        plan = repo / ".terraform/plans/review.tfplan"
        context = Path(str(plan) + ".context")
        arguments = ["--plan-file", str(plan)]
        for path in ("outside.tfplan", ".terraform/plans/../outside.tfplan"):
            result = run("--plan-only", "--plan-file", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.calls())
        result = run("--plan-only", *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(context.is_file())
        self.assertEqual(plan.stat().st_mode & 0o077, 0)
        self.assertFalse(any(call[0] == "apply" for call in self.calls()))
        result = run("--env", "test", *arguments)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Saved plan context does not match", result.stderr)
        self.assertTrue(plan.is_file())
        local_vars = repo / "ansible/group_vars/foundation.yml"
        original = local_vars.read_text()
        local_vars.write_text(original + "\n# changed after review\n")
        changed = run(*arguments)
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("Saved plan context does not match", changed.stderr)
        self.assertFalse(any(call[0] == "apply" for call in self.calls()))
        local_vars.write_text(original)
        result = run(*arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        apply = next(call for call in self.calls() if call[0] == "apply")
        self.assertEqual(apply, ["apply", "-input=false", "-lock-timeout=60s", str(plan)])
        self.assertFalse(plan.exists())
        self.assertFalse(context.exists())
        self.assertNotEqual(run(*arguments).returncode, 0)
        self.assertEqual(run("--plan-only", *arguments).returncode, 0)
        result = run("--plan-only", *arguments, overrides={"TEST_FAIL_PLAN": "true"})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(plan.exists())
        self.assertFalse(context.exists())

    def test_successful_infrastructure_can_resume_failed_configuration_without_reapply(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        for stem in ("inventory/hosts", "group_vars/all", "group_vars/foundation"):
            shutil.copyfile(repo / f"ansible/{stem}.yml.example", repo / f"ansible/{stem}.yml")
        root = repo / "terraform/deployments/foundation"
        shutil.copyfile(root / "terraform.tfvars.example", root / "terraform.tfvars")
        self.executable("ansible-playbook", """#!/bin/sh
case "$*" in *control-node.yml*) exit 0;; esac
exit "${TEST_CONFIGURATION_EXIT:-0}"
""")
        self.executable("terraform", """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['TEST_CI_LOG'], 'a') as output:
    output.write(json.dumps(args) + '\\n')
for arg in args:
    if arg.startswith('-out='):
        pathlib.Path(arg[5:]).write_text('saved plan')
""")
        env = dict(self.environment, PROXMOX_API_URL="https://pve.invalid:8006/",
                   PROXMOX_API_TOKEN_ID="test@pve!fixture", PROXMOX_API_TOKEN_SECRET="fixture-only")
        args = ["bash", "scripts/deploy.sh", "foundation", "--plan-file", ".terraform/plans/retry.tfplan"]
        result = subprocess.run(args + ["--plan-only"], cwd=repo, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(args, cwd=repo, env=dict(env, TEST_CONFIGURATION_EXIT="7"),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        marker = repo / ".terraform/plans/retry.tfplan.applied.context"
        self.assertTrue(marker.is_file())
        result = subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sum(call[0] == "apply" for call in self.calls()), 1)
        self.assertFalse(marker.exists())

    def test_trusted_ci_rejects_implicit_trust_dirty_shared_and_cleans_job_secrets(self):
        repo = self.commands / "tier-0"
        shared = self.commands / "shared"
        (repo / "scripts").mkdir(parents=True)
        (shared / "scripts").mkdir(parents=True)
        (repo / ".deployment-setups").write_text("foundation\n")
        (repo / "approved.env").write_text("# Non-secret deployment settings only\n")
        self.executable("git", """#!/usr/bin/env python3
import os, sys
if 'rev-parse' in sys.argv:
    print('a' * 40)
if 'diff' in sys.argv and 'shared' in ' '.join(sys.argv) and os.getenv('TEST_DIRTY_SHARED'):
    sys.exit(1)
""")
        self.executable("vault", """#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ['TEST_CI_LOG'], 'a') as output:
    output.write(json.dumps(args) + '\\n')
if args[0] == 'write':
    assert sys.stdin.read() == 'fixture-id-token'
    print('fixture-vault-token')
elif args[:2] == ['kv', 'get']:
    print('fixture-secret')
""")
        deploy = shared / "scripts/deploy.sh"
        deploy.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
key = pathlib.Path(os.environ['ANSIBLE_PRIVATE_KEY_FILE'])
assert key.read_text().strip() == 'fixture-secret'
assert key.stat().st_mode & 0o077 == 0
assert 'VAULT_ID_TOKEN' not in os.environ
with open(os.environ['TEST_CI_LOG'], 'a') as output:
    output.write(json.dumps(['deploy', sys.argv[1:], str(key)]) + '\\n')
sys.exit(int(os.environ.get('TEST_DEPLOY_EXIT', '0')))
""")
        # The entry point invokes Bash, so use a shell adapter around the test double.
        deploy.rename(shared / "scripts/deploy-fixture.py")
        deploy.write_text('#!/bin/sh\nexec python3 "$IAC_SHARED_DIR/scripts/deploy-fixture.py" "$@"\n')
        env = dict(self.environment, IAC_TRUST_CI_CONTROL_PLANE="true", IAC_REPOSITORY_DIR=str(repo),
                   IAC_SHARED_DIR=str(shared), IAC_SHARED_REVISION="a" * 40, IAC_SETUP="foundation",
                   IAC_ENV_FILE=str(repo / "approved.env"), VAULT_ADDR="https://vault.invalid",
                   VAULT_CACERT=str(repo / "ca.pem"), VAULT_ROLE="tier0", VAULT_SECRET_PATH="kv/ci/tier0",
                   VAULT_ID_TOKEN="fixture-id-token", CI_COMMIT_SHA="a" * 40,
                   CI_PIPELINE_ID="123", CI_COMMIT_REF_PROTECTED="true")

        def run(overrides=None):
            return subprocess.run(["bash", str(UPSTREAM / "shared/scripts/gitlab-iac.sh"), "plan"],
                                  cwd=repo, env=dict(env, **(overrides or {})), capture_output=True, text=True)

        for denied in ({"IAC_TRUST_CI_CONTROL_PLANE": "false"}, {"CI_COMMIT_REF_PROTECTED": "false"},
                       {"CI_DEBUG_TRACE": "true"}, {"VAULT_SKIP_VERIFY": "true"},
                       {"TF_VAR_proxmox_api_token_secret": "old-credential"},
                       {"TEST_DIRTY_SHARED": "true"}):
            self.assertNotEqual(run(denied).returncode, 0)
            self.assertFalse(self.calls())
        for status in (0, 7):
            self.log.unlink(missing_ok=True)
            result = run({"TEST_DEPLOY_EXIT": str(status)})
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            call = next(call for call in self.calls() if call[0] == "deploy")
            self.assertIn("--plan-only", call[1])
            self.assertIn(".terraform/plans/ci-123-foundation.tfplan", call[1])
            self.assertFalse(Path(call[2]).exists())
            self.assertIn(["token", "revoke", "-self"], self.calls())
            self.assertNotIn("fixture-secret", result.stdout + result.stderr + self.log.read_text())


if __name__ == "__main__":
    unittest.main()
