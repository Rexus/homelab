#!/usr/bin/env python3
"""Spinnaker Job entry point. Git writes occur only in the execute operation."""

import argparse
import json
import os
from pathlib import Path
import tempfile
import subprocess

from promotion_flux import KubernetesReader, wait_for_release
from promotion_git import (PromotionError, Repository, canonical, decode_plan, encode_plan,
                           require, validate_policy)


def run(operation, policy, repository, signing_key):
    if operation == "preview":
        request = {field: os.environ["PROMOTION_" + field.upper()] for field in
                   ("config_revision", "image_digest", "release_id", "mode", "compatibility_reference")}
        request["base"] = repository.head(policy["branch"])
        plan = repository.candidate(policy, request, signing_key)
        return {"plan_b64": encode_plan(plan), "candidate": plan["candidate"], "base": plan["base"],
                "config_revision": plan["config_revision"], "image_digest": plan["image_digest"],
                "compatibility_reference": plan["compatibility_reference"], "mode": plan["mode"],
                "diff": plan["diff"], "result": "awaiting-judgment"}
    approved = decode_plan(os.environ["PROMOTION_PLAN_B64"])
    request = {field: approved[field] for field in
               ("base", "config_revision", "image_digest", "release_id", "mode", "compatibility_reference")}
    rebuilt = repository.candidate(policy, request, signing_key)
    require(canonical(rebuilt) == canonical(approved), "Approved preview changed; obtain a new judgment")
    result = repository.publish(policy, approved)
    wait_for_release(KubernetesReader(), repository, policy, approved,
                     timeout=policy.get("timeout_seconds", 900))
    return {"candidate": approved["candidate"], "release_id": approved["release_id"],
            "result": "reconciled", "git_result": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "execute"))
    parser.add_argument("--policy", default="/policy/policy.json")
    args = parser.parse_args()
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ASKPASS"] = str(Path(__file__).with_name("promotion") / "git-askpass.py")
    context = {"release_id": os.environ.get("PROMOTION_RELEASE_ID", "")}
    try:
        if args.operation == "execute":
            approved = decode_plan(os.environ["PROMOTION_PLAN_B64"])
            context = {field: approved[field] for field in ("release_id", "candidate")}
        policy = json.loads(Path(args.policy).read_text())
        validate_policy(policy)
        signing_key = os.environ.get("PROMOTION_SIGNING_KEY", "/signing/key")
        require(Path(signing_key).is_file(), "Mount the retained SSH commit-signing key at /signing/key")
        with tempfile.TemporaryDirectory(prefix="promotion-") as directory:
            repository = Repository(directory, policy["repository"])
            output = run(args.operation, policy, repository, signing_key)
        print("SPINNAKER_CONFIG_JSON=" + json.dumps(output, ensure_ascii=True))
    except (PromotionError, KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print("SPINNAKER_CONFIG_JSON=" + json.dumps(dict(context, result="failed", reason=str(error))))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
