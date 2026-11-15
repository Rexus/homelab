#!/usr/bin/env python3
"""Retain and verify exact Tier 1 Git revisions and independent pinned artifact files.

This creates a recovery package, not a service-data backup. Secrets in configuration must be SOPS
encrypted; private decryption keys and infrastructure state retain their independent custody owner.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import yaml

SOURCES = {"platform", "tier1-platform", "tier1-applications"}
COMMIT = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")


def git(directory, *arguments):
    result = subprocess.run(["git", "-C", str(directory), *arguments], check=True,
                            capture_output=True, text=True, timeout=120)
    return result.stdout.strip()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assignment(values):
    result = {}
    for value in values:
        name, separator, content = value.partition("=")
        if not separator or name not in SOURCES or not content or name in result:
            raise ValueError("Use one known source=path or source=commit assignment per source.")
        result[name] = content
    return result


def confined(root, relative):
    candidate = root / relative
    if any(part.is_symlink() for part in (candidate, *candidate.parents)):
        raise ValueError("Recovery entries must be ordinary files without linked path components.")
    path = candidate.resolve()
    if (Path(relative).is_absolute() or '..' in Path(relative).parts or
            not path.is_relative_to(root.resolve()) or path == root.resolve()):
        raise ValueError("Recovery entry escapes its package directory.")
    return path


def validate_configuration(repository, commit):
    # Check selected configuration, never decrypt keys or include working-tree/private overlays.
    paths = git(repository, "ls-tree", "-r", "--name-only", commit).splitlines()
    for path in paths:
        if Path(path).suffix.lower() not in (".yaml", ".yml", ".json"):
            continue
        content = git(repository, "show", f"{commit}:{path}")
        for document in yaml.safe_load_all(content):
            if not isinstance(document, dict) or document.get("kind") != "Secret":
                continue
            if (document.get("data") or document.get("stringData")) and "sops" not in document:
                raise ValueError("Configuration contains an unencrypted Kubernetes Secret; package not accepted.")


def export_package(args):
    os.umask(0o077)
    record = json.loads(args.record.read_text())
    if record.get("version") != 1 or set(record.get("sources", {})) != SOURCES:
        raise ValueError("Record must contain all three accepted independent source revisions.")
    repositories = assignment(args.repository)
    if set(repositories) != SOURCES:
        raise ValueError("Provide the independently available checkout of every recorded source.")
    for name, revision in assignment(args.replace).items():
        record["sources"][name]["commit"] = revision
        record["sources"][name]["ref"] = {"commit": revision}
    artifacts = json.loads(args.artifacts.read_text())
    revisions = {name: source.get('commit') for name, source in record['sources'].items()}
    if artifacts.get('sources') != revisions:
        raise ValueError('The independently approved artifact lock must bind all three configuration commits.')
    if not isinstance(artifacts.get("files"), list) or not artifacts["files"]:
        raise ValueError("Artifact lock needs nonempty files with relative path and SHA-256.")
    if args.output.exists():
        raise ValueError("Use a new recovery-package directory; existing custody is never overwritten.")
    args.output.mkdir(parents=True, mode=0o700)
    manifests = {"version": 1, "sources": record["sources"], "files": [],
                 "artifact_lock_sha256": sha256(args.artifacts),
                 "scope": "configuration-and-artifacts-only; service data and keys have separate custody"}
    for name in sorted(SOURCES):
        revision = record["sources"][name]["commit"]
        if not COMMIT.fullmatch(revision):
            raise ValueError("Every recovery source must identify an immutable full Git commit.")
        repository = Path(repositories[name]).resolve(strict=True)
        if git(repository, "rev-parse", f"{revision}^{{commit}}") != revision:
            raise ValueError("Selected revision does not resolve to the recorded commit.")
        validate_configuration(repository, revision)
        bundle = args.output / f"{name}.bundle"
        with tempfile.TemporaryDirectory(prefix="flux-recovery-") as scratch:
            git(scratch, "init", "--bare", "--quiet", "--object-format=" + ("sha256" if len(revision) == 64 else "sha1"))
            git(scratch, "fetch", "--no-tags", str(repository), f"{revision}:refs/heads/recovery")
            git(scratch, "bundle", "create", str(bundle.resolve()), "refs/heads/recovery")
        manifests["sources"][name]["bundle"] = bundle.name
        manifests["files"].append({"path": bundle.name, "sha256": sha256(bundle)})
    shutil.copyfile(args.artifacts, args.output / "artifact-lock.json")
    manifests["files"].append({"path": "artifact-lock.json", "sha256": sha256(args.artifacts)})
    artifact_root = args.artifacts.resolve().parent
    for entry in artifacts["files"]:
        if not re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", "")):
            raise ValueError("Every staged artifact requires a full SHA-256.")
        original = confined(artifact_root, entry["path"])
        if not original.is_file() or sha256(original) != entry["sha256"]:
            raise ValueError("Staged artifact is missing or differs from its approved checksum.")
        target = confined(args.output, f"artifacts/{entry['path']}")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(original, target)
        manifests["files"].append({"path": target.relative_to(args.output).as_posix(), "sha256": sha256(target)})
    (args.output / "manifest.json").write_text(json.dumps(manifests, indent=2) + "\n")
    verify_package(argparse.Namespace(directory=args.output, expect=[], expect_lock=""))
    print("Verified configuration and artifact package; retain keys, state and product-data backups separately.")


def verify_package(args):
    root = args.directory.resolve(strict=True)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("version") != 1 or set(manifest.get("sources", {})) != SOURCES:
        raise ValueError("Recovery manifest is incomplete.")
    listed = set()
    for entry in manifest.get("files", []):
        path = confined(root, entry["path"])
        if entry["path"] in listed or not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError("Recovery entry is duplicated, missing or modified.")
        listed.add(entry["path"])
    if not any(path.startswith("artifacts/") for path in listed):
        raise ValueError("Configuration alone is not an independent artifact supply.")
    if "artifact-lock.json" not in listed or sha256(root / "artifact-lock.json") != manifest.get("artifact_lock_sha256"):
        raise ValueError("The approved artifact lock is not retained.")
    if args.expect_lock and args.expect_lock != manifest["artifact_lock_sha256"]:
        raise ValueError("Artifact lock differs from the independently approved checksum.")
    lock = json.loads((root / 'artifact-lock.json').read_text())
    if lock.get('sources') != {name: source.get('commit') for name, source in manifest['sources'].items()}:
        raise ValueError('Recovery configuration differs from the independently approved source commits.')
    locked_paths = set()
    for entry in lock.get('files', []):
        relative = 'artifacts/' + entry['path']
        path = confined(root, relative)
        if (relative in locked_paths or relative not in listed or not path.is_file() or
                not re.fullmatch(r'[a-f0-9]{64}', entry.get('sha256', '')) or sha256(path) != entry['sha256']):
            raise ValueError('Retained artifact differs from its independently approved checksum.')
        locked_paths.add(relative)
    if not locked_paths or locked_paths != {path for path in listed if path.startswith('artifacts/')}:
        raise ValueError('Recovery artifacts do not match the complete approved lock.')
    for name, source in manifest["sources"].items():
        if not COMMIT.fullmatch(source.get("commit", "")) or source.get("bundle") not in listed:
            raise ValueError("Recovery revision or bundle is not verified.")
        bundle = confined(root, source["bundle"])
        heads = subprocess.run(["git", "bundle", "list-heads", str(bundle)], capture_output=True,
                               text=True, check=True, timeout=30).stdout.splitlines()
        if f"{source['commit']} refs/heads/recovery" not in heads:
            raise ValueError("Bundle does not advertise its accepted recovery revision.")
        with tempfile.TemporaryDirectory(prefix="flux-verify-") as scratch:
            git(scratch, "init", "--bare", "--quiet", "--object-format=" +
                ("sha256" if len(source["commit"]) == 64 else "sha1"))
            git(scratch, "bundle", "verify", str(bundle))
            git(scratch, "fetch", str(bundle), "refs/heads/recovery:refs/heads/recovery")
            validate_configuration(scratch, source["commit"])
    for name, expected in assignment(args.expect).items():
        if manifest["sources"][name]["commit"] != expected:
            raise ValueError("Recovery package does not retain the exact proposed revision.")


def restore_repositories(args):
    verify_package(argparse.Namespace(directory=args.directory, expect=[], expect_lock=args.expect_lock))
    manifest = json.loads((args.directory / "manifest.json").read_text())
    digest = sha256(args.directory / "manifest.json")
    marker = args.output / "recovery-manifest.sha256"
    if args.output.exists():
        if not marker.is_file() or marker.read_text().strip() != digest:
            raise ValueError("Existing repositories belong to another package; use a new recovery directory.")
        for name, source in manifest["sources"].items():
            if git(args.output / f"{name}.git", "rev-parse", "refs/heads/recovery") != source["commit"]:
                raise ValueError("Existing recovery repository differs from its accepted commit.")
        return
    args.output.mkdir(parents=True, mode=0o750)
    for name, source in manifest["sources"].items():
        target = args.output / f"{name}.git"
        git(args.output, "clone", "--bare", "--single-branch", "--branch", "recovery",
            str((args.directory / source["bundle"]).resolve()), str(target.resolve()))
        if name == "tier1-applications":
            git(target, "update-ref", f"refs/heads/{args.application_branch}", source["commit"])
    marker.write_text(digest + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--record", type=Path, required=True)
    export.add_argument("--repository", action="append", default=[], required=True)
    export.add_argument("--replace", action="append", default=[])
    export.add_argument("--artifacts", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    verify.add_argument("--expect", action="append", default=[])
    verify.add_argument("--expect-lock", default="")
    restore = commands.add_parser("restore")
    restore.add_argument("--directory", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)
    restore.add_argument("--expect-lock", required=True)
    restore.add_argument("--application-branch", default="delivery")
    run = commands.add_parser("run", help="Execute the accepted Ansible recovery plan and recheck checkpoints")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--expect-plan", required=True)
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--phase", choices=["restore", "resume"], default="restore")
    args = parser.parse_args()
    try:
        if args.command == "restore" and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*", args.application_branch):
            raise ValueError("Invalid application delivery branch.")
        if args.command == "run":
            from flux_recovery_run import run_recovery
            run_recovery(args, verify_package)
        else:
            {"export": export_package, "verify": verify_package, "restore": restore_repositories}[args.command](args)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, yaml.YAMLError) as error:
        parser.exit(1, f"Recovery package rejected: {type(error).__name__}. Check source revisions, encryption and artifact checksums.\n")


if __name__ == "__main__":
    main()
