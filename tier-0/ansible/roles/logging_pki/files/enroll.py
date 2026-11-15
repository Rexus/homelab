"""Submit an approved logging CSR and resume only its native requester actions."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from native import EnrollmentError, NativeIssuer


def save(path, value):
    temporary = path.with_suffix('.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_context(workflow, request):
    context = workflow['context']
    profile = f"logging_{request['profile']}"
    if context.get('cert_profile') and context['cert_profile'] != profile:
        raise EnrollmentError('Workflow profile changed after submission')
    if context.get('cert_subject_style') and context['cert_subject_style'] != 'approved_csr':
        raise EnrollmentError('Workflow subject style changed after submission')
    if context.get('pkcs10') and context['pkcs10'].strip() != request['csr_pem'].strip():
        raise EnrollmentError('Workflow CSR changed after submission')
    if context.get('cert_subject') and context['cert_subject'] != f"CN={request['name']}":
        raise EnrollmentError('Workflow subject changed after submission')
    if context.get('cert_subject_parts'):
        if context['cert_subject_parts'] != {'logging_name': request['name']}:
            raise EnrollmentError('Workflow subject fields changed after submission')
    if context.get('cert_subject_alt_name'):
        observed = sorted(f'{kind}:{value}' for kind, value in context['cert_subject_alt_name'])
        if observed != sorted(request.get('san', [])):
            raise EnrollmentError('Workflow SAN changed after submission')
    if workflow['state'] == 'SUCCESS':
        if (context.get('cert_profile') != profile or context.get('cert_subject_style') != 'approved_csr'
                or context.get('pkcs10', '').strip() != request['csr_pem'].strip()
                or context.get('cert_subject') != f"CN={request['name']}"
                or sorted(f'{kind}:{value}' for kind, value in context.get('cert_subject_alt_name') or [])
                   != sorted(request.get('san', []))):
            raise EnrollmentError('Completed workflow lacks the accepted certificate identity')


def progress(issuer, workflow_id, request):
    for unused in range(12):
        workflow = issuer.show(workflow_id)
        validate_context(workflow, request)
        state = workflow['state']
        if state in ['SUCCESS', 'PENDING', 'PENDING_POLICY_VIOLATION', 'ONHOLD']:
            return workflow
        if workflow['proc_state'] in ['running', 'pause', 'wakeup', 'retry_exceeded']:
            return workflow
        actions = {
            'SETUP_REQUEST_TYPE': ('csr_upload_pkcs10', {'pkcs10': request['csr_pem'], 'csr_type': 'pkcs10'})
                if workflow['context'].get('cert_profile') else ('csr_select_profile', {
                    'cert_profile': f"logging_{request['profile']}", 'cert_subject_style': 'approved_csr'}),
            'ENTER_SUBJECT': ('csr_edit_subject', {'cert_subject_parts': 'OXJSF1:' + json.dumps(
                {'logging_name': request['name']}, separators=(',', ':'))}),
            'ENTER_SAN': ('csr_edit_san', {'cert_san_parts': 'OXJSF1:' + json.dumps(
                {'dns': [name[4:] for name in request.get('san', [])]}, separators=(',', ':'))})
                if request['profile'] == 'server' else ('global_skip', {}),
            'ENTER_CERT_INFO': ('global_skip', {}),
            'SUBJECT_COMPLETE': ('csr_submit', {}),
        }
        if state not in actions:
            raise EnrollmentError(f'Workflow {workflow_id} requires issuer review in state {state}')
        action, params = actions[state]
        try:
            issuer.execute(workflow_id, action, params)
        except EnrollmentError as error:
            raise EnrollmentError(f'Workflow {workflow_id} stopped in {state}. {error}') from error
    raise EnrollmentError('Native requester transition budget exceeded')


def collect(issuer, workflow, directory):
    identifier = workflow['context']['cert_identifier']
    chain = issuer.api('get_chain', {'start_with': identifier, 'format': 'PEM'})
    if not chain['complete'] or chain['revoked'] or len(chain['certificates']) != 3:
        raise EnrollmentError('Expected the complete leaf, issuing CA and root chain without revocation')
    if chain['identifiers'][0] != identifier:
        raise EnrollmentError('Native certificate chain begins with another certificate')
    for certificate in chain['certificates']:
        if not re.fullmatch(r'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*', certificate):
            raise EnrollmentError('Native certificate response contains material outside a public certificate')
    # Native metadata modules and openssl verify check all signatures, pins, powers and CRL next.
    save(directory / 'leaf.pem', chain['certificates'][0])
    save(directory / 'issuer.pem', chain['certificates'][1])
    save(directory / 'root.pem', chain['certificates'][2])
    save(directory / 'ca.pem', '\n'.join(chain['certificates'][1:]))
    crl = issuer.api('get_crl', {'issuer_identifier': chain['identifiers'][1],
                               'format': 'PEM', 'ignore_expired': 1}, raw=True)
    if not re.fullmatch(r'-----BEGIN X509 CRL-----\s+[A-Za-z0-9+/=\s]+-----END X509 CRL-----\s*', crl):
        raise EnrollmentError('The issuing CA has no current public CRL; run native CRL publication')
    save(directory / 'revoked.pem', crl)


def enroll(config, issuer=None):
    issuer = issuer or NativeIssuer(config)
    issuer.check()
    request = config['request']
    identity = {key: request[key] for key in ['name', 'profile', 'key_sha256', 'csr_pem']}
    identity['san'] = sorted(request.get('san', []))
    identity.update({key: config[key] for key in ['realm', 'generation', 'issuer_sha256', 'root_sha256']})
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = Path(config['workspace']) / digest
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise EnrollmentError('Enrollment workspace must be a private real directory')
    lock_fd = os.open(directory / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = directory / 'workflow.json'
        previous = json.loads(receipt.read_text()) if receipt.exists() else {}
        if previous and previous['request_sha256'] != digest:
            raise EnrollmentError('Retained request receipt differs')
        workflow_id = issuer.locked_workflow(f'logging-{digest}', previous.get('workflow_id'))
        save(receipt, json.dumps({'request_sha256': digest, 'workflow_id': workflow_id}))
        for attempt in range(config['attempts']):
            workflow = progress(issuer, workflow_id, request)
            if workflow['state'] == 'SUCCESS':
                collect(issuer, workflow, directory)
                break
            if attempt + 1 < config['attempts']:
                time.sleep(config['interval'])
        return {'name': request['name'], 'workflow_id': workflow_id, 'state': workflow['state'],
                'directory': str(directory), 'changed': issuer.changed}


if __name__ == '__main__':
    try:
        print(json.dumps(enroll(json.load(sys.stdin))))
    except EnrollmentError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Never dump native response/context or credential content.
        print(f'Logging enrollment stopped ({type(error).__name__}). Inspect the protected issuer receipt/audit log.',
              file=sys.stderr)
        sys.exit(1)
