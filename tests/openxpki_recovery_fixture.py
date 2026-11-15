"""Confined recovery fixture with native files, crypto and encrypted archives.

Database, service, package and hardware actions are doubled. The production
binding and recovery orchestration run unchanged apart from fixture paths and
file ownership. Storage qualification has its own native guard tests.
"""

import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/openxpki'
CONFIGURATION = b'original immutable configuration artifact fixture\n'
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None
NATIVE = ANSIBLE and shutil.which('openssl') and shutil.which('age') and shutil.which('age-keygen')
DOUBLE = '''
import json
from pathlib import Path
from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        variables = task_vars or {}
        action = self._task.action.rsplit('.', 1)[-1]
        args = self._task.args
        event = dict(action=action, args=args)
        with Path(variables['fixture_events']).open('a') as stream:
            stream.write(json.dumps(event) + '\\n')
        if action == 'service_facts':
            return dict(result, changed=False, ansible_facts=dict(services={
                name + '.service': dict(state='running')
                for name in ('apache2', 'openxpki-clientd', 'openxpki-serverd')}))
        if action == 'mariadb_query':
            return dict(result, changed=False, query_result=[
                [dict(total=variables.get('fixture_certificates', 0))],
                [dict(total=variables.get('fixture_workflows', 0))]])
        if action == 'mariadb_db':
            target = Path(args['target'])
            if not target.is_relative_to(Path(variables['fixture_root'])):
                return dict(result, failed=True, msg='Database fixture escaped its workspace')
            if args['state'] == 'dump':
                target.write_text('fixture original database including issuance and workflows\\n')
            elif args['state'] == 'import':
                if variables.get('fixture_import_failure'):
                    return dict(result, failed=True, msg='Fixture database import failed')
                Path(variables['fixture_imported']).write_bytes(target.read_bytes())
            else:
                return dict(result, failed=True, msg='Unexpected database operation')
        if action == 'command':
            argv = args['argv']
            if len(argv) == 4 and argv[1] == '--module' and argv[3] == '--list-token-slots':
                text = 'Slot 0: original fixture token\\n  serial num : ' + variables['fixture_serial']
            elif argv[:2] == ['openssl', 'pkey'] and '-pubout' in argv:
                if '-inform' not in argv or 'ENGINE' not in argv or '-out' in argv:
                    return dict(result, failed=True, msg='Unexpected private-key operation')
                text = variables['fixture_public_key']
            else:
                return dict(result, failed=True, msg='Forbidden hardware operation')
            return dict(result, changed=False, rc=0, stdout=text, stderr='',
                        stdout_lines=text.splitlines(), stderr_lines=[])
        return dict(result, changed=action in ('mariadb_db', 'systemd_service'))
'''


class RecoveryFixture:
    def setUp(self):
        import grp

        self.temp = tempfile.TemporaryDirectory(prefix='openxpki-recovery-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roles = self.root / 'roles'
        self.data = self.root / 'issuer'
        self.backups = self.root / 'backups'
        self.recovery = self.root / 'staging/recovery'
        self.events_path = self.root / 'events.jsonl'
        self.imported = self.root / 'imported.sql'
        native = self.root / 'native-provider'
        native.mkdir()
        for name in ('module.so', 'engine.so'):
            (native / name).touch()
        for name in ('openxpki', 'hsm_provider'):
            source = UPSTREAM / f'tier-0/ansible/roles/{name}'
            destination = self.roles / name
            shutil.copytree(source, destination)
            for folder in ('tasks', 'handlers'):
                for path in (destination / folder).glob('*.yml'):
                    content = path.read_text().replace('^/srv/', '^' + str(self.root) + '/')
                    content = content.replace('/etc/hsm-provider', str(native))
                    for action in ('apt', 'systemd_service', 'service_facts', 'mariadb_db', 'mariadb_query'):
                        namespace = 'ansible.mariadb' if action.startswith('mariadb_') else 'ansible.builtin'
                        content = content.replace(f'{namespace}.{action}:', f'fixture.recovery.{action}:')
                    if name == 'hsm_provider':
                        content = content.replace('ansible.builtin.command:', 'fixture.recovery.command:')
                    content = content.replace('owner: root', 'owner: ' + getpass.getuser())
                    content = content.replace('owner: openxpki', 'owner: ' + getpass.getuser())
                    for group in ('root', 'openxpki', 'www-data'):
                        content = content.replace('group: ' + group, 'group: ' + grp.getgrgid(os.getgid()).gr_name)
                    path.write_text(content)
        # The test owns ordinary temporary directories, not mounted guest disks.
        (self.roles / 'openxpki/tasks/preflight.yml').write_text(
            '- ansible.builtin.import_tasks: binding.yml\n')
        staging = self.roles / 'openxpki/tasks/restore-stage.yml'
        if staging.exists():
            tasks = yaml.safe_load(staging.read_text())
            block = next(task['block'] for task in tasks if 'block' in task)
            transfer = next(task for task in block if 'ansible.builtin.copy' in task)
            # Simulate disappearance after the controller manifest was checked.
            transfer['ansible.builtin.copy']['src'] = (
                "{{ fixture_copy_source | default(openxpki_restore_source_directory) }}/")
            publication = next(i for i, task in enumerate(block) if 'ansible.builtin.command' in task)
            # Create a competing empty destination immediately before the real mv.
            block[publication:publication] = [
                {'ansible.builtin.file': {'path': '{{ openxpki_restore_directory }}', 'state': 'directory',
                                         'mode': '0700'},
                 'when': 'fixture_concurrent_publication | default(false) | bool'},
                {'ansible.builtin.stat': {'path': '{{ openxpki_restore_directory }}'},
                 'register': 'fixture_concurrent_destination',
                 'when': 'fixture_concurrent_publication | default(false) | bool'},
                {'ansible.builtin.copy': {'dest': str(self.root / 'concurrent-destination.json'),
                                         'content': '{{ fixture_concurrent_destination.stat | to_json }}',
                                         'mode': '0600'},
                 'when': 'fixture_concurrent_publication | default(false) | bool'},
            ]
            staging.write_text(yaml.safe_dump(tasks, sort_keys=False))
        plugins = self.root / 'collections/ansible_collections/fixture/recovery/plugins'
        for action in ('apt', 'systemd_service', 'service_facts', 'mariadb_db', 'mariadb_query', 'command'):
            (plugins / 'action').mkdir(parents=True, exist_ok=True)
            (plugins / 'modules').mkdir(exist_ok=True)
            (plugins / f'action/{action}.py').write_text(DOUBLE)
            (plugins / f'modules/{action}.py').write_text(
                'from ansible.module_utils.basic import AnsibleModule\n'
                'AnsibleModule(argument_spec={}).fail_json(msg="Recovery action double not loaded")\n')
        self.run_native(['age-keygen', '-o', str(self.root / 'age.key')])
        recipient = self.run_native(['age-keygen', '-y', str(self.root / 'age.key')]).stdout.strip()
        self.inputs = dict(
            ansible_connection='local', ansible_become=False,
            ansible_python_interpreter=shutil.which('python3'),
            ansible_distribution='Debian', ansible_distribution_major_version='12',
            ansible_os_family='Debian', ansible_service_mgr='systemd',
            openxpki_data_mount=str(self.data),
            openxpki_configuration_sha256=hashlib.sha256(CONFIGURATION).hexdigest(),
            openxpki_deployment_id='original-issuer', openxpki_realm='infrastructure',
            openxpki_package_versions={'libopenxpki-perl': '3.34.0-1'},
            openxpki_database_password='database-' + 'x' * 32,
            openxpki_session_password='session-' + 'y' * 32, openxpki_session_secret='z' * 40,
            openxpki_managed_cli=True, openxpki_activate_runtime=True,
            openxpki_backup_directory=str(self.backups), openxpki_backup_id='original',
            openxpki_backup_recipient=recipient, openxpki_restore_directory=str(self.recovery),
            hsm_provider='pkcs11', hsm_provider_mode='client', hsm_provider_custody_ready=True,
            hsm_provider_packages=['approved-native-provider'], hsm_provider_library=str(native / 'module.so'),
            hsm_provider_expected_serial='ORIGINAL123', hsm_provider_user='openxpki', hsm_provider_group='openxpki',
            hsm_issuer_engine_library=str(native / 'engine.so'),
            hsm_issuer_key='pkcs11:serial=ORIGINAL123;id=%01;type=private',
            hsm_issuer_pin='fixture-changed-credential',
            fixture_serial='ORIGINAL123',
            fixture_events=str(self.events_path), fixture_root=str(self.root), fixture_imported=str(self.imported),
        )
        self.environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(self.roles), ANSIBLE_NOCOLOR='1',
                                ANSIBLE_COLLECTIONS_PATH=str(self.root / 'collections') + os.pathsep
                                + os.environ.get('ANSIBLE_COLLECTIONS_PATH', ''))
        self.environment.pop('ANSIBLE_CONFIG', None)
        (self.root / 'ansible.cfg').write_text('[defaults]\n')

    def run_native(self, argv, **kwargs):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def prepare(self, backend):
        release = self.data / ('configuration/' + self.inputs['openxpki_configuration_sha256'])
        for name in ('keys', 'identity', 'public'):
            (self.data / name).mkdir(parents=True)
        realm = release / 'config.d/realm/infrastructure'
        realm.mkdir(parents=True)
        system = release / 'config.d/system'
        system.mkdir()
        (system / 'crypto.yaml').write_text('secret:\n  svault:\n    value: original-datavault-secret\n')
        signer = dict(engine='OpenSSL', key_store='OPENXPKI', key=str(self.data / 'keys/issuer.pem'))
        if backend == 'pkcs11':
            signer = dict(engine='PKCS11', key_store='ENGINE', key=self.inputs['hsm_issuer_key'],
                          engine_section='MODULE_PATH = ' + self.inputs['hsm_provider_library']
                          + '\ndynamic_path = ' + self.inputs['hsm_issuer_engine_library'] + '\nPIN = __PIN__')
        (realm / 'crypto.yaml').write_text(yaml.safe_dump({'token': {'ca-signer': signer}}))
        password = 'separately-custodied-fixture-software-password'
        key = self.data / 'keys/issuer.pem' if backend == 'software' else self.root / 'outside-token-fixture.key'
        self.run_native(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:secp384r1',
                         '-days', '2', '-subj', '/CN=Original Fixture Issuer',
                         '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                         '-passout', 'env:FIXTURE_KEY_PASSWORD', '-keyout', str(key),
                         '-out', str(self.data / 'identity/issuer.pem')],
                        env=dict(os.environ, FIXTURE_KEY_PASSWORD=password))
        public_key = self.run_native(['openssl', 'pkey', '-in', str(key), '-passin', 'env:FIXTURE_KEY_PASSWORD',
                                      '-pubout'], env=dict(os.environ, FIXTURE_KEY_PASSWORD=password)).stdout
        fingerprint = self.run_native(['openssl', 'x509', '-in', str(self.data / 'identity/issuer.pem'),
                                       '-noout', '-fingerprint', '-sha256']).stdout.strip().split('=', 1)[1]
        self.inputs.update(openxpki_issuer_fingerprint=fingerprint, fixture_public_key=public_key,
                           openxpki_signer_password=password if backend == 'software' else '',
                           openxpki_required_state_paths=[str(self.data / 'identity/issuer.pem'),
                                                         str(system / 'crypto.yaml'), str(realm / 'crypto.yaml')])
        (self.data / 'keys/cli.pem').write_text('original-cli-custody\n')
        (self.data / 'public/issuer.crl').write_text('original-publication-state\n')
        (self.data / 'schema-initialized').write_text(self.inputs['openxpki_configuration_sha256'])
        (self.data / 'configuration.tar.gz').write_bytes(CONFIGURATION)
        binding = {field.removeprefix('openxpki_'): self.inputs[field] for field in (
            'openxpki_deployment_id', 'openxpki_configuration_sha256', 'openxpki_package_versions')}
        binding['secret_digest'] = hashlib.sha256(json.dumps([self.inputs[field] for field in (
            'openxpki_database_password', 'openxpki_session_password', 'openxpki_session_secret')]).encode()).hexdigest()
        (self.data / 'deployment.json').write_text(json.dumps(binding))

    def run_role(self, entry, **updates):
        values = dict(self.inputs, **updates)
        inputs = self.root / 'inputs.yml'
        inputs.write_text(yaml.safe_dump(values))
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([dict(hosts='localhost', gather_facts=False, tasks=[
            {'ansible.builtin.include_role': {'name': 'openxpki', 'tasks_from': entry}},
        ])], sort_keys=False))
        return subprocess.run([ANSIBLE, '-i', 'localhost,', str(play), '-e', '@' + str(inputs)],
                              cwd=self.root, env=self.environment, capture_output=True, text=True, timeout=180)

    def backup_and_prepare_restore(self):
        result = self.run_role('backup')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.archive = self.backups / 'original.tar.gz.age'
        plaintext = self.root / 'recovery.tar.gz'
        self.run_native(['age', '--decrypt', '--identity', str(self.root / 'age.key'),
                         '--output', str(plaintext), str(self.archive)])
        self.recovery.mkdir(parents=True)
        with tarfile.open(plaintext) as archive:
            archive.extractall(self.recovery, filter='data')
        for relative in ('keys/issuer.pem', 'identity/issuer.pem'):
            (self.data / relative).unlink(missing_ok=True)
        self.events_path.write_text('')
        self.inputs.update(openxpki_activate_runtime=False, openxpki_restore_approved=True)
        self.authorize_manifest()

    def authorize_manifest(self):
        self.inputs['openxpki_restore_manifest_sha256'] = hashlib.sha256(
            (self.recovery / 'recovery.json').read_bytes()).hexdigest()

    def events(self):
        return [json.loads(line) for line in self.events_path.read_text().splitlines()]
