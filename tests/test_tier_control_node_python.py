"""Controller Python convergence, with OS acquisition confined to a safe fixture."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import venv
import zipfile

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


PLAYBOOK = Path('ansible/playbooks/control-node.yml')
FILTERS = Path('tasks/control-node-network-filters.yml')
NATIVE = os.name != 'nt' and bool(shutil.which('ansible-playbook'))


class ControlNodePythonContract(TierRepositoryTestCase):
    def test_generated_final_include_checks_selected_filters_even_when_no_collections_are_missing(self):
        self.generate('--repo', 'shared')
        for owner in (UPSTREAM / 'shared', self.root / 'verify-shared'):
            play = yaml.safe_load((owner / PLAYBOOK).read_text())[0]
            include = play['tasks'][-1]
            self.assertEqual(include['ansible.builtin.include_tasks'], str(FILTERS).replace('\\', '/'))
            self.assertEqual(include['vars'], dict(
                ansible_python_interpreter='{{ ansible_playbook_python }}',
                control_node_network_filter_requirement='netaddr>=0.10.1'))
            self.assertIn('control_node_required_collections', include['when'])
            self.assertIn("'ansible.utils'", include['when'])
            self.assertNotIn('missing', include['when'])
            self.assertEqual((owner / PLAYBOOK.parent / FILTERS).read_bytes(),
                             (UPSTREAM / 'shared' / PLAYBOOK.parent / FILTERS).read_bytes())


@unittest.skipUnless(NATIVE, 'Requires Linux Ansible, prepared community.general/ansible.utils and netaddr')
class ControlNodePythonNative(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.generate('--repo', 'shared')
        self.work = Path(self.temp.name) / 'python-probe'
        self.work.mkdir()
        self.play = yaml.safe_load((self.root / 'verify-shared' / PLAYBOOK).read_text())[0]
        self.filters = yaml.safe_load((UPSTREAM / 'shared' / PLAYBOOK.parent / FILTERS).read_text())
        self.launcher = Path(shutil.which('ansible-playbook'))
        interpreter = self.launcher.read_text().splitlines()[0][2:]
        probe = subprocess.run([interpreter, '-c',
            'import importlib.util as u, importlib.metadata as m, json; '
            'names="ansible jinja2 yaml markupsafe packaging resolvelib cryptography cffi _cffi_backend netaddr"; '
            'print(json.dumps(dict(paths={n: (list(s.submodule_search_locations)[0] '
            'if s.submodule_search_locations else s.origin) for n in names.split() '
            'if (s := u.find_spec(n))}, metadata=[str(m.distribution(n)._path) '
            'for n in ("ansible-core", "jinja2")], version=m.version("netaddr"))))'],
            capture_output=True, text=True, check=True, timeout=15)
        prepared = json.loads(probe.stdout)
        self.runtime = self.work / 'runtime'
        self.runtime.mkdir()
        for name, path in prepared['paths'].items():
            if name != 'netaddr':
                source = Path(path)
                (self.runtime / (name if source.is_dir() else source.name)).symlink_to(source)
        for path in prepared['metadata']:
            (self.runtime / Path(path).name).symlink_to(path)
        self.netaddr = Path(prepared['paths']['netaddr'])
        self.venv = self.work / 'venv'
        venv.EnvBuilder(with_pip=True).create(self.venv)
        self.python = self.venv / 'bin/python'
        wheel = self.work / f'netaddr-{prepared["version"]}-py3-none-any.whl'
        with zipfile.ZipFile(wheel, 'w') as archive:
            for path in self.netaddr.rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    archive.write(path, str(Path('netaddr') / path.relative_to(self.netaddr)))
            metadata = f'netaddr-{prepared["version"]}.dist-info'
            archive.writestr(f'{metadata}/METADATA',
                             f'Metadata-Version: 2.1\nName: netaddr\nVersion: {prepared["version"]}\n')
            archive.writestr(f'{metadata}/WHEEL', 'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
            archive.writestr(f'{metadata}/RECORD', ''.join(f'{name},,\n' for name in archive.namelist()))
        self.marker = self.work / 'package-installed'
        library = self.work / 'library'
        library.mkdir()
        # These module fixtures replace every OS write before any extracted task can run.
        (library / 'regression_package.py').write_text(
            'import os\nfrom pathlib import Path\nfrom ansible.module_utils.basic import AnsibleModule\n'
            'm = AnsibleModule(argument_spec=dict(name=dict(type="str"), state=dict(type="str")))\n'
            'assert m.params == dict(name="python3-netaddr", state="present")\n'
            'if os.environ["PROBE_SYSTEM"] != "1" or os.environ.get("PROBE_FAIL"):\n'
            '    m.fail_json(msg="Fixture package acquisition refused")\n'
            'p = Path(os.environ["PROBE_MARKER"])\nchanged = not p.exists()\n'
            'p.write_text("python3-netaddr")\nm.exit_json(changed=changed)\n')
        (library / 'regression_info.py').write_text(
            'import os, sys\nfrom pathlib import Path\nfrom ansible.module_utils.basic import AnsibleModule\n'
            'm = AnsibleModule(argument_spec=dict(dependencies=dict(type="list", elements="str")))\n'
            'assert m.params["dependencies"] == ["netaddr>=0.10.1"]\n'
            'm.exit_json(changed=False, python=sys.executable, mismatched={}, '
            'not_found=[] if Path(os.environ["PROBE_MARKER"]).exists() else ["netaddr"])\n')
        (library / 'regression_forbidden.py').write_text(
            'from ansible.module_utils.basic import AnsibleModule\n'
            'AnsibleModule(argument_spec=dict(name=dict(type="str"), virtualenv=dict(type="str")))'
            '.fail_json(msg="Unexpected pip acquisition")\n')
        self.env = dict(os.environ, PYTHONPATH=str(self.runtime), PYTHONNOUSERSITE='1',
                        PYTHONDONTWRITEBYTECODE='1', ANSIBLE_NOCOLOR='1', ANSIBLE_LIBRARY=str(library),
                        PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1', PIP_FIND_LINKS=str(self.work),
                        PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_CACHE_DIR='1',
                        PROBE_MARKER=str(self.marker), PROBE_SYSTEM='0')

    def run_precheck(self, mode='auto', family='Debian', selected=None, system=False, fail=False):
        tasks = deepcopy(self.filters)
        for task in tasks:
            for child in task.get('block', []):
                if 'ansible.builtin.package' in child:
                    child['regression_package'] = child.pop('ansible.builtin.package')
                    child['become'] = False
                if system and 'ansible.builtin.pip' in child:
                    child['regression_forbidden'] = child.pop('ansible.builtin.pip')
            if system and 'community.general.python_requirements_info' in task:
                task['regression_info'] = task.pop('community.general.python_requirements_info')
        for task in tasks + [child for task in tasks for child in task.get('block', [])]:
            self.assertNotIn('ansible.builtin.package', task, 'OS acquisition must stay intercepted')
            if system:
                self.assertNotIn('ansible.builtin.pip', task, 'System Python must never invoke pip')
        taskfile = self.work / 'filters.yml'
        taskfile.write_text(yaml.safe_dump(tasks, sort_keys=False))
        names = ['Resolve required collections for selected setup', 'Check required Ansible collections',
                 'Track missing Ansible collections', 'Build OS package list for missing Ansible collections']
        prefix = [deepcopy(next(t for t in self.play['tasks'] if t['name'] == name)) for name in names]
        prefix.append({'ansible.builtin.assert': {'that': [
            'control_node_missing_collections | length == 0', 'control_node_collection_packages | length == 0']}})
        include = deepcopy(self.play['tasks'][-1])
        include['ansible.builtin.include_tasks'] = str(taskfile)
        verify_interpreter = {'ansible.builtin.assert': {'that': [
            'control_node_network_filter_python_final.python == ansible_playbook_python']},
            'when': include['when']}
        variables = dict(self.play['vars'], control_node_selected_setup='probe',
                         control_node_setup_collection_names=dict(
                             probe=['ansible.utils'] if selected is None else selected),
                         control_node_collections_mode=mode, ansible_os_family=family,
                         ansible_python_interpreter=sys.executable)
        path = self.work / 'play.yml'
        path.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=variables, tasks=prefix + [include, verify_interpreter])],
                                      sort_keys=False))
        env = dict(self.env, PROBE_SYSTEM=str(int(system)), PROBE_FAIL='1' if fail else '')
        if system and not (self.runtime / 'netaddr').exists():
            (self.runtime / 'netaddr').symlink_to(self.netaddr)
        python = str(Path(sys.executable).resolve()) if system else str(self.python)
        result = subprocess.run([python, str(self.launcher),
                                 '-i', 'localhost,', str(path)], cwd=self.work, env=env,
                                capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout + result.stderr

    def test_system_package_branches_converge_and_package_failures_remain_fatal(self):
        for family in ('Debian', 'RedHat'):
            with self.subTest(family=family):
                self.marker.unlink(missing_ok=True)
                status, output = self.run_precheck(system=True, family=family, fail=True)
                self.assertNotEqual(status, 0, output)
                self.assertIn('Fixture package acquisition refused', output)
                self.assertNotIn('TASK [Recheck network-filter dependencies', output)
                self.assertFalse(self.marker.exists())
                for changed in (1, 0):
                    status, output = self.run_precheck(system=True, family=family)
                    self.assertEqual(status, 0, output)
                    self.assertIn(f'changed={changed}', output)
                self.assertEqual(self.marker.read_text(), 'python3-netaddr')

    def test_isolated_venv_installs_prepared_wheel_once_and_runs_real_ipaddr(self):
        for changed in (1, 0):
            status, output = self.run_precheck()
            self.assertEqual(status, 0, output)
            self.assertIn(f'changed={changed}', output)
            self.assertIn('Verify the controller can run the declared network filter', output)
        status, output = self.run_precheck(mode='check')
        self.assertEqual(status, 0, output)
        self.assertIn('changed=0', output)
        self.assertFalse(self.marker.exists())

    def test_check_mode_rejects_missing_library_without_dependency_writes(self):
        before = {p.relative_to(self.venv): p.stat().st_mtime_ns for p in self.venv.rglob('*') if p.is_file()}
        status, output = self.run_precheck(mode='check')
        self.assertNotEqual(status, 0, output)
        self.assertIn('Collection check mode never installs Python dependencies', output)
        self.assertFalse(self.marker.exists())
        self.assertEqual(before, {p.relative_to(self.venv): p.stat().st_mtime_ns
                                  for p in self.venv.rglob('*') if p.is_file()})

    def test_unrelated_empty_and_nonempty_setups_skip_python_preparation(self):
        for selected in ([], ['community.general']):
            with self.subTest(selected=selected):
                status, output = self.run_precheck(selected=selected)
                self.assertEqual(status, 0, output)
                self.assertIn('changed=0', output)
                self.assertNotIn('TASK [Inspect network-filter dependencies', output)
                self.assertFalse(self.marker.exists())
