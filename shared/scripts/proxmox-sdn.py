#!/usr/bin/env python3
"""Read one VNet's IPv4 subnet for Terraform's external data source.

The provider's native subnet data source requires a CIDR selector. This narrow
GET fills that discovery gap without putting API credentials in Terraform data.
Reference: docs/08-reference/network-inputs.md#sdn-subnet-lookup
"""

import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


class LookupError(ValueError):
    """An actionable failure that is safe to print without credentials."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the publishing/provisioning token to a redirected host.
        return None


def credentials(environ):
    for name in ("PROXMOX_VE_INSECURE", "PM_VE_INSECURE"):
        if environ.get(name, "").lower() not in ("", "0", "f", "false"):
            raise LookupError("SDN lookup requires verified TLS; remove the TLS bypass and install API trust.")
    endpoints = {environ[name].rstrip("/") for name in
                 ("TF_VAR_proxmox_api_url", "PROXMOX_VE_ENDPOINT", "PROXMOX_API_URL") if environ.get(name)}
    tokens = {environ["PROXMOX_VE_API_TOKEN"]} if environ.get("PROXMOX_VE_API_TOKEN") else set()
    for id_name, secret_name in (
        ("TF_VAR_proxmox_api_token_id", "TF_VAR_proxmox_api_token_secret"),
        ("PROXMOX_API_TOKEN_ID", "PROXMOX_API_TOKEN_SECRET"),
    ):
        token_id, secret = environ.get(id_name), environ.get(secret_name)
        if token_id or secret:
            if not token_id or not secret:
                raise LookupError("SDN lookup requires both API token ID and secret.")
            tokens.add(f"{token_id}={secret}")
    if len(endpoints) != 1 or len(tokens) != 1:
        raise LookupError("Set one consistent Proxmox API endpoint and token in the execution environment.")
    endpoint, token = endpoints.pop(), tokens.pop()
    try:
        parsed = urllib.parse.urlsplit(endpoint)
    except ValueError as exc:
        raise LookupError("Set a valid HTTPS Proxmox endpoint.") from exc
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise LookupError("SDN lookup requires an HTTPS Proxmox endpoint without embedded credentials or query parameters.")
    token_id, separator, secret = token.partition("=")
    if not separator or "!" not in token_id or not secret or any(c in token for c in "\r\n"):
        raise LookupError("Set a valid Proxmox API token outside Git.")
    return endpoint.removesuffix("/api2/json"), token


def resolve_subnet(records):
    if not isinstance(records, list):
        raise LookupError("Proxmox returned an invalid subnet list.")
    candidates = []
    for record in records:
        try:
            network = ipaddress.ip_network(record["cidr"], strict=True)
        except (KeyError, TypeError, ValueError) as exc:
            raise LookupError("A VNet subnet has an invalid CIDR; correct the SDN subnet record.") from exc
        if network.version == 4:
            candidates.append((network, record.get("gateway")))
    if len(candidates) != 1:
        raise LookupError("SDN lookup requires exactly one IPv4 subnet on the selected VNet; use explicit settings otherwise.")
    network, gateway_text = candidates[0]
    try:
        gateway = ipaddress.IPv4Address(gateway_text)
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise LookupError("The SDN IPv4 subnet needs its existing gateway address recorded.") from exc
    if (gateway not in network or not 1 <= network.prefixlen <= 30
            or gateway in (network.network_address, network.broadcast_address)):
        raise LookupError("The SDN gateway must be a usable host address inside an IPv4 subnet with prefix 1-30.")
    return {"cidr_ipv4": str(network), "gateway_ipv4": str(gateway)}


def lookup(vnet, environ):
    if not isinstance(vnet, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,7}", vnet):
        raise LookupError("Select a valid Proxmox SDN VNet ID, not a zone or alias.")
    endpoint, token = credentials(environ)
    request = urllib.request.Request(
        f"{endpoint}/api2/json/cluster/sdn/vnets/{vnet}/subnets?running=1",
        headers={"Authorization": f"PVEAPIToken={token}", "Accept": "application/json"},
    )
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )
        with opener.open(request, timeout=20) as response:
            payload = json.load(response)
        return resolve_subnet(payload["data"])
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise LookupError(
                f"Proxmox SDN lookup returned HTTP 403 for VNet {vnet}; subnet reads require SDN.Audit, "
                "not just SDN.Use. Check the effective VNet permissions of the token and owning user."
            ) from exc
        raise LookupError(f"Proxmox SDN lookup returned HTTP {exc.code}; check the VNet and scoped SDN.Audit permissions.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        if isinstance(reason, ssl.SSLCertVerificationError):
            detail = "TLS certificate verification failed; check the approved CA, certificate dates and API hostname/SAN"
        elif isinstance(reason, socket.gaierror):
            detail = "cannot resolve the API hostname; check execution-host DNS"
        elif isinstance(reason, (TimeoutError, socket.timeout)):
            detail = "API connection timed out; check routing, firewall rules and port 8006"
        elif isinstance(reason, ConnectionRefusedError):
            detail = "API connection refused; check the endpoint port and Proxmox API service"
        elif isinstance(reason, ssl.SSLError):
            detail = "TLS handshake failed; check the API certificate and execution-host TLS configuration"
        else:
            detail = "check the endpoint, connectivity and execution-host CA trust files"
        raise LookupError(f"Cannot read the SDN subnet over verified HTTPS: {detail}.") from exc
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LookupError("Proxmox returned an invalid SDN API response.") from exc


def main():
    try:
        query = json.load(sys.stdin)
        if not isinstance(query, dict):
            raise LookupError("Provide a VNet lookup query object.")
        result = lookup(query.get("vnet"), os.environ)
    except (LookupError, json.JSONDecodeError) as exc:
        print(f"SDN lookup: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
