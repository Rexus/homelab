"""Native Ansible preparation with real XML/file modules and no hardware or OS changes.

Only package/service/device actions and the baseline's OS work are doubled. The
production tasks, handlers, native plist editing and entry-point selection run
under Ansible; all files are confined to the temporary fixture workspace.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/hsm_provider'
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None
KEYS = ('ifdVendorID', 'ifdProductID', 'ifdFriendlyName')
DOUBLE = '''
import json
from pathlib import Path
from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        variables = task_vars or {}
        log = Path(variables['fixture_events'])
        action = self._task.action.rsplit('.', 1)[-1]
        args = self._task.args
        event = {'action': action, 'args': args,
                 'become_user': self._play_context.become_user}
        with log.open('a') as stream:
            stream.write(json.dumps(event) + '\\n')
        state_path = log.with_suffix('.state')
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        changed = False
        if action == 'command':
            argv = args.get('argv', [])
            allowed = (
                len(argv) == 4 and argv[1] == '--module' and argv[3] == '--list-token-slots'
            ) or argv in (['opensc-tool', '--list-readers'], ['opensc-tool', '--version'])
            if not allowed:
                return dict(result, failed=True, msg='Forbidden hardware operation in preparation fixture')
            text = ('Slot 0: PicoHSM (uninitialized)\\n  serial num : CANDIDATE123\\n'
                    if '--list-token-slots' in argv else '0: PicoHSM public reader 00 00\\n')
            if '--version' in argv:
                text = 'OpenSC 0.25.1 (test fixture)\\n'
            return dict(result, changed=False, rc=0, stdout=text, stderr='',
                        stdout_lines=text.splitlines(), stderr_lines=[])
        if action == 'package':
            names = args['name'] if isinstance(args['name'], list) else [args['name']]
            for name in names:
                changed |= name not in state.get('packages', [])
            state['packages'] = sorted(set(state.get('packages', []) + names))
        elif action == 'systemd_service':
            name = args['name']
            selected = {key: args[key] for key in ('state', 'enabled') if key in args}
            changed = selected.get('state') == 'restarted' or state.get(name) != selected
            state[name] = selected
        state_path.write_text(json.dumps(state))
        return dict(result, changed=changed)
'''


@unittest.skipUnless(ANSIBLE, 'Requires native Ansible on Linux/WSL')
class NativePicoPreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hsm-prepare-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'ansible.cfg').write_text('[defaults]\n')
        self.role = self.root / 'tier-0/ansible/roles/hsm_provider'
        shutil.copytree(ROLE, self.role)
        for folder in ('tasks', 'handlers'):
            for path in (self.role / folder).glob('*.yml'):
                text = path.read_text()
                for action in ('package', 'systemd_service', 'command'):
                    text = text.replace(f'ansible.builtin.{action}:', f'fixture.hsm.{action}:')
                path.write_text(text)
        for forbidden in ('pcsc', 'yubihsm', 'issuer', 'token'):
            (self.role / f'tasks/{forbidden}.yml').write_text(yaml.safe_dump([{
                'ansible.builtin.fail': {'msg': f'Forbidden {forbidden} task in preparation'},
            }]))
        baseline = self.role.parent / 'baseline/tasks'
        baseline.mkdir(parents=True)
        for task in ('repository_proxy', 'package_sources', 'package_consumer'):
            (baseline / f'{task}.yml').write_text(yaml.safe_dump([{
                'name': f'Fixture native baseline {task}',
                'ansible.builtin.debug': {'msg': task},
            }]))
        collection = self.root / 'collections/ansible_collections/fixture/hsm/plugins'
        for action in ('command', 'package', 'systemd_service'):
            (collection / 'action').mkdir(parents=True, exist_ok=True)
            (collection / 'modules').mkdir(exist_ok=True)
            (collection / f'action/{action}.py').write_text(DOUBLE)
            (collection / f'modules/{action}.py').write_text(
                'from ansible.module_utils.basic import AnsibleModule\n'
                'AnsibleModule(argument_spec={}).fail_json(msg="Action double was not loaded")\n')
        self.library = self.root / 'opensc-pkcs11.so'
        self.library.touch()
        self.plist = self.root / 'Info.plist'
        self.events_path = self.root / 'events.jsonl'
        self.write_plist(['0x1111'], ['0x2222'], ['Existing reader'])
        self.inputs = {
            'ansible_connection': 'local', 'ansible_become': False,
            'ansible_python_interpreter': shutil.which('python3'),
            'ansible_os_family': 'Debian', 'ansible_service_mgr': 'systemd',
            'hsm_provider': 'picohsm', 'hsm_provider_mode': 'usb',
            'hsm_provider_packages': ['opensc'], 'hsm_provider_library': str(self.library),
            'hsm_provider_user': 'openxpki', 'hsm_provider_expected_serial': '',
            'hsm_provider_ccid_plist': str(self.plist),
            'fixture_events': str(self.events_path),
        }

    def write_plist(self, vendors, products, names):
        plist = ET.Element('plist', version='1.0')
        dictionary = ET.SubElement(plist, 'dict')
        ET.SubElement(dictionary, 'key').text = 'ifdLogLevel'
        ET.SubElement(dictionary, 'string').text = '0x0003'
        for key, values in zip(KEYS, (vendors, products, names)):
            ET.SubElement(dictionary, 'key').text = key
            array = ET.SubElement(dictionary, 'array')
            for value in values:
                ET.SubElement(array, 'string').text = value
        self.plist.write_bytes(ET.tostring(plist, encoding='utf-8', xml_declaration=True))
        self.plist.chmod(0o640)

    def mappings(self):
        entries = list(ET.parse(self.plist).getroot().find('dict'))
        return {entries[i].text: [child.text for child in entries[i + 1]]
                for i in range(0, len(entries), 2) if entries[i].text in KEYS}

    def events(self):
        return [json.loads(line) for line in self.events_path.read_text().splitlines()] \
            if self.events_path.exists() else []

    def run_tasks(self, task='prepare', overrides=None, entrypoint=False, inventory=None, syntax=False):
        variables = self.root / 'inputs.json'
        variables.write_text(json.dumps(dict(self.inputs, **(overrides or {}))))
        if entrypoint:
            playbook = self.entrypoint()
        else:
            playbook = self.root / 'playbook.yml'
            playbook.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'gather_facts': False,
                'tasks': [{'ansible.builtin.import_role': {'name': 'hsm_provider', 'tasks_from': task}}],
            }]))
        command = [ANSIBLE, '-i', inventory or 'localhost,', '-c', 'local', str(playbook), '-e', f'@{variables}']
        if syntax:
            command.append('--syntax-check')
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, env=dict(
            os.environ, ANSIBLE_CONFIG=str(self.root / 'ansible.cfg'),
            ANSIBLE_ROLES_PATH=str(self.role.parent), TMPDIR=str(self.root),
            PYTHONPATH=os.environ.get('HSM_PREPARE_TEST_PYTHONPATH', '') + ':' + os.environ.get('PYTHONPATH', ''),
            ANSIBLE_COLLECTIONS_PATH=str(self.root / 'collections') + ':' + os.environ.get('ANSIBLE_COLLECTIONS_PATH', ''),
            ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'),
            ANSIBLE_REMOTE_TEMP=str(self.root / 'ansible-remote'), ANSIBLE_NOCOLOR='1',
        ))
        return result.returncode, result.stdout + result.stderr

    def entrypoint(self):
        recipes = self.root / 'tier-0/ansible/playbooks/deployment'
        recipes.mkdir(parents=True, exist_ok=True)
        target = recipes / 'hsm-prepare.yml'
        shutil.copy2(UPSTREAM / 'tier-0/ansible/playbooks/deployment/hsm-prepare.yml', target)
        (recipes.parent / 'control-node.yml').write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'gather_facts': False,
            'tasks': [{'ansible.builtin.assert': {'that': [
                "control_node_setup == 'hsm'", 'not control_node_require_terraform | bool',
            ]}}],
        }]))
        shared = self.root / 'shared/ansible/playbooks'
        shared.mkdir(parents=True, exist_ok=True)
        shutil.copy2(UPSTREAM / 'shared/ansible/playbooks/guest-ready.yml', shared / 'guest-ready.yml')
        return target

    def assert_public_only(self):
        commands = [event for event in self.events() if event['action'] == 'command']
        self.assertEqual(len(commands), 3, commands)
        self.assertTrue(all(event['become_user'] == 'root' for event in commands), commands)
        self.assertEqual(commands[0]['args']['argv'],
                         ['/usr/bin/pkcs11-tool', '--module', str(self.library), '--list-token-slots'])
        self.assertEqual(commands[1]['args']['argv'], ['opensc-tool', '--list-readers'])
        self.assertEqual(commands[2]['args']['argv'], ['opensc-tool', '--version'])
        services = [event['args']['name'] for event in self.events() if event['action'] == 'systemd_service']
        self.assertTrue(set(services) <= {'pcscd.socket', 'pcscd.service'}, services)

    def test_blank_discovery_registers_native_ccid_once_preserves_rows_and_uses_root(self):
        code, output = self.run_tasks(overrides={
            'baseline_rpm_repositories': [{'id': 'accepted'}], 'repository_proxy_enabled': True,
        })
        self.assertEqual(code, 0, output)
        self.assertIn('Unaccepted candidate', output)
        self.assertIn('CANDIDATE123', output)
        self.assertIn('PicoHSM public reader', output)
        self.assertIn(str(self.library), output)
        self.assertIn('OpenSC 0.25.1', output)
        self.assert_public_only()
        self.assertEqual(self.mappings(), dict(zip(KEYS, (
            ['0x1111', '0x2e8a'], ['0x2222', '0x10fd'], ['Existing reader', 'PicoHSM']))))
        self.assertEqual(ET.parse(self.plist).find('dict/string').text, '0x0003')
        self.assertEqual(self.plist.stat().st_mode & 0o777, 0o640)
        actions = self.events()
        restart = next(i for i, event in enumerate(actions)
                       if event['args'].get('name') == 'pcscd.service')
        first_command = next(i for i, event in enumerate(actions) if event['action'] == 'command')
        self.assertLess(restart, first_command)
        packages = [event['args']['name'] for event in actions if event['action'] == 'package']
        self.assertIn(['pcscd', 'libccid'], packages)
        self.assertIn('python3-lxml', packages)
        self.assertLess(output.index('Fixture native baseline repository_proxy'),
                        output.index('Install approved middleware'))
        self.assertLess(output.index('Fixture native baseline package_sources'),
                        output.index('Install approved middleware'))
        self.assertIn('Fixture native baseline package_consumer', output)
        retained = self.plist.read_bytes()
        self.events_path.unlink()
        code, output = self.run_tasks()
        self.assertEqual(code, 0, output)
        self.assertRegex(output, r'changed=0\s')
        self.assertEqual(retained, self.plist.read_bytes())
        self.assert_public_only()
        self.assertFalse(any(event['args'].get('state') == 'restarted' for event in self.events()))

    def test_existing_official_pair_is_unchanged_and_redhat_transport_is_native(self):
        self.write_plist(['0x2E8A'], ['0x10FD'], ['Retained vendor-friendly name'])
        retained = self.plist.read_bytes()
        code, output = self.run_tasks(overrides={
            'hsm_provider_expected_serial': 'CANDIDATE123', 'ansible_os_family': 'RedHat',
        })
        self.assertEqual(code, 0, output)
        self.assertIn('Recorded token serial matched', output)
        self.assertEqual(retained, self.plist.read_bytes())
        self.assertIn(['pcsc-lite', 'pcsc-lite-ccid'],
                      [event['args']['name'] for event in self.events() if event['action'] == 'package'])
        self.assertFalse(any(event['args'].get('state') == 'restarted' for event in self.events()))
        self.assert_public_only()

    def test_pair_at_different_indices_requires_one_aligned_registration(self):
        self.write_plist(['0x2e8a', '0x1234'], ['0x1234', '0x10fd'], ['Reader one', 'Reader two'])
        code, output = self.run_tasks()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.mappings(), dict(zip(KEYS, (
            ['0x2e8a', '0x1234', '0x2e8a'], ['0x1234', '0x10fd', '0x10fd'],
            ['Reader one', 'Reader two', 'PicoHSM']))))

    def test_empty_aligned_arrays_are_supported(self):
        self.write_plist([], [], [])
        code, output = self.run_tasks()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.mappings(), dict(zip(KEYS, (['0x2e8a'], ['0x10fd'], ['PicoHSM']))))

    def test_wrong_or_partial_recorded_serial_fails(self):
        for serial in ('WRONG', 'CANDIDATE12', 'ANDIDATE123'):
            with self.subTest(serial=serial):
                code, output = self.run_tasks(overrides={'hsm_provider_expected_serial': serial})
                self.assertNotEqual(code, 0, output)
                self.assertIn('The recorded token serial is absent', output)
                self.assertNotIn('Show public commissioning inventory', output)

    def test_normal_preflight_and_inspection_still_require_a_recorded_serial(self):
        for task in ('preflight', 'inspect'):
            with self.subTest(task=task):
                code, output = self.run_tasks(task)
                self.assertNotEqual(code, 0, output)
                self.assertIn('expected token serial' if task == 'preflight' else
                              'independently recorded token serial before listing', output)
                self.assertFalse(self.events(), 'Strict identity rejection must precede package or device access')

    def test_bad_arrays_or_xml_preserve_original_and_prevent_device_access(self):
        for content in ('misaligned', 'duplicate', 'nonstring', 'malformed'):
            with self.subTest(content=content):
                self.write_plist(['0x1111'], ['0x2222'], [] if content == 'misaligned' else ['Existing'])
                if content == 'duplicate':
                    document = ET.parse(self.plist)
                    dictionary = document.getroot().find('dict')
                    ET.SubElement(dictionary, 'key').text = 'ifdVendorID'
                    ET.SubElement(dictionary, 'array')
                    document.write(self.plist)
                elif content == 'nonstring':
                    document = ET.parse(self.plist)
                    ET.SubElement(document.getroot().find('dict/array'), 'integer').text = '1234'
                    document.write(self.plist)
                elif content == 'malformed':
                    self.plist.write_text('<plist><dict>not well formed')
                retained = self.plist.read_bytes()
                code, output = self.run_tasks()
                self.assertNotEqual(code, 0, output)
                if content == 'misaligned':
                    self.assertIn('arrays are misaligned', output)
                elif content in ('duplicate', 'nonstring'):
                    self.assertIn('must contain one array of strings', output)
                else:
                    self.assertIn('Error while parsing document', output)
                self.assertEqual(retained, self.plist.read_bytes())
                self.assertFalse(any(event['action'] == 'command' for event in self.events()))

    def test_staged_edit_failure_does_not_publish_a_partial_mapping(self):
        taskfile = self.role / 'tasks/tools.yml'
        text = taskfile.read_text().replace(
            "- {key: ifdProductID, value: '0x10fd'}",
            "- {key: missingProductArray, value: '0x10fd'}")
        taskfile.write_text(text)
        retained = self.plist.read_bytes()
        code, output = self.run_tasks()
        self.assertNotEqual(code, 0, output)
        self.assertEqual(retained, self.plist.read_bytes())
        self.assertIn("Remove only this operation's temporary reader table", output)
        self.assertFalse(any(event['action'] == 'command' for event in self.events()))
        self.assertFalse(list(self.root.rglob('ansible-picohsm-*.plist')))

    def test_preparation_rejects_other_providers_before_packages_or_device_access(self):
        for overrides in ({'hsm_provider': 'yubihsm2'}, {'hsm_provider_mode': 'client'},
                          {'hsm_provider_packages': []}):
            with self.subTest(inputs=overrides):
                code, output = self.run_tasks(overrides=overrides)
                self.assertNotEqual(code, 0, output)
                self.assertFalse(self.events())

    def test_entrypoint_supports_explicit_localhost_and_default_issuer_group(self):
        for selected in ('localhost', 'all'):
            code, output = self.run_tasks(entrypoint=True, overrides={'hsm_prepare_group': selected})
            self.assertEqual(code, 0, output)
            self.assertIn('Unaccepted candidate', output)
            self.assertNotIn('Fixture native baseline repository_proxy', output)
            self.assert_public_only()
            self.events_path.unlink()
        inventory = self.root / 'hosts.yml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'issuing_ca': {'hosts': {'localhost': {}}},
        }}}))
        code, output = self.run_tasks(entrypoint=True, inventory=str(inventory))
        self.assertEqual(code, 0, output)
        self.assert_public_only()
        self.events_path.unlink()
        code, output = self.run_tasks(entrypoint=True, overrides={'hsm_prepare_group': 'absent_group'})
        self.assertNotEqual(code, 0, output)
        self.assertFalse(self.events())

    def test_actual_entrypoint_and_normal_provider_parse_on_native_ansible(self):
        for name in ('hsm-prepare.yml',):
            result = subprocess.run(
                [ANSIBLE, '-i', 'localhost,', str(UPSTREAM / 'tier-0/ansible/playbooks/deployment' / name),
                 '--syntax-check'], capture_output=True, text=True, timeout=60,
                env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_NOCOLOR='1',
                         ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local')),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        code, output = self.run_tasks('main', syntax=True)
        self.assertEqual(code, 0, output)


if __name__ == '__main__':
    unittest.main()
