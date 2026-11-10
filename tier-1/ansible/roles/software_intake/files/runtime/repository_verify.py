"""Read sealed vendor repositories; native tools/libraries own formats and signatures.

No network, package installation, metadata rewriting or writes to the payload.
DNF/debmirror acquire; this adapter closes the post-copy integrity gap before promotion.
"""

import argparse
import bz2
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


def command(argv, allowed_returncodes=(0,)):
    result = subprocess.run([str(arg) for arg in argv], capture_output=True, text=True,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode not in allowed_returncodes:
        raise ValueError(f'{argv[0]} verification failed: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout


def contained_file(root, name):
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or '..' in relative.parts or ':' in name or '\\' in name:
        raise ValueError(f'Nonlocal repository reference: {name}')
    path = root
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f'Symlink in sealed repository: {name}')
    if not path.is_file():
        raise ValueError(f'Missing repository file: {name}')
    return path


def check_file(root, name, digest, size, algorithm='sha256'):
    if algorithm not in ('sha256', 'sha384', 'sha512'):
        raise ValueError(f'Unsupported weak checksum: {algorithm}')
    path = contained_file(root, name)
    if path.stat().st_size != int(size):
        raise ValueError(f'Repository size mismatch: {name}')
    calculated = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            calculated.update(chunk)
    if calculated.hexdigest() != digest:
        raise ValueError(f'Repository checksum mismatch: {name}')
    return path


def require_complete_payload(root, allowed):
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Nonordinary entry in sealed repository')
        if path.is_file():
            actual.add(str(path.relative_to(root)))
    if actual != allowed:
        extra = sorted(actual - allowed)
        missing = sorted(allowed - actual)
        raise ValueError(f'Unauthenticated extra repository files: {extra}; missing authenticated files: {missing}')


def check_key(path, fingerprint, home):
    records = command(['gpg', '--no-options', '--batch', '--homedir', home,
                       '--with-colons', '--show-keys', path]).splitlines()
    primary, fingerprints = False, []
    for line in records:
        fields = line.split(':')
        if fields[0] == 'pub':
            if fields[1] in ('r', 'e'):
                raise ValueError('Publisher key is revoked or expired')
            primary = True
        elif fields[0] == 'fpr' and primary:
            fingerprints.append(fields[9].upper())
            primary = False
    if fingerprints != [fingerprint.upper()]:
        raise ValueError('Publisher keyring must contain only the pinned primary key')


def check_signature(args, signature, data=None, output=None):
    argv = ['gpgv', '--homedir', args.work / 'gnupg', '--status-fd=1', '--keyring', args.keyring]
    if output:
        argv += ['--output', output]
    # Like native APT, permit unknown additional signers only alongside a valid
    # pinned signer. gpgv returns 2 for that mixed case; cryptography stays in gpgv.
    status = command(argv + [signature] + ([data] if data else []), allowed_returncodes=(0, 2))
    records = [line.split()[1:] for line in status.splitlines() if line.startswith('[GNUPG:] ')]
    valid = False
    for record in records:
        if record[0] == 'VALIDSIG' and len(record) >= 10:
            if record[1].upper() == args.fingerprint.upper() or record[-1].upper() == args.fingerprint.upper():
                if record[8] not in ('8', '9', '10', '11'):
                    raise ValueError('Weak publisher signature digest')
                valid = True
        if record[0] in ('EXPKEYSIG', 'EXPSIG', 'REVKEYSIG', 'KEYEXPIRED', 'SIGEXPIRED', 'BADSIG', 'ERROR', 'FAILURE'):
            raise ValueError('Missing, expired, revoked or bad publisher signature')
        if record[0] == 'ERRSIG' and (len(record) < 7 or record[6] != '9'):
            raise ValueError('Unsupported or invalid publisher signature')
    if not valid:
        raise ValueError('Missing valid pinned publisher signature')


def verify_rpm(args):
    import createrepo_c as cr

    repomd_path = contained_file(args.payload, 'repodata/repomd.xml')
    allowed = {'repodata/repomd.xml'}
    metadata_signed = (args.payload / 'repodata/repomd.xml.asc').exists()
    if args.repo_gpgcheck == 'true' or metadata_signed:
        check_signature(args, contained_file(args.payload, 'repodata/repomd.xml.asc'), repomd_path)
        allowed.add('repodata/repomd.xml.asc')
    metadata = cr.Repomd(str(repomd_path))
    primary = []
    for record in metadata.records:
        if record.location_base:
            raise ValueError('External RPM metadata locations are not publishable')
        path = check_file(args.payload, record.location_href, record.checksum, record.size, record.checksum_type)
        allowed.add(str(path.relative_to(args.payload)))
        if record.type == 'primary':
            primary.append(path)
    if len(primary) != 1:
        raise ValueError('Require exactly one authenticated RPM primary index')
    # Requiring both classes rejects unsigned RPMs even where distro defaults accept digests alone.
    rpmkeys = ['rpmkeys', '--dbpath', args.work / 'rpmdb', '--define', '_keyring rpmdb',
               '--define', '_pkgverify_level all', '--define', '_pkgverify_flags 0x0']
    command(rpmkeys + ['--import', args.key])
    verified, outside = {}, 0

    def package(pkg):
        nonlocal outside
        if pkg.arch not in args.architectures:
            outside += 1
            return
        if pkg.location_base:
            raise ValueError('External RPM package locations are not publishable')
        name = str(PurePosixPath(pkg.location_href))
        identity = (pkg.pkgId, pkg.size_package, pkg.checksum_type)
        if name in verified:
            if verified[name] != identity:
                raise ValueError('Conflicting RPM records for one path')
            return
        check_file(args.payload, pkg.location_href, pkg.pkgId, pkg.size_package, pkg.checksum_type)
        verified[name] = identity

    cr.xml_parse_primary(str(primary[0]), pkgcb=package, do_files=False)
    if not verified:
        raise ValueError('No RPM packages in selected architecture scope')
    require_complete_payload(args.payload, allowed | set(verified))
    paths = list(verified)
    for offset in range(0, len(paths), 128):
        command(rpmkeys + ['--checksig', '--'] + [args.payload / name for name in paths[offset:offset + 128]])
    return {'kind': 'rpm', 'packages_verified': len(verified), 'metadata_files_verified': len(metadata.records),
            'metadata_signature': metadata_signed, 'architectures': sorted(args.architectures),
            'package_records_outside_scope': outside}


def verify_apt(args):
    from debian.deb822 import Packages, Release

    distribution = args.payload / 'dists' / args.distribution
    prefix = f'dists/{args.distribution}/'
    allowed = set()
    if (distribution / 'InRelease').is_file():
        release_file = args.work / 'Release.verified'
        check_signature(args, contained_file(args.payload, f'dists/{args.distribution}/InRelease'), output=release_file)
        allowed.add(prefix + 'InRelease')
    else:
        release_file = contained_file(args.payload, f'dists/{args.distribution}/Release')
        check_signature(args, contained_file(args.payload, f'dists/{args.distribution}/Release.gpg'), release_file)
        allowed.update((prefix + 'Release', prefix + 'Release.gpg'))
    if (distribution / 'InRelease').is_file() and (distribution / 'Release').exists():
        plain = contained_file(args.payload, f'dists/{args.distribution}/Release')
        check_signature(args, contained_file(args.payload, f'dists/{args.distribution}/Release.gpg'), plain)
        allowed.update((prefix + 'Release', prefix + 'Release.gpg'))
        if plain.read_bytes().replace(b'\r\n', b'\n') != release_file.read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('Signed APT Release and InRelease disagree')
    with release_file.open('rb') as stream:
        release = Release(stream)
    if release.get('Codename') != (args.expected_codename or args.distribution):
        raise ValueError('Signed APT codename differs from the selected distribution')
    if not set(args.architectures) <= set(release.get('Architectures', '').split()):
        raise ValueError('Selected APT architecture is absent from signed Release')
    if not set(args.components) <= set(release.get('Components', '').split()):
        raise ValueError('Selected APT component is absent from signed Release')
    now = datetime.now(timezone.utc)
    date = parsedate_to_datetime(release['Date'])
    if date.tzinfo is None or date > now + timedelta(minutes=10):
        raise ValueError('Invalid or future APT Release date')
    expiry = release.get('Valid-Until')
    if expiry:
        until = parsedate_to_datetime(expiry)
        if until.tzinfo is None or until <= now or until < date:
            raise ValueError('APT Release has expired or has invalid validity dates')
    entries = {entry['name']: entry for entry in release.get('SHA256', [])}
    if not entries:
        raise ValueError('Signed Release has no SHA256 index bindings')
    for name, entry in entries.items():
        if (distribution / name).exists():
            path = check_file(distribution, name, entry['sha256'], entry['size'])
            allowed.add(str(path.relative_to(args.payload)))
    verified = {}
    for component in args.components:
        for architecture in args.architectures:
            prefix = f'{component}/binary-{architecture}/Packages'
            indexes = [prefix + suffix for suffix in ('.xz', '.gz', '.bz2', '')
                       if prefix + suffix in entries and (distribution / (prefix + suffix)).is_file()]
            if not indexes:
                raise ValueError(f'Missing signed package index for selected scope: {prefix}')
            index = contained_file(distribution, indexes[0])
            opener = {'.xz': lzma.open, '.gz': gzip.open, '.bz2': bz2.open}.get(index.suffix, open)
            with opener(index, 'rb') as stream:
                for pkg in Packages.iter_paragraphs(stream, use_apt_pkg=False):
                    name = str(PurePosixPath(pkg['Filename']))
                    identity = (pkg['SHA256'], int(pkg['Size']))
                    if pkg['Architecture'] not in (architecture, 'all'):
                        raise ValueError('APT package architecture differs from its selected index')
                    if name in verified and verified[name] != identity:
                        raise ValueError('Conflicting APT records for one path')
                    if name not in verified:
                        check_file(args.payload, name, *identity)
                        verified[name] = identity
    if not verified:
        raise ValueError('No APT packages in selected scope')
    require_complete_payload(args.payload, allowed | set(verified))
    return {'kind': 'apt', 'packages_verified': len(verified), 'metadata_signature': True,
            'distribution': args.distribution, 'codename': release['Codename'],
            'architectures': sorted(args.architectures),
            'components': args.components, 'release_valid_until': expiry,
            'release_expiry_enforced': bool(expiry)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('rpm', 'apt'), required=True)
    for name in ('payload', 'work', 'key', 'keyring'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--fingerprint', required=True)
    parser.add_argument('--architectures', required=True)
    parser.add_argument('--repo-gpgcheck', choices=('true', 'false'), default='false')
    parser.add_argument('--distribution', default='')
    parser.add_argument('--expected-codename', default='')
    parser.add_argument('--components', default='')
    args = parser.parse_args()
    args.payload = args.payload.resolve(strict=True)
    args.key, args.keyring = args.key.resolve(strict=True), args.keyring.resolve(strict=True)
    args.work = args.work.resolve()
    if args.work.is_relative_to(args.payload) or args.payload.is_relative_to(args.work):
        raise ValueError('Verification work must be outside the sealed payload')
    args.architectures = set(args.architectures.split(','))
    args.components = args.components.split(',')
    if not re.fullmatch(r'[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64}', args.fingerprint):
        raise ValueError('Require a full publisher fingerprint')
    args.work.mkdir(mode=0o700, parents=True, exist_ok=True)
    (args.work / 'gnupg').mkdir(mode=0o700, exist_ok=True)
    os.environ.update(HOME=str(args.work), TMPDIR=str(args.work), GNUPGHOME=str(args.work / 'gnupg'))
    check_key(args.key, args.fingerprint, args.work / 'gnupg')
    check_key(args.keyring, args.fingerprint, args.work / 'gnupg')
    evidence = verify_rpm(args) if args.kind == 'rpm' else verify_apt(args)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Repository verification rejected: {error}', file=sys.stderr)
        sys.exit(1)
