"""Isolated syslog-ng process fixtures; never install packages or touch host services."""

import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import time

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / "tier-0/ansible/roles/syslog_ng"
BINARY = os.environ.get("SYSLOG_NG_TEST_BINARY")


def render_config(directory, port, udp_sources=None):
    from jinja2 import Environment, StrictUndefined

    values = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    values.update(
        syslog_ng_data_mount=str(directory / "data"),
        syslog_ng_config_dir=str(directory), syslog_ng_listen_address="127.0.0.1",
        syslog_ng_tls_port=port, syslog_ng_udp_port=port,
        syslog_ng_tls_crl_src='',
        syslog_ng_user=str(os.getuid()), syslog_ng_read_group=str(os.getgid()),
        syslog_ng_queue_bytes=1048576,
        syslog_ng_sources=[dict(name="producer", address="127.0.0.1", tier=0, tls_dn="CN=producer")],
        syslog_ng_legacy_sources=udp_sources or [],
    )
    template = Environment(undefined=StrictUndefined, keep_trailing_newline=True).from_string(
        (ROLE / "templates/receiver.conf.j2").read_text())
    return template.render(**values)


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise AssertionError(f"{' '.join(map(str, args))}\n{result.stdout}{result.stderr}")
    return result


def certificates(directory):
    tls = directory / "tls"
    tls.mkdir()
    command("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
            "-subj", "/CN=disposable-test-ca", "-keyout", str(tls / "ca.key"), "-out", str(tls / "ca.pem"))
    for name in ("server", "producer", "impostor"):
        command("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={name}",
                "-keyout", str(tls / f"{name}.key"), "-out", str(tls / f"{name}.csr"))
        extensions = tls / f"{name}.ext"
        extensions.write_text("subjectAltName=IP:127.0.0.1,DNS:localhost\nextendedKeyUsage=serverAuth,clientAuth\n")
        command("openssl", "x509", "-req", "-in", str(tls / f"{name}.csr"), "-CA", str(tls / "ca.pem"),
                "-CAkey", str(tls / "ca.key"), "-CAcreateserial", "-days", "2",
                "-extfile", str(extensions), "-out", str(tls / f"{name}.pem"))
    (tls / "key.pem").write_bytes((tls / "server.key").read_bytes())
    command("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
            "-subj", "/CN=producer", "-keyout", str(tls / "untrusted.key"), "-out", str(tls / "untrusted.pem"))


def send(directory, port, messages, identity="producer"):
    context = ssl.create_default_context(cafile=str(directory / "tls/ca.pem"))
    if identity:
        context.load_cert_chain(str(directory / f"tls/{identity}.pem"), str(directory / f"tls/{identity}.key"))
    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
        with context.wrap_socket(connection, server_hostname="127.0.0.1") as encrypted:
            encrypted.sendall(b"".join(message.encode() + b"\n" for message in messages))
            try:
                encrypted.unwrap().close()
            except (ssl.SSLError, OSError):
                pass


def records(directory):
    return [json.loads(line) for path in (directory / "data/records").rglob("*.jsonl")
            for line in path.read_text().splitlines()]


def wait_for_records(directory, count):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        found = records(directory)
        if len(found) >= count:
            return found
        time.sleep(0.05)
    raise AssertionError(f"Only {len(records(directory))} of {count} records persisted")
