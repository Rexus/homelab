"""Shamir native API state transitions, media-only restic and target-bound retries.

No production Kubernetes, Vault or storage service is accessed. The Raft API is a
behavioral double. Native local restic encryption and verification are real when
CONTROL_BACKUP_RESTIC is supplied. The Ansible fixture uses real kubernetes.core
modules against a loopback API whose Job controller completes simulated work.
"""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import jinja2
import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-1/ansible/roles/platform_recovery'
CONTROL = ROOT / 'tier-0/ansible/roles/control_backup/files'
sys.path.insert(0, str(CONTROL))
import control_backup_io as IO
import restore_files as RESTORE

spec = importlib.util.spec_from_file_location('vault_recovery', ROLE / 'files/vault_recovery.py')
VAULT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VAULT)
RESTIC = os.environ.get('CONTROL_BACKUP_RESTIC') or shutil.which('restic')
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
CLUSTER = '12345678-1234-1234-1234-123456789abc'
SECRET = {'retained': 'original-value'}


def render(template, **variables):
    environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
    environment.filters['to_json'] = json.dumps
    return yaml.safe_load(environment.from_string((ROLE / 'templates' / template).read_text()).render(**variables))


def product():
    return {'name': 'vault', 'kind': 'vault-raft', 'tier': 0, 'namespace': 'vault',
        'backup_id': 'a' * 64, 'data_claims': ['data-vault-0', 'audit-vault-0', 'data-vault-1'],
        'claim_uids': {'data-vault-0': 'new', 'audit-vault-0': 'new', 'data-vault-1': 'new'},
        'vault': {'seal': 'shamir', 'version': '1.21.0', 'image': 'hashicorp/vault@sha256:' + 'd' * 64,
            'statefulset': 'vault', 'container': 'vault', 'tls_secret': 'vault-tls',
            'cluster_id': CLUSTER, 'shamir_threshold': 2, 'snapshot_sha256': 'b' * 64,
            'members': [{'pod': 'vault-0', 'node_id': 'vault-0', 'data_claim': 'data-vault-0'},
                        {'pod': 'vault-1', 'node_id': 'vault-1', 'data_claim': 'data-vault-1'}],
            'leader_api_addr': 'https://vault-0.vault-internal:8200', 'tls_server_name': 'vault.example.internal',
            'known_secret': {'path': 'secret/data/proof', 'pointer': ['data', 'data'],
                'sha256': VAULT.checksum(json.dumps(SECRET, sort_keys=True, separators=(',', ':')).encode())}}}


def media_product():
    return {'kind': 'netbox-media', 'name': 'netbox-media', 'tier': 0, 'namespace': 'netbox',
        'backup_id': 'a' * 64, 'data_claims': ['netbox-media'], 'claim_uids': {'netbox-media': 'new'},
        'restic_image': 'independent/restic@sha256:' + 'b' * 64, 'restic_version': '0.18.1',
        'restic_secret': 'original-restic',
        'control_backup': {'set_path': '/srv/control-backup/retained-set',
            'manifest_sha256': 'c' * 64, 'vault_sha256': 'd' * 64, 'repository_id': 'e' * 64},
        'media': {'claim': 'netbox-media', 'path': '/mnt/netbox-recovery-media',
            'source_marker': 'original-source-marker', 'known_file': 'image-attachments/example.png',
            'known_file_sha256': 'f' * 64, 'run_as_user': 1000, 'run_as_group': 1000}}


class VaultAPI:
    def __init__(self):
        self.events = []
        self.states = {f'vault-{index}': dict(type='shamir', version='1.21.0', initialized=False,
            sealed=True, t=2, cluster_id='') for index in range(2)}
        self.progress = {name: set() for name in self.states}
        self.fail_after_restore = False
        self.fail_before_restore = False
        self.secret = copy.deepcopy(SECRET)
        self.extra_peer = False

    def request(self, member, method, path, body=None, token=None):
        name = member['pod']
        state = self.states[name]
        self.events.append((name, method, path))
        if path == 'sys/seal-status':
            return copy.deepcopy(state)
        if path == 'sys/init':
            if state['initialized']:
                raise RuntimeError('Already initialized')
            state.update(initialized=True, cluster_id='temporary', t=1)
            return {'keys_base64': ['temporary-share'], 'root_token': 'temporary-token'}
        if path == 'sys/unseal':
            if body.get('reset'):
                self.progress[name].clear()
                return copy.deepcopy(state)
            valid = ['temporary-share'] if state['cluster_id'] == 'temporary' else ['original-one', 'original-two']
            if body['key'] not in valid:
                raise ValueError('Wrong original key')
            self.progress[name].add(body['key'])
            if len(self.progress[name]) >= state['t']:
                state['sealed'] = False
            return copy.deepcopy(state)
        if path == 'sys/storage/raft/snapshot-force':
            if token != 'temporary-token':
                raise ValueError('Temporary restore authority required')
            if self.fail_before_restore:
                raise OSError('Submission was interrupted before native acceptance')
            state.update(cluster_id=CLUSTER, t=2, sealed=True)
            if self.fail_after_restore:
                self.fail_after_restore = False
                raise OSError('Response lost after native acceptance')
            return {}
        if path == 'sys/storage/raft/join':
            if state['initialized']:
                raise RuntimeError('Follower must not be independently initialized')
            if body['leader_api_addr'] != 'https://vault-0.vault-internal:8200':
                raise ValueError('Wrong native leader')
            state.update(initialized=True, cluster_id=CLUSTER)
            return {'joined': True}
        if token != 'original-token':
            raise ValueError('Original authorized identity required after restoration')
        if path == 'secret/data/proof':
            return {'data': {'data': self.secret}}
        if path == 'sys/storage/raft/configuration':
            names = [pod for pod, status in self.states.items() if status['initialized'] and not status['sealed']]
            if self.extra_peer:
                names.append('unaccepted-peer')
            return {'data': {'config': {'servers': [{'node_id': pod, 'voter': True} for pod in names]}}}
        raise AssertionError(path)


class ShamirNativeRecovery(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.ca = self.root / 'ca.pem'
        self.ca.write_text('retained-test-ca')
        self.config = {'product': product()}
        self.config['product']['vault']['ca_file'] = str(self.ca)
        self.api = VaultAPI()
        self.record = {'phase': 'planned'}
        self.saved = []
        self.session = {}
        self.credentials = {'unseal_keys_b64': ['original-one', 'original-two'], 'token': 'original-token'}

    def recovery(self):
        return VAULT.VaultRecovery(self.config, self.api.request,
            lambda record: self.saved.append(copy.deepcopy(record)), self.record,
            self.credentials, sleep=lambda _: None)

    def leader(self):
        self.recovery().leader(self.root / 'vault.snap', self.session or None, self.session.update)

    def test_native_single_leader_then_original_quorum_and_join_without_follower_init(self):
        self.leader()
        self.recovery().members()
        self.assertEqual(self.record['phase'], 'verified')
        self.assertEqual([event for event in self.api.events if event[2] == 'sys/init'], [('vault-0', 'PUT', 'sys/init')])
        self.assertIn(('vault-1', 'POST', 'sys/storage/raft/join'), self.api.events)
        self.assertEqual(self.saved[2]['phase'], 'snapshot-submitted')
        self.assertNotIn('original-token', json.dumps(self.saved))
        self.assertNotIn('original-one', json.dumps(self.saved))

    def test_lost_restore_response_resumes_original_data_without_snapshot_replay(self):
        self.api.fail_after_restore = True
        with self.assertRaises(OSError):
            self.leader()
        self.assertEqual(self.record['phase'], 'snapshot-submitted')
        self.leader()
        self.recovery().members()
        self.leader()
        self.recovery().members()
        self.assertEqual(sum(path == 'sys/storage/raft/snapshot-force' for _, _, path in self.api.events), 1)
        self.assertEqual(sum(path == 'sys/init' for _, _, path in self.api.events), 1)

    def test_uncertain_unaccepted_restore_is_preserved_and_never_overwritten(self):
        self.api.fail_before_restore = True
        with self.assertRaises(OSError):
            self.leader()
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.leader()
        self.assertEqual(sum(path == 'sys/storage/raft/snapshot-force' for _, _, path in self.api.events), 1)

    def test_initialized_unjournaled_or_lost_bootstrap_response_blocks_fresh_init(self):
        self.api.states['vault-0']['initialized'] = True
        with self.assertRaisesRegex(ValueError, 'Unjournaled'):
            self.leader()
        self.record['phase'] = 'initialization-submitted'
        with self.assertRaisesRegex(ValueError, 'private temporary'):
            self.leader()
        self.assertFalse(any(path == 'sys/init' for _, _, path in self.api.events))

    def test_wrong_seal_version_identity_threshold_content_and_membership_block_success(self):
        for change in ['seal', 'version', 'identity', 'threshold', 'content', 'peers']:
            with self.subTest(change=change):
                self.setUp()
                if change == 'seal':
                    self.api.states['vault-0']['type'] = 'transit'
                elif change == 'version':
                    self.api.states['vault-0']['version'] = '1.21.1'
                else:
                    self.leader()
                    if change == 'identity':
                        self.api.states['vault-0']['cluster_id'] = 'wrong'
                    elif change == 'threshold':
                        self.api.states['vault-0']['t'] = 1
                    elif change == 'content':
                        self.api.secret = {'retained': 'wrong backup'}
                    else:
                        self.api.extra_peer = True
                with self.assertRaises(ValueError):
                    self.recovery().members() if change not in ['seal', 'version'] else self.leader()
                self.assertNotEqual(self.record['phase'], 'verified')

    def test_unseal_shares_and_original_token_are_required_for_actual_content_proof(self):
        self.credentials['unseal_keys_b64'] = ['wrong']
        with self.assertRaises(ValueError):
            self.leader()
        self.credentials['unseal_keys_b64'] = ['original-one', 'original-two']
        self.leader()
        self.credentials['token'] = 'different-token'
        with self.assertRaisesRegex(ValueError, 'Original authorized'):
            self.recovery().members()

    @unittest.skipUnless(os.name == 'posix', 'Native private journals use Linux flock')
    def test_controller_journal_binds_target_uids_and_removes_only_temporary_credentials(self):
        (self.root / 'receipts').mkdir()
        self.config.update(workspace=str(self.root), plan_sha256='1' * 64,
                           namespace_uid='native-namespace', statefulset_uid='native-statefulset',
                           claim_uids={'data-vault-0': 'native-claim-zero', 'data-vault-1': 'native-claim-one'})
        self.config['product']['vault']['custody'] = {'directory': str(self.root)}
        with patch.object(VAULT, 'validate', return_value=self.credentials), \
                patch.object(VAULT, 'prepare_snapshot', return_value=self.root / 'vault.snap'), \
                patch.object(VAULT, 'native_request', side_effect=lambda config, *args, **kwargs: self.api.request(*args, **kwargs)):
            VAULT.execute(self.config, 'leader', IO, RESTORE)
            self.assertFalse(list(self.root.glob('*-temporary.json')))
            VAULT.execute(self.config, 'members', IO, RESTORE)
            record = json.loads((self.root / 'receipts/vault-vault.json').read_text())
            self.assertEqual(record['phase'], 'verified')
            self.assertEqual(record['claim_uids'], self.config['claim_uids'])
            for field in ['namespace_uid', 'statefulset_uid', 'claim_uids', 'plan_sha256']:
                changed = copy.deepcopy(self.config)
                changed[field] = {'data-vault-0': 'replacement'} if field == 'claim_uids' else '2' * 64
                before = len(self.api.events)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'changed on retry'):
                    VAULT.execute(changed, 'members', IO, RESTORE)
                self.assertEqual(len(self.api.events), before)


@unittest.skipUnless(os.name == 'posix', 'Linux owner-only custody checks')
class CustodyInputs(unittest.TestCase):
    def setUp(self):
        self.old_umask = os.umask(0o077)
        self.addCleanup(os.umask, self.old_umask)
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.config = {'product': product()}
        current = self.config['product']
        vault = current['vault']
        certificate = ssl.DER_cert_to_PEM_cert(ssl.create_default_context().get_ca_certs(binary_form=True)[0])
        for name, contents in [('original.json', json.dumps({'token': 'original-token', 'unseal_keys_b64': ['one', 'two']})),
                               ('ca.pem', certificate), ('password', 'restic-password')]:
            (self.root / name).write_text(contents)
        vault.update(ca_file=str(self.root / 'ca.pem'), ca_sha256=IO.digest(self.root / 'ca.pem'),
                     custody={'mode': 'ephemeral-file', 'directory': str(self.root),
                              'file': str(self.root / 'original.json'), 'sha256': IO.digest(self.root / 'original.json')})
        current['control_backup'] = {'password_file': str(self.root / 'password'),
            'password_sha256': IO.digest(self.root / 'password'), 'set_path': '/control-backup/exact-set'}

    def test_valid_custody_and_changed_file_permissions_symlink_git_or_checksum(self):
        VAULT.validate(self.config)
        original = self.root / 'original.json'
        original.chmod(0o644)
        with self.assertRaisesRegex(ValueError, '0600'):
            VAULT.validate(self.config)
        original.chmod(0o600)
        link = self.root / 'link.json'
        link.symlink_to(original)
        self.config['product']['vault']['custody']['file'] = str(link)
        with self.assertRaisesRegex(ValueError, 'canonical'):
            VAULT.validate(self.config)
        self.config['product']['vault']['custody']['file'] = str(original)
        original.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            VAULT.validate(self.config)
        (self.root / '.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'outside Git'):
            VAULT.validate(self.config)

    def test_physical_custody_choice_and_unsupported_seals_stop_before_any_restore(self):
        self.config['product']['vault']['custody']['mode'] = 'physical-custodians'
        with self.assertRaisesRegex(ValueError, 'before the unattended'):
            VAULT.validate(self.config)
        self.config['product']['vault']['seal'] = 'transit'
        with self.assertRaisesRegex(ValueError, 'Transit/PKCS11'):
            VAULT.validate(self.config)

    def test_preflight_needs_only_product_and_rejects_unsafe_https_or_identity(self):
        VAULT.validate({'product': self.config['product']})
        for field, invalid in [('leader_api_addr', 'http://vault-0:8200'),
                               ('leader_api_addr', 'https://user:password@vault-0:8200'),
                               ('leader_api_addr', 'https://vault-0:8200/?redirect=other'),
                               ('tls_server_name', 'vault.*.internal'),
                               ('tls_server_name', 'vault\n.example.internal'),
                               ('cluster_id', '.*')]:
            with self.subTest(field=field, invalid=invalid):
                changed = copy.deepcopy(self.config)
                changed['product']['vault'][field] = invalid
                with self.assertRaises(ValueError):
                    VAULT.validate(changed)

    def test_original_custody_cannot_be_reused_by_general_verification_headers(self):
        self.config['product']['checks'] = [{'url': 'https://vault.example.internal/v1/sys/seal-status', 'authenticated': True}]
        with self.assertRaisesRegex(ValueError, 'stay in the controller helper'):
            VAULT.validate(self.config)
        self.config['product']['checks'][0]['authenticated'] = False
        VAULT.validate(self.config)

    def test_public_ca_can_use_normal_readable_permissions_while_custody_stays_private(self):
        (self.root / 'ca.pem').chmod(0o644)
        VAULT.validate(self.config)
        (self.root / 'password').chmod(0o644)
        with self.assertRaisesRegex(ValueError, '0600'):
            VAULT.validate(self.config)


class RenderedControlJobs(unittest.TestCase):
    def variables(self):
        return {'platform_recovery': {'recovery_id': 'accepted', 'plan_sha256': '1' * 64},
            'recovery_product': product(), 'recovery_control_guard_name': 'vault-one-claim',
            'recovery_control_claim': 'data-vault-0', 'recovery_control_claim_uids': {'data-vault-0': 'actual-uid'},
            'recovery_control_claim_observed': {'resources': [{'metadata': {'uid': 'actual-uid'}}]}}

    def test_guard_uses_one_rwo_claim_and_no_custody_credentials_reach_jobs(self):
        variables = self.variables()
        guard = render('vault-claim-guard.yml.j2', **variables)
        proof = render('vault-verified.yml.j2', **variables)
        self.assertEqual(guard['spec']['template']['spec']['volumes'], [
            {'name': 'data', 'persistentVolumeClaim': {'claimName': 'data-vault-0'}}])
        for job in [guard, proof]:
            pod = job['spec']['template']['spec']
            self.assertFalse(pod['automountServiceAccountToken'])
            self.assertEqual(job['spec']['backoffLimit'], 0)
            self.assertTrue(pod['securityContext']['runAsNonRoot'])
            self.assertNotIn('custody', json.dumps(job))
            self.assertNotIn('VAULT_TOKEN', json.dumps(job))
            self.assertFalse(pod['containers'][0]['securityContext']['allowPrivilegeEscalation'])

    def test_media_native_selection_excludes_sql_and_other_claims(self):
        variables = self.variables()
        variables.update(recovery_product=media_product(), recovery_control_claim_uids={'netbox-media': 'actual-media-uid'})
        job = render('netbox-media-restore.yml.j2', **variables)
        pod = job['spec']['template']['spec']
        self.assertEqual([volume['persistentVolumeClaim']['claimName'] for volume in pod['volumes']
                          if 'persistentVolumeClaim' in volume], ['netbox-media'])
        script = pod['containers'][0]['args'][0]
        self.assertIn('"$SNAPSHOT:$MEDIA_PATH" --target /media --verify', script)
        self.assertIn('media_selected', script)
        self.assertIn('check --read-data', script)

    @unittest.skipUnless(os.name == 'posix', 'Native guarded filesystem inspection uses Linux sh')
    def test_vault_empty_claim_guard_rejects_existing_data_and_failed_inspection(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        target = root / 'data'
        target.mkdir()
        job = render('vault-claim-guard.yml.j2', **self.variables())
        script = job['spec']['template']['spec']['containers'][0]['args'][0].replace('/data', str(target))
        command = ['sh', '-ec', script]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        (target / 'retained-raft-data').write_bytes(b'must survive')
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual((target / 'retained-raft-data').read_bytes(), b'must survive')
        tools = root / 'tools'
        tools.mkdir()
        (tools / 'find').write_text('#!/bin/sh\nexit 1\n')
        (tools / 'find').chmod(0o700)
        result = subprocess.run(command, env=dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH']),
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(os.name == 'posix', 'Linux native Git and independent custody fixtures')
class ReadPlanControlProducts(unittest.TestCase):
    def setUp(self):
        import test_tier_flux_recovery as fixture
        self.runner = fixture.RUNNER
        self.fixture = fixture.RecoveryInputs('test_accepts_exact_independent_sources_and_original_state')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.plan, self.root = self.fixture.plan, self.fixture.root
        self.plan['scope'] = 'all-vms'
        source = copy.deepcopy(self.plan['automation']['tier-1'])
        directory = self.root / 'tier-0'
        shutil.copytree(Path(source['directory']), directory)
        source['directory'] = str(directory)
        self.plan['automation']['tier-0'] = source
        cluster = copy.deepcopy(self.plan['clusters'][0])
        cluster.update(tier=0, kubeconfig='tier-0/secrets/talos/kubeconfig', context='tier0-recovery',
            nodes=[{'name': 'core-1', 'node': 'pve01', 'vmid': 201}],
            bootstrap_inputs='tier-0/secrets/bootstrap.yml', provider_environment='tier-0/secrets/provider.env',
            restore_resources='tier-0/secrets/resources.yml', restore_engines='tier-0/secrets/engines.yml',
            recovery_git_inputs='tier-0/secrets/recovery-git.yml',
            package=dict(copy.deepcopy(self.plan['package']), directory=str(self.root / 'tier0-package')),
            cutover={'resume_roots': ['platform'], 'health_checks': [{'kind': 'StatefulSet', 'name': 'vault'}],
                'sources': {'platform': {'url': 'ssh://git@core.test/platform', 'ref': 'refs/heads/recovery',
                    'secret_name': 'tier0-source', 'identity_file': 'tier-0/secrets/source-identity',
                    'known_hosts_file': 'tier-0/secrets/source-known-hosts', 'secret_file': 'tier-0/secrets/source.yml'}}})
        cluster['package']['sources']['platform'] = 'd' * 40
        self.plan['clusters'].insert(0, cluster)
        self.plan['template_rebuild'] = {'catalog': 'tier-0/secrets/resources.yml',
            'provider_environment': 'tier-0/secrets/provider.env', 'assets': {'talos': 'talos.raw'}}
        self.retain('tier-0', '.terraform/state/proxmox-templates/terraform.tfstate', '{"version":4,"lineage":"retained"}')
        self.retain('tier-0', 'secrets/bootstrap.yml', yaml.safe_dump({'cluster_platform_action': 'apply',
            'cluster_platform_flux_recovery': True, 'cluster_platform_flux_commit': 'd' * 40}))
        for tier in (0, 1):
            self.retain(f'tier-{tier}', 'secrets/recovery-git.yml', yaml.safe_dump({
                'flux_recovery_git_user': f'recovery-tier{tier}', 'flux_recovery_git_root': f'/srv/recovery/tier{tier}'}))
        self.custody = self.root / 'independent-custody'
        self.custody.mkdir(mode=0o700)
        certificate = ssl.DER_cert_to_PEM_cert(ssl.create_default_context().get_ca_certs(binary_form=True)[0])
        for name, content in [('original.json', json.dumps({'token': 'original-token', 'unseal_keys_b64': ['one', 'two']})),
                              ('ca.pem', certificate), ('password', 'independent-restic-password')]:
            path = self.custody / name
            path.write_text(content)
            path.chmod(0o600)
        current = product()
        current['vault'].update(ca_file=str(self.custody / 'ca.pem'), ca_sha256=IO.digest(self.custody / 'ca.pem'),
            custody={'mode': 'ephemeral-file', 'directory': str(self.custody), 'file': str(self.custody / 'original.json'),
                     'sha256': IO.digest(self.custody / 'original.json')})
        current['control_backup'] = {'repository': '/mnt/control-recovery', 'repository_id': 'e' * 64,
            'password_file': str(self.custody / 'password'), 'password_sha256': IO.digest(self.custody / 'password'),
            'restic_binary': '/usr/bin/restic', 'restic_version': '0.18.1', 'vault_binary': '/usr/bin/vault',
            'set_path': '/var/lib/control-backup/accepted-set', 'manifest_sha256': 'f' * 64}
        for selected in [current, media_product()]:
            selected.update(namespace_uid='new', python_image='retained/python@sha256:' + 'e' * 64,
                verification_ca_secret='recovery-ca', verification_headers_secret='empty-status-headers',
                writers=[{'kind': 'StatefulSet', 'name': 'vault'}] if selected['kind'] == 'vault-raft' else
                    [{'kind': 'Deployment', 'name': 'netbox'}, {'kind': 'Deployment', 'name': 'netbox-worker'}],
                checks=[{'url': 'https://control.test/status', 'status': 200, 'content_sha256': 'f' * 64},
                        {'url': 'https://control.test/denied', 'status': 403}])
            self.plan['products'].append(selected)

    def retain(self, owner, relative, content):
        repository = self.plan['automation'][owner]
        target = Path(repository['directory']) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        repository['private_files'] = [item for item in repository['private_files'] if item['path'] != relative]
        repository['private_files'].append({'path': relative, 'sha256': self.runner.checksum(target)})

    def read(self, **kwargs):
        path, digest = self.fixture.accepted()
        return self.runner.read_plan(path, digest, **kwargs)

    def test_read_plan_accepts_default_control_kinds_and_rejects_missing_required_inputs(self):
        self.assertEqual({item['kind'] for item in self.read()['products']}, {'harbor', 'vault-raft', 'netbox-media'})
        for kind, field in [('vault-raft', 'vault'), ('vault-raft', 'control_backup'),
                            ('vault-raft', 'data_claims'), ('netbox-media', 'media'),
                            ('netbox-media', 'restic_version'), ('netbox-media', 'claim_uids')]:
            current = next(item for item in self.plan['products'] if item['kind'] == kind)
            saved = current.pop(field)
            with self.subTest(kind=kind, field=field), self.assertRaises(ValueError):
                self.read()
            current[field] = saved

    def test_read_plan_rejects_bad_custody_before_any_target_while_completed_audit_omits_shares(self):
        original = self.custody / 'original.json'
        before = original.read_bytes()
        original.write_text('{"token":"changed","unseal_keys_b64":[]}')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.read()
        original.write_bytes(before)
        original.chmod(0o644)
        with self.assertRaisesRegex(ValueError, '0600'):
            self.read()
        original.unlink()
        self.assertEqual(self.read(verify_custody=False)['scope'], 'all-vms')
        with self.assertRaises(FileNotFoundError):
            self.read()

    def test_media_runtime_identity_and_scope_fail_before_target_mutation(self):
        current = next(item for item in self.plan['products'] if item['kind'] == 'netbox-media')
        for field in ('run_as_user', 'run_as_group'):
            original = current['media'][field]
            for value in (True, 0, -1, 1000.5, '1000'):
                current['media'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.read()
            current['media'][field] = original
        for field, value in [('known_file', '.control-backup-source'),
                             ('known_file', '.platform-recovery-media'), ('path', '/unsafe path')]:
            original = current['media'][field]
            current['media'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.read()
            current['media'][field] = original
        current['repository_claim'] = current['media']['claim']
        with self.assertRaises(ValueError):
            self.read()


@unittest.skipUnless(RESTIC and os.name == 'posix', 'Requires local native restic and Linux')
class NativeControlFiles(unittest.TestCase):
    def setUp(self):
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        (self.tools / 'restic').symlink_to(Path(RESTIC).resolve())
        self.password = self.root / 'password'
        self.password.write_text('isolated-test-only-password')
        self.env = dict(os.environ, RESTIC_REPOSITORY=str(self.root / 'repository'),
            RESTIC_PASSWORD_FILE=str(self.password), PATH=str(self.tools) + os.pathsep + os.environ['PATH'])
        self.native('init')
        self.repository_id = json.loads(self.native('cat', 'config'))['id']
        self.media = self.root / 'original-media'
        (self.media / 'image-attachments').mkdir(parents=True)
        (self.media / '.control-backup-source').write_text('original-source-marker\n')
        (self.media / 'image-attachments/example.png').write_bytes(b'original retained media bytes')
        self.backup = self.root / 'original-set'
        self.backup.mkdir()
        (self.backup / 'vault.snap').write_bytes(b'native snapshot format represented by API double')
        self.manifest = {'schema': 1, 'vault_sha256': IO.digest(self.backup / 'vault.snap'), 'media_selected': True}
        IO.atomic_json(self.backup / 'manifest.json', self.manifest)
        self.snapshot = self.save_backup()
        self.restic_version = self.native('version').decode().split()[1]

    def native(self, *arguments):
        result = subprocess.run([str(self.tools / 'restic'), *arguments], env=self.env,
            capture_output=True, timeout=120)
        if result.returncode:
            self.fail(result.stderr.decode())
        return result.stdout

    def save_backup(self):
        lines = self.native('backup', '--json', str(self.media), str(self.backup)).splitlines()
        return next(json.loads(line)['snapshot_id'] for line in lines if json.loads(line).get('message_type') == 'summary')

    def media_job(self):
        current = media_product()
        current.update(backup_id=self.snapshot, restic_version=self.restic_version)
        current['control_backup'].update(set_path=str(self.backup), repository_id=self.repository_id,
            manifest_sha256=IO.digest(self.backup / 'manifest.json'), vault_sha256=self.manifest['vault_sha256'])
        current['media'].update(path=str(self.media), known_file_sha256=IO.digest(self.media / 'image-attachments/example.png'))
        variables = {'recovery_product': current, 'platform_recovery': {'recovery_id': 'accepted', 'plan_sha256': '1' * 64},
                     'recovery_control_claim_uids': {'netbox-media': 'exact-native-uid'}}
        return render('netbox-media-restore.yml.j2', **variables)

    def run_media(self, job, target):
        proof = self.root / 'proof'
        proof.mkdir(exist_ok=True)
        script = job['spec']['template']['spec']['containers'][0]['args'][0]
        script = script.replace('/media', str(target)).replace('/proof', str(proof))
        environment = dict(self.env)
        for variable in job['spec']['template']['spec']['containers'][0]['env']:
            environment[variable['name']] = variable['value']
        environment['RESTIC_CACHE_DIR'] = str(self.root / 'cache')
        return subprocess.run(['sh', '-ec', script], env=environment, capture_output=True, timeout=180)

    def test_real_restic_media_only_restore_verifies_content_and_rejects_target_reuse(self):
        target = self.root / 'new-media'
        target.mkdir()
        job = self.media_job()
        result = self.run_media(job, target)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / 'image-attachments/example.png').read_bytes(), b'original retained media bytes')
        self.assertFalse((target / 'vault.snap').exists())
        self.assertFalse((target / 'manifest.json').exists())
        second = self.run_media(job, target)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual((target / 'image-attachments/example.png').read_bytes(), b'original retained media bytes')

    def test_wrong_manifest_missing_media_marker_and_known_content_block_native_restore(self):
        for change in ['manifest', 'marker', 'content', 'selection']:
            with self.subTest(change=change):
                job = self.media_job()
                values = job['spec']['template']['spec']['containers'][0]['env']
                field = {'manifest': 'MANIFEST_SHA256', 'marker': 'SOURCE_MARKER', 'content': 'KNOWN_FILE_SHA256'}
                if change == 'selection':
                    self.manifest['media_selected'] = False
                    IO.atomic_json(self.backup / 'manifest.json', self.manifest)
                    self.snapshot = self.save_backup()
                    job = self.media_job()
                else:
                    for value in values:
                        if value['name'] == field[change]:
                            value['value'] = '0' * 64
                target = self.root / ('wrong-' + change)
                target.mkdir()
                result = self.run_media(job, target)
                self.assertNotEqual(result.returncode, 0)
                if change != 'content':
                    self.assertEqual(list(target.iterdir()), [])

    def test_native_control_backup_subset_and_original_tools_before_vault_mutation(self):
        vault_cli = self.tools / 'vault'
        vault_cli.write_text('#!/bin/sh\nif [ "$1" = version ]; then printf \'{"version":"1.21.0"}\';\n'
                             'else test "$1 $2 $3" = "operator raft snapshot"; fi\n')
        vault_cli.chmod(0o700)
        (self.root / 'receipts').mkdir()
        current = product()
        current['backup_id'] = self.snapshot
        current['vault']['snapshot_sha256'] = self.manifest['vault_sha256']
        current['control_backup'] = {'repository': self.env['RESTIC_REPOSITORY'], 'repository_id': self.repository_id,
            'password_file': str(self.password), 'directory': str(self.root),
            'restic_binary': str(self.tools / 'restic'), 'restic_version': self.restic_version,
            'vault_binary': str(vault_cli), 'set_path': str(self.backup),
            'manifest_sha256': IO.digest(self.backup / 'manifest.json')}
        config = {'workspace': str(self.root), 'product': current}
        restored = VAULT.prepare_snapshot(config, IO, RESTORE)
        self.assertEqual(restored.read_bytes(), (self.backup / 'vault.snap').read_bytes())
        self.assertEqual(sorted(item.name for item in restored.parent.iterdir()), ['manifest.json', 'vault.snap'])
        self.assertEqual(VAULT.prepare_snapshot(config, IO, RESTORE), restored)
        current['vault']['version'] = '1.21.1'
        with self.assertRaisesRegex(ValueError, 'exact original'):
            VAULT.prepare_snapshot(config, IO, RESTORE)
        current['vault']['version'] = '1.21.0'
        restored.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'snapshot does not match'):
            VAULT.prepare_snapshot(config, IO, RESTORE)


@unittest.skipUnless(ANSIBLE and os.name == 'posix', 'Requires native Ansible and kubernetes.core')
class NativeControlJobJournal(unittest.TestCase):
    def setUp(self):
        from backup_storage_api_support import BackupStorageAPI

        class ControlAPI(BackupStorageAPI):
            resources = dict(BackupStorageAPI.resources,
                jobs=('Job', True, 'batch/v1'), pods=('Pod', True, 'v1'))

            def put(self, value):
                if value['kind'] == 'Job':
                    value['status'] = {'succeeded': 1, 'conditions': [{'type': 'Complete', 'status': 'True'}]}
                super().put(value)

        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.api = ControlAPI()
        self.addCleanup(self.api.close)
        self.kubeconfig = self.root / 'kubeconfig'
        self.kubeconfig.write_text(yaml.safe_dump(self.api.kubeconfig()))
        (self.root / 'receipts').mkdir()
        self.current = media_product()
        self.namespace_uid = 'original-new-namespace'
        self.api.put({'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim', 'metadata': {
            'namespace': 'netbox', 'name': 'netbox-media', 'uid': 'original-new-media-claim',
            'annotations': {'recovery.homelab/plan-sha256': '1' * 64}}, 'spec': {'volumeName': 'media-pv'}})

    def play(self, success=True):
        variables = {'ansible_python_interpreter': sys.executable,
            'recovery_kubeconfig': str(self.kubeconfig), 'recovery_context': 'offline',
            'recovery_product': self.current, 'recovery_namespace': {'resources': [{'metadata': {'uid': self.namespace_uid}}]},
            'platform_recovery': {'workspace': str(self.root), 'recovery_id': 'accepted', 'plan_sha256': '1' * 64}}
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': [{'ansible.builtin.include_role': {
                'name': 'platform_recovery', 'tasks_from': 'netbox-media'}}]}]))
        env = dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent),
                   ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)], env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_native_adapter_reobserves_job_and_refuses_replaced_claim_or_job_uid(self):
        self.play()
        creates = lambda: sum(method == 'POST' and '/jobs' in path for method, path, *_ in self.api.mutations)
        self.assertEqual(creates(), 1)
        job = next(value for (kind, _, _), value in self.api.objects.items() if kind == 'jobs')
        journal = next((self.root / 'receipts').glob('job-*.json'))
        self.assertEqual(json.loads(journal.read_text())['uid'], job['metadata']['uid'])
        self.play()
        self.assertEqual(creates(), 1)
        claim = self.api.objects['persistentvolumeclaims', 'netbox', 'netbox-media']
        original_uid = claim['metadata']['uid']
        claim['metadata']['uid'] = 'different-pvc-with-same-name'
        self.play(success=False)
        self.assertEqual(creates(), 1)
        claim['metadata']['uid'] = original_uid
        job['metadata']['uid'] = 'different-job-with-same-name'
        self.play(success=False)
        self.assertEqual(creates(), 1)

    def test_changed_restore_scope_and_failed_job_cannot_replay_on_partial_data(self):
        self.play()
        job = next(value for (kind, _, _), value in self.api.objects.items() if kind == 'jobs')
        self.current['media']['path'] = '/different-approved-path'
        self.play(success=False)
        self.current['media']['path'] = '/mnt/netbox-recovery-media'
        job['status'] = {'failed': 1}
        self.play(success=False)
        self.assertEqual(sum(method == 'POST' and '/jobs' in path for method, path, *_ in self.api.mutations), 1)

    def test_retained_claim_receipt_is_required_before_accepting_an_existing_job(self):
        self.play()
        (self.root / 'receipts/netbox-media-netbox-media-claim.json').unlink()
        self.play(success=False)
        self.assertEqual(sum(method == 'POST' and '/jobs' in path for method, path, *_ in self.api.mutations), 1)


@unittest.skipUnless(ANSIBLE and os.name == 'posix' and shutil.which('openssl'), 'Requires native Ansible, Kubernetes modules and OpenSSL')
class NativeCompletedProductAudit(unittest.TestCase):
    def setUp(self):
        from test_tier_platform_recovery_flow import RecoveryAPI
        from backup_storage_api_support import BackupStorageAPI

        class AuditAPI(RecoveryAPI):
            resources = dict(RecoveryAPI.resources, **{
                'restores': ('Restore', True, 'velero.io/v1'),
                'backups': ('Backup', True, 'velero.io/v1'),
                'clusters': ('Cluster', True, 'postgresql.cnpg.io/v1')})

        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='completed-product-audit-'))).resolve()
        self.roles = self.root / 'roles'
        fixture_role = self.roles / 'platform_recovery'
        shutil.copytree(ROLE, fixture_role, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        # GitLab's API fencing helper has separate behavioral qualification. Keep
        # its real Ansible caller and every Kubernetes GET/UID gate in this fixture.
        (fixture_role / 'files/gitlab_recovery_fence.py').write_text('''import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--operation', required=True, choices=['verify'])
arguments = parser.parse_args()
config = json.loads(Path(arguments.config).read_text())
root = Path(config['workspace'])
product = config['product']
namespace = json.loads((root / 'receipts' / (product['name'] + '-namespace.json')).read_text())
assert product['kind'] == 'gitlab'
assert config['namespace_uid'] == namespace['uid']
assert config['plan_sha256'] == namespace['plan_sha256']
with (root / 'gitlab-helper-calls.jsonl').open('a') as stream:
    stream.write(json.dumps({'operation': arguments.operation, 'product': product['name'],
        'namespace_uid': config['namespace_uid'], 'plan_sha256': config['plan_sha256']}) + '\\n')
print(json.dumps({'changed': False}))
''')
        self.api = AuditAPI(self.root)
        self.addCleanup(self.api.close)
        self.health = BackupStorageAPI()
        self.addCleanup(self.health.close)
        self.health.server.RequestHandlerClass = self.api.server.RequestHandlerClass
        self.certificate, key = self.root / 'ca.pem', self.root / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
            '-keyout', str(key), '-out', str(self.certificate)], check=True, capture_output=True)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.certificate, key)
        self.health.server.socket = tls.wrap_socket(self.health.server.socket, server_side=True)
        self.url = f'https://127.0.0.1:{self.health.server.server_port}'
        self.kubeconfig = self.root / 'kubeconfig'
        self.kubeconfig.write_text(yaml.safe_dump(self.api.kubeconfig()))
        (self.root / 'receipts').mkdir()
        self.plan = {'workspace': str(self.root), 'plan_sha256': '1' * 64, 'recovery_id': 'accepted', 'phase': 'verify',
            'clusters': [{'tier': tier, 'kubeconfig': 'kubeconfig', 'context': 'offline'} for tier in (0, 1)]}

    def save(self, name, value):
        (self.root / 'receipts' / name).write_text(json.dumps(value))

    def prepare(self, kind):
        current = {'kind': kind, 'name': kind, 'namespace': kind, 'namespace_uid': 'new',
                   'tier': 0 if kind in ['vault-raft', 'netbox-media', 'cnpg-files'] else 1, 'backup_id': 'retained-native-backup'}
        claims = []
        if kind == 'spinnaker':
            current.update(mysql={'claim': 'sql-data'}, redis={'claim': 'redis-data'})
            claims = ['sql-data', 'redis-data']
        elif kind == 'victoriametrics':
            current['claim'] = 'metrics-data'
            claims = ['metrics-data']
        elif kind not in ['cnpg-files', 'gitlab']:
            current['data_claims'] = ['native-data']
            claims = ['native-data']
        self.current = current
        self.claims = {name: 'actual-' + kind + '-' + name for name in claims}
        namespace = {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': kind, 'uid': 'actual-ns-' + kind,
            'annotations': {'recovery.homelab/plan-sha256': self.plan['plan_sha256']}}}
        self.api.put(namespace)
        self.namespace = copy.deepcopy(namespace)
        self.save(kind + '-namespace.json', {'plan_sha256': self.plan['plan_sha256'], 'uid': namespace['metadata']['uid']})
        for name, uid in self.claims.items():
            self.api.put({'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
                'metadata': {'name': name, 'namespace': kind, 'uid': uid}, 'spec': {}, 'status': {'phase': 'Bound'}})
        operation = {'kind': 'Job', 'namespace': kind, 'name': 'restore-' + kind, 'uid': 'actual-op-' + kind}
        api_version = 'batch/v1'
        native = {'apiVersion': api_version, 'kind': 'Job', 'metadata': {
            'name': operation['name'], 'namespace': kind, 'uid': operation['uid'],
            'annotations': {'recovery.homelab/plan-sha256': self.plan['plan_sha256']}},
            'spec': {'template': {'spec': {'containers': [{'name': 'restore', 'env': [
                {'name': 'RECOVERY_PVC_UID', 'value': next(iter(self.claims.values()), '')}]}]}}}}
        if kind in ['harbor', 'argocd', 'netdata']:
            operation.update(kind='Restore', name=kind + '-accepted', namespace='velero', backup_uid='actual-backup-' + kind)
            api_version = 'velero.io/v1'
            backup = {'apiVersion': api_version, 'kind': 'Backup',
                'metadata': {'name': current['backup_id'], 'namespace': 'velero', 'uid': operation['backup_uid']},
                'spec': {'includedNamespaces': [kind]}, 'status': {'phase': 'Completed', 'errors': 0}}
            current['backup_spec_sha256'] = VAULT.checksum(json.dumps(backup['spec'], sort_keys=True).encode())
            self.api.put(backup)
            native = {'apiVersion': api_version, 'kind': 'Restore', 'metadata': {
                'name': operation['name'], 'namespace': 'velero', 'uid': operation['uid'],
                'annotations': {'recovery.homelab/plan-sha256': self.plan['plan_sha256']}},
                'spec': {'backupName': current['backup_id']}, 'status': {'phase': 'Completed', 'errors': 0}}
            self.save(kind + '-velero.json', {'plan_sha256': self.plan['plan_sha256'], 'claims': self.claims,
                'restore_uid': operation['uid'], 'backup_uid': operation['backup_uid']})
        elif kind == 'cnpg-files':
            current.update(cnpg_cluster='restored-database', system_identifier='original-system-id')
            operation.update(kind='Cluster', name=current['cnpg_cluster'], system_identifier=current['system_identifier'])
            api_version = 'postgresql.cnpg.io/v1'
            native = {'apiVersion': api_version, 'kind': 'Cluster', 'metadata': {
                'name': operation['name'], 'namespace': kind, 'uid': operation['uid']},
                'spec': {}, 'status': {'systemID': current['system_identifier'], 'readyInstances': 1}}
        elif kind == 'opensearch':
            current.update(url=self.url, repository='retained', backup_id='accepted-snapshot', backup_uid='native-snapshot-uid',
                client_cert='ca.pem', client_key='key.pem', ca_path='ca.pem', indices=['records'])
            operation = {'kind': 'OpenSearchSnapshot', 'uuid': current['backup_uid'],
                'indices': [{'index': 'records', 'uuid': self.api.search_index_uid}]}
            api_version = 'opensearch'
        if kind != 'opensearch':
            self.api.put(native)
        self.operation = operation
        self.native = native
        self.variables = {'platform_recovery': self.plan, 'recovery_product': current,
            'recovery_namespace': {'resources': [self.namespace]}, 'recovery_native_receipt': operation,
            'recovery_kubeconfig': str(self.kubeconfig), 'recovery_context': 'offline',
            'recovery_control_claim_uids': self.claims, 'recovery_velero_claim_uids': self.claims,
            'recovery_search_claim_identities': [{'name': name, 'namespace': kind, 'uid': uid} for name, uid in self.claims.items()],
            'recovery_metrics_claim': {'resources': [{'metadata': {'uid': next(iter(self.claims.values()), '')}}]}}
        for database in ['mysql', 'redis'] if kind == 'spinnaker' else []:
            self.save(kind + '-' + database + '-claim.json', {'plan_sha256': self.plan['plan_sha256'],
                'namespace_uid': namespace['metadata']['uid'], 'uid': self.claims[current[database]['claim']]})
        for name, uid in self.claims.items():
            self.save(kind + '-' + name + '-claim.json', {'plan_sha256': self.plan['plan_sha256'],
                'namespace_uid': namespace['metadata']['uid'], 'uid': uid})
        self.record = {'version': 2, 'recovery_id': self.plan['recovery_id'], 'plan_sha256': self.plan['plan_sha256'],
            'backup_id': current['backup_id'], 'namespace': kind, 'namespace_uid': namespace['metadata']['uid'],
            'product': kind, 'kind': kind, 'tier': current['tier'], 'claims': self.claims,
            'restore': dict(operation, api_version=api_version)}
        self.save(kind + '-restore.json', self.record)
        if kind == 'gitlab':
            # A completed recovery already retained this private command input.
            # The real task's copy must observe identical content during an audit.
            fence_inputs = {'workspace': str(self.root), 'plan_sha256': self.plan['plan_sha256'],
                'namespace_uid': namespace['metadata']['uid'], 'product': current}
            path = self.root / 'receipts' / (kind + '-gitlab-fence-inputs.json')
            path.write_text(json.dumps(fence_inputs, indent=4, sort_keys=True))
            path.chmod(0o600)

    def play(self, tasks, *, success=True):
        variables = dict(self.variables, ansible_python_interpreter=sys.executable)
        play = self.root / 'audit.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': tasks}]))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)],
            env=dict(os.environ, ANSIBLE_ROLES_PATH=str(self.roles), ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local')),
            capture_output=True, text=True, timeout=150)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def audit(self, success=True):
        before = {path.name: path.read_bytes() for path in (self.root / 'receipts').glob('*')}
        mutations = copy.deepcopy(self.api.mutations)
        helper_log = self.root / 'gitlab-helper-calls.jsonl'
        previous_calls = helper_log.read_text().splitlines() if helper_log.exists() else []
        self.play([{'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'verify-product-target'}}], success=success)
        self.assertEqual(self.api.mutations, mutations)
        self.assertEqual({path.name: path.read_bytes() for path in (self.root / 'receipts').glob('*')}, before)
        calls = helper_log.read_text().splitlines() if helper_log.exists() else []
        if self.current['kind'] == 'gitlab' and success:
            self.assertEqual(len(calls), len(previous_calls) + 1)
            self.assertEqual(json.loads(calls[-1]), {'operation': 'verify', 'product': self.current['name'],
                'namespace_uid': self.namespace['metadata']['uid'], 'plan_sha256': self.plan['plan_sha256']})
        else:
            self.assertEqual(calls, previous_calls)

    def record_tail(self, success=True):
        tasks = yaml.safe_load((ROLE / 'tasks/product.yml').read_text())
        start = next(index for index, task in enumerate(tasks)
                     if task['name'] == 'Select only data claims actually owned by the native product adapter')
        return self.play(tasks[start:], success=success)

    def test_record_and_readonly_audit_cover_all_native_product_kinds_with_actual_uids(self):
        for kind in ['spinnaker', 'victoriametrics', 'vault-raft', 'netbox-media', 'harbor', 'argocd', 'netdata', 'cnpg-files', 'gitlab', 'opensearch']:
            with self.subTest(kind=kind):
                self.prepare(kind)
                self.record_tail()
                recorded = json.loads((self.root / 'receipts' / (kind + '-restore.json')).read_text())
                self.assertEqual(recorded['namespace_uid'], self.namespace['metadata']['uid'])
                self.assertEqual(recorded['claims'], self.claims)
                self.audit()

    def test_readonly_audit_rejects_replaced_namespace_claim_or_native_operation(self):
        for kind in ['netbox-media', 'gitlab']:
            self.prepare(kind)
            keys = [('namespaces', '', kind), ('jobs', kind, self.operation['name'])]
            keys.extend(('persistentvolumeclaims', kind, name) for name in self.claims)
            for key in keys:
                with self.subTest(kind=kind, key=key):
                    original = self.api.objects[key]['metadata']['uid']
                    self.api.objects[key]['metadata']['uid'] = 'replacement-with-same-name'
                    self.audit(success=False)
                    self.api.objects[key]['metadata']['uid'] = original
            for name in self.claims:
                key = ('persistentvolumeclaims', kind, name)
                original = self.api.objects.pop(key)
                self.audit(success=False)
                self.api.objects[key] = original

    def test_incomplete_or_failed_native_operations_and_unbound_claims_block_audit(self):
        for kind, status in [('netbox-media', {'succeeded': 1, 'failed': 1}),
                             ('vault-raft', {'succeeded': 1, 'conditions': []}),
                             ('harbor', {'phase': 'PartiallyFailed', 'errors': 1}),
                             ('cnpg-files', {'systemID': 'wrong-system', 'readyInstances': 1}),
                             ('cnpg-files', {'systemID': 'original-system-id', 'readyInstances': 0})]:
            with self.subTest(kind=kind, status=status):
                self.prepare(kind)
                resource = {'Job': 'jobs', 'Restore': 'restores', 'Cluster': 'clusters'}[self.operation['kind']]
                self.api.objects[resource, self.operation['namespace'], self.operation['name']]['status'] = status
                self.audit(success=False)
        self.prepare('netbox-media')
        self.api.objects['persistentvolumeclaims', 'netbox-media', 'native-data']['status']['phase'] = 'Pending'
        self.audit(success=False)

    def test_changed_velero_backup_search_index_or_claim_inventory_is_rejected(self):
        self.prepare('harbor')
        self.api.objects['backups', 'velero', self.current['backup_id']]['metadata']['uid'] = 'different-backup'
        self.audit(success=False)
        self.prepare('opensearch')
        self.api.search_index_uid = 'different-index'
        self.audit(success=False)
        self.api.search_index_uid = self.record['restore']['indices'][0]['uuid']
        self.audit()
        self.prepare('gitlab')
        self.record['claims'] = {'unrelated-database': 'injected-uid'}
        self.save('gitlab-restore.json', self.record)
        self.audit(success=False)

    def test_original_checkpoint_supports_readonly_legacy_receipts_without_requiring_shamir(self):
        for kind in ['spinnaker', 'victoriametrics', 'vault-raft', 'netbox-media', 'harbor', 'cnpg-files', 'gitlab']:
            with self.subTest(kind=kind):
                self.prepare(kind)
                self.record.update(version=1, namespace_uid='new')
                self.record.pop('claims')
                for field in ['namespace', 'kind', 'tier']:
                    self.record.pop(field)
                self.record['restore'] = self.operation
                self.save(kind + '-restore.json', self.record)
                self.audit()

    def test_receipt_retry_cannot_accept_replaced_adapter_targets_or_operation(self):
        self.prepare('netbox-media')
        self.api.objects['persistentvolumeclaims', 'netbox-media', 'native-data']['metadata']['uid'] = 'changed-after-adapter'
        self.record_tail(success=False)
        self.prepare('cnpg-files')
        self.variables['recovery_native_receipt']['uid'] = 'changed-cluster'
        self.record_tail(success=False)

    def test_fresh_receipt_and_completed_scope_gate_actual_content_requests(self):
        self.prepare('victoriametrics')
        receipt = self.root / 'receipts/victoriametrics-restore.json'
        receipt.unlink()
        self.record_tail()
        recorded = json.loads(receipt.read_text())
        self.assertEqual(recorded['version'], 2)
        self.assertEqual(recorded['namespace_uid'], self.namespace['metadata']['uid'])
        self.assertEqual(recorded['claims'], self.claims)
        self.plan['clusters'] = [self.plan['clusters'][1]]
        self.plan['products'] = [self.current]
        self.api.put({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'kube-system', 'uid': 'actual-cluster'}})
        self.save('tier-1-cluster.json', {'plan_sha256': self.plan['plan_sha256'], 'uid': 'actual-cluster'})
        tasks = [{'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'verify-targets'}},
                 {'ansible.builtin.uri': {'url': self.url + '/retained', 'method': 'GET',
                     'ca_path': str(self.certificate), 'validate_certs': True, 'use_proxy': False}}]
        self.play(tasks)
        requests = sum(path == '/retained' for _, path in self.api.requests)
        self.assertEqual(requests, 1)
        self.api.objects['persistentvolumeclaims', 'victoriametrics', 'metrics-data']['metadata']['uid'] = 'replacement'
        mutations = copy.deepcopy(self.api.mutations)
        before = {path.name: path.read_bytes() for path in (self.root / 'receipts').glob('*')}
        self.play(tasks, success=False)
        self.assertEqual(sum(path == '/retained' for _, path in self.api.requests), requests)
        self.assertEqual(self.api.mutations, mutations)
        self.assertEqual({path.name: path.read_bytes() for path in (self.root / 'receipts').glob('*')}, before)


if __name__ == '__main__':
    unittest.main()
