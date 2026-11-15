"""Construct a reviewable, deterministic application-only Git promotion."""

import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import time


class PromotionError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def require(condition, message):
    if not condition:
        raise PromotionError(message)


def validate_signing_key(path):
    public = subprocess.run(["ssh-keygen", "-y", "-P", "", "-f", path],
                            capture_output=True, timeout=15)
    require(public.returncode == 0, "Use a readable unencrypted retained Ed25519 SSH signing key")
    require(public.stdout.split()[0] == b"ssh-ed25519",
            "Ed25519 is required for byte-identical signed preview and execute commits")


def validate_policy(policy):
    require(re.fullmatch(r"https://[^/@\s]+/[^\s]+", policy["repository"]) is not None,
            "Use the dedicated HTTPS application project without embedded credentials")
    path = PurePosixPath(policy["manifest_path"])
    require(not path.is_absolute() and ".." not in path.parts and path.suffix == ".json",
            "manifest_path must be a repository-relative JSON Kubernetes manifest")
    require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9/_-]*", policy["branch"]) is not None,
            "Use a fixed protected delivery branch")
    require(policy["target"]["kind"] in ("Deployment", "HelmRelease"), "Unsupported target kind")
    require(policy["target"]["namespace"] in policy["application_namespaces"],
            "Target must be in the bootstrap-approved application namespace list")
    require(policy["target"]["namespace"] not in
            ("flux-system", "spinnaker", "delivery-promotion", "delivery-promotion-authority", "kube-system", "default"),
            "Use a dedicated application namespace")


class Repository:
    def __init__(self, directory, remote):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.git("init", "--bare", ".")
        self.git("remote", "add", "origin", remote)

    def git(self, *arguments, data=None, environment=None, attempts=1):
        for attempt in range(attempts):
            result = subprocess.run(
                ["git", "-c", "credential.helper=", *arguments], cwd=self.directory,
                input=data, capture_output=True, env=dict(os.environ, **(environment or {})),
                timeout=120,
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8").strip()
            if attempt + 1 < attempts:
                time.sleep(attempt + 1)
        # Git stderr can contain credential-bearing endpoint details. Keep it out of Job logs.
        raise PromotionError("Git operation failed: " + arguments[0])

    def head(self, branch):
        result = self.git("ls-remote", "--exit-code", "origin", "refs/heads/" + branch, attempts=3)
        require(bool(result), "Delivery branch must already exist")
        return result.split()[0]

    def fetch(self, revision):
        require(re.fullmatch(r"[0-9a-f]{40}", revision) is not None, "Use a full Git SHA-1 commit")
        self.git("fetch", "--no-tags", "origin", revision, attempts=3)
        require(self.git("cat-file", "-t", revision) == "commit", "Revision must identify a commit")

    def document(self, revision, path):
        entry = self.git("ls-tree", revision, "--", path).split()
        require(len(entry) >= 3 and entry[0] == "100644", "Target must be a regular tracked file")
        return json.loads(self.git("show", revision + ":" + path))

    def candidate(self, policy, request, signing_key):
        for field in ("base", "config_revision"):
            self.fetch(request[field])
        require(re.fullmatch(r"sha256:[0-9a-f]{64}", request["image_digest"]) is not None,
                "Use an immutable SHA-256 image digest")
        require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", request["release_id"]) is not None,
                "release_id must be a bounded release identifier")
        require(request["mode"] in ("promote", "rollback"), "Unknown promotion mode")
        require(bool(request["compatibility_reference"].strip()),
                "Record application/data compatibility evidence for approval")
        previous = self.document(request["base"], policy["manifest_path"])
        desired = self.document(request["config_revision"], policy["manifest_path"])
        target = policy["target"]
        for document in (previous, desired):
            require(document["kind"] == target["kind"] and
                    document["metadata"]["namespace"] == target["namespace"] and
                    document["metadata"]["name"] == target["name"], "Configuration changes target identity")
            require(set(document) <= {"apiVersion", "kind", "metadata", "spec"},
                    "Configuration must contain one desired Kubernetes resource")
        desired = copy.deepcopy(desired)
        if target["kind"] == "HelmRelease":
            require(desired["apiVersion"] == "helm.toolkit.fluxcd.io/v2", "Use HelmRelease v2")
            require(desired["spec"]["chart"]["spec"]["sourceRef"] == policy["chart_source"],
                    "Helm chart must use the platform-approved source")
            require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?",
                                 desired["spec"]["chart"]["spec"]["version"]) is not None,
                    "Use an exact Helm chart version")
            require(desired["spec"].get("serviceAccountName") == "application-reconciler",
                    "Helm must use the restricted application-reconciler")
            image = desired["spec"].setdefault("values", {}).setdefault("image", {})
            image.update(repository=policy["image_repository"], digest=request["image_digest"])
            image.pop("tag", None)
            desired["spec"]["driftDetection"] = {"mode": "enabled"}
        else:
            require(desired["apiVersion"] == "apps/v1", "Use Deployment apps/v1")
            containers = desired["spec"]["template"]["spec"]["containers"]
            selected = [item for item in containers if item["name"] == policy["container"]]
            require(len(selected) == 1, "The selected Deployment container must exist exactly once")
            selected[0]["image"] = policy["image_repository"] + "@" + request["image_digest"]
        annotations = desired["metadata"].setdefault("annotations", {})
        for field in ("config_revision", "release_id", "image_digest", "compatibility_reference", "mode"):
            annotations["delivery.homelab/" + field.replace("_", "-")] = request[field]
        blob = self.git("hash-object", "-w", "--stdin", data=canonical(desired).encode())
        index = {"GIT_INDEX_FILE": str(self.directory / "promotion-index")}
        self.git("read-tree", request["base"], environment=index)
        self.git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + policy["manifest_path"],
                 environment=index)
        tree = self.git("write-tree", environment=index)
        timestamp = int(self.git("show", "-s", "--format=%ct", request["base"])) + 1
        identity = {"GIT_AUTHOR_NAME": "Delivery promotion", "GIT_COMMITTER_NAME": "Delivery promotion",
                    "GIT_AUTHOR_EMAIL": policy["commit_email"], "GIT_COMMITTER_EMAIL": policy["commit_email"],
                    "GIT_AUTHOR_DATE": f"{timestamp} +0000", "GIT_COMMITTER_DATE": f"{timestamp} +0000"}
        message = canonical(request)
        arguments = ["commit-tree", tree, "-p", request["base"]]
        if signing_key:
            validate_signing_key(signing_key)
            arguments = ["-c", "gpg.format=ssh", "-c", "user.signingkey=" + signing_key, *arguments, "-S"]
        revision = self.git(*arguments, data=message.encode(), environment=identity)
        diff = self.git("diff", "--no-ext-diff", "--no-color", request["base"], revision, "--",
                        policy["manifest_path"])
        require(len(diff.encode()) <= 100000, "Preview exceeds the 100 KB judgment limit")
        return dict(request, candidate=revision, diff=diff, desired=desired,
                    policy_sha256=hashlib.sha256(canonical(policy).encode()).hexdigest())

    def publish(self, policy, plan):
        current = self.head(policy["branch"])
        if current == plan["candidate"]:
            return "already-published"
        require(current == plan["base"], "Superseded: delivery branch moved; obtain a fresh preview and approval")
        try:
            self.git("push", "--porcelain", "--force-with-lease=refs/heads/" + policy["branch"] + ":" +
                     plan["base"], "origin", plan["candidate"] + ":refs/heads/" + policy["branch"])
        except PromotionError:
            # A transport failure after the server accepted the push is safely retryable.
            require(self.head(policy["branch"]) == plan["candidate"],
                    "Git compare-and-swap failed; delivery branch changed or push was rejected")
        return "published"
