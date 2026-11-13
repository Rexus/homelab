"""Native account bootstrap: repeatability, authority boundaries and one-time secrets."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from account_bootstrap_fixture import NetBoxFixture
from tier_repo_test_support import UPSTREAM


NATIVE = os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('openssl')


@unittest.skipUnless(NATIVE, 'Requires Linux Ansible, OpenSSL and prepared native collections/clients')
class AccountBootstrapNative(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='account-bootstrap-')
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.env = os.environ.copy()
        self.env.update(ANSIBLE_NOCOLOR='1', ANSIBLE_HOST_KEY_CHECKING='False',
                        ANSIBLE_ROLES_PATH=str(UPSTREAM / 'tier-0/ansible/roles'),
                        NO_PROXY='localhost,127.0.0.1', no_proxy='localhost,127.0.0.1')
        collections = self.env.get('ACCOUNT_BOOTSTRAP_COLLECTIONS')
        clients = self.env.get('ACCOUNT_BOOTSTRAP_PYTHON')
        if collections:
            self.env['ANSIBLE_COLLECTIONS_PATH'] = collections + ':' + self.env.get('ANSIBLE_COLLECTIONS_PATH', '')
        if clients:
            self.env['PYTHONPATH'] = clients + ':' + self.env.get('PYTHONPATH', '')

    def run_play(self, tasks=None, variables=None, role=None, hosts='localhost', inventory=None, check=False):
        play = dict(name='Isolated native account fixture', hosts=hosts, gather_facts=False,
                    connection='local', vars=variables or {})
        play['vars']['ansible_python_interpreter'] = '{{ ansible_playbook_python }}'
        if role:
            play['roles'] = [role]
        else:
            play['tasks'] = tasks
        path = self.work / 'play.yml'
        path.write_text(yaml.safe_dump([play], sort_keys=False))
        argv = ['ansible-playbook', '-i', inventory or 'localhost,', str(path)]
        if check:
            argv.append('--check')
        result = subprocess.run(argv, env=self.env, cwd=self.work, capture_output=True,
                                text=True, timeout=100)
        return result

    def prepare_netbox(self, v2_admin=False):
        self.cert = self.work / 'ca.crt'
        key = self.work / 'server.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(key), '-out', str(self.cert)], check=True, capture_output=True)
        self.api = NetBoxFixture(self.cert, key)
        self.addCleanup(self.api.close)
        admin_secret = {'api_token': self.api.admin}
        if v2_admin:
            admin_secret['api_key'] = 'AdminKey0001'
            self.api.admin = 'nbt_AdminKey0001.' + self.api.admin
        self.token = self.work / 'credentials' / 'audit-token'
        self.variables = dict(
            netbox_audit_account_enabled=True, netbox_audit_account_url=self.api.url,
            netbox_audit_account_password='isolated-test-password-not-for-live-use',
            netbox_audit_account_token_expires=(datetime.now(timezone.utc) + timedelta(days=30))
                .strftime('%Y-%m-%dT%H:%M:%SZ'),
            netbox_audit_account_token_file=str(self.token), netbox_audit_account_ca_file=str(self.cert),
            control_applications_secrets={'netbox/netbox-superuser': admin_secret})

    def bootstrap(self):
        return self.run_play(role='netbox_audit_account', variables=self.variables)

    def require_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_netbox_native_create_repeat_and_missing_plaintext_fail_closed(self):
        self.prepare_netbox(v2_admin=True)
        first = self.bootstrap()
        self.require_success(first)
        self.assertEqual([w[:2] for w in self.api.writes],
                         [('POST', 'permissions'), ('POST', 'users'), ('POST', 'tokens')])
        self.assertEqual(self.api.rows['permissions'][0]['actions'], ['view'])
        self.assertEqual(self.api.rows['permissions'][0]['object_types'], ['core.objectchange'])
        self.assertEqual(self.api.rows['users'][0]['groups'], [])
        self.assertFalse(self.api.rows['tokens'][0]['write_enabled'])
        self.assertEqual(self.token.read_text(), 'nbt_' + self.api.key + '.' + self.api.secret)
        self.assertEqual(self.token.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.token.parent.stat().st_mode & 0o777, 0o700)
        stamp = self.token.stat().st_mtime_ns
        writes = deepcopy(self.api.writes)
        second = self.bootstrap()
        self.require_success(second)
        self.assertEqual(self.api.writes, writes)
        self.assertEqual(self.token.stat().st_mtime_ns, stamp)
        self.assertIn('changed=0', second.stdout)
        for secret in (self.api.secret, self.api.admin, self.variables['netbox_audit_account_password']):
            self.assertNotIn(secret, first.stdout + first.stderr + second.stdout + second.stderr)
        self.token.unlink()
        missing = self.bootstrap()
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('Restore the original private controller file', missing.stdout)
        self.assertEqual(self.api.writes, writes)
        self.assertFalse(self.token.exists())

    def test_netbox_rejects_superuser_group_and_broader_permission_before_mutation(self):
        self.prepare_netbox()
        self.require_success(self.bootstrap())
        writes = deepcopy(self.api.writes)
        for condition in ('superuser', 'group', 'permission', 'writable'):
            with self.subTest(condition=condition):
                rows = deepcopy(self.api.rows)
                self.api.superuser = condition == 'superuser'
                if condition == 'group':
                    self.api.rows['users'][0]['groups'] = [dict(id=99, name='operators')]
                if condition == 'permission':
                    self.api.rows['permissions'][0]['actions'] = ['view', 'change']
                if condition == 'writable':
                    self.api.rows['tokens'][0]['write_enabled'] = True
                result = self.bootstrap()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.api.writes, writes)
                self.api.rows = rows
                self.api.superuser = False

    def test_netbox_rejects_bad_tls_and_missing_inputs_without_changes(self):
        self.prepare_netbox()
        unrelated = self.work / 'unrelated-ca.crt'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                        '-subj', '/CN=unrelated', '-keyout', str(self.work / 'unrelated.key'),
                        '-out', str(unrelated)], check=True, capture_output=True)
        for field, value in [('netbox_audit_account_enabled', False),
                             ('netbox_audit_account_password', ''),
                             ('netbox_audit_account_url', 'http://localhost'),
                             ('netbox_audit_account_ca_file', str(unrelated)),
                             ('netbox_audit_account_ca_file', '/missing/bootstrap-ca.crt')]:
            with self.subTest(field=field):
                original = self.variables[field]
                self.variables[field] = value
                result = self.bootstrap()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.api.writes)
                self.assertFalse(self.token.exists())
                self.variables[field] = original

    def test_netbox_check_mode_validates_without_creating_account_or_token(self):
        self.prepare_netbox()
        result = self.run_play(role='netbox_audit_account', variables=self.variables, check=True)
        self.require_success(result)
        self.assertFalse(self.api.writes)
        self.assertFalse(self.token.exists())
        self.assertIn('changed=0', result.stdout)

    def test_native_account_entry_points_have_valid_syntax(self):
        for name in ('freeipa-ldap-reader.yml', 'netbox-audit-account.yml'):
            result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', 'localhost,',
                str(UPSTREAM / 'tier-0/ansible/playbooks/deployment' / name)],
                env=self.env, cwd=self.work, capture_output=True, text=True, timeout=30)
            self.require_success(result)

    def test_generated_account_entry_points_have_valid_syntax(self):
        generated = self.work / 'generated'
        result = subprocess.run([sys.executable, str(UPSTREAM / 'scripts/tier-repos/generate.py'),
            '--root', str(generated), '--prefix', 'account'], env=self.env,
            capture_output=True, text=True, timeout=90)
        self.require_success(result)
        owner = generated / 'account-iac/account-tier-0'
        environment = self.env | {'ANSIBLE_ROLES_PATH': str(owner / 'ansible/roles')}
        for name in ('freeipa-ldap-reader.yml', 'netbox-audit-account.yml'):
            result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', 'localhost,',
                str(owner / 'ansible/playbooks/deployment' / name)],
                env=environment, cwd=owner, capture_output=True, text=True, timeout=30)
            self.require_success(result)

    def test_pinned_netbox_chart_exposes_v2_admin_key_only_to_the_web_process(self):
        chart = os.environ.get('ACCOUNT_BOOTSTRAP_NETBOX_CHART')
        if not chart or not shutil.which('helm'):
            self.skipTest('Set ACCOUNT_BOOTSTRAP_NETBOX_CHART to the prepared official 8.3.95 chart')
        from test_tier_control_applications import rendered_releases
        release = next(r for r in rendered_releases() if r['name'] == 'netbox')
        values = self.work / 'netbox-values.yml'
        values.write_text(yaml.safe_dump(release['values']))
        result = subprocess.run(['helm', 'template', 'netbox', chart, '--namespace', 'netbox',
                                 '-f', str(values)], env=self.env, capture_output=True, text=True, timeout=45)
        self.require_success(result)
        documents = [d for d in yaml.safe_load_all(result.stdout) if d]
        for item in documents:
            if item['kind'] == 'Deployment':
                pod = item['spec']['template']['spec']
            elif item['kind'] == 'CronJob':
                pod = item['spec']['jobTemplate']['spec']['template']['spec']
            else:
                continue
            environment = {e['name']: e for e in pod['containers'][0]['env']}
            if item['metadata']['name'] == 'netbox':
                self.assertIn('v4.7.3', pod['containers'][0]['image'])
                self.assertEqual(environment['SUPERUSER_API_KEY']['valueFrom']['secretKeyRef'],
                                 dict(name='netbox-superuser', key='api_key', optional=True))
            else:
                self.assertNotIn('SUPERUSER_API_KEY', environment)

    def test_existing_controller_helper_checks_selected_netbox_clients_without_changes(self):
        result = self.run_play(tasks=[{'ansible.builtin.include_tasks': str(
            UPSTREAM / 'shared/ansible/playbooks/tasks/control-node-python.yml')},
            {'ansible.builtin.assert': {'that': [
                'control_node_python_final.not_found | length == 0',
                'control_node_python_final.mismatched | length == 0',
                'control_node_python_import_check.rc == 0']}}], variables=dict(
                control_node_required_collections=[dict(name='netbox.netbox')],
                control_node_collections_mode='check', ansible_os_family='Debian'))
        self.require_success(result)
        self.assertIn('changed=0', result.stdout)

    def test_ldap_rejects_wrong_target_and_identity_scope_with_native_assertions(self):
        role = UPSTREAM / 'tier-0/ansible/roles/freeipa_ldap_reader'
        variables = yaml.safe_load((role / 'defaults/main.yml').read_text())
        variables.update(freeipa_ldap_reader_enabled=True, ansible_os_family='RedHat',
                         freeipa_ldap_reader_base_dn='dc=lab,dc=example,dc=com',
                         freeipa_ldap_reader_ldapi_socket='/run/slapd-LAB-EXAMPLE-COM.socket',
                         freeipa_ldap_reader_password='isolated-bind-password-not-for-live-use',
                         freeipa_ldap_reader_password_expiration='20380119031407Z')
        tasks = yaml.safe_load((role / 'tasks/main.yml').read_text())
        inventory = self.work / 'inventory.yml'
        inventory.write_text(yaml.safe_dump(dict(all=dict(children=dict(identity_primary=dict(hosts=dict(primary={})))))))
        self.require_success(self.run_play(tasks[:2], deepcopy(variables), hosts='primary', inventory=str(inventory)))
        for field, value in [('freeipa_ldap_reader_bind_dn', 'uid=admin,cn=users,cn=accounts,dc=lab,dc=example,dc=com'),
                             ('freeipa_ldap_reader_ldapi_socket', 'ldaps://remote.example.com'),
                             ('freeipa_ldap_reader_password_expiration', '20000101000000Z')]:
            invalid = deepcopy(variables)
            invalid[field] = value
            self.assertNotEqual(self.run_play(tasks[:2], invalid, hosts='primary',
                                             inventory=str(inventory)).returncode, 0)
        inspect = next(t for t in tasks if 'block' in t)['block'][1]
        for classes, extra in [(['top', 'account', 'simpleSecurityObject', 'posixAccount'], {}),
                               (['top', 'account', 'simpleSecurityObject'], {'memberOf': 'cn=admins'}),
                               (['top', 'account', 'simpleSecurityObject'], {'krbPrincipalName': 'admin@LAB.EXAMPLE.COM'}),
                               (['top', 'account', 'simpleSecurityObject'], {'aci': 'unexpected existing grant'})]:
            invalid = deepcopy(variables)
            invalid['freeipa_ldap_reader_existing'] = dict(results=[dict(
                dn='uid=keycloak,cn=sysaccounts,cn=etc,dc=lab,dc=example,dc=com',
                objectClass=classes, **extra)])
            self.assertNotEqual(self.run_play([inspect], invalid, hosts='primary',
                                             inventory=str(inventory)).returncode, 0)


if __name__ == '__main__':
    unittest.main()
