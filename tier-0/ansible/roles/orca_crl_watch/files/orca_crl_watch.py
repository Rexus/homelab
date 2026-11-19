#!/usr/bin/env python3
"""Inspect public ORCA trust objects; never load signing keys or manage the root VM."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import ssl
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request


UTC = timezone.utc


class WatchError(Exception):
    """An actionable check failure safe to send without endpoint credentials."""


def validate_url(value, label, allow_http=True):
    try:
        parts = urllib.parse.urlsplit(value)
        valid = (parts.scheme in (['http', 'https'] if allow_http else ['https'])
                 and parts.hostname and parts.port != 0 and not parts.username
                 and not parts.password and not parts.fragment
                 and not re.search(r'[\s<>]', value))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise WatchError(f'{label}: supply an accepted HTTP(S) URL without userinfo or fragments; '
                         'deadman HTTP requires explicit private-endpoint acceptance')
    return parts


def endpoint_path(url):
    parts = urllib.parse.urlsplit(url)
    return (parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80),
            urllib.parse.unquote(parts.path).rstrip('/'))


def load_config(path):
    with open(path, encoding='utf-8') as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise WatchError('Watchdog configuration must be a JSON object')
    for name in ('crl_url', 'root_certificate', 'root_fingerprint', 'success_url'):
        if not isinstance(config.get(name), str) or not config[name]:
            raise WatchError(f'Set {name} in the private orca_crl_watch inputs')
    validate_url(config['crl_url'], 'crl_url')
    fingerprint = config['root_fingerprint'].replace(':', '').upper()
    if not re.fullmatch(r'[0-9A-F]{64}', fingerprint):
        raise WatchError('root_fingerprint must be the accepted certificate SHA256 hex fingerprint')
    config['root_fingerprint'] = fingerprint
    allow_http = config.setdefault('allow_http_deadman', False)
    if type(allow_http) is not bool:
        raise WatchError('allow_http_deadman must be a boolean')
    success = validate_url(config['success_url'], 'success_url', allow_http)
    if not success.path.strip('/') or success.path.rstrip('/').split('/')[-1] in ('fail', 'start', 'log'):
        raise WatchError('success_url must identify a unique success check, not a service root/fail/start/log route')
    failure_url = config.get('failure_url', '')
    if not failure_url:
        if success.query:
            raise WatchError('Set failure_url explicitly when success_url has query parameters')
        failure_url = config['success_url'].rstrip('/') + '/fail'
    validate_url(failure_url, 'failure_url', allow_http)
    if failure_url.rstrip('/') == config['success_url'].rstrip('/'):
        raise WatchError('failure_url must never be the success URL')
    config['failure_url'] = failure_url
    if endpoint_path(config['crl_url']) in (
            endpoint_path(config['success_url']), endpoint_path(failure_url)):
        raise WatchError('Deadman URLs must not target the public CRL publication path')
    # Legacy configurations retain only outbound alert routing; internal CRLs default to direct.
    config.setdefault('crl_proxy_url', '')
    config.setdefault('deadman_proxy_url', config.get('proxy_url', ''))
    for name in ('crl_proxy_url', 'deadman_proxy_url'):
        if not isinstance(config[name], str):
            raise WatchError(f'{name} must be an accepted proxy URL or an empty string for direct access')
        if config[name]:
            validate_url(config[name], name)
    defaults = {'warning_after_days': 45, 'ceremony_interval_days': 60, 'expiry_safety_days': 7,
                'max_crl_days': 90, 'clock_skew_seconds': 300, 'http_timeout_seconds': 15}
    for name, default in defaults.items():
        value = config.setdefault(name, default)
        if type(value) is not int or value <= 0:
            raise WatchError(f'{name} must be a positive integer')
    if not (config['warning_after_days'] < config['ceremony_interval_days']
            and config['ceremony_interval_days'] + config['expiry_safety_days'] < config['max_crl_days']):
        raise WatchError('Require warning_after_days < ceremony_interval_days and '
                         'ceremony_interval_days + expiry_safety_days < max_crl_days')
    if config['http_timeout_seconds'] > 30 or config['clock_skew_seconds'] > 300:
        raise WatchError('Limit HTTP deadline to 30 seconds and clock skew tolerance to 300 seconds')
    return config


def openssl(*args, data=None):
    try:
        result = subprocess.run(['/usr/bin/openssl', *args], input=data, capture_output=True,
                                timeout=10, env={**os.environ, 'LC_ALL': 'C'})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise WatchError('OpenSSL unavailable or exceeded its ten-second deadline') from error
    if result.returncode:
        raise WatchError('OpenSSL rejected the public certificate/CRL or its signature')
    return result.stdout, result.stderr


def parse_dates(output):
    fields = {}
    for line in output.decode('ascii').splitlines():
        if '=' in line:
            name, value = line.split('=', 1)
            fields[name] = value
    return fields


def certificate_time(value):
    try:
        return datetime.strptime(value, '%b %d %H:%M:%S %Y GMT').replace(tzinfo=UTC)
    except (ValueError, TypeError) as error:
        raise WatchError('Missing or invalid signed certificate/CRL time') from error


def public_root(path):
    with open(path, 'rb') as handle:
        pem = handle.read(65537)
    if len(pem) > 65536 or pem.count(b'-----BEGIN CERTIFICATE-----') != 1 or b'PRIVATE KEY' in pem:
        raise WatchError('Supply one PUBLIC accepted PEM root certificate, never a private key or bundle')
    der, _ = openssl('x509', '-in', path, '-outform', 'DER')
    return der


def accepted_root(config, now):
    path = config['root_certificate']
    der = public_root(path)
    if hashlib.sha256(der).hexdigest().upper() != config['root_fingerprint']:
        raise WatchError('Accepted root SHA256 fingerprint mismatch; obtain trust from custody, not the endpoint')
    info, _ = openssl('x509', '-in', path, '-noout', '-dates', '-subject', '-issuer', '-nameopt', 'RFC2253')
    fields = parse_dates(info)
    if fields.get('subject') != fields.get('issuer'):
        raise WatchError('The accepted ORCA certificate must be a self-issued root')
    if not certificate_time(fields.get('notBefore')) <= now < certificate_time(fields.get('notAfter')):
        raise WatchError('Root certificate is outside its validity interval; verify the host clock and accepted root')
    constraints, _ = openssl('x509', '-in', path, '-noout', '-ext', 'basicConstraints')
    if b'CA:TRUE' not in constraints:
        raise WatchError('The accepted root certificate is not a CA')
    openssl('verify', '-check_ss_sig', '-attime', str(int(now.timestamp())),
            '-CAfile', path, '-no-CApath', '-no-CAstore', path)
    return fields


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise WatchError('HTTP redirect rejected; configure the final accepted publication or deadman URL')


@contextmanager
def deadline(seconds):
    # socket timeouts alone do not bound DNS lookup or a server trickling response bytes.
    def expired(signum, frame):
        raise WatchError('HTTP request exceeded its total deadline')
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def http_request(url, config, body=None):
    if body is None:
        if url != config['crl_url']:
            raise WatchError('Public CRL transport must use only the configured publication URL')
        proxy = config['crl_proxy_url']
    else:
        if (url not in (config['success_url'], config['failure_url'])
                or endpoint_path(url) == endpoint_path(config['crl_url'])):
            raise WatchError('Refuse to send deadman credentials or status to the CRL publication path')
        proxy = config['deadman_proxy_url']
    proxies = {'http': proxy, 'https': proxy} if proxy else {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies), NoRedirect(),
                                        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    request = urllib.request.Request(url, data=body, headers={
        'User-Agent': 'orca-crl-watch/1', 'Cache-Control': 'no-cache', 'Content-Type': 'text/plain'})
    limit = 4 * 1024 * 1024 if body is None else 4096
    try:
        with deadline(config['http_timeout_seconds']):
            with opener.open(request, timeout=config['http_timeout_seconds']) as response:
                if response.status != 200:
                    raise WatchError('HTTP endpoint did not return 200 OK')
                result = response.read(limit + 1)
                if len(result) > limit:
                    raise WatchError('HTTP response exceeded the bounded public-object size')
                return result
    except (urllib.error.URLError, OSError, ValueError) as error:
        # URLError strings can disclose private ping URLs; only send fixed diagnostic text.
        raise WatchError('Public CRL or deadman HTTP transport failed; check DNS, routing, TLS and endpoint policy') from error


def clock_synchronized():
    try:
        result = subprocess.run(['/usr/bin/timedatectl', 'show', '--property=NTPSynchronized', '--value'],
                                capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise WatchError('Cannot verify clock synchronization with timedatectl') from error
    if result.returncode or result.stdout.strip() != b'yes':
        raise WatchError('Host clock is not synchronized; repair the accepted NTP/chrony configuration')


def inspect_crl(config, payload, root, now, previous):
    encoding = 'PEM' if payload.lstrip().startswith(b'-----BEGIN X509 CRL-----') else 'DER'
    with tempfile.TemporaryDirectory(prefix='orca-crl-') as directory:
        crl = Path(directory) / 'public.crl'
        crl.write_bytes(payload)
        info, verification = openssl('crl', '-in', str(crl), '-inform', encoding,
                                     '-CAfile', config['root_certificate'], '-no-CApath', '-no-CAstore',
                                     '-verify', '-noout', '-lastupdate', '-nextupdate', '-issuer',
                                     '-crlnumber', '-nameopt', 'RFC2253')
        # OpenSSL <3.3 may return zero even on signature failure: require the positive verdict too.
        if b'verify OK' not in (info + verification).splitlines():
            raise WatchError('CRL signature verification failed against the accepted root')
        der, _ = openssl('crl', '-in', str(crl), '-inform', encoding, '-outform', 'DER')
    fields = parse_dates(info)
    if fields.get('issuer') != root['subject']:
        raise WatchError('Published CRL issuer is not the accepted ORCA root')
    issued = certificate_time(fields.get('lastUpdate'))
    expires = certificate_time(fields.get('nextUpdate'))
    skew = timedelta(seconds=config['clock_skew_seconds'])
    if issued > now + skew:
        raise WatchError('CRL thisUpdate is in the future; verify clock and publication')
    if issued < certificate_time(root['notBefore']):
        raise WatchError('CRL thisUpdate precedes the accepted root validity interval')
    if expires <= issued or expires > certificate_time(root['notAfter']):
        raise WatchError('Invalid CRL validity interval')
    if expires - issued > timedelta(days=config['max_crl_days']) + skew:
        raise WatchError('CRL validity exceeds the accepted maximum; expiry cannot replace the ceremony schedule')
    try:
        number = int(fields['crlNumber'], 0)
    except (ValueError, KeyError) as error:
        raise WatchError('Require a signed CRL number for rollback detection') from error
    observation = {'checked_at': now.timestamp(), 'this_update': issued.timestamp(), 'number': number,
                   'crl_sha256': hashlib.sha256(der).hexdigest(), 'root_fingerprint': config['root_fingerprint']}
    if previous:
        if previous['root_fingerprint'] != config['root_fingerprint']:
            raise WatchError('Accepted root differs from retained observation; review the explicit root transition')
        if now.timestamp() + skew.total_seconds() < previous['checked_at']:
            raise WatchError('Clock moved backwards since the retained observation')
        if (number < previous['number'] or issued.timestamp() < previous['this_update']
                or (number == previous['number'] and observation['crl_sha256'] != previous['crl_sha256'])):
            raise WatchError('Published CRL rolled back or reused an observed CRL number')
        observation['checked_at'] = max(observation['checked_at'], previous['checked_at'])
    age = now - issued
    remaining = expires - now
    if age >= timedelta(days=config['ceremony_interval_days']):
        return 'CRITICAL', 'Expected ORCA ceremony interval missed; arrange a ceremony and publish its new CRL', observation
    if remaining <= timedelta(days=config['expiry_safety_days']):
        return 'CRITICAL', 'CRL expired or entered the expiry safety window; arrange emergency renewal/publication', observation
    if age >= timedelta(days=config['warning_after_days']):
        return 'WARNING', 'ORCA ceremony advance warning; schedule renewal before the accepted interval', observation
    return 'OK', 'Public ORCA CRL signature, ceremony schedule and expiry margin verified', observation


def run_once(config, state_path, now=None, transport=http_request):
    now = now or datetime.now(UTC)
    status, message = 'CRITICAL', 'Public CRL check did not finish'
    try:
        clock_synchronized()
        previous = json.loads(state_path.read_text()) if state_path.exists() else None
        if state_path.exists() and (not isinstance(previous, dict) or not previous):
            raise WatchError('Retained watchdog state is invalid; investigate rather than resetting observations')
        root = accepted_root(config, now)
        payload = transport(config['crl_url'], config)
        status, message, observation = inspect_crl(config, payload, root, now, previous)
        # Persist only verified observations, including warnings. Never reset age from install/last ping.
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(observation) + '\n', encoding='utf-8')
        os.replace(temporary, state_path)
    except (WatchError, OSError, ValueError, KeyError, TypeError) as error:
        status = 'CRITICAL'
        message = str(error) if isinstance(error, WatchError) else 'Cannot read/retain trustworthy watchdog state or public inputs'
    try:
        url = config['success_url'] if status == 'OK' else config['failure_url']
        if transport(url, config, f'{status}: {message}\n'.encode()).strip() != b'OK':
            raise WatchError('Deadman did not acknowledge the check; verify its unique URL and service status')
    except (WatchError, OSError):
        # If success transport fails, do not report a healthy process exit; missed-ping alarm remains armed.
        status, message = 'CRITICAL', message + '; independent deadman delivery failed'
    print(f"<{'6' if status == 'OK' else '4' if status == 'WARNING' else '2'}>{status}: {message}", flush=True)
    return 0 if status == 'OK' else 1 if status == 'WARNING' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--config')
    inputs.add_argument('--validate-root')
    parser.add_argument('--state', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.validate_root:
            public_root(args.validate_root)
            return 0
        config = load_config(args.config)
        if args.validate_only:
            accepted_root(config, datetime.now(UTC))
            return 0
        if not args.state:
            raise WatchError('Supply --state in a persistent systemd StateDirectory')
        return run_once(config, args.state)
    except (WatchError, OSError, ValueError, TypeError) as error:
        message = str(error) if isinstance(error, WatchError) else 'Invalid or unreadable watchdog configuration'
        print(f'<2>CRITICAL: {message}; no healthy heartbeat sent', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
