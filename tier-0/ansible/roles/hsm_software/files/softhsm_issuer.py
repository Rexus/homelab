#!/usr/bin/python3
"""Bounded SoftHSM ceremony via Debian's native PyKCS11 binding.

JSON input is delivered on stdin by a no_log Ansible task. Neither PIN is an
argument or persisted. The pending marker deliberately survives failed writes:
partial commissioning needs recovery, never a blind repeat of C_InitToken.
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import PyKCS11 as p11
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular_tree(path):
    require(path.resolve() == path.absolute(), 'Linked custody path; recover original storage.')
    require(path.is_dir(), 'Missing original token directory; recover it.')
    for child in path.rglob('*'):
        require(not child.is_symlink() and (child.is_file() or child.is_dir()),
                'Linked or special token entry; recover original storage.')


def write_new(path, value):
    # Exclusive, durable creation also refuses symlinks and existing partial records.
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def key_uri(label, serial, key_id):
    key_bytes = ''.join('%%%02X' % byte for byte in bytes.fromhex(key_id))
    return f'pkcs11:token={label};serial={serial};id={key_bytes};type=private'


def initialized_tokens(library):
    return [(slot, library.getTokenInfo(slot)) for slot in library.getSlotList(tokenPresent=True)
            if library.getTokenInfo(slot).flags & p11.CKF_TOKEN_INITIALIZED]


def public_identity(library, slot, request, pin=''):
    session = library.openSession(slot, p11.CKF_SERIAL_SESSION)
    try:
        if pin:
            session.login(pin)
        public = session.findObjects([(p11.CKA_CLASS, p11.CKO_PUBLIC_KEY)])
        require(len(public) == 1, 'Expected exactly one original public key; recover token.')
        key_id, label, modulus, exponent = session.getAttributeValue(public[0], [
            p11.CKA_ID, p11.CKA_LABEL, p11.CKA_MODULUS, p11.CKA_PUBLIC_EXPONENT])
        require(bytes(key_id).hex() == request['key_id'] and label == request['key_label'],
                'Original key ID or label differs; no key is replaced.')
        key = rsa.RSAPublicNumbers(int.from_bytes(bytes(exponent), 'big'),
                                   int.from_bytes(bytes(modulus), 'big')).public_key()
        require(key.key_size == request['rsa_bits'], 'Original RSA size differs.')
        if pin:
            private = session.findObjects([(p11.CKA_CLASS, p11.CKO_PRIVATE_KEY)])
            require(len(private) == 1, 'Expected exactly one original private key.')
            attrs = session.getAttributeValue(private[0], [
                p11.CKA_ID, p11.CKA_LABEL, p11.CKA_SENSITIVE, p11.CKA_EXTRACTABLE,
                p11.CKA_SIGN, p11.CKA_DECRYPT, p11.CKA_UNWRAP])
            require(bytes(attrs[0]).hex() == request['key_id'] and attrs[1] == request['key_label']
                    and attrs[2:] == [True, False, True, False, False],
                    'Private key identity or signing-only attributes differ.')
            challenge = os.urandom(32)
            signature = bytes(session.sign(private[0], challenge,
                                          p11.Mechanism(p11.CKM_SHA256_RSA_PKCS, None)))
            key.verify(signature, challenge, padding.PKCS1v15(), hashes.SHA256())
        der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return hashlib.sha256(der).hexdigest()
    finally:
        session.closeSession()


def validate_pins(request):
    for name in ('so_pin', 'user_pin'):
        require(isinstance(request.get(name), str) and 16 <= len(request[name].encode()) <= 255,
                'Explicit initialization requires two independent PINs of 16 to 255 bytes.')
    require(request['so_pin'] != request['user_pin'], 'SO and application PINs must differ.')
    require(not re.search(r'[\x00-\x1f\x7f"\\$]', request['user_pin']),
            'Application PIN must satisfy the existing immutable PKCS11 policy credential contract.')


def initialize(library, request):
    free = [slot for slot in library.getSlotList(tokenPresent=True)
            if not library.getTokenInfo(slot).flags & p11.CKF_TOKEN_INITIALIZED]
    require(len(free) == 1, 'Expected exactly one empty SoftHSM slot.')
    # C_InitToken requires a 32-byte space-padded label. Older PyKCS11 pads with
    # NULs otherwise, which breaks libp11's exact token-label URI selection.
    library.initToken(free[0], request['so_pin'], request['label'].ljust(32, ' '))
    tokens = initialized_tokens(library)
    require(len(tokens) == 1, 'Token initialization did not produce one selected token.')
    slot, info = tokens[0]
    session = library.openSession(slot, p11.CKF_SERIAL_SESSION | p11.CKF_RW_SESSION)
    try:
        session.login(request['so_pin'], p11.CKU_SO)
        session.initPin(request['user_pin'])
        session.logout()
        session.login(request['user_pin'])
        common = [(p11.CKA_TOKEN, True), (p11.CKA_ID, tuple(bytes.fromhex(request['key_id']))),
                  (p11.CKA_LABEL, request['key_label'])]
        session.generateKeyPair(
            common + [(p11.CKA_CLASS, p11.CKO_PUBLIC_KEY), (p11.CKA_PRIVATE, False),
                      (p11.CKA_MODULUS_BITS, request['rsa_bits']),
                      (p11.CKA_PUBLIC_EXPONENT, (1, 0, 1)), (p11.CKA_VERIFY, True),
                      (p11.CKA_ENCRYPT, False), (p11.CKA_WRAP, False)],
            common + [(p11.CKA_CLASS, p11.CKO_PRIVATE_KEY), (p11.CKA_PRIVATE, True),
                      (p11.CKA_SENSITIVE, True), (p11.CKA_EXTRACTABLE, False),
                      (p11.CKA_SIGN, True), (p11.CKA_DECRYPT, False), (p11.CKA_UNWRAP, False)])
    finally:
        session.closeSession()
    return slot, info


def run(request):
    operation = request['operation']
    require(operation in ('configure', 'initialize', 'inspect', 'bind'), 'Unknown software-token operation.')
    require(re.fullmatch(r'[A-Za-z0-9_-]{3,32}', request['label']) is not None
            and re.fullmatch(r'[A-Za-z0-9_-]{3,32}', request['key_label']) is not None
            and re.fullmatch(r'(?:[a-f0-9]{2}){1,16}', request['key_id']) is not None
            and request['rsa_bits'] in (3072, 4096), 'Invalid token identity inputs.')
    root = Path(request['root'])
    tokens = root / 'tokens'
    regular_tree(root)
    regular_tree(tokens)
    record = root / 'identity.json'
    pending = root / 'initialization.pending'
    # Lock only this automation; an inactive issuer is enforced by the playbook.
    lock_flags = os.O_RDONLY if operation == 'inspect' else os.O_RDWR | os.O_CREAT
    with os.fdopen(os.open(root / '.ceremony.lock', lock_flags | os.O_NOFOLLOW, 0o600),
                   'r' if operation == 'inspect' else 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        require(not pending.exists(), 'Incomplete initialization: retain files and recover; do not initialize again.')
        library = p11.PyKCS11Lib()
        library.load(request['library'])
        present = initialized_tokens(library)
        expected = {key: request[key] for key in ('label', 'key_label', 'key_id', 'rsa_bits', 'library')}
        if record.exists():
            binding = json.loads(record.read_text())
            require(set(binding) == set(expected) | {'serial', 'spki_sha256', 'key_uri'},
                    'Unexpected identity record fields; recover the original record.')
            require(all(binding.get(key) == value for key, value in expected.items()),
                    'Recorded token configuration differs; restore or plan a custody migration.')
            require(binding['key_uri'] == key_uri(binding['label'], binding['serial'], binding['key_id']),
                    'Recorded key URI differs from its token/key identity; recover the original record.')
            require(len(present) == 1, 'Missing or additional initialized token; recover original token directory.')
            slot, info = present[0]
            require(info.label.strip() == binding['label'] and info.serialNumber.strip() == binding['serial'],
                    'Original token serial or label differs; recover original token.')
            fingerprint = public_identity(library, slot, request,
                                          request.get('user_pin', '') if operation == 'initialize' else '')
            require(fingerprint == binding['spki_sha256'], 'Original public key differs; recover original key.')
            for field, pin in (('serial', 'expected_serial'), ('spki_sha256', 'expected_spki_sha256')):
                require(not request.get(pin) or request[pin] == binding[field],
                        'Independently recorded identity pin differs; no mutation permitted.')
            return dict(binding, initialized=True, changed=False)
        require(not present and not any(tokens.iterdir()),
                'Unregistered token data: recover its identity record; never initialize over it.')
        require(not request.get('expected_serial') and not request.get('expected_spki_sha256'),
                'Previously pinned token is missing; recover its files instead of generating a new key.')
        if operation == 'configure':
            return {'initialized': False, 'changed': False,
                    'next': 'Run explicit initialize once with independent protected PINs.'}
        require(operation == 'initialize', 'Initialize explicitly on a fresh issuer or restore the original token.')
        # A PKCS11 initializer must never become an implicit PEM/installed-issuer migration.
        data = Path(request['issuer_data'])
        require(not any((data / path).exists() for path in (
            'deployment.json', 'keys/issuer.pem', 'identity/issuer.pem', 'identity/issuer.csr')),
            'Existing issuer state requires a planned migration, not fresh initialization.')
        validate_pins(request)
        write_new(pending, expected)
        slot, info = initialize(library, request)
        serial = info.serialNumber.strip()
        require(re.fullmatch(r'[a-f0-9]{16}', serial) is not None, 'Unexpected SoftHSM token serial.')
        fingerprint = public_identity(library, slot, request, request['user_pin'])
        binding = dict(expected, serial=serial, spki_sha256=fingerprint,
                       key_uri=key_uri(request['label'], serial, request['key_id']))
        write_new(record, binding)
        pending.unlink()
        sync_directory(root)
        return dict(binding, initialized=True, changed=True)


if __name__ == '__main__':
    os.umask(0o077)
    try:
        print(json.dumps(run(json.load(sys.stdin)), sort_keys=True))
    except ValueError as error:
        print(json.dumps({'error': str(error)}))
        sys.exit(1)
    except Exception:
        # Native-library exceptions/tracebacks must not reflect sensitive inputs.
        print(json.dumps({'error': 'Native token operation failed; preserve state and inspect recovery records.'}))
        sys.exit(1)
