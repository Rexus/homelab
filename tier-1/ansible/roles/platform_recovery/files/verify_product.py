#!/usr/bin/env python3
"""Verify retained product content and authorization from an isolated recovery Job."""

import hashlib
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def verify(checks, fetch):
    if not any("content_sha256" in check for check in checks):
        raise ValueError("Require independently recorded recovered content.")
    if not any(check["status"] in (401, 403) for check in checks):
        raise ValueError("Require an actual denied access path.")
    for check in checks:
        status, content = fetch(check)
        if status != check["status"]:
            raise ValueError("Product returned an unexpected response status.")
        if "content_sha256" in check and hashlib.sha256(content).hexdigest() != check["content_sha256"]:
            raise ValueError("Product contents differ from the selected retained backup.")
    return len(checks)


def main():
    checks = json.loads(Path("/verification/checks.json").read_text())
    context = ssl.create_default_context(cafile="/roots/ca.pem")
    client = build_opener(ProxyHandler({}), HTTPSHandler(context=context), NoRedirect())

    def fetch(check):
        headers = {}
        if check.get("authenticated", False):
            headers = json.loads(Path("/credentials/headers.json").read_text())
        if not check["url"].startswith("https://"):
            raise ValueError("Product verification requires its private verified HTTPS endpoint.")
        try:
            response = client.open(Request(check["url"], headers=headers), timeout=30)
        except HTTPError as response:
            return response.code, response.read()
        with response:
            return response.status, response.read()

    print(json.dumps({"verified_checks": verify(checks, fetch)}, sort_keys=True))


if __name__ == "__main__":
    main()
