"""Inspect retained recovery sources with native offline Kustomize, SOPS and Helm.

These checks render local artifacts and validate saved plans. They do not establish
live controller behavior, registry availability, storage attachment or recovery.
"""

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml
from jinja2 import Environment, StrictUndefined

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


SCRIPTS = UPSTREAM / "tier-1/scripts"
sys.path.insert(0, str(SCRIPTS))
import recovery_helm as HELM
import recovery_payload as PAYLOAD
import recovery_talos as TALOS


KUSTOMIZE = os.name != "nt" and shutil.which("kubectl")
NATIVE_HELM = KUSTOMIZE and shutil.which("helm")
NATIVE_SOPS = KUSTOMIZE and all(shutil.which(tool) for tool in ("sops", "age-keygen"))


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def native(*arguments, **options):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=120, **options)
    if result.returncode:
        raise AssertionError(f"Native {Path(arguments[0]).name} exited {result.returncode}\n{result.stderr}")
    return result


def object_yaml(kind, name, namespace="services", **fields):
    return {"apiVersion": "v1", "kind": kind,
            "metadata": {"name": name, "namespace": namespace}, **fields}


class SourceFixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="recovery-source-")))
        self.package = self.root / "package"
        (self.package / "artifacts").mkdir(parents=True)
        self.plan = {"workspace": str(self.root / "working"), "automation": {}, "products": [],
                     "artifact_supply": [], "package": {"directory": str(self.package)}}
        self.cluster = {"tier": 1, "cutover": {"resume_roots": []}, "source_age_keys": {}}
        self.roots = {}
        self.paths = {}
        for source in ("platform", "tier1-platform", "tier1-applications"):
            root = self.root / source
            self.roots[source] = root
            self.paths[source] = "selected"
            self.stage(root / "selected", [])

    def stage(self, path, documents):
        path.mkdir(parents=True, exist_ok=True)
        (path / "resources.yaml").write_text(yaml.safe_dump_all(documents))
        resources = ["resources.yaml"] if documents else []
        (path / "kustomization.yaml").write_text(yaml.safe_dump({
            "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
            "resources": resources}))

    def child(self, name="child", source="tier1-platform", path="child", **overrides):
        spec = {"interval": "1m", "path": path, "prune": False,
                "sourceRef": {"kind": "GitRepository", "name": source}, **overrides}
        return {"apiVersion": "kustomize.toolkit.fluxcd.io/v1", "kind": "Kustomization",
                "metadata": {"name": name, "namespace": "flux-system"}, "spec": spec}

    def inventory(self):
        return PAYLOAD.reachable_inventory(self.roots, self.paths, self.plan, self.cluster)

    def retained(self, path, content):
        repository, _, relative = path.partition("/")
        destination = Path(self.plan["workspace"]) / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
        destination.chmod(0o600)
        entry = {"path": relative, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
        self.plan["automation"].setdefault(repository, {"private_files": []})["private_files"].append(entry)
        return destination


class RecoveryAuthorityEpoch(SourceFixture):
    def setUp(self):
        super().setUp()
        key = 'fixture-' * 8
        secret = object_yaml('Secret', 'authority-credential', 'delivery-promotion-authority',
                             data={'ticket-key': base64.b64encode(key.encode()).decode()})
        self.retained('tier-1/secrets/authority.yaml', yaml.safe_dump(secret))
        self.plan['promotion_authority'] = {
            'secret_file': 'tier-1/secrets/authority.yaml',
            'new_ticket_key_sha256': hashlib.sha256(key.encode()).hexdigest()}
        self.documents = [copy.deepcopy(secret), object_yaml('Deployment', 'delivery-promotion-authority',
            'delivery-promotion-authority', spec={'template': {'spec': {'volumes': [
                {'name': 'authority', 'secret': {'secretName': 'authority-credential'}}]}}})]

    def test_operating_source_carries_the_originally_accepted_replacement_epoch(self):
        PAYLOAD.verify_authority_epoch(self.documents, self.plan)
        secret = self.documents[0]
        secret['stringData'] = {'ticket-key': base64.b64decode(secret['data']['ticket-key']).decode()}
        PAYLOAD.verify_authority_epoch(self.documents, self.plan)

    def test_old_missing_or_overriding_ticket_key_blocks_source_resumption(self):
        original = copy.deepcopy(self.documents)
        for variant in ('old-data', 'overriding-stringData', 'missing-secret'):
            self.documents = copy.deepcopy(original)
            if variant == 'missing-secret':
                self.documents.pop(0)
            elif variant == 'old-data':
                self.documents[0]['data']['ticket-key'] = base64.b64encode(b'obsolete ticket identity').decode()
            else:
                self.documents[0]['stringData'] = {'ticket-key': 'obsolete ticket identity'}
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'replacement.*epoch'):
                PAYLOAD.verify_authority_epoch(self.documents, self.plan)

    def test_authority_cannot_mount_another_credential_after_verified_rotation(self):
        self.documents[1]['spec']['template']['spec']['volumes'][0]['secret']['secretName'] = 'old-credential'
        with self.assertRaisesRegex(ValueError, 'must mount'):
            PAYLOAD.verify_authority_epoch(self.documents, self.plan)


@unittest.skipUnless(KUSTOMIZE, "Requires native kubectl kustomize")
class RecoverySourceGraph(SourceFixture):
    def test_native_git_packages_use_checksum_bound_bootstrap_paths_and_accepted_commits(self):
        self.stage(self.roots["platform"] / "selected", [self.child()])
        self.stage(self.roots["tier1-platform"] / "child", [object_yaml("ConfigMap", "retained")])
        sources = {}
        for name, root in self.roots.items():
            self.stage(root / "unreferenced", [object_yaml("PersistentVolumeClaim", "unrestored")])
            native("git", "init", "--quiet", str(root))
            native("git", "-C", str(root), "add", "--all")
            native("git", "-C", str(root), "-c", "user.name=Offline recovery fixture",
                   "-c", "user.email=recovery@example.test", "-c", "commit.gpgsign=false",
                   "commit", "--quiet", "-m", "Retain selected recovery source")
            commit = native("git", "-C", str(root), "rev-parse", "HEAD").stdout.strip()
            native("git", "-C", str(root), "bundle", "create", str(self.package / (name + ".bundle")), "HEAD")
            sources[name] = {"commit": commit, "bundle": name + ".bundle"}
        (self.package / "manifest.json").write_text(json.dumps({"sources": sources}))
        self.plan["package"]["sources"] = {name: value["commit"] for name, value in sources.items()}
        bootstrap = self.retained("tier-1/secrets/bootstrap.yaml", yaml.safe_dump({
            "cluster_platform_flux_path": "selected", "cluster_platform_flux_platform_path": "selected",
            "cluster_platform_flux_application_path": "selected"}))
        self.cluster["bootstrap_inputs"] = "tier-1/secrets/bootstrap.yaml"
        self.plan["clusters"] = [self.cluster]
        self.assertEqual(PAYLOAD.operating_resources(self.plan), [])
        bootstrap.write_text(bootstrap.read_text() + "\n# changed after approval\n")
        with self.subTest(case="changed private bootstrap"), self.assertRaisesRegex(ValueError, "checksum-bound"):
            PAYLOAD.operating_resources(self.plan)
        self.plan["package"]["sources"]["platform"] = "0" * 40
        with self.subTest(case="wrong accepted source commit"), self.assertRaisesRegex(ValueError, "accepted source commit"):
            PAYLOAD.operating_resources(self.plan)

    def test_only_selected_reachable_sources_and_children_enter_inventory(self):
        self.stage(self.roots["platform"] / "selected", [self.child()])
        self.stage(self.roots["tier1-platform"] / "child", [
            object_yaml("ConfigMap", "selected-platform"),
            self.child(name="application-child", source="tier1-applications", path="workloads")])
        self.stage(self.roots["tier1-applications"] / "workloads", [object_yaml("ConfigMap", "selected-app")])
        for root in self.roots.values():
            (root / "unreferenced.yaml").write_text("not: [valid YAML")
            self.stage(root / "abandoned", [object_yaml("PersistentVolumeClaim", "unrestored")])
        documents = self.inventory()
        names = {item["metadata"]["name"]: item for item in documents}
        self.assertEqual(set(names), {"child", "application-child", "selected-platform", "selected-app"})
        self.assertEqual(names["selected-platform"]["_recovery_source"], "tier1-platform")
        self.assertEqual(names["selected-app"]["_recovery_source"], "tier1-applications")
        PAYLOAD.inspect_inventory(documents, [], 1)

    def test_intentionally_paused_child_is_followed_only_for_selected_resume(self):
        self.stage(self.roots["platform"] / "selected", [self.child(suspend=True)])
        self.stage(self.roots["tier1-platform"] / "child", [object_yaml("ConfigMap", "resumed-child")])
        self.assertNotIn("resumed-child", [item["metadata"]["name"] for item in self.inventory()])
        self.cluster["cutover"]["resume_roots"] = ["child"]
        self.assertIn("resumed-child", [item["metadata"]["name"] for item in self.inventory()])

    def test_every_source_requires_its_explicit_selected_path(self):
        del self.paths["tier1-platform"]
        with self.assertRaisesRegex(ValueError, "source_paths"):
            self.inventory()

    def test_remote_missing_and_escaping_local_resources_are_refused(self):
        stage = self.roots["platform"] / "selected"
        outside = self.root / "outside.yaml"
        outside.write_text(yaml.safe_dump(object_yaml("ConfigMap", "outside")))
        references = ["https://unavailable.invalid/kustomize", "git::https://unavailable.invalid/repo",
                      "github.com/example/repo//base", "gitlab.com/example/repo//base",
                      "../../outside.yaml", "missing.yaml"]
        for reference in references:
            with self.subTest(reference=reference):
                (stage / "kustomization.yaml").write_text(yaml.safe_dump({"resources": [reference]}))
                with self.assertRaises(ValueError):
                    PAYLOAD.check_local_build(self.roots["platform"].resolve(), stage)

    def test_escaping_or_missing_flux_child_cannot_select_other_files(self):
        for path in ("../outside", "missing"):
            with self.subTest(path=path):
                self.stage(self.roots["platform"] / "selected", [self.child(path=path)])
                with self.assertRaises(ValueError):
                    self.inventory()

    def test_unretained_or_non_git_flux_source_is_refused(self):
        for reference in ({"kind": "GitRepository", "name": "unretained"},
                          {"kind": "OCIRepository", "name": "tier1-platform"}):
            with self.subTest(reference=reference):
                self.stage(self.roots["platform"] / "selected", [self.child(sourceRef=reference)])
                with self.assertRaisesRegex(ValueError, "unretained source"):
                    self.inventory()

    def test_runtime_transformations_cannot_bypass_inspected_manifests(self):
        transforms = {"postBuild": {"substitute": {"IMAGE": "unretained"}},
                      "patches": [{"patch": "opaque-patch"}], "images": [{"name": "unretained"}],
                      "components": ["unretained"], "targetNamespace": "other",
                      "commonMetadata": {"labels": {"uninspected": "true"}}}
        for field, value in transforms.items():
            with self.subTest(field=field):
                self.stage(self.roots["platform"] / "selected", [self.child(**{field: value})])
                with self.assertRaisesRegex(ValueError, "runtime transformations"):
                    self.inventory()

    def test_opaque_active_helm_release_is_refused(self):
        release = {"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease",
                   "metadata": {"name": "harbor", "namespace": "harbor"}, "spec": {}}
        self.stage(self.roots["tier1-platform"] / "selected", [release])
        with self.assertRaisesRegex(ValueError, "retained native chart render contract"):
            self.inventory()


@unittest.skipUnless(NATIVE_SOPS, "Requires native SOPS, age-keygen and kubectl")
class RecoverySourceSecrets(SourceFixture):
    def encrypted(self, source, name):
        path = self.root / (source + ".agekey")
        native("age-keygen", "-o", str(path))
        recipient = native("age-keygen", "-y", str(path)).stdout.strip()
        key = self.retained("tier-1/secrets/" + source + ".agekey", path.read_text())
        self.cluster["source_age_keys"][source] = "tier-1/secrets/" + source + ".agekey"
        plain = self.root / (source + ".plain.yaml")
        plain.write_text(yaml.safe_dump(object_yaml("Secret", name,
            stringData={"password": "offline-selected-secret"})))
        encrypted = native("sops", "--encrypt", "--age", recipient, "--encrypted-regex",
                           "^(data|stringData)$", str(plain)).stdout
        self.stage(self.roots[source] / "selected", [yaml.safe_load(encrypted)])
        return key

    def test_each_source_decrypts_using_its_checksum_bound_private_age_key(self):
        for source in self.roots:
            self.encrypted(source, "secret-" + source)
        documents = self.inventory()
        self.assertEqual(len(documents), 3)
        self.assertTrue(all(item["stringData"]["password"] == "offline-selected-secret" for item in documents))
        self.assertTrue(all("sops" not in item for item in documents))

    def test_missing_changed_or_wrong_source_age_key_blocks_inventory(self):
        key = self.encrypted("tier1-platform", "private")
        accepted = key.read_text()
        with self.subTest(case="missing source binding"):
            del self.cluster["source_age_keys"]["tier1-platform"]
            with self.assertRaises(ValueError):
                self.inventory()
        self.cluster["source_age_keys"]["tier1-platform"] = "tier-1/secrets/tier1-platform.agekey"
        with self.subTest(case="modified custody file"):
            key.write_text(accepted + "\n# changed after acceptance\n")
            with self.assertRaisesRegex(ValueError, "checksum-bound"):
                self.inventory()
        key.write_text(accepted)
        wrong = self.root / "wrong.agekey"
        native("age-keygen", "-o", str(wrong))
        self.retained("tier-1/secrets/wrong.agekey", wrong.read_text())
        self.cluster["source_age_keys"]["tier1-platform"] = "tier-1/secrets/wrong.agekey"
        with self.subTest(case="other retained source key"), self.assertRaises(subprocess.CalledProcessError):
            self.inventory()


@unittest.skipUnless(NATIVE_HELM, "Requires native Helm and kubectl")
class RecoveryHelmContracts(SourceFixture):
    def platform_chart(self):
        """A small local chart exercises native Helm without fetching a live repository."""
        root = self.root / "fixture-chart"
        (root / "templates").mkdir(parents=True)
        (root / "Chart.yaml").write_text("apiVersion: v2\nname: flux2\nversion: 2.17.0\n")
        (root / "values.yaml").write_text("replicas: 1\n")
        (root / "templates/controller.yaml").write_text("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-source-controller
spec:
  replicas: {{ .Values.replicas }}
  selector:
    matchLabels: {app: source-controller}
  template:
    metadata:
      labels: {app: source-controller}
    spec:
      containers:
        - name: source-controller
          image: ghcr.io/fluxcd/source-controller:v1.7.0
""")
        native("helm", "package", str(root), "--destination", str(self.package / "artifacts"))
        return self.release("flux2", "2.17.0", "flux-system"), "flux2-2.17.0.tgz", []

    def release(self, chart, version, namespace):
        return {"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease",
                "metadata": {"name": chart, "namespace": namespace},
                "spec": {"interval": "1m", "releaseName": chart,
                         "chart": {"spec": {"chart": chart, "version": version,
                                            "sourceRef": {"kind": "HelmRepository", "name": "retained"}}}}}

    def lock(self, archive):
        path = self.package / "artifacts" / archive
        (self.package / "artifact-lock.json").write_text(json.dumps({"files": [
            {"path": archive, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]}))

    def prepare(self, release, archive, objects=None, product=None):
        self.lock(archive)
        release_file, objects_file = self.root / "release.yaml", self.root / "objects.yaml"
        release_file.write_text(yaml.safe_dump(release))
        objects_file.write_text(yaml.safe_dump_all(objects or []))
        output = self.root / "accepted-contract.json"
        arguments = [sys.executable, str(SCRIPTS / "recovery_helm.py"), "--release", str(release_file),
                     "--objects", str(objects_file), "--package", str(self.package), "--archive", archive,
                     "--source", "tier1-platform", "--kube-version", "1.34.0", "--output", str(output)]
        arguments.extend(["--product", product["name"], "--product-kind", product["kind"]]
                         if product else ["--platform-chart"])
        result = native(*arguments)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        contract = json.loads(output.read_text())
        self.assertEqual(contract["spec_sha256"], canonical_sha256(release["spec"]))
        for field in ("spec_sha256", "values_sha256", "render_sha256"):
            self.assertRegex(contract[field], r"^[a-f0-9]{64}$")
        return contract

    def object_map(self, objects):
        return {(item["kind"], item["metadata"]["namespace"], item["metadata"]["name"]): item
                for item in objects}

    def test_native_cli_prepares_private_hash_only_flux2_contract_and_retries(self):
        release, archive, objects = self.platform_chart()
        secret_value = "offline-private-flux-values-do-not-emit"
        objects = [object_yaml("Secret", "flux-values", "flux-system",
            data={"values.yaml": base64.b64encode(yaml.safe_dump({"replicas": 2,
                "privateFixture": secret_value}).encode()).decode()})]
        release["spec"]["valuesFrom"] = [{"kind": "Secret", "name": "flux-values"}]
        contract = self.prepare(release, archive, objects)
        self.assertNotIn(secret_value, json.dumps(contract))
        self.assertNotIn("values", contract)
        self.assertNotIn("spec", contract)
        first = HELM.render_release(release, contract, self.object_map(objects), self.package, [])
        second = HELM.render_release(release, contract, self.object_map(objects), self.package, [])
        self.assertEqual(first, second)
        self.assertEqual(first[0]["spec"]["replicas"], 2)
        self.assertTrue(first[0]["_recovery_platform_chart"])
        PAYLOAD.inspect_inventory(first, [], 1)

    def test_changed_archive_release_values_and_render_are_denied(self):
        release, archive, objects = self.platform_chart()
        objects = [object_yaml("ConfigMap", "values", "flux-system", data={"values.yaml": "replicas: 2\n"})]
        release["spec"]["valuesFrom"] = [{"kind": "ConfigMap", "name": "values"}]
        contract = self.prepare(release, archive, objects)
        with self.subTest(case="changed specification"):
            changed = copy.deepcopy(release)
            changed["spec"]["values"] = {"replicas": 7}
            with self.assertRaisesRegex(ValueError, "accepted native specification"):
                HELM.render_release(changed, contract, self.object_map(objects), self.package, [])
        with self.subTest(case="changed values object"):
            changed = copy.deepcopy(objects)
            changed[0]["data"]["values.yaml"] = "replicas: 7\n"
            with self.assertRaisesRegex(ValueError, "values differ"):
                HELM.render_release(release, contract, self.object_map(changed), self.package, [])
        with self.subTest(case="changed output hash"):
            changed = {**contract, "render_sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "render differs"):
                HELM.render_release(release, changed, self.object_map(objects), self.package, [])
        with self.subTest(case="changed archive bytes"):
            path = self.package / "artifacts" / archive
            path.write_bytes(path.read_bytes() + b"changed-after-acceptance")
            with self.assertRaisesRegex(ValueError, "artifact lock"):
                HELM.render_release(release, contract, self.object_map(objects), self.package, [])

    def test_native_archive_identity_is_checked_beyond_reaccepted_bytes(self):
        release, archive, objects = self.platform_chart()
        contract = self.prepare(release, archive)
        source = self.root / "fixture-chart/Chart.yaml"
        source.write_text("apiVersion: v2\nname: different-chart\nversion: 2.17.0\n")
        native("helm", "package", str(source.parent), "--destination", str(self.package / "artifacts"))
        shutil.copyfile(self.package / "artifacts/different-chart-2.17.0.tgz", self.package / "artifacts" / archive)
        self.lock(archive)
        with self.assertRaisesRegex(ValueError, "different native chart identity"):
            HELM.render_release(release, contract, {}, self.package, [])

    def test_uninspected_remote_cluster_and_hidden_values_are_refused(self):
        release, archive, objects = self.platform_chart()
        contract = self.prepare(release, archive)
        for field, value in (("kubeConfig", {"secretRef": {"name": "other-cluster"}}),
                             ("upgrade", {"preserveValues": True}),
                             ("chart", {"spec": {**release["spec"]["chart"]["spec"],
                                                 "valuesFiles": ["hidden-values.yaml"]}})):
            with self.subTest(field=field):
                changed = copy.deepcopy(release)
                changed["spec"][field] = value
                accepted = {**contract, "spec_sha256": canonical_sha256(changed["spec"])}
                with self.assertRaisesRegex(ValueError, "complete explicit native Helm values"):
                    HELM.render_release(changed, accepted, {}, self.package, [])
        for reference in ({"kind": "Secret", "name": "missing"},
                          {"kind": "Secret", "name": "missing", "optional": True},
                          {"kind": "Secret", "name": "missing", "targetPath": "password"}):
            with self.subTest(reference=reference):
                changed = copy.deepcopy(release)
                changed["spec"]["valuesFrom"] = [reference]
                accepted = {**contract, "spec_sha256": canonical_sha256(changed["spec"])}
                with self.assertRaises(ValueError):
                    HELM.render_release(changed, accepted, {}, self.package, [])

    def test_reachable_flux_helm_release_uses_native_contract_and_checks_coverage(self):
        release, archive, objects = self.platform_chart()
        contract = self.prepare(release, archive)
        self.cluster["helm_releases"] = [contract]
        self.stage(self.roots["tier1-platform"] / "selected", [release])
        documents = self.inventory()
        self.assertEqual([item["kind"] for item in documents], ["Deployment"])
        self.assertEqual(documents[0]["metadata"]["namespace"], "flux-system")
        PAYLOAD.inspect_inventory(documents, [], 1)

    @unittest.skipUnless(os.environ.get("NATIVE_CHART_CACHE"), "Requires retained Harbor chart 1.18.0")
    def test_real_harbor_118_role_values_render_repeatably_and_cover_every_claim(self):
        cache = Path(os.environ["NATIVE_CHART_CACHE"]) / "harbor-1.18.0.tgz"
        self.assertTrue(cache.is_file(), str(cache))
        shutil.copyfile(cache, self.package / "artifacts" / cache.name)
        role = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
        inputs = yaml.safe_load((role / "defaults/main.yml").read_text())
        credentials = {f"harbor/harbor-{name}-internal-tls": {
            "ca.crt": "offline-retained-ca", "tls.crt": f"offline-retained-{name}-certificate",
            "tls.key": f"offline-retained-{name}-key"}
            for name in ("core", "jobservice", "registry", "portal", "trivy")}
        inputs.update(delivery_platform_owner="flux", delivery_platform_secrets=credentials,
                      delivery_platform_ingress_class="accepted-ingress", delivery_platform_harbor_host="harbor.lab.test",
                      delivery_platform_harbor_storage_class="retained-csi",
                      delivery_platform_harbor_database_password="offline-retained-database-password")
        environment = Environment(undefined=StrictUndefined, trim_blocks=True)
        environment.filters["to_json"] = json.dumps
        values = environment.from_string((role / "templates/harbor-values.yml.j2").read_text()).render(inputs)
        release = self.release("harbor", "1.18.0", "harbor")
        release["spec"]["valuesFrom"] = [{"kind": "Secret", "name": "harbor-values"}]
        objects = [object_yaml("Secret", "harbor-values", "harbor", stringData={"values.yaml": values})]
        product = {"tier": 1, "name": "registry", "kind": "harbor", "namespace": "harbor"}
        contract = self.prepare(release, cache.name, objects, product)
        self.assertNotIn(inputs["delivery_platform_harbor_database_password"], json.dumps(contract))
        rendered = HELM.render_release(release, contract, self.object_map(objects), self.package, [product])
        retry = HELM.render_release(release, contract, self.object_map(objects), self.package, [product])
        self.assertEqual(rendered, retry)
        with self.subTest(case="wrong restore namespace"), self.assertRaisesRegex(ValueError, "target namespace"):
            HELM.render_release(release, contract, self.object_map(objects), self.package,
                                [{**product, "namespace": "unrestored"}])
        claims = []
        for resource in rendered:
            if resource["kind"] == "PersistentVolumeClaim":
                claims.append(resource["metadata"]["name"])
            if resource["kind"] == "StatefulSet":
                claims.extend(claim["metadata"]["name"] + "-" + resource["metadata"]["name"] + "-0"
                              for claim in resource["spec"].get("volumeClaimTemplates", []))
        self.assertGreaterEqual(len(claims), 5)
        product["data_claims"] = claims
        PAYLOAD.inspect_inventory(rendered, [product], 1)
        product["data_claims"] = claims[:-1]
        with self.assertRaisesRegex(ValueError, "uncovered persistent|outside the native restore"):
            PAYLOAD.inspect_inventory(rendered, [product], 1)
        self.cluster["helm_releases"] = [contract]
        self.plan["products"] = [product]
        self.stage(self.roots["tier1-platform"] / "selected", [release, *objects])
        self.assertIn("StatefulSet", [item["kind"] for item in self.inventory()])


class RecoveryPersistenceCoverage(unittest.TestCase):
    def test_native_runner_managers_cannot_poll_retained_jobs_during_source_handoff(self):
        runner = object_yaml('Deployment', 'gitlab-runner', 'ci-jobs', spec={'replicas': 0,
            'template': {'spec': {'serviceAccountName': 'gitlab-runner', 'containers': [
                {'name': 'gitlab-runner', 'image': 'registry.example.test/runner@sha256:' + 'a' * 64}]}}})
        PAYLOAD.inspect_inventory([runner], [], 1)
        runner['spec']['replicas'] = 1
        with self.assertRaisesRegex(ValueError, 'Runner managers stopped'):
            PAYLOAD.inspect_inventory([runner], [], 1)
        del runner['spec']['replicas']
        with self.assertRaisesRegex(ValueError, 'Runner managers stopped'):
            PAYLOAD.inspect_inventory([runner], [], 1)

    def test_claim_workload_and_statefulset_coverage_are_bound_to_tier_and_namespace(self):
        claim = object_yaml("PersistentVolumeClaim", "service-data")
        product = {"kind": "harbor", "name": "registry", "namespace": "services", "tier": 1,
                   "data_claims": ["service-data", "data-database-0", "data-database-1"]}
        stateful = object_yaml("StatefulSet", "database", spec={"replicas": 2,
            "volumeClaimTemplates": [{"metadata": {"name": "data"}}],
            "template": {"spec": {"volumes": [{"persistentVolumeClaim": {"claimName": "service-data"}}]}}})
        PAYLOAD.inspect_inventory([claim, stateful], [product], 1)
        for changed in ({**product, "tier": 0}, {**product, "namespace": "other"},
                        {**product, "data_claims": ["service-data", "data-database-0"]}):
            with self.subTest(product=changed), self.assertRaises(ValueError):
                PAYLOAD.inspect_inventory([claim, stateful], [changed], 1)

    def test_cnpg_requires_matching_selected_cluster_and_denies_fresh_initdb(self):
        cluster = object_yaml("Cluster", "identity-db", "identity", spec={
            "bootstrap": {"recovery": {"source": "retained"}}})
        cluster["apiVersion"] = "postgresql.cnpg.io/v1"
        product = {"kind": "cnpg-files", "name": "identity", "namespace": "identity", "tier": 0,
                   "cnpg_cluster": "identity-db"}
        PAYLOAD.inspect_inventory([cluster], [product], 0)
        with self.subTest(case="unselected database"), self.assertRaises(ValueError):
            PAYLOAD.inspect_inventory([cluster], [], 0)
        cluster["spec"]["bootstrap"] = {"initdb": {"database": "identity"}}
        with self.subTest(case="fresh initializer"), self.assertRaisesRegex(ValueError, "fresh initializer"):
            PAYLOAD.inspect_inventory([cluster], [product], 0)

    def test_unknown_jobs_and_opaque_releases_cannot_initialize_unrestored_data(self):
        job = object_yaml("Job", "initialize", spec={"template": {"spec": {"containers": []}}})
        cron = object_yaml("CronJob", "initialize", spec={"jobTemplate": {"spec": job["spec"]}})
        for resource in (job, cron, object_yaml("HelmRelease", "opaque")):
            with self.subTest(kind=resource["kind"]), self.assertRaises(ValueError):
                PAYLOAD.inspect_inventory([resource], [], 1)

    def test_native_spinnaker_verification_job_refuses_initialize_action(self):
        product = {"kind": "spinnaker", "name": "delivery", "namespace": "spinnaker", "tier": 1,
                   "mysql": {"claim": "mysql-data"}, "redis": {"claim": "redis-data"}}
        job = object_yaml("Job", "spinnaker-databases-verify-accepted", "spinnaker", spec={
            "template": {"spec": {"containers": [{"name": "mysql", "env": [
                {"name": "SPINNAKER_DATABASE_ACTION", "value": "verify"}]}]}}})
        PAYLOAD.inspect_inventory([job], [product], 1)
        job["spec"]["template"]["spec"]["containers"][0]["env"][0]["value"] = "initialize"
        with self.assertRaisesRegex(ValueError, "fresh data initialization"):
            PAYLOAD.inspect_inventory([job], [product], 1)


class RecoveryImageSupply(unittest.TestCase):
    def setUp(self):
        self.image = "ghcr.io/fluxcd/source-controller:v1.7.0"
        self.entry = {"kind": "oci", "tier": 1, "source_image": self.image,
                      "destination": "recovery.test/fluxcd/source-controller", "digest": "a" * 64,
                      "tag": "v1.7.0"}
        self.plan = {"products": [], "artifact_supply": [self.entry]}
        self.cluster = {"tier": 1, "bootstrap_images": [self.image],
                        "registry_mirrors": {"ghcr.io": "recovery.test"}}

    def test_original_tag_requires_native_mirror_same_repository_and_published_tag(self):
        PAYLOAD.verify_images([], self.plan, self.cluster)
        variants = [({**self.entry, "tag": "changed"}, self.cluster),
                    ({**self.entry, "destination": "recovery.test/wrong-path"}, self.cluster),
                    (self.entry, {**self.cluster, "registry_mirrors": {}}),
                    ({**self.entry, "source_image": self.image + "-other"}, self.cluster)]
        for entry, cluster in variants:
            with self.subTest(entry=entry, cluster=cluster), self.assertRaises(ValueError):
                PAYLOAD.verify_images([], {**self.plan, "artifact_supply": [entry]}, cluster)

    def test_destination_digest_and_docker_library_tags_have_exact_supply(self):
        cluster = {"tier": 1, "bootstrap_images": [self.entry["destination"] + "@sha256:" + self.entry["digest"]]}
        PAYLOAD.verify_images([], self.plan, cluster)
        library = {**self.entry, "source_image": "redis:8.2.1",
                   "destination": "recovery.test/library/redis", "tag": "8.2.1"}
        PAYLOAD.verify_images([], {"products": [], "artifact_supply": [library]}, {
            "tier": 1, "bootstrap_images": ["redis:8.2.1"], "registry_mirrors": {"docker.io": "recovery.test"}})

    def test_workload_init_cron_cnpg_restore_and_bootstrap_images_all_require_supply(self):
        documents = [object_yaml("Deployment", "consumer", spec={"template": {"spec": {
            "containers": [{"name": "consumer", "image": self.image}],
            "initContainers": [{"name": "setup", "image": "missing.test/init:1"}]}}}),
            object_yaml("CronJob", "backup", spec={"jobTemplate": {"spec": {"template": {"spec": {
                "containers": [{"name": "backup", "image": "missing.test/cron:1"}]}}}}}),
            object_yaml("Cluster", "sql", spec={"imageName": "missing.test/cnpg:1"})]
        for resource in documents:
            with self.subTest(kind=resource["kind"]), self.assertRaisesRegex(ValueError, "no unique locked"):
                PAYLOAD.verify_images([resource], self.plan, self.cluster)
        product = {"tier": 1, "kind": "spinnaker", "image": self.image, "restic_image": "missing.test/restic:1",
                   "python_image": self.image, "mysql": {"image": self.image}, "redis": {"image": self.image}}
        with self.assertRaisesRegex(ValueError, "no unique locked"):
            PAYLOAD.verify_images([], {**self.plan, "products": [product]}, self.cluster)
        with self.assertRaises(ValueError):
            PAYLOAD.verify_images([], {**self.plan, "artifact_supply": []}, self.cluster)

    def test_duplicate_or_other_tier_supply_and_changed_original_digest_are_refused(self):
        for entries in ([self.entry, copy.deepcopy(self.entry)], [{**self.entry, "tier": 0}]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                PAYLOAD.verify_images([], {**self.plan, "artifact_supply": entries}, self.cluster)
        image = "ghcr.io/fluxcd/source-controller@sha256:" + "b" * 64
        with self.assertRaisesRegex(ValueError, "digest differs"):
            PAYLOAD.verify_images([], {**self.plan, "artifact_supply": [{**self.entry, "source_image": image}]},
                                  {**self.cluster, "bootstrap_images": [image]})


class RecoveryTalosResolvedInputs(unittest.TestCase):
    def setUp(self):
        self.cluster = {"nodes": [{"name": "cp-1", "node": "pve01", "vmid": 1101},
                                  {"name": "cp-2", "node": "pve02", "vmid": 1102}],
                        "recovery_bridge": "vmbr9", "registry_mirrors": {"ghcr.io": "recovery.test"},
                        "bootstrap_images": ["ghcr.io/siderolabs/kubelet:v1.34.0",
                                             "ghcr.io/siderolabs/installer:v1.11.0"]}
        self.machine = {"machine": {"install": {"image": self.cluster["bootstrap_images"][1]},
                                   "kubelet": {"image": self.cluster["bootstrap_images"][0]},
                                   "registries": {"mirrors": {"ghcr.io": {"endpoints": ["https://recovery.test"], "skipFallback": True}},
                                                  "config": {"recovery.test": {"tls": {"ca": "retained-ca"}}}}}}
        self.plan = {"resource_changes": []}
        for node in self.cluster["nodes"]:
            self.plan["resource_changes"].append({"type": "proxmox_virtual_environment_vm", "change": {
                "actions": ["create"], "after": {"name": node["name"], "node_name": node["node"],
                    "vm_id": node["vmid"], "network_device": [{"bridge": "vmbr9"}]}}})
            self.plan["resource_changes"].append({"type": "talos_machine_configuration_apply", "index": node["name"],
                "change": {"actions": ["create"], "after": {"machine_configuration_input": yaml.safe_dump(self.machine)}}})

    def test_saved_plan_resolves_all_nodes_images_and_verified_native_mirrors(self):
        TALOS.validate_plan(self.plan, self.cluster)
        for mirror in ({"endpoints": ["http://recovery.test"]}, {"endpoints": ["https://other.test"]},
                       {"endpoints": ["https://recovery.test", "https://external.test"]},
                       {"endpoints": ["https://recovery.test"], "overridePath": True}):
            with self.subTest(mirror=mirror):
                configuration = copy.deepcopy(self.machine)
                configuration["machine"]["registries"]["mirrors"]["ghcr.io"] = mirror
                self.reject_configuration(configuration, "accepted verified independent endpoint")
        configuration = copy.deepcopy(self.machine)
        configuration["machine"]["registries"]["config"]["recovery.test"]["tls"]["insecureSkipVerify"] = True
        self.reject_configuration(configuration, "accepted verified independent endpoint")

    def reject_configuration(self, configuration, message):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][1]["change"]["after"]["machine_configuration_input"] = yaml.safe_dump(configuration)
        with self.assertRaisesRegex(ValueError, message):
            TALOS.validate_plan(plan, self.cluster)

    def test_missing_resolved_configuration_or_nested_image_blocks_apply(self):
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"].pop()
        with self.assertRaisesRegex(ValueError, "every selected Talos configuration"):
            TALOS.validate_plan(plan, self.cluster)
        self.reject_configuration({"machine": {"install": {"image": "unretained.test/installer:latest"}}},
                                  "missing from independent bootstrap supply")
        self.reject_configuration({"machine": {"pods": [{"containers": [
            {"image": "unretained.test/bootstrap:latest"}]}]}}, "missing from independent bootstrap supply")
        self.reject_configuration({"cluster": {}}, "resolved Talos machine configuration")

    def test_configuration_count_cannot_substitute_for_each_selected_node(self):
        duplicate = copy.deepcopy(self.plan)
        duplicate["resource_changes"][3]["index"] = "cp-1"
        with self.subTest(case="duplicate selected node"), self.assertRaises(ValueError):
            TALOS.validate_plan(duplicate, self.cluster)
        unknown = copy.deepcopy(self.plan)
        unknown["resource_changes"][3]["index"] = "unselected-node"
        with self.subTest(case="unselected node"), self.assertRaises(ValueError):
            TALOS.validate_plan(unknown, self.cluster)

    def test_native_registry_documents_keep_tls_and_disable_original_registry_fallback(self):
        machine = copy.deepcopy(self.machine)
        del machine['machine']['registries']
        mirror = {'apiVersion': 'v1alpha1', 'kind': 'RegistryMirrorConfig', 'name': 'ghcr.io',
                  'endpoints': [{'url': 'https://recovery.test'}], 'skipFallback': True}
        roots = {'apiVersion': 'v1alpha1', 'kind': 'RegistryTLSConfig', 'name': 'recovery.test', 'ca': 'retained-ca'}
        def resolved(extra):
            value = copy.deepcopy(self.plan)
            for resource in value['resource_changes']:
                if resource['type'] == 'talos_machine_configuration_apply':
                    resource['change']['after']['machine_configuration_input'] = yaml.safe_dump_all([machine, *extra])
            return value
        TALOS.validate_plan(resolved([mirror, roots]), self.cluster)
        for changed in ({**mirror, 'skipFallback': False}, {**mirror, 'endpoints': [{'url': 'http://recovery.test'}]},
                        {**mirror, 'endpoints': [{'url': 'https://recovery.test', 'overridePath': True}]}):
            with self.subTest(mirror=changed), self.assertRaises(ValueError):
                TALOS.validate_plan(resolved([changed, roots]), self.cluster)
        with self.assertRaises(ValueError):
            TALOS.validate_plan(resolved([mirror, {**roots, 'insecureSkipVerify': True}]), self.cluster)
        with self.assertRaises(ValueError):
            TALOS.validate_plan(resolved([mirror, mirror, roots]), self.cluster)


class RecoverySourceGeneratedPayload(TierRepositoryTestCase):
    def test_generated_tier_one_carries_same_source_and_helm_helpers(self):
        self.generate()
        for filename in ("recovery_payload.py", "recovery_helm.py"):
            generated = self.root / "verify-tier-1/scripts" / filename
            self.assertTrue(generated.is_file(), str(generated))
            self.assertEqual(generated.read_bytes(), (SCRIPTS / filename).read_bytes())
        source = self.root / "verify-tier-1/scripts"
        result = native(sys.executable, "-B", "-c", "import recovery_payload, recovery_helm", cwd=source)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
