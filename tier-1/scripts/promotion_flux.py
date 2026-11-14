"""Read exact Flux and application objects using a projected service-account token."""

import json
import os
from pathlib import Path
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from promotion_git import PromotionError, require


class KubernetesReader:
    def __init__(self, server=None, token_file=None, ca_file=None):
        root = "/var/run/secrets/kubernetes.io/serviceaccount/"
        self.server = server or "https://" + os.environ["KUBERNETES_SERVICE_HOST"] + ":" + os.environ.get(
            "KUBERNETES_SERVICE_PORT_HTTPS", "443")
        self.token_file = token_file or root + "token"
        self.context = ssl.create_default_context(cafile=ca_file or root + "ca.crt")

    def get(self, group, version, resource, namespace, name):
        path = f"/apis/{group}/{version}/namespaces/{namespace}/{resource}/{name}"
        request = Request(self.server + path, headers={
            "Authorization": "Bearer " + Path(self.token_file).read_text().strip(),
            "Accept": "application/json",
        })
        try:
            with urlopen(request, context=self.context, timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code in (404, 429, 500, 502, 503, 504):
                return None
            raise PromotionError(f"Observation API denied request ({error.code})") from None
        except (URLError, TimeoutError):
            return None


def ready(resource):
    if not resource or resource.get("spec", {}).get("suspend", False):
        return False
    generation = resource["metadata"]["generation"]
    status = resource.get("status", {})
    conditions = status.get("conditions", [])
    return (status.get("observedGeneration") == generation and
            any(item["type"] == "Ready" and item["status"] == "True" and
                item.get("observedGeneration") == generation for item in conditions) and
            not any(item["type"] in ("Reconciling", "Stalled") and item["status"] == "True"
                    for item in conditions))


def revision_matches(value, sha):
    return value == sha or value.endswith("@sha1:" + sha) or value.endswith(":sha1:" + sha)


def contains(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and contains(value, actual[key])
                                                for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(
            contains(left, right) for left, right in zip(expected, actual))
    return expected == actual


def target_healthy(plan, live):
    if not live or not contains(plan["desired"]["spec"], live.get("spec", {})):
        return False
    if any(live.get(field) != plan["desired"][field] for field in ("kind", "apiVersion")) or any(
            live["metadata"].get(field) != plan["desired"]["metadata"][field] for field in ("namespace", "name")):
        return False
    expected = plan["desired"]["metadata"]["annotations"]
    if not contains(expected, live["metadata"].get("annotations", {})):
        return False
    if live["kind"] == "HelmRelease":
        return ready(live)
    generation = live["metadata"]["generation"]
    status = live.get("status", {})
    count = live["spec"].get("replicas", 1)
    return (count > 0 and status.get("observedGeneration") == generation and
            all(status.get(field) == count for field in
                ("replicas", "updatedReplicas", "readyReplicas", "availableReplicas")) and
            any(item["type"] == "Available" and item["status"] == "True"
                for item in status.get("conditions", [])))


def wait_for_release(reader, repository, policy, plan, timeout=900, interval=10):
    deadline = time.monotonic() + timeout
    target = policy["target"]
    while time.monotonic() < deadline:
        require(repository.head(policy["branch"]) == plan["candidate"],
                "Superseded: a later delivery revision replaced this release")
        source = reader.get("source.toolkit.fluxcd.io", "v1", "gitrepositories",
                            "flux-system", "tier1-applications")
        kustomization = reader.get("kustomize.toolkit.fluxcd.io", "v1", "kustomizations",
                                   "flux-system", "tier1-applications")
        if source and kustomization:
            require(source["spec"]["url"] == policy["repository"] and
                    source["spec"]["ref"] == {"branch": policy["branch"]},
                    "Application source no longer follows the approved repository/branch")
            reference = kustomization["spec"]["sourceRef"]
            require(reference["kind"] == "GitRepository" and reference["name"] == "tier1-applications" and
                    reference.get("namespace", "flux-system") == "flux-system" and
                    kustomization["spec"].get("serviceAccountName") == "application-reconciler" and
                    kustomization["spec"]["path"] == policy["kustomization_path"],
                    "Application reconciliation boundary changed")
            source_revision = source.get("status", {}).get("artifact", {}).get("revision", "")
            applied = kustomization.get("status", {}).get("lastAppliedRevision", "")
            if (ready(source) and ready(kustomization) and
                    revision_matches(source_revision, plan["candidate"]) and
                    revision_matches(applied, plan["candidate"])):
                group, version, plural = ("apps", "v1", "deployments")
                if target["kind"] == "HelmRelease":
                    group, version, plural = "helm.toolkit.fluxcd.io", "v2", "helmreleases"
                live = reader.get(group, version, plural, target["namespace"], target["name"])
                if target_healthy(plan, live):
                    # Recheck source and Git after workload observation to reject a known intervening release.
                    final = reader.get("source.toolkit.fluxcd.io", "v1", "gitrepositories",
                                       "flux-system", "tier1-applications")
                    if final and ready(final) and revision_matches(
                            final.get("status", {}).get("artifact", {}).get("revision", ""), plan["candidate"]):
                        require(repository.head(policy["branch"]) == plan["candidate"],
                                "Superseded during workload observation")
                        return
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise PromotionError("Timed out awaiting the exact Flux revision and selected workload health")
