"""Credential boundary for one platform-approved application promotion policy.

Fiat/Orca are read independently of mutable Job arguments. HMAC tickets bind the
preview to its execution; Git's existing compare-and-swap provides replay control.
Only this service mounts Git, signing and ticket credentials.
"""

import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPSHandler, HTTPRedirectHandler

from promotion_git import PromotionError, Repository, canonical, require, validate_policy
from promotion_flux import KubernetesReader, wait_for_release


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        raise PromotionError('Authority credentials must not follow HTTP redirects')


def json_request(url, *, ca=None, headers=None, body=None, timeout=30):
    context = ssl.create_default_context(cafile=ca)
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context), NoRedirect())
    request = Request(url, headers=dict(headers or {}, **{'Content-Type': 'application/json'}),
                      data=json.dumps(body).encode() if body is not None else None)
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def approval_instructions(ticket):
    plan = ticket['plan']
    return ('Approve this exact application operation.\n' + canonical({key: plan[key] for key in
            ('candidate', 'base', 'config_revision', 'image_digest', 'release_id', 'mode',
             'compatibility_reference', 'policy_sha256')}) + '\n' + plan['diff'] +
            '\nExecution: ' + ticket['execution_id'] + '\nPreview expires: ' + str(ticket['expires']))


class Authority:
    def __init__(self, policy, key, execution_reader, permission_reader, repository_factory,
                 signing_key, observer=None, clock=time.time):
        validate_policy(policy)
        require(len(key) >= 32, 'Retain an independent ticket key of at least 32 bytes')
        self.policy, self.key = policy, key
        self.execution_reader, self.permission_reader = execution_reader, permission_reader
        self.repository_factory, self.signing_key = repository_factory, signing_key
        self.observer = observer or (lambda repository, plan: wait_for_release(
            KubernetesReader(), repository, policy, plan, timeout=policy.get('timeout_seconds', 900)))
        self.clock = clock

    def execution(self, identifier, mode):
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', identifier) is not None, 'Invalid execution identity')
        value = self.execution_reader(identifier)
        require(value.get('id') == identifier and value.get('application') == self.policy['application'] and
                value.get('pipelineConfigId') == self.policy['pipeline_ids'][mode],
                'Execution is outside the selected saved pipeline/application')
        require(value.get('status') in ('RUNNING', 'PAUSED'), 'Execution is not active')
        return value

    def encode(self, payload):
        data = canonical(payload).encode()
        return base64.urlsafe_b64encode(data).decode() + '.' + hmac.new(self.key, data, hashlib.sha256).hexdigest()

    def decode(self, token):
        require(isinstance(token, str) and len(token) <= 350000, 'Invalid approval ticket')
        encoded, signature = token.rsplit('.', 1)
        data = base64.b64decode(encoded, altchars=b'-_', validate=True)
        require(hmac.compare_digest(hmac.new(self.key, data, hashlib.sha256).hexdigest(), signature),
                'Approval ticket was changed or signed by a retired authority')
        value = json.loads(data)
        require(value['issued'] <= self.clock() <= value['expires'], 'Approval ticket has expired')
        require(value['plan']['policy_sha256'] == hashlib.sha256(canonical(self.policy).encode()).hexdigest(),
                'Promotion policy changed; obtain a new preview and judgment')
        return value

    def preview(self, request):
        require(set(request) == {'execution_id', 'config_revision', 'image_digest', 'release_id',
                                 'mode', 'compatibility_reference'}, 'Unexpected preview parameters')
        self.execution(request['execution_id'], request['mode'])
        with self.repository_factory() as repository:
            operation = {key: value for key, value in request.items() if key != 'execution_id'}
            operation['base'] = repository.head(self.policy['branch'])
            plan = repository.candidate(self.policy, operation, self.signing_key)
        issued = int(self.clock())
        ticket = {'execution_id': request['execution_id'], 'plan': plan, 'issued': issued,
                  'expires': issued + int(self.policy.get('ticket_ttl_seconds', 86400))}
        return dict(plan, approval_ticket=self.encode(ticket), approval_instructions=approval_instructions(ticket),
                    result='awaiting-judgment')

    def execute(self, request):
        require(set(request) == {'execution_id', 'approval_ticket'}, 'Unexpected execution parameters')
        ticket = self.decode(request['approval_ticket'])
        require(request['execution_id'] == ticket['execution_id'], 'Approval belongs to another execution')
        plan = ticket['plan']
        execution = self.execution(ticket['execution_id'], plan['mode'])
        judgments = [stage for stage in execution.get('stages', []) if stage.get('refId') == 'approval']
        require(len(judgments) == 1, 'Expected one approval stage')
        judgment = judgments[0]
        context = judgment.get('context', {})
        actor = judgment.get('lastModified', {}).get('user', '')
        # lastModified is set by Orca from authenticated Gate context, not a context-supplied username.
        require(judgment.get('type') == 'manualJudgment' and judgment.get('status') == 'SUCCEEDED' and
                context.get('judgmentStatus') == 'continue' and actor and
                judgment.get('lastModified', {}).get('lastModifiedTime', 0) >= ticket['issued'] * 1000,
                'The exact operation has no completed authenticated judgment')
        permission = self.permission_reader(actor)
        roles = {role['name'] for role in permission.get('roles', [])}
        require(permission.get('name') == actor and
                (self.policy['approver_role'] in roles or permission.get('admin') is True),
                'Actual judgment actor lacks the required Fiat approval role')
        require(context.get('approvalTicket') == request['approval_ticket'] and
                context.get('instructions') == approval_instructions(ticket),
                'Judgment payload differs from the authenticated preview')
        with self.repository_factory() as repository:
            operation = {key: plan[key] for key in ('base', 'config_revision', 'image_digest', 'release_id',
                                                    'mode', 'compatibility_reference')}
            rebuilt = repository.candidate(self.policy, operation, self.signing_key)
            require(canonical(rebuilt) == canonical(plan), 'Preview reconstruction changed')
            result = repository.publish(self.policy, plan)
            self.observer(repository, plan)
        print(json.dumps({'event': 'delivery.promotion', 'execution': ticket['execution_id'], 'actor': actor,
                          'candidate': plan['candidate'], 'result': result}), flush=True)
        return {'candidate': plan['candidate'], 'release_id': plan['release_id'], 'git_result': result,
                'result': 'reconciled'}


def verify_client(token, policy):
    service = os.environ['KUBERNETES_SERVICE_HOST']
    port = os.environ.get('KUBERNETES_SERVICE_PORT_HTTPS', '443')
    credentials = Path('/var/run/secrets/kubernetes.io/serviceaccount')
    result = json_request('https://' + service + ':' + port + '/apis/authentication.k8s.io/v1/tokenreviews',
        ca=str(credentials/'ca.crt'), headers={'Authorization': 'Bearer ' + (credentials/'token').read_text().strip()},
        body={'apiVersion': 'authentication.k8s.io/v1', 'kind': 'TokenReview', 'spec': {
            'token': token, 'audiences': ['delivery-promotion-authority']}}).get('status', {})
    require(result.get('authenticated') is True and
            'delivery-promotion-authority' in result.get('audiences', []) and
            result.get('user', {}).get('username') == 'system:serviceaccount:delivery-promotion:delivery-promoter',
            'Promotion client identity was not accepted')


def serve(policy, secrets='/authority', signing_key='/signing/key'):
    from contextlib import contextmanager
    private = Path(secrets)
    gate_headers = json.loads((private/'gate-headers.json').read_text())
    require(urlsplit(policy['gate_url']).scheme == 'https', 'Gate requires verified HTTPS')
    require(urlsplit(policy['fiat_url']).scheme == 'https', 'Fiat requires verified HTTPS')

    @contextmanager
    def repository():
        with tempfile.TemporaryDirectory(prefix='promotion-authority-') as directory:
            yield Repository(directory, policy['repository'])

    authority = Authority(policy, (private/'ticket-key').read_bytes(),
        lambda identifier: json_request(policy['gate_url'].rstrip('/') + '/pipelines/' + quote(identifier, safe=''),
                                       ca=str(private/'gate-ca.pem'), headers=gate_headers),
        lambda actor: json_request(policy['fiat_url'].rstrip('/') + '/authorize/' + quote(actor, safe=''),
                                  ca=str(private/'fiat-ca.pem')),
        repository, signing_key)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == '/healthz' else 404)
            self.end_headers()

        def do_POST(self):
            try:
                require(self.path in ('/preview', '/execute'), 'Unknown promotion operation')
                authorization = self.headers.get('Authorization', '')
                require(authorization.startswith('Bearer '), 'A projected client token is required')
                verify_client(authorization[7:], policy)
                length = int(self.headers.get('Content-Length', 0))
                require(0 < length <= 400000, 'Request exceeds the bounded promotion payload')
                result = getattr(authority, self.path[1:])(json.loads(self.rfile.read(length)))
                self.send_response(200)
            except Exception:
                # Request bodies, Git errors, cookies and ticket keys never enter HTTP or Job logs.
                result = {'result': 'denied', 'reason': 'Promotion authorization or execution check failed'}
                self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        def log_message(self, *arguments):
            pass

    server = ThreadingHTTPServer(('0.0.0.0', 8443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(private/'tls.crt'), str(private/'tls.key'))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
