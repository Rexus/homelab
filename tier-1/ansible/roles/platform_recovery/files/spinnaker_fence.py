#!/usr/bin/env python3
"""Terminalize retained Orca executions through its native recovery admin API.

The SQL inventory is read by the native MySQL client from the restored database.
Orca runs with keiko.queue.enabled=false throughout this operation.
"""

import json
import os
from pathlib import Path
import re
import ssl
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler


TERMINAL = {"SUCCEEDED", "FAILED_CONTINUE", "TERMINAL", "CANCELED", "STOPPED", "SKIPPED"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise ValueError("Recovery admin requests must not redirect credentials.")


def fence(inventory, request):
    """Visit every retained SQL execution, including orphaned application histories."""
    entries = []
    for line in inventory.splitlines():
        kind, separator, identity = line.partition("\t")
        if (not separator or kind not in ("PIPELINE", "ORCHESTRATION") or
                not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identity)):
            raise ValueError("Unexpected execution identity from the restored SQL inventory.")
        entries.append((kind, identity))
    if len(set(entries)) != len(entries):
        raise ValueError("Duplicate execution identities in restored inventory.")
    for kind, identity in entries:
        query = urlencode({"executionId": identity, "executionType": kind,
                           "canceledBy": "independent-platform-recovery"})
        request("PUT", "/admin/forceCancelExecution?" + query)
        path = ("/pipelines/" if kind == "PIPELINE" else "/tasks/") + identity
        result = request("GET", path)
        if result.get("status") not in TERMINAL:
            raise ValueError("Native execution remains nonterminal. Keep queue processing disabled.")
    # Recheck the complete retained inventory after all cancellation writes have finished.
    for kind, identity in entries:
        result = request("GET", ("/pipelines/" if kind == "PIPELINE" else "/tasks/") + identity)
        if result.get("status") not in TERMINAL:
            raise ValueError("Execution state changed during recovery. Keep consumers fenced.")
    return {"verified_execution_count": len(entries), "action": "native-force-cancel"}


def main():
    endpoint = os.environ["ORCA_URL"].rstrip("/")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
        raise ValueError("Use the exact private HTTPS Orca endpoint.")
    headers = json.loads(Path("/credentials/headers.json").read_text())
    context = ssl.create_default_context(cafile="/roots/platform.crt")
    client = build_opener(HTTPSHandler(context=context), NoRedirect())

    def request(method, path):
        with client.open(Request(endpoint + path, method=method, headers=headers), timeout=30) as response:
            data = response.read()
            return json.loads(data) if data else {}

    result = fence(Path("/work/executions.tsv").read_text(), request)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
