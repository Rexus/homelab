"""Bounded OpenXPKI Community 3.34 CLI calls for logging enrollment.

Reviewed native source is openxpki/openxpki at 5c0389789c6275095aec7d6db2dbd85cd5869405.
The CLI's key=value arguments avoid the broken --payload reader in this revision.
No issuer key, token password, or authentication key content enters this process.
"""

import json
import subprocess


class EnrollmentError(RuntimeError):
    pass


class NativeIssuer:
    def __init__(self, config):
        self.config = config
        self.changed = False

    def call(self, command, arguments=(), params=None, raw=False):
        argv = [self.config['cli'], '--auth-key', self.config['auth_key'], '--json']
        argv += list(command) + ['--realm', self.config['realm']] + list(arguments)
        if params:
            argv += ['--'] + [f'{key}={value}' for key, value in params.items()]
        try:
            completed = subprocess.run(argv, text=True, capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as error:
            raise EnrollmentError('Native CLI timed out; rerun to recover the existing workflow lock') from error
        if completed.returncode:
            # Native stderr can contain workflow context. Publish only the failed operation name.
            raise EnrollmentError(f"OpenXPKI {' '.join(command)} failed; inspect the issuer audit log")
        if raw:
            return completed.stdout
        if not completed.stdout.strip():
            return None
        try:
            return json.loads(completed.stdout)
        except ValueError as error:
            raise EnrollmentError('Native CLI returned an unsupported response shape') from error

    def api(self, name, params=None, raw=False):
        return self.call(['api', name], params=params, raw=raw)

    def check(self):
        try:
            version = subprocess.run([self.config['cli'], '--version'], text=True,
                                     capture_output=True, timeout=15, check=False)
        except subprocess.TimeoutExpired as error:
            raise EnrollmentError('Installed oxi did not return its version within the probe deadline') from error
        if version.returncode or version.stdout.strip() != self.config['cli_version']:
            raise EnrollmentError('Installed oxi version differs from the reviewed CLI contract')
        server = self.api('version')['server']
        if server['version'] != self.config['cli_version'].rsplit(' v', 1)[-1] or server['api'] != 2:
            raise EnrollmentError('Running issuer version differs from the reviewed native API contract')
        session = self.api('get_session_info')
        if session['pki_realm'] != self.config['realm'] or session['role'] != 'System':
            raise EnrollmentError('Expected the issuer-local System requester in the selected realm')
        policy = self.api('config_show', {'path': 'workflow.def.certificate_signing_request_v2'})
        approval = policy['condition']['acl_can_approve']['param']
        if (approval.get('condition1') != 'global_is_operator'
                or approval.get('condition2') != '!global_is_creator'
                or policy['condition']['acl_can_approve'].get('class') != 'Workflow::Condition::LazyAND'
                or policy['action']['approve_csr'].get('class')
                   != 'OpenXPKI::Server::Workflow::Activity::Tools::Approve'
                or policy['action']['approve_csr']['param'].get('check_creator') != 1
                or policy['condition']['is_approved'].get('class')
                   != 'OpenXPKI::Server::Workflow::Condition::Approved'
                or policy['condition']['is_approved']['param'].get('role') != 'RA Operator'):
            raise EnrollmentError('The native independent RA Operator approval policy differs')
        for name in ['logging_client', 'logging_server']:
            try:
                profile = self.api('config_show', {'path': f'profile.{name}'})
            except EnrollmentError as error:
                raise EnrollmentError('Logging profiles are unavailable. Fresh bundles include logging_client and logging_server; '
                                      'an existing issuer requires a qualified configuration upgrade, not routine reconciliation.') from error
            extensions = profile['extensions']
            expected = 'client_auth' if name == 'logging_client' else 'server_auth'
            if (extensions.get('basic_constraints') != {'critical': 1, 'ca': 0}
                    or extensions.get('key_usage') != {'critical': 1, 'digital_signature': 1}
                    or extensions.get('extended_key_usage') != {'critical': 0, expected: 1}
                    or profile.get('key', {}).get('generate') != 'client'
                    or profile.get('validity', {}).get('notafter') != '+000030'):
                raise EnrollmentError('Install the reviewed leaf-only logging profiles in the issuer bundle')

    def locked_workflow(self, lock, receipt_id=None):
        entry = self.api('get_data_pool_entry', {'namespace': 'workflow.lock', 'key': lock,
                                               'decrypt': 0})
        if entry:
            workflow_id = int(entry['value'])
            if receipt_id and workflow_id != receipt_id:
                raise EnrollmentError('Native workflow lock differs from the retained workflow ID')
            return workflow_id
        if receipt_id:
            raise EnrollmentError('Retained native workflow lock is missing; recover issuer state')
        # In this native workflow the first action only selects optional context fields.
        # With no fields it stops at SETUP_REQUEST_TYPE, which offers csr_select_profile.
        # This uses the native lock without the CLI's defective nested --payload path.
        self.api('create_workflow_instance', {'workflow': 'certificate_signing_request_v2',
                 'use_lock': lock})
        self.changed = True
        entry = self.api('get_data_pool_entry', {'namespace': 'workflow.lock', 'key': lock,
                                               'decrypt': 0})
        if not entry:
            raise EnrollmentError('Created workflow has no durable native lock')
        return int(entry['value'])

    def show(self, workflow_id):
        response = self.call(['workflow', 'show'], ['--id', str(workflow_id), '--deserialize'])
        workflow = response['workflow']
        if (int(workflow['id']) != workflow_id
                or workflow['type'] != 'certificate_signing_request_v2'):
            raise EnrollmentError('Native workflow identity differs from the accepted request')
        return workflow

    def execute(self, workflow_id, action, params=None):
        available = self.api('get_workflow_activities', {'id': workflow_id})
        if action not in available:
            raise EnrollmentError(f'Native workflow does not offer the expected {action} activity')
        self.call(['workflow', 'execute'], ['--id', str(workflow_id), '--action', action], params)
        self.changed = True
