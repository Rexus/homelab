"""Exercise first-run inputs, native proxy routing and isolated identity health checks."""

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


def load(relative):
    return yaml.safe_load((UPSTREAM / relative).read_text())


class FirstRunContracts(unittest.TestCase):
    def test_identity_exception_is_checked_before_baseline_and_health_before_replicas(self):
        values = load('tier-0/ansible/group_vars/foundation.yml.example')
        self.assertFalse(values['baseline_disable_ipv6'])
        plays = load('tier-0/ansible/playbooks/deployment/identity-freeipa.yml')
        self.assertIn('not baseline_disable_ipv6 | default(true) | bool',
                      plays[0]['tasks'][0]['ansible.builtin.assert']['that'])
        primary = next(i for i, play in enumerate(plays) if play.get('hosts') == 'identity_primary')
        replica = next(i for i, play in enumerate(plays) if play.get('hosts') == 'identity_replicas')
        check = plays[primary + 1]
        self.assertLess(primary + 1, replica)
        self.assertEqual(check['ansible.builtin.import_playbook'], '../maintenance/foundation.yml')
        self.assertEqual(check['vars']['foundation_health_hosts'], 'identity_primary')
        self.assertIn("== 'complete'", check['when'])

    def test_issuer_prepares_package_proxy_before_installation(self):
        plays = load('tier-0/ansible/playbooks/deployment/openxpki.yml')
        wait = next(index for index, play in enumerate(plays)
                    if play.get('ansible.builtin.import_playbook', '').endswith('/guest-ready.yml'))
        issuer = next(index for index, play in enumerate(plays) if play.get('hosts') == 'issuing_ca')
        self.assertLess(wait, issuer)
        self.assertEqual(plays[wait]['vars']['guest_ready_group'], 'issuing_ca')
        recipe = plays[issuer]
        self.assertEqual(recipe['roles'], ['baseline', 'openxpki'])


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('bash'),
                     'Requires Linux/WSL Ansible and Bash')
class NativeFirstRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tier-first-run-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'))

    def run_play(self, play, success=True):
        path = self.root / 'verify.yml'
        path.write_text(yaml.safe_dump([play], sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)],
                                env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_changed_recipes_parse_with_the_tier_inventory(self):
        for tier, recipe in (('tier-0', 'identity-freeipa'), ('tier-0', 'openxpki'),
                             ('tier-2', 'outbound-cache')):
            repo = UPSTREAM / tier
            inventory = self.root / f'{tier}-hosts.yml'
            inventory.write_text((repo / 'ansible/inventory/hosts.yml.example').read_text())
            result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', str(inventory),
                str(repo / f'ansible/playbooks/deployment/{recipe}.yml')],
                env=dict(self.env, ANSIBLE_CONFIG=str(repo / 'ansible/ansible.cfg')),
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('No inventory was parsed', result.stderr)

    def test_documented_logging_catalog_reuses_global_setup_and_inventory_without_host_files(self):
        docs = (UPSTREAM / 'docs/03-deployment/stage-03-logging/README.md').read_text()
        catalog = next(yaml.safe_load(block) for block in re.findall(r'```yaml\n(.*?)```', docs, re.S)
                       if 'logging_producer_hosts:' in block)
        inventory = self.root / 'ansible/inventory'
        variables = self.root / 'ansible/group_vars'
        recipes = self.root / 'ansible/playbooks/deployment'
        for directory in (inventory, variables, recipes):
            directory.mkdir(parents=True)
        receiver_inventory = load('tier-0/ansible/inventory/hosts.yml.example')
        (inventory / 'hosts.yml').write_text(yaml.safe_dump(receiver_inventory))
        for name in ('all', 'syslog', 'foundation'):
            (variables / f'{name}.yml').write_text(
                (UPSTREAM / f'tier-0/ansible/group_vars/{name}.yml.example').read_text())
        (variables / 'logging_producers.yml').write_text(yaml.safe_dump(catalog))
        expected_ips = {}
        for setup in ('syslog', 'foundation'):
            expected_ips.update(yaml.safe_load((variables / f'{setup}.yml').read_text())['platform_host_ips'])
        verify = recipes / 'inputs.yml'
        assertions = [
            "groups.logging_workflow_producers | sort == ['ca-1', 'log-1', 'pve01']",
            "hostvars['log-1'].ansible_host == expected_ips['log-1']",
            "hostvars['ca-1'].ansible_host == expected_ips['ca-1']",
            "hostvars['pve01'].ansible_host == 'pve01.' ~ platform_internal_domain",
            "hostvars['pve01'].ansible_user == ansible_user",
            "hostvars['ca-1'].ansible_user == ansible_user",
            "hostvars['log-1'].log_forwarder_streams[0].name == 'log-1-os'",
            "hostvars['ca-1'].log_forwarder_streams[0].name == 'ca-1-os'",
            "log_forwarder_peer == 'logs.' ~ platform_internal_domain",
            "logging_run.target == log_forwarder_peer",
            "logging_run.requests == logging_run.workspace ~ '/requests'",
        ]
        verify.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'become': False,
            'vars': {'expected_ips': expected_ips, 'logging_workflow_repository': str(self.root),
                     'logging_workflow_workspace': str(self.root / 'private-workspace'),
                     'logging_workflow_issuer': 'provided'},
            'tasks': [{'ansible.builtin.include_role': {'name': 'logging_workflow'}},
                      {'ansible.builtin.assert': {'that': assertions}}],
        }], sort_keys=False))
        # Only controller-side input resolution runs. Guest execution and issuance
        # are covered by the workflow's native integration suite, not SSH doubles.
        # The real custody boundary requires this directory to be outside the repo.
        workspace = self.root.parent / f'{self.root.name}-logging-custody'
        self.addCleanup(lambda: shutil.rmtree(workspace, ignore_errors=True))
        for action in ('prepare', 'prepare', 'verify'):
            result = subprocess.run([
                'ansible-playbook', '-i', str(inventory / 'hosts.yml'), str(verify),
                '-e', f'@{variables / "all.yml"}', '-e', f'logging_workflow_action={action}',
                '-e', f'logging_workflow_workspace={workspace}',
            ], cwd=self.root, env=dict(self.env, ANSIBLE_SSH_EXECUTABLE='/bin/false',
                ANSIBLE_ROLES_PATH=os.pathsep.join([str(UPSTREAM / 'tier-0/ansible/roles'),
                                                  str(UPSTREAM / 'shared/ansible/roles')])),
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('UNREACHABLE', result.stdout)
        self.assertFalse((inventory / 'host_vars').exists())
        self.assertEqual({path.name for path in workspace.iterdir()}, {'requests', 'public', 'receivers'})

    def test_native_download_and_cache_validation_follow_the_selected_proxy(self):
        requests = []

        class Proxy(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'approved-content')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        key = next(task for task in load('tier-0/ansible/roles/openxpki/tasks/packages.yml')
                   if 'ansible.builtin.get_url' in task)
        key['ansible.builtin.get_url'].update(dest=str(self.root / 'key'), owner=os.getuid(),
                                             group=os.getgid(), checksum='')
        cache = next(task for task in load('tier-2/ansible/roles/cache_proxy/tasks/services.yml')
                     if 'ansible.builtin.uri' in task)
        self.run_play({'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'vars': {
            'repository_proxy_active': True, 'repository_proxy_url': f'http://127.0.0.1:{port}',
            'repository_proxy_effective_https_url': f'http://127.0.0.1:{port}', 'shell_proxy_no_proxy': '',
            'openxpki_repository_key_url': 'http://127.0.0.2:9/key', 'openxpki_repository_key_sha256': '',
            'cache_squid_http_port': port, 'cache_validation_url': 'http://127.0.0.2:9/cache',
            'cache_validation_enabled': True}, 'tasks': [key, cache]})
        self.assertEqual((self.root / 'key').read_bytes(), b'approved-content')
        self.assertEqual(requests, ['http://127.0.0.2:9/key', 'http://127.0.0.2:9/cache'])

    def test_cache_deployment_validation_requires_only_the_vip_from_the_controller(self):
        requests = []

        class Proxy(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(403 if 'denied.invalid' in self.path else 200)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        play = deepcopy(load('tier-2/ansible/playbooks/deployment/outbound-cache.yml')[-1])
        play.update(hosts='localhost', connection='local')
        play['vars'].update(cache_proxy_vip='127.0.0.1', cache_proxy_port=port,
                            cache_validation_url='http://approved.invalid/file',
                            cache_validation_denied_url='http://denied.invalid/file',
                            cache_proxy_fqdn='', cache_validation_enabled=True,
                            platform_host_ips={'cache-1': '192.0.2.1', 'cache-2': '192.0.2.2'})
        self.run_play(play)
        self.assertEqual(requests, ['http://approved.invalid/file', 'http://denied.invalid/file'])

        server.shutdown()
        server.server_close()
        play['vars']['cache_validation_connect_timeout'] = 1
        self.run_play(play, success=False)

    def test_identity_health_obtains_its_own_ticket_and_cleans_up_after_failure(self):
        binaries = self.root / 'bin'
        binaries.mkdir()
        stub = '''#!/usr/bin/python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
cache = os.environ.get('KRB5CCNAME', '')
if name == 'kinit':
    cache = sys.argv[sys.argv.index('-c') + 1]
    pathlib.Path(cache.removeprefix('FILE:')).write_text('temporary host ticket')
with open(os.environ['HEALTH_EVENTS'], 'a') as events:
    events.write(json.dumps({'name': name, 'cache': cache}) + '\\n')
if name == 'klist':
    sys.exit(1)
if name == 'ipa':
    assert pathlib.Path(cache.removeprefix('FILE:')).read_text() == 'temporary host ticket'
    sys.exit(int(os.environ['HEALTH_API_FAILURE']))
'''
        for name in ('kinit', 'klist', 'kdestroy', 'ipactl', 'ipa'):
            path = binaries / name
            path.write_text(stub)
            path.chmod(0o755)
        operator = self.root / 'operator-ticket'
        operator.write_text('unrelated credential')
        for failure in (False, True):
            events = self.root / 'events.jsonl'
            events.write_text('')
            play = deepcopy(load('tier-0/ansible/playbooks/maintenance/foundation.yml')[0])
            play.update(hosts='localhost', connection='local', become=False, vars={
                'foundation_freeipa_enabled': True, 'platform_fqdn': 'idm-1.corp.test',
                'foundation_freeipa_realm': 'CORP.TEST'}, environment={
                    'PATH': str(binaries) + ':' + os.environ['PATH'], 'KRB5CCNAME': f'FILE:{operator}',
                    'HEALTH_EVENTS': str(events), 'HEALTH_API_FAILURE': str(int(failure))})
            block = play['tasks'][1]['block']
            block[0]['ansible.builtin.tempfile']['path'] = str(self.root)
            block[-1].update(retries=0, delay=0)
            self.run_play(play, success=not failure)
            recorded = [json.loads(line) for line in events.read_text().splitlines()]
            acquired = next(item['cache'] for item in recorded if item['name'] == 'kinit')
            self.assertEqual(next(item['cache'] for item in recorded if item['name'] == 'ipa'), acquired)
            self.assertFalse(Path(acquired.removeprefix('FILE:')).parent.exists())
            self.assertEqual(operator.read_text(), 'unrelated credential')


if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'Requires Linux/WSL Bash')
class LoggingInputInitialization(TierRepositoryTestCase):
    def test_syslog_initialization_creates_the_catalog_and_preserves_local_edits(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        catalog = repo / 'ansible/group_vars/logging_producers.yml'
        for iteration in range(2):
            result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'syslog'],
                                    cwd=repo, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(catalog.is_file())
            if iteration == 0:
                self.assertIn('logging_producer_hosts', yaml.safe_load(catalog.read_text()))
                catalog.write_text('logging_producer_hosts: {existing-host: {}}\n')
            else:
                self.assertEqual(catalog.read_text(), 'logging_producer_hosts: {existing-host: {}}\n')
        self.assertFalse((repo / 'ansible/inventory/host_vars/log-1.yml').exists())

    def test_foundation_initialization_prepares_issuer_and_preserves_inputs_and_state(self):
        import hcl2

        self.generate()
        repo = self.root / 'verify-tier-0'
        variables = repo / 'ansible/group_vars'
        issuer = variables / 'issuer.yml'
        foundation = variables / 'foundation.yml'
        overlay = variables / 'foundation.test.yml'
        terraform = repo / 'terraform/deployments/foundation/terraform.tfvars'

        def initialize(*options):
            result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'foundation', *options],
                                    cwd=repo, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        initialize('--env', 'test')
        self.assertEqual(issuer.read_bytes(), issuer.with_suffix('.yml.example').read_bytes())
        self.assertEqual(foundation.read_bytes(), foundation.with_suffix('.yml.example').read_bytes())
        self.assertTrue(overlay.is_file())
        self.assertFalse((variables / 'issuer.test.yml').exists())
        values = hcl2.loads(terraform.read_text())
        self.assertEqual({name.strip('"') for name in values['vm_instances']}, {'ca-1'})
        self.assertEqual(values['lxc_instances'], {})
        self.assertEqual({path.parent.name for path in repo.glob('terraform/deployments/*/terraform.tfvars')},
                         {'foundation'})
        for unrelated in ('syslog', 'cache', 'hsm', 'logging_producers'):
            self.assertFalse((variables / f'{unrelated}.yml').exists())
        self.assertEqual(issuer.stat().st_mode & 0o777, 0o600)

        issuer.write_text('openxpki_realm: retained-issuer\n')
        foundation.write_text('platform_host_ips: {ca-1: 192.0.2.30}\n')
        overlay.write_text('platform_host_ips: {ca-1: 192.0.2.31}\n')
        terraform.write_text(terraform.read_text() + '\n# Retained deployment choices.\n')
        retained = {path: path.read_bytes() for path in (issuer, foundation, overlay, terraform)}
        state = repo / '.terraform/state/foundation/test/terraform.tfstate'
        state.parent.mkdir(parents=True)
        state_bytes = b'{"version":4,"serial":23,"lineage":"retained-fixture","resources":[]}\n'
        state.write_bytes(state_bytes)

        initialize('--env', 'test')
        for path, content in retained.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(state.read_bytes(), state_bytes)
        self.assertFalse(list(repo.rglob('*.bak.*')))

        # A previously initialized foundation can gain its missing companion independently.
        issuer.unlink()
        initialize('--env', 'test')
        self.assertEqual(issuer.read_bytes(), issuer.with_suffix('.yml.example').read_bytes())
        self.assertEqual(foundation.read_bytes(), retained[foundation])
        self.assertEqual(terraform.read_bytes(), retained[terraform])
        self.assertEqual(state.read_bytes(), state_bytes)
        issuer.write_bytes(retained[issuer])

        initialize('--env', 'test', '--overwrite')
        for path, content in retained.items():
            backups = list(path.parent.glob(path.name + '.bak.*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), content)
        self.assertEqual(issuer.read_bytes(), issuer.with_suffix('.yml.example').read_bytes())
        self.assertEqual(state.read_bytes(), state_bytes)

        # Older generated tiers can legitimately have foundation inputs without issuer examples.
        issuer.with_suffix('.yml.example').unlink()
        issuer.unlink()
        initialize('--env', 'test')
        self.assertFalse(issuer.exists())
        self.assertEqual(state.read_bytes(), state_bytes)
        self.assertEqual({path.parent.name for path in repo.glob('terraform/deployments/*/terraform.tfvars')},
                         {'foundation'})
