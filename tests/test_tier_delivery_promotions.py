"""Offline promotion tests using real Git CAS and a local Kubernetes HTTP fixture."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
import copy
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

SCRIPTS = UPSTREAM / "tier-1/scripts"
sys.path.insert(0, str(SCRIPTS))
from promotion_git import (PromotionError, Repository, canonical, decode_plan, encode_plan,
                           validate_policy, validate_signing_key)
from promotion_flux import KubernetesReader, ready, target_healthy, wait_for_release
import promote

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
    state = {"application": None, "pipelines": {}, "writes": []}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, value, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
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
        self.assertEqual(decode_plan(encode_plan(plan)), plan)
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

    def test_execute_rejects_a_changed_preview_before_push(self):
        repository = self.repository()
        plan = self.plan(repository)
        plan["diff"] += "tampered"
        with patch.dict(os.environ, PROMOTION_PLAN_B64=encode_plan(plan)):
            with self.assertRaisesRegex(PromotionError, "Approved preview changed"):
                promote.run("execute", self.policy, repository, None)
        self.assertEqual(repository.head("delivery"), self.base)

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
        with patch.object(sys, "argv", ["promote.py", "preview", "--policy", str(policy)]), patch.dict(
                os.environ, PROMOTION_SIGNING_KEY=str(signing_key)), patch.object(
                promote, "Repository"), patch.object(promote, "run", return_value=output), redirect_stdout(captured):
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
            self.assertEqual(pod["containers"][0]["securityContext"]["capabilities"]["drop"], ["ALL"])
        resources = list(yaml.safe_load_all(environment.from_string((UPSTREAM /
            "tier-1/ansible/roles/delivery_promotion/templates/resources.yml.j2").read_text()).render(values)))
        for role in (item for item in resources if item["kind"] == "Role"):
            for rule in role["rules"]:
                self.assertEqual(rule["verbs"], ["get"])
                self.assertTrue(rule["resourceNames"])
                self.assertNotIn("secrets", rule["resources"])


class PromotionPipelineImport(TierRepositoryTestCase):
    def test_generated_payload_contains_worker_and_preserves_project_pipeline(self):
        self.generate()
        generated = self.root / "verify-tier-1"
        for relative in ("scripts/promote.py", "scripts/promotion_git.py", "scripts/promotion_flux.py",
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
        inputs["delivery_promotion_controls_accepted"] = dict.fromkeys(inputs["delivery_promotion_controls_accepted"], True)
        return inputs

    def run_role(self, inputs):
        variables = Path(self.temp.name) / "inputs.json"
        variables.write_text(json.dumps(inputs))
        return subprocess.run(["ansible-playbook", "-i", "localhost,",
                               "ansible/playbooks/deployment/delivery-promotions.yml", "-e", "@" + str(variables)],
                              cwd=UPSTREAM / "tier-1", capture_output=True, text=True, timeout=300,
                              env=dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / "tier-1/ansible/ansible.cfg")))

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
        inputs["delivery_promotion_controls_accepted"]["executor_api_job_and_credential_bypass"] = False
        result = self.run_role(inputs)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
