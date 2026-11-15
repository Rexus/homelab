#!/usr/bin/env python3
"""Secretless Spinnaker client and separately provisioned authority entry point."""

import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "execute", "authority"))
    parser.add_argument("--policy", default="/policy/policy.json")
    args = parser.parse_args()
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    os.environ["GIT_ASKPASS"] = str(Path(__file__).with_name("promotion") / "git-askpass.py")
    try:
        if args.operation == 'authority':
            from promotion_authority import serve
            serve(json.loads(Path(args.policy).read_text()))
            return
        from promotion_client import request
        output = request(args.operation)
        print("SPINNAKER_CONFIG_JSON=" + json.dumps(output, ensure_ascii=True))
    except Exception:
        print('SPINNAKER_CONFIG_JSON={"result":"failed","reason":"Promotion authority request failed"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
