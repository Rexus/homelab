#!/usr/bin/env python3
"""Fingerprint reviewed deployment inputs without storing their secret contents."""

import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(repo, shared, setup, environment, state, inputs):
    roots = [repo / "ansible", repo / "terraform/modules", repo / "terraform/deployments" / setup,
             shared / "ansible", shared / "scripts", shared / "config", shared / "templates"]
    files = set()
    extensions = {".yml", ".yaml", ".j2", ".cfg", ".tf", ".hcl", ".sh", ".py", ".json", ".tfvars"}
    for root in roots:
        for path in root.rglob("*"):
            if any(part in {".terraform", "__pycache__", ".git"} for part in path.relative_to(root).parts):
                continue
            if path.is_file() and path.suffix in extensions:
                files.add(path.resolve())
    files.update(Path(value).resolve(strict=True) for value in inputs if value)
    return {
        "version": 2, "setup": setup, "environment": environment, "state": str(state),
        "input_order": [str(Path(value).resolve()) for value in inputs if value],
        "inputs": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "shared", "setup", "environment", "state"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("inputs", nargs="*")
    args = parser.parse_args()
    result = fingerprint(Path(args.repo).resolve(), Path(args.shared).resolve(), args.setup,
                         args.environment, Path(args.state).resolve(), args.inputs)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
