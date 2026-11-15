"""Offline promotion tests using real Git CAS and a local Kubernetes HTTP fixture."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import io
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import jinja2
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from backup_storage_api_support import BackupStorageAPI

SCRIPTS = UPSTREAM / "tier-1/scripts"
sys.path.insert(0, str(SCRIPTS))
from promotion_git import (PromotionError, Repository, canonical,
                           validate_policy, validate_signing_key)
from promotion_flux import KubernetesReader, ready, target_healthy, wait_for_release
import promote
from promotion_authority import Authority, approval_instructions, json_request, verify_client

DIGEST = "sha256:" + "a" * 64
OTHER_DIGEST = "sha256:" + "b" * 64
NATIVE = os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("openssl")


def helm_manifest():
    return {"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease",
            "metadata": {"namespace": "example", "name": "example"},
            "spec": {"interval": "1m", "serviceAccountName": "application-reconciler",
                     "chart": {"spec": {"chart": "example", "version": "1.2.3", "sourceRef": {
                         "kind": "HelmRepository", "name": "application-charts", "namespace": "example"}}},
                     "values": {"image": {"repository": "registry.test/app", "tag": "old"}}}}


def mark_ready(resource):
    resource["metadata"]["generation"] = 2
    resource["status"] = {"observedGeneration": 2, "conditions": [
        {"type": "Ready", "status": "True", "observedGeneration": 2}]}
    return resource


@contextmanager
def kubernetes_fixture(objects, token):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.command, self.path, self.headers.get("Authorization")))
            if self.headers.get("Authorization") != "Bearer " + token:
                self.send_error(403)
                return
            value = objects.get(self.path)
            self.send_response(200 if value is not None else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(value or {}).encode())

        def log_message(self, *arguments):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port), calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def gate_fixture(directory):
    certificate = directory / "gate.crt"
    key = directory / "gate.key"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key),
                    "-out", str(certificate), "-days", "1", "-subj", "/CN=localhost", "-addext",
                    "subjectAltName=IP:127.0.0.1"], capture_output=True, check=True, timeout=30)
    state = {"application": None, "pipelines": {}, "writes": [], 'executions': {}, 'permissions': {},
             'retired_token': {'id': 17, 'revoked': False}, 'fail_revoke': False}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, value, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == '/api/v4/personal_access_tokens/17':
                return self.reply(state['retired_token'])
            if path == '/redirect':
                self.send_response(302)
                self.send_header('Location', 'https://credential-sink.invalid/')
                self.end_headers()
                return
            if path.startswith('/pipelines/'):
                return self.reply(state['executions'].get(path.rsplit('/', 1)[1], {}))
            if path.startswith('/authorize/'):
                return self.reply(state['permissions'].get(path.rsplit('/', 1)[1], {}))
            if path == "/pipelineConfigs":
                return self.reply(list(state["pipelines"].values()))
            if path.startswith("/tasks/"):
                return self.reply({"status": "SUCCEEDED"})
            if "/pipelineConfigs/" in path:
                pipeline = state["pipelines"].get(path.rsplit("/", 1)[1])
                return self.reply(pipeline or {}, 200 if pipeline else 404)
            return self.reply({"attributes": state["application"]} if state["application"] else {},
                              200 if state["application"] else 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["writes"].append((self.path, body))
            if self.path.endswith("/tasks"):
                state["application"] = body["job"][0]["application"]
                return self.reply({"ref": "/tasks/permissions"})
            if self.path == "/pipelines?staleCheck=true":
                current = state["pipelines"].get(body["name"])
                if current and body.get("updateTs") != current["updateTs"]:
                    return self.reply({"error": "stale pipeline"}, 409)
                state["pipelines"][body["name"]] = dict(body, updateTs="revision-" + str(len(state["writes"])))
                return self.reply({})
            return self.reply({}, 404)

        def do_DELETE(self):
            if self.path != '/api/v4/personal_access_tokens/17':
                return self.reply({}, 404)
            if state['fail_revoke']:
                return self.reply({'error': 'fixture unavailable'}, 503)
            state['retired_token']['revoked'] = True
            self.send_response(204)
            self.end_headers()

        def log_message(self, *arguments):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(certificate), str(key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "https://127.0.0.1:" + str(server.server_port), certificate, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class DeliveryPromotions(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.work = Path(self.temp.name) / "author"
        self.work.mkdir()
        self.remote = Path(self.temp.name) / "application.git"
        self.command("init", "--bare", str(self.remote))
        self.command("init", str(self.work))
        self.command("config", "user.name", "Fixture")
        self.command("config", "user.email", "fixture@example.test")
        self.command("config", "commit.gpgsign", "false")
        self.path = self.work / "apps/example/helmrelease.json"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(canonical(helm_manifest()))
        self.command("add", ".")
        self.command("commit", "-m", "Initial application fixture")
        self.base = self.command("rev-parse", "HEAD")
        self.command("push", str(self.remote), "HEAD:refs/heads/delivery")
        revised = helm_manifest()
        revised["spec"]["values"]["replicaCount"] = 2
        self.path.write_text(canonical(revised))
        self.command("add", ".")
        self.command("commit", "-m", "New application configuration")
        self.config = self.command("rev-parse", "HEAD")
        self.command("push", str(self.remote), "HEAD:refs/heads/configuration")
        self.policy = {
            "repository": "https://gitlab.test/delivery/application.git", "branch": "delivery",
            "manifest_path": "apps/example/helmrelease.json", "kustomization_path": "./apps",
            "application_namespaces": ["example"],
            "target": {"kind": "HelmRelease", "namespace": "example", "name": "example"},
            "chart_source": {"kind": "HelmRepository", "name": "application-charts", "namespace": "example"},
            "image_repository": "registry.test/app", "commit_email": "delivery@example.test"}
        self.request = {"base": self.base, "config_revision": self.config, "image_digest": DIGEST,
                        "release_id": "release-1", "mode": "promote", "compatibility_reference": "review-123"}

    def command(self, *arguments):
        result = subprocess.run(["git", *arguments], cwd=self.work, capture_output=True, text=True,
                                timeout=30, env=dict(os.environ, GIT_CONFIG_NOSYSTEM="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def repository(self, name="worker"):
        return Repository(Path(self.temp.name) / name, str(self.remote))

    def plan(self, repository=None, **changes):
        return (repository or self.repository()).candidate(self.policy, dict(self.request, **changes), None)

    def observation_objects(self, plan):
        source = mark_ready({"metadata": {}, "spec": {"url": self.policy["repository"], "ref": {"branch": "delivery"}}})
        source["status"]["artifact"] = {"revision": "delivery@sha1:" + plan["candidate"]}
        kustomization = mark_ready({"metadata": {}, "spec": {"path": "./apps",
            "serviceAccountName": "application-reconciler", "sourceRef": {"kind": "GitRepository", "name": "tier1-applications"}}})
        kustomization["status"]["lastAppliedRevision"] = "delivery@sha1:" + plan["candidate"]
        live = mark_ready(copy.deepcopy(plan["desired"]))
        return {
            "/apis/source.toolkit.fluxcd.io/v1/namespaces/flux-system/gitrepositories/tier1-applications": source,
            "/apis/kustomize.toolkit.fluxcd.io/v1/namespaces/flux-system/kustomizations/tier1-applications": kustomization,
            "/apis/helm.toolkit.fluxcd.io/v2/namespaces/example/helmreleases/example": live}

    def test_deterministic_exact_preview_changes_only_application_file(self):
        repository = self.repository()
        plan = self.plan(repository)
        other = self.plan(self.repository("retry"))
        self.assertEqual(plan, other)
        self.assertEqual(repository.head("delivery"), self.base)
        self.assertEqual(repository.git("diff", "--name-only", self.base, plan["candidate"]),
                         "apps/example/helmrelease.json")
        self.assertIn(DIGEST, plan["diff"])
        self.assertIn(self.config, plan["diff"])
        self.assertNotIn("tag", plan["desired"]["spec"]["values"]["image"])

    def test_git_racing_promotions_use_exact_compare_and_swap(self):
        repositories = [self.repository("first"), self.repository("second")]
        plans = [self.plan(repositories[0]), self.plan(repositories[1], release_id="release-2", image_digest=OTHER_DIGEST)]
        barrier = threading.Barrier(2)

        def publish(index):
            barrier.wait()
            try:
                return repositories[index].publish(self.policy, plans[index])
            except PromotionError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(publish, range(2)))
        self.assertEqual(sorted(results), ["published", "rejected"])
        winner = results.index("published")
        self.assertEqual(repositories[winner].head("delivery"), plans[winner]["candidate"])
        self.assertEqual(repositories[winner].publish(self.policy, plans[winner]), "already-published")
        with self.assertRaisesRegex(PromotionError, "Superseded"):
            repositories[1-winner].publish(self.policy, plans[1-winner])

    def test_transport_failure_after_accepted_push_is_idempotent(self):
        repository = self.repository()
        plan = self.plan(repository)
        native_git = repository.git

        def lost_reply(*arguments, **kwargs):
            result = native_git(*arguments, **kwargs)
            if arguments[0] == "push":
                raise PromotionError("fixture lost reply")
            return result

        with patch.object(repository, "git", side_effect=lost_reply):
            self.assertEqual(repository.publish(self.policy, plan), "published")

    def test_rejects_mutable_inputs_and_rollback_without_compatibility(self):
        repository = self.repository()
        for invalid in ({"image_digest": "latest"}, {"config_revision": "main"},
                        {"mode": "rollback", "compatibility_reference": ""}):
            with self.subTest(invalid=invalid), self.assertRaises(PromotionError):
                self.plan(repository, **invalid)
        plan = self.plan(repository, mode="rollback", config_revision=self.base)
        self.assertEqual(plan["desired"]["metadata"]["annotations"]["delivery.homelab/mode"], "rollback")

    def test_cli_cannot_execute_a_legacy_unsigned_plan_locally(self):
        with patch.dict(os.environ, PROMOTION_PLAN_B64='untrusted-legacy-plan'), patch.object(
                sys, 'argv', ['promote.py', 'execute']), patch('promotion_client.request',
                side_effect=PromotionError('Authority denied')) as client, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                promote.main()
        client.assert_called_once_with('execute')
        self.assertFalse(hasattr(promote, 'run'))

    @unittest.skipUnless(shutil.which("ssh-keygen"), "Requires OpenSSH for real SSH-signature verification")
    def test_worker_creates_repeatable_signed_commits(self):
        key_directory = self.enterContext(tempfile.TemporaryDirectory(prefix="promotion-signing-"))
        key = str(Path(key_directory) / "signing-key")
        generated = subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-f", key],
                                   capture_output=True, text=True, timeout=20)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        repository = self.repository()
        first = repository.candidate(self.policy, self.request, key)
        second = repository.candidate(self.policy, self.request, key)
        self.assertEqual(first["candidate"], second["candidate"])
        self.assertIn("BEGIN SSH SIGNATURE", repository.git("cat-file", "commit", first["candidate"]))
        allowed = Path(key_directory) / "allowed-signers"
        allowed.write_text("delivery@example.test " + Path(key + ".pub").read_text())
        repository.git("-c", "gpg.format=ssh", "-c", "gpg.ssh.allowedSignersFile=" + str(allowed),
                       "verify-commit", first["candidate"])

    @unittest.skipUnless(shutil.which("ssh-keygen"), "Requires OpenSSH")
    def test_randomized_signing_algorithms_are_rejected(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(prefix="promotion-rsa-"))
        key = str(Path(directory) / "key")
        subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "2048", "-N", "", "-f", key],
                       capture_output=True, check=True, timeout=30)
        with self.assertRaisesRegex(PromotionError, "Ed25519 is required"):
            validate_signing_key(key)

    def test_worker_stdout_matches_pinned_kubernetes_job_property_parser(self):
        policy = Path(self.temp.name) / "policy.json"
        policy.write_text(canonical(self.policy))
        signing_key = Path(self.temp.name) / "mounted-signing-key"
        signing_key.write_text("fixture key validated by the candidate signing tests")
        output = {"candidate": "a" * 40, "plan_b64": "fixture==", "diff": "first\nsecond\n"}
        captured = io.StringIO()
        with patch.object(sys, "argv", ["promote.py", "preview", "--policy", str(policy)]), patch(
                'promotion_client.request', return_value=output), redirect_stdout(captured):
            promote.main()
        lines = captured.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        # Pinned PropertyParser's anchored SPINNAKER_CONFIG_JSON= path parses this object.
        self.assertTrue(lines[0].startswith("SPINNAKER_CONFIG_JSON="))
        self.assertEqual(json.loads(lines[0].removeprefix("SPINNAKER_CONFIG_JSON=")), output)

    def test_http_fixture_requires_exact_revision_and_current_helm_health(self):
        repository = self.repository()
        plan = self.plan(repository)
        repository.publish(self.policy, plan)
        objects = self.observation_objects(plan)
        token_file = Path(self.temp.name) / "token"
        token_file.write_text("fixture-token")
        with kubernetes_fixture(objects, "fixture-token") as (server, calls):
            with patch("promotion_flux.ssl.create_default_context", return_value=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)):
                reader = KubernetesReader(server, str(token_file))
            wait_for_release(reader, repository, self.policy, plan, timeout=2, interval=0.001)
            self.assertTrue(all(method == "GET" and auth == "Bearer fixture-token"
                                for method, path, auth in calls))
            self.assertTrue(all("tier1-platform" not in path for method, path, auth in calls))
            source = next(value for path, value in objects.items() if "gitrepositories" in path)
            kustomization = next(value for path, value in objects.items() if "kustomizations" in path)
            live = next(value for path, value in objects.items() if "helmreleases" in path)
            cases = [(source["status"]["artifact"], "revision", "delivery@sha1:" + self.base),
                     (kustomization["status"], "lastAppliedRevision", "delivery@sha1:" + self.base),
                     (kustomization["status"], "observedGeneration", 1),
                     (live["status"], "observedGeneration", 1),
                     (live["spec"]["values"]["image"], "digest", OTHER_DIGEST)]
            for target, field, value in cases:
                with self.subTest(field=field, value=value):
                    previous = target[field]
                    target[field] = value
                    with self.assertRaisesRegex(PromotionError, "Timed out"):
                        wait_for_release(reader, repository, self.policy, plan, timeout=0.05, interval=0.001)
                    target[field] = previous
            del objects["/apis/helm.toolkit.fluxcd.io/v2/namespaces/example/helmreleases/example"]
            objects["/apis/helm.toolkit.fluxcd.io/v2/namespaces/example/helmreleases/unrelated"] = live
            with self.assertRaisesRegex(PromotionError, "Timed out"):
                wait_for_release(reader, repository, self.policy, plan, timeout=0.05, interval=0.001)

    def test_superseded_revision_cannot_report_success(self):
        repository = self.repository()
        plan = self.plan(repository)
        with self.assertRaisesRegex(PromotionError, "Superseded"):
            wait_for_release(None, repository, self.policy, plan, timeout=1, interval=0.001)

    def test_deployment_health_accepts_api_defaults_and_rejects_old_images(self):
        desired = {"apiVersion": "apps/v1", "kind": "Deployment",
                   "metadata": {"name": "example", "namespace": "example", "annotations": {}},
                   "spec": {"replicas": 2, "template": {"spec": {"containers": [
                       {"name": "app", "image": "registry.test/app@" + DIGEST}]}}}}
        live = copy.deepcopy(desired)
        live["metadata"]["generation"] = 4
        live["spec"]["template"]["spec"]["containers"][0]["imagePullPolicy"] = "IfNotPresent"
        live["status"] = {"observedGeneration": 4, "replicas": 2, "updatedReplicas": 2,
                          "readyReplicas": 2, "availableReplicas": 2,
                          "conditions": [{"type": "Available", "status": "True"}]}
        self.assertTrue(target_healthy({"desired": desired}, live))
        live["spec"]["template"]["spec"]["containers"][0]["image"] = "registry.test/app@" + OTHER_DIGEST
        self.assertFalse(target_healthy({"desired": desired}, live))

    def test_policy_rejects_platform_namespaces_and_credential_urls(self):
        validate_policy(self.policy)
        for changes in ({"repository": "https://bot:secret@gitlab.test/app.git"},
                        {"manifest_path": "../platform.json"},
                        {"target": {"kind": "HelmRelease", "namespace": "flux-system", "name": "flux"}}):
            with self.subTest(changes=changes), self.assertRaises(PromotionError):
                validate_policy(dict(self.policy, **changes))

    def test_pipeline_and_worker_rbac_render_with_native_stage_contracts(self):
        defaults = yaml.safe_load((UPSTREAM / "tier-1/ansible/roles/delivery_promotion/defaults/main.yml").read_text())
        values = dict(defaults, delivery_promotion_mode="promote",
                      delivery_promotion_pipeline_ids={"promote": "fixture-promote", "rollback": "fixture-rollback"},
                      delivery_promotion_worker_image="registry.test/worker@" + DIGEST,
                      delivery_promotion_policy=self.policy, delivery_promotion_egress=[{"to": [{"ipBlock": {"cidr": "192.0.2.1/32"}}]}])
        environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
        environment.filters["to_json"] = json.dumps
        environment.filters['hash'] = lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest()
        environment.globals['lookup'] = lambda plugin, path: 'PUBLIC CA FIXTURE'
        template = environment.from_string((UPSTREAM / "tier-1/pipelines/flux-promotion.yml.j2").read_text())
        pipeline = yaml.safe_load(template.render(values))
        self.assertEqual([stage["type"] for stage in pipeline["stages"]],
                         ["runJobManifest", "manualJudgment", "checkPreconditions", "runJobManifest"])
        self.assertEqual(pipeline["triggers"], [])
        self.assertEqual(pipeline["stages"][1]["requiredJudgmentRoles"], [values["delivery_promotion_approver_role"]])
        for stage in (pipeline["stages"][0], pipeline["stages"][-1]):
            self.assertEqual(stage["propertyFile"], "worker")
            job = stage["manifest"]
            self.assertEqual(job["metadata"]["namespace"], "delivery-promotion")
            pod = job["spec"]["template"]["spec"]
            self.assertEqual(pod["serviceAccountName"], "delivery-promoter")
            self.assertFalse(pod['automountServiceAccountToken'])
            self.assertTrue(all('secret' not in volume for volume in pod['volumes']))
            self.assertEqual(pod['volumes'][0]['projected']['sources'][0]['serviceAccountToken']['audience'],
                             'delivery-promotion-authority')
            self.assertEqual(pod["containers"][0]["securityContext"]["capabilities"]["drop"], ["ALL"])
        resources = list(yaml.safe_load_all(environment.from_string((UPSTREAM /
            "tier-1/ansible/roles/delivery_promotion/templates/resources.yml.j2").read_text()).render(values)))
        for role in (item for item in resources if item["kind"] == "Role"):
            for rule in role["rules"]:
                self.assertEqual(rule["verbs"], ["get"])
                self.assertTrue(rule["resourceNames"])
                self.assertNotIn("secrets", rule["resources"])
        authority = next(item for item in resources if item['kind'] == 'Deployment')
        self.assertEqual(authority['metadata']['namespace'], 'delivery-promotion-authority')
        self.assertEqual({volume['secret']['secretName'] for volume in authority['spec']['template']['spec']['volumes']
                          if 'secret' in volume}, {values['delivery_promotion_authority_secret'],
                              values['delivery_promotion_git_secret'], values['delivery_promotion_signing_secret']})
        review = next(item for item in resources if item['kind'] == 'ClusterRole')
        self.assertEqual(review['rules'], [{'apiGroups': ['authentication.k8s.io'],
            'resources': ['tokenreviews'], 'verbs': ['create']}])
        admission = next(item for item in resources if item['kind'] == 'ValidatingAdmissionPolicy')
        self.assertEqual(admission['spec']['failurePolicy'], 'Fail')
        client_network = next(item for item in resources if item['kind'] == 'NetworkPolicy' and
                              item['metadata']['namespace'] == 'delivery-promotion')
        self.assertEqual(client_network['spec']['podSelector'], {},
                         'An arbitrary requester Job cannot escape network isolation by omitting labels')
        deployment = next(item for item in resources if item['kind'] == 'Deployment')
        previous = deployment['spec']['template']['metadata']['annotations']['delivery.homelab/policy-sha256']
        values['delivery_promotion_policy'] = dict(values['delivery_promotion_policy'], approver_role='new-approvers')
        changed = list(yaml.safe_load_all(environment.from_string((UPSTREAM /
            'tier-1/ansible/roles/delivery_promotion/templates/resources.yml.j2').read_text()).render(values)))
        current = next(item for item in changed if item['kind'] == 'Deployment')
        self.assertNotEqual(previous, current['spec']['template']['metadata']['annotations'][
            'delivery.homelab/policy-sha256'], 'Policy changes must roll the startup-loaded authority')

    def test_authority_requires_native_actor_and_immutable_approval_before_real_git_write(self):
        policy = dict(self.policy, application='tier1promotions', pipeline_ids={'promote': 'promote-id',
            'rollback': 'rollback-id'}, approver_role='approvers', ticket_ttl_seconds=3600)
        execution = {'id': 'execution-1', 'application': 'tier1promotions', 'pipelineConfigId': 'promote-id',
                     'status': 'RUNNING', 'stages': [{'refId': 'approval', 'type': 'manualJudgment',
                        'status': 'RUNNING', 'context': {}}]}
        @contextmanager
        def repository():
            with tempfile.TemporaryDirectory(dir=self.temp.name) as directory:
                yield Repository(directory, str(self.remote))
        permissions = {'requester': {'name': 'requester', 'roles': [{'name': 'requesters'}]},
                       'approver': {'name': 'approver', 'roles': [{'name': 'approvers'}]}}
        clock = [1000]
        authority = Authority(policy, b'x' * 32, lambda identifier: copy.deepcopy(execution),
            lambda actor: permissions.get(actor, {}), repository, None, observer=lambda *args: None,
            clock=lambda: clock[0])
        request = {key: value for key, value in self.request.items() if key != 'base'}
        preview = authority.preview(dict(request, execution_id='execution-1'))
        execute = {'execution_id': 'execution-1', 'approval_ticket': preview['approval_ticket']}
        for field, replacement in (('application', 'privileged-application'), ('pipelineConfigId', 'another-pipeline')):
            original = execution[field]
            execution[field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(PromotionError, 'outside'):
                authority.execute(execute)
            execution[field] = original
        with self.assertRaises(PromotionError):
            authority.execute(execute)
        judgment = execution['stages'][0]
        judgment.update(status='SUCCEEDED', lastModified={'user': 'requester', 'lastModifiedTime': 1000000})
        judgment['context'] = {'judgmentStatus': 'continue', 'lastModifiedBy': 'approver',
            'requiredJudgmentRoles': [], 'approvalTicket': preview['approval_ticket'],
            'instructions': preview['approval_instructions']}
        with self.assertRaisesRegex(PromotionError, 'Actual judgment actor'):
            authority.execute(execute)
        judgment['lastModified']['user'] = 'approver'
        permissions['approver']['name'] = 'another-user'
        with self.assertRaisesRegex(PromotionError, 'Actual judgment actor'):
            authority.execute(execute)
        permissions['approver']['name'] = 'approver'
        retired = Authority(dict(policy, approver_role='new-approvers'), b'x' * 32,
            lambda identifier: copy.deepcopy(execution), lambda actor: permissions.get(actor, {}),
            repository, None, observer=lambda *args: None, clock=lambda: clock[0])
        with self.assertRaisesRegex(PromotionError, 'policy changed'):
            retired.execute(execute)
        for change in ({'execution_id': 'execution-2'}, {'image_digest': OTHER_DIGEST},
                       {'approval_ticket': preview['approval_ticket'][:-1] +
                        ('0' if preview['approval_ticket'][-1] != '0' else '1')}):
            with self.subTest(changed_field=next(iter(change))), self.assertRaises((PromotionError, ValueError)):
                authority.execute(dict(execute, **change))
        judgment['context']['instructions'] = 'Approve something else'
        with self.assertRaisesRegex(PromotionError, 'Judgment payload'):
            authority.execute(execute)
        judgment['context']['instructions'] = preview['approval_instructions']
        with repository() as inspection:
            self.assertEqual(inspection.head('delivery'), self.base)
        result = authority.execute(execute)
        self.assertEqual(result['git_result'], 'published')
        self.assertEqual(authority.execute(execute)['git_result'], 'already-published')
        # Another release/head cannot reuse this approval, even with the same execution and actor.
        with repository() as other:
            changed = other.candidate(policy, dict(self.request, base=preview['candidate'], release_id='other'), None)
            other.publish(policy, changed)
        with self.assertRaisesRegex(PromotionError, 'Superseded'):
            authority.execute(execute)
        clock[0] = 5000
        with self.assertRaisesRegex(PromotionError, 'expired'):
            authority.execute(execute)

    @unittest.skipUnless(NATIVE, 'Requires native OpenSSL for a verified HTTPS authority fixture')
    def test_authority_reads_execution_and_fiat_over_verified_https(self):
        with gate_fixture(Path(self.temp.name)) as (url, certificate, state):
            state['executions']['run-1'] = {'id': 'run-1', 'pipelineConfigId': 'saved-1'}
            state['permissions']['reviewer@example.test'] = {'name': 'reviewer@example.test',
                'roles': [{'name': 'approvers'}]}
            execution = json_request(url + '/pipelines/run-1', ca=str(certificate),
                                     headers={'Cookie': 'fixture-gate-session'})
            permission = json_request(url + '/authorize/reviewer%40example.test', ca=str(certificate))
            self.assertEqual(execution['pipelineConfigId'], 'saved-1')
            self.assertEqual(permission['roles'], [{'name': 'approvers'}])
            with self.assertRaises(Exception):
                json_request(url + '/pipelines/run-1')
            with self.assertRaisesRegex(PromotionError, 'must not follow'):
                json_request(url + '/redirect', ca=str(certificate),
                             headers={'Authorization': 'Bearer fixture-private-reader'})

    def test_authority_client_identity_requires_native_token_review_subject_and_audience(self):
        import promotion_authority
        accepted = {'authenticated': True, 'audiences': ['delivery-promotion-authority'],
                    'user': {'username': 'system:serviceaccount:delivery-promotion:delivery-promoter'}}
        with patch.dict(os.environ, KUBERNETES_SERVICE_HOST='api.example.test'), patch.object(
                Path, 'read_text', return_value='fixture-token'):
            for changes in ({'authenticated': False}, {'audiences': ['kubernetes']},
                            {'user': {'username': 'system:serviceaccount:default:default'}}):
                with patch.object(promotion_authority, 'json_request', return_value={'status': dict(accepted, **changes)}):
                    with self.assertRaises(PromotionError):
                        verify_client('fixture-client-token', self.policy)
            with patch.object(promotion_authority, 'json_request', return_value={'status': accepted}) as call:
                verify_client('fixture-client-token', self.policy)
                self.assertEqual(call.call_args.kwargs['body']['spec']['audiences'], ['delivery-promotion-authority'])


class PromotionPipelineImport(TierRepositoryTestCase):
    @unittest.skipUnless(NATIVE, 'Requires native Ansible and Kubernetes client modules')
    def test_native_adoption_remains_fenced_on_revocation_failure_and_retries_safely(self):
        class API(BackupStorageAPI):
            resources = dict(BackupStorageAPI.resources, secrets=('Secret', True, 'v1'),
                pods=('Pod', True, 'v1'), jobs=('Job', True, 'batch/v1'),
                deployments=('Deployment', True, 'apps/v1'))
        api = API()
        self.addCleanup(api.close)
        inputs = self.inputs(Path(self.temp.name) / 'adopt')
        kubeconfig = Path(self.temp.name) / 'kubeconfig.yml'
        kubeconfig.write_text(yaml.safe_dump(api.kubeconfig()))
        for name in inputs['delivery_promotion_credentials']:
            api.put({'apiVersion': 'v1', 'kind': 'Secret',
                     'metadata': {'name': name, 'namespace': 'delivery-promotion-authority'}})
        for kind, version, name in [('Secret', 'v1', 'delivery-promotion-git'),
                                    ('Secret', 'v1', 'delivery-promotion-signing'),
                                    ('Job', 'batch/v1', 'old-client'), ('Pod', 'v1', 'orphan-client')]:
            api.put({'apiVersion': version, 'kind': kind,
                     'metadata': {'name': name, 'namespace': 'delivery-promotion'}})
        api.put({'apiVersion': 'apps/v1', 'kind': 'Deployment',
                 'metadata': {'name': 'delivery-promotion-authority', 'namespace': 'delivery-promotion-authority',
                              'generation': 2}, 'status': {'observedGeneration': 2, 'replicas': 1,
                                                         'updatedReplicas': 1, 'availableReplicas': 1}})
        api.put({'apiVersion': 'apps/v1', 'kind': 'Deployment',
                 'metadata': {'name': 'orca', 'namespace': 'spinnaker', 'generation': 2},
                 'spec': {'replicas': 1, 'template': {'metadata': {'annotations': {
                     'delivery.homelab/request-http-profile': 'deny-user-http-v1'}}}},
                 'status': {'observedGeneration': 2, 'replicas': 1,
                            'updatedReplicas': 1, 'availableReplicas': 1}})
        with gate_fixture(Path(self.temp.name)) as (url, certificate, state):
            inputs.update(delivery_promotion_action='adopt', delivery_promotion_kubeconfig=str(kubeconfig),
                delivery_promotion_context='offline', delivery_promotion_gate_url=url,
                delivery_promotion_gate_headers={'Cookie': 'fixture-authenticated-session'},
                delivery_promotion_gate_ca_path=str(certificate), delivery_promotion_gitlab_url=url,
                delivery_promotion_retired_token_id=17, delivery_promotion_gitlab_ca_path=str(certificate),
                delivery_promotion_gitlab_headers={'PRIVATE-TOKEN': 'fixture-placeholder'})
            state['fail_revoke'] = True
            result = self.run_role(inputs)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(state['application']['permissions']['EXECUTE'], ['tier1-delivery-admins'])
            self.assertFalse(state['retired_token']['revoked'])
            self.assertFalse(api.mutations, 'No legacy credentials/clients removed before native revocation')
            state['fail_revoke'] = False
            result = self.run_role(inputs)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(state['retired_token']['revoked'])
            self.assertIn('tier1-promotion-requesters', state['application']['permissions']['EXECUTE'])
            self.assertIn('tier1-delivery-readers', state['application']['permissions']['READ'])
            self.assertNotIn('tier1-delivery-readers', state['application']['permissions']['EXECUTE'])
            self.assertNotIn('tier1-delivery-readers', state['application']['permissions']['WRITE'])
            self.assertFalse([key for key in api.objects if key[1] == 'delivery-promotion'])
            self.assertEqual(len([key for key in api.objects if key[1] == 'delivery-promotion-authority']), 4)

    def test_generated_payload_contains_worker_and_preserves_project_pipeline(self):
        self.generate()
        generated = self.root / "verify-tier-1"
        for relative in ("scripts/promote.py", "scripts/promotion_git.py", "scripts/promotion_flux.py",
                         "scripts/promotion_authority.py", "scripts/promotion_client.py",
                         "scripts/promotion/Dockerfile", "scripts/promotion/git-askpass.py",
                         "pipelines/flux-promotion.yml.j2", "ansible/playbooks/deployment/delivery-promotions.yml",
                         "ansible/group_vars/delivery_promotion.yml.example",
                         "ansible/roles/delivery_promotion/templates/application.yml.j2",
                         "ansible/roles/delivery_promotion/tasks/import-pipeline.yml"):
            self.assertEqual((generated / relative).read_bytes(), (UPSTREAM / "tier-1" / relative).read_bytes())
        pipeline = generated / "pipelines/flux-promotion.yml.j2"
        project_definition = pipeline.read_text() + "\n# Project-owned approval integration\n"
        pipeline.write_text(project_definition)
        self.generate("--refresh")
        self.assertEqual(pipeline.read_text(), project_definition)

    def inputs(self, output):
        inputs = yaml.safe_load((UPSTREAM / "tier-1/ansible/group_vars/delivery_promotion.yml.example").read_text())
        inputs.update(delivery_promotion_output=str(output),
                      delivery_promotion_flux_output="",
                      delivery_promotion_worker_image="registry.test/worker@" + DIGEST,
                      delivery_promotion_initial_image_digest=DIGEST,
                      delivery_promotion_chart_repository="https://charts.fixture.test/application",
                      delivery_promotion_chart="example", delivery_promotion_chart_version="1.2.3",
                      delivery_promotion_egress=[{"to": [{"ipBlock": {"cidr": "192.0.2.1/32"}}]}])
        authority_ca = Path(self.temp.name) / 'authority-ca.pem'
        authority_ca.write_text('PUBLIC CA FIXTURE')
        inputs.update(delivery_promotion_authority_ca_file=str(authority_ca),
                      delivery_promotion_authority_gate_url='https://spinnaker.fixture.test/api/v1',
                      delivery_promotion_authority_egress=[{'to': [{'ipBlock': {'cidr': '192.0.2.1/32'}}]}])
        inputs['delivery_promotion_credentials'] = {
            'delivery-promotion-git': {'username': 'fixture-user', 'password': 'fixture-placeholder'},
            'delivery-promotion-signing': {'key': 'fixture-signing-placeholder'},
            'delivery-promotion-authority': dict.fromkeys(
                ['ticket-key', 'gate-headers.json', 'gate-ca.pem', 'fiat-ca.pem', 'tls.crt', 'tls.key'],
                'fixture-placeholder')}
        inputs["delivery_promotion_controls_accepted"] = dict.fromkeys(inputs["delivery_promotion_controls_accepted"], True)
        return inputs

    def run_role(self, inputs, tier=None, environment=None):
        tier = tier or UPSTREAM / "tier-1"
        variables = Path(self.temp.name) / "inputs.json"
        variables.write_text(json.dumps(inputs))
        return subprocess.run(["ansible-playbook", "-i", "localhost,",
                               "ansible/playbooks/deployment/delivery-promotions.yml", "-e", "@" + str(variables)],
                              cwd=tier, capture_output=True, text=True, timeout=300,
                              env=dict(environment or os.environ, ANSIBLE_CONFIG=str(tier / "ansible/ansible.cfg")))

    @unittest.skipUnless(NATIVE, "Requires native Ansible")
    def test_export_tool_failure_stops_source_and_generated_entrypoints_before_output(self):
        self.generate()
        tools = Path(self.temp.name) / "unavailable-tools"
        tools.mkdir()
        sops = tools / "sops"
        sops.write_text("#!/bin/sh\nprintf 'Fixture unavailable SOPS\\n' >&2\nexit 1\n")
        sops.chmod(0o755)
        environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                           CONTROL_NODE_COLLECTIONS_MODE="check")
        for index, tier in enumerate((UPSTREAM / "tier-1", self.root / "verify-tier-1")):
            with self.subTest(tier=tier):
                output = Path(self.temp.name) / f"missing-tool-{index}"
                inputs = self.inputs(output)
                inputs["delivery_promotion_flux_output"] = str(Path(self.temp.name) / "platform")
                result = self.run_role(inputs, tier=tier, environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Setup delivery-promotions cannot run sops --version", result.stdout)
                self.assertFalse(output.exists(), result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and OpenSSL")
    def test_native_gate_import_is_repeatable_and_preserves_stable_ids(self):
        inputs = self.inputs(Path(self.temp.name) / "render")
        with gate_fixture(Path(self.temp.name)) as (server, certificate, state):
            inputs.update(delivery_promotion_action="import", delivery_promotion_gate_url=server,
                          delivery_promotion_gate_ca_path=str(certificate),
                          delivery_promotion_gate_headers={"Cookie": "fixture-authenticated-session"})
            for run in range(2):
                result = self.run_role(inputs)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(state["writes"]), 3)
                self.assertEqual(len(state["pipelines"]), 2)
            output = Path(inputs["delivery_promotion_output"])
            index = output / "application-source/clusters/tier1/applications/kustomization.yaml"
            self.assertEqual(yaml.safe_load(index.read_text())["resources"], ["example/helmrelease.json"])
            selected = json.loads((index.parent / "example/helmrelease.json").read_text())
            self.assertEqual(selected["spec"]["chart"]["spec"]["version"], "1.2.3")
            self.assertEqual(selected["spec"]["values"]["image"]["digest"], DIGEST)
            sources = [item for item in yaml.safe_load_all((output / "promotion-resources.yml").read_text())
                       if item["kind"] == "HelmRepository"]
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]["metadata"], {"name": "application-charts", "namespace": "applications"})
            self.assertEqual(sources[0]["spec"]["url"], "https://charts.fixture.test/application")
            self.assertEqual(state["application"]["permissions"]["WRITE"], ["tier1-delivery-admins"])
            ids = {mode: json.loads((output / (mode + ".json")).read_text())["id"] for mode in ("promote", "rollback")}
            self.assertEqual({pipeline["id"] for pipeline in state["pipelines"].values()}, set(ids.values()))
            state["pipelines"]["Flux promote"]["description"] = "External edit"
            result = self.run_role(inputs)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(state["writes"]), 4)
            self.assertEqual(state["writes"][-1][1]["updateTs"], "revision-2")
            state["pipelines"]["Flux promote"]["id"] = "unadopted-id"
            result = self.run_role(inputs)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Adopt the existing pipeline identifier", result.stdout)
            self.assertEqual(len(state["writes"]), 4)
            state["pipelines"]["Flux promote"]["id"] = ids["promote"]
            del state["pipelines"]["Flux rollback"]
            state["pipelines"]["Other application's pipeline"] = {
                "id": ids["rollback"], "name": "Other application's pipeline", "application": "anotherapp"}
            result = self.run_role(inputs)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("belongs to another application or pipeline name", result.stdout)
            self.assertEqual(len(state["writes"]), 4)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and OpenSSL")
    def test_native_deployment_seed_uses_approved_namespace_without_helm_source(self):
        output = Path(self.temp.name) / "deployment"
        inputs = self.inputs(output)
        inputs.update(delivery_promotion_target={"kind": "Deployment", "namespace": "applications", "name": "example"},
                      delivery_promotion_chart_repository="", delivery_promotion_chart="",
                      delivery_promotion_chart_version="",
                      delivery_promotion_manifest_path="clusters/tier1/applications/example/deployment.json")
        result = self.run_role(inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        index = output / "application-source/clusters/tier1/applications/kustomization.yaml"
        self.assertEqual(yaml.safe_load(index.read_text())["resources"], ["example/deployment.json"])
        selected = json.loads((index.parent / "example/deployment.json").read_text())
        self.assertEqual(selected["kind"], "Deployment")
        self.assertEqual(selected["spec"]["template"]["spec"]["containers"][0]["image"],
                         inputs["delivery_promotion_image_repository"] + "@" + DIGEST)
        resources = list(yaml.safe_load_all((output / "promotion-resources.yml").read_text()))
        self.assertFalse(any(item["kind"] == "HelmRepository" for item in resources))
        original_ids = {json.loads((output / (mode + ".json")).read_text())["id"] for mode in ("promote", "rollback")}
        inputs["delivery_promotion_application"] = "anotherapp"
        result = self.run_role(inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        new_ids = {json.loads((output / (mode + ".json")).read_text())["id"] for mode in ("promote", "rollback")}
        self.assertTrue(original_ids.isdisjoint(new_ids))
        inputs["delivery_promotion_application_namespaces"] = ["other-approved-namespace"]
        result = self.run_role(inputs)
        self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and OpenSSL")
    def test_native_admission_rejects_missing_acceptance_before_output(self):
        output = Path(self.temp.name) / "rejected"
        inputs = self.inputs(output)
        inputs['delivery_promotion_authority_gate_url'] = ''
        result = self.run_role(inputs)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
