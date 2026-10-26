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

from tier_repo_test_support import UPSTREAM


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
        recipe = load('tier-0/ansible/playbooks/deployment/openxpki.yml')[0]
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

    def test_documented_logging_commands_load_global_setup_and_host_inputs(self):
        docs = (UPSTREAM / 'docs/deployment/stage-2-logging/sources.md').read_text()
        blocks = re.findall(r'```bash\n(.*?)```', docs, re.S)
        inputs = next(block for block in blocks if 'logging_inputs=' in block)
        commands = [block for block in blocks if 'ansible-playbook "${logging_inputs[@]}"' in block]
        inventory = self.root / 'ansible/inventory'
        variables = self.root / 'ansible/group_vars'
        hosts = self.root / 'ansible/host_vars'
        for directory in (inventory, variables, hosts):
            directory.mkdir(parents=True)
        (inventory / 'hosts.yml').write_text((UPSTREAM / 'tier-0/ansible/inventory/hosts.yml.example').read_text())
        for name in ('all', 'syslog', 'foundation', 'logging_producers', 'logging_archive', 'logging_backup'):
            (variables / f'{name}.yml').write_text(
                (UPSTREAM / f'tier-0/ansible/group_vars/{name}.yml.example').read_text())
        (inventory / 'hosts.yml').write_text(yaml.safe_dump({'all': {'vars': {
            'ansible_host': "{{ platform_host_ips[inventory_hostname] }}"}, 'hosts': {
                'log-1': {}, 'ca-1': {}, 'recovery': {}}}}))
        for name in ('log-1', 'ca-1', 'recovery'):
            (hosts / f'{name}.yml').write_text(yaml.safe_dump({
                'ansible_user': name + '-operator', 'log_forwarder_streams': [{'name': name + '-os'}],
                **({'ansible_host': '192.0.2.20'} if name == 'recovery' else {})}))
        verify = self.root / 'inputs.yml'
        expected_ips = {'recovery': '192.0.2.20'}
        for setup in ('syslog', 'foundation'):
            expected_ips.update(yaml.safe_load((variables / f'{setup}.yml').read_text())['platform_host_ips'])
        verify.write_text(yaml.safe_dump([{'hosts': 'all', 'gather_facts': False,
            'vars': {'expected_ips': expected_ips}, 'tasks': [{
            'ansible.builtin.assert': {'that': [
                "ansible_user == inventory_hostname ~ '-operator'", "platform_domain == 'corp.example.com'",
                "ansible_host == expected_ips[inventory_hostname]",
                "log_forwarder_streams[0].name == inventory_hostname ~ '-os'"]}}]}]))
        # Keep the real documented arguments; replace only the infrastructure play with local assertions.
        cases = [(inputs + command, f'{host}\nansible/group_vars/{setup}.yml\n{self.root}/public\n',
                  'ansible/playbooks/deployment/logging-producers.yml')
                 for host, setup in (('log-1', 'syslog'), ('ca-1', 'foundation')) for command in commands]
        archive = (UPSTREAM / 'docs/deployment/stage-2-logging/step-3c-nas-archive.md').read_text()
        for variable, host, recipe in (('LOGGING_COLLECTOR', 'log-1', 'logging-archive'),
                                       ('LOGGING_RECOVERY_HOST', 'recovery', 'logging-backup')):
            block = next(block for block in re.findall(r'```bash\n(.*?)```', archive, re.S)
                         if f':?Select one' in block and f'${{{variable}' in block)
            cases.append((block, host + '\n', f'ansible/playbooks/deployment/{recipe}.yml'))
        for script, answers, recipe in cases:
            result = subprocess.run(['bash', '-eu', '-c', script.replace(recipe, str(verify))],
                                    input=answers, cwd=self.root, env=self.env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.count('"All assertions passed"'), 1)

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
