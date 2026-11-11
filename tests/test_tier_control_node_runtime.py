"""Direct deployment prechecks and safe native controller dependency convergence."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
import venv

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


SHARED = UPSTREAM / 'shared/ansible/playbooks'
PLAY = yaml.safe_load((SHARED / 'control-node.yml').read_text())[0]
PYTHON = SHARED / 'tasks/control-node-python.yml'
LAUNCHER = shutil.which(os.getenv('ANSIBLE_PLAYBOOK', 'ansible-playbook'))
NATIVE = os.name != 'nt' and bool(LAUNCHER)


class DirectControllerContract(TierRepositoryTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='controller-generated-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'

    def test_source_and_generated_direct_local_plays_start_with_the_selected_precheck(self):
        self.generate('--repo', 'shared', '--repo', 'tier-0', '--repo', 'tier-1', '--repo', 'tier-2')
        for collection, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            shared = collection / f'{prefix}shared/ansible/playbooks'
            self.assertEqual((shared / 'tasks/control-node-python.yml').read_bytes(), PYTHON.read_bytes())
            for tier in ('tier-0', 'tier-1', 'tier-2'):
                playbooks = collection / f'{prefix}{tier}/ansible/playbooks'
                settings = yaml.safe_load((playbooks / 'control-node.yml').read_text())[0]['vars']
                for path in (playbooks / 'deployment').glob('*.yml'):
                    if path.stem.startswith('hsm-') or path.stem in ('source-control-vm', 'telemetry-hosts'):
                        continue
                    plays = yaml.safe_load(path.read_text())
                    if not any(p.get('hosts') == 'localhost' for p in plays):
                        continue
                    self.assertEqual(plays[0].get('ansible.builtin.import_playbook'),
                                     '../control-node.yml', str(path))
                    selected = plays[0]['vars']['control_node_setup']
                    self.assertIn(selected, settings['control_node_setup_collection_names'], str(path))
                    self.assertFalse(plays[0]['vars']['control_node_require_terraform'], str(path))
        tier0 = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/control-node.yml').read_text())[0]['vars']
        for setup in ('vault-configure', 'vault-seal'):
            self.assertEqual(tier0['control_node_setup_collection_names'][setup],
                             ['community.hashi_vault', 'community.general'])
        tier2 = yaml.safe_load((UPSTREAM / 'tier-2/ansible/playbooks/control-node.yml').read_text())[0]['vars']
        self.assertNotIn('lab-environment', tier2['control_node_setup_tool_commands'])


@unittest.skipUnless(NATIVE, 'Requires Linux Ansible and prepared community.general')
class NativeControllerRuntime(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='controller-runtime-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.launcher = Path(LAUNCHER)
        interpreter = shlex.split(self.launcher.read_text().splitlines()[0][2:])
        probe = subprocess.run([*interpreter, '-c',
            'import ansible, importlib.util as u, importlib.metadata as m, json, sys; '
            'names="ansible jinja2 yaml markupsafe packaging resolvelib cryptography cffi _cffi_backend '
            'pycparser setuptools pkg_resources _distutils_hack"; '
            'wanted={"ansible-core","jinja2","pyyaml","markupsafe","packaging","resolvelib",'
            '"cryptography","cffi","pycparser","setuptools"}; '
            'print(json.dumps(dict(core=ansible.__version__, base_python=sys._base_executable, '
            'paths={n: (list(s.submodule_search_locations)[0] if s.submodule_search_locations else s.origin) '
            'for n in names.split() if (s := u.find_spec(n))}, '
            'metadata=[str(d._path) for d in m.distributions() '
            'if d.metadata["Name"].lower().replace("_","-") in wanted])))'],
            capture_output=True, text=True, check=True, timeout=15)
        self.runtime = json.loads(probe.stdout)
        # Reuse only this launcher's engine and dependencies in disposable interpreters.
        # Kubernetes/Vault clients stay absent until the precheck installs prepared wheels.
        self.engine = self.root / 'engine'
        self.engine.mkdir()
        for name, path in self.runtime['paths'].items():
            source = Path(path)
            (self.engine / (name if source.is_dir() else source.name)).symlink_to(source)
        for path in self.runtime['metadata']:
            destination = self.engine / Path(path).name
            if not destination.exists():
                destination.symlink_to(path)
        self.env = dict(os.environ, ANSIBLE_NOCOLOR='1', PYTHONDONTWRITEBYTECODE='1',
                        PIP_NO_INDEX='1', PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK='1',
                        PIP_NO_CACHE_DIR='1', http_proxy='http://127.0.0.1:9',
                        https_proxy='http://127.0.0.1:9', no_proxy='localhost,127.0.0.1')
        self.env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(self.engine), self.env.get('PYTHONPATH')]))
        self.marker = self.root / 'deployment-changed'

    def run_python(self, selected, mode='check', python=None, dry_run=False, tasks=None, family='Debian'):
        include = next(t for t in PLAY['tasks'] if t['name'] ==
                       'Prepare controller Python clients for selected collections')
        include = deepcopy(include)
        include['ansible.builtin.include_tasks'] = str(tasks or PYTHON)
        variables = dict(control_node_required_collections=[dict(name=n) for n in selected],
                         control_node_collections_mode=mode, ansible_os_family=family,
                         ansible_python_interpreter='/deliberately/wrong/module/python')
        sentinel = {'ansible.builtin.copy': dict(dest=str(self.marker), content='changed'),
                    'vars': dict(ansible_python_interpreter='{{ ansible_playbook_python }}')}
        play = [dict(hosts='localhost', connection='local', gather_facts=False, vars=variables,
                     tasks=[include, sentinel])]
        return self.run_play(play, python, dry_run)

    def run_play(self, play, python=None, dry_run=False):
        path = self.root / 'play.yml'
        for item in play:
            item.setdefault('pre_tasks', []).insert(0, {'ansible.builtin.assert': {
                'that': 'ansible_version.full == expected_core',
            }, 'vars': dict(expected_core=self.runtime['core'])})
        path.write_text(yaml.safe_dump(play, sort_keys=False))
        command = ([str(python)] if python else []) + [str(self.launcher), '-i', 'localhost,', str(path)]
        if dry_run:
            command.append('--check')
        result = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout + result.stderr

    def test_dependency_check_and_ansible_check_refuse_missing_clients_before_deployment(self):
        # An absent local distribution makes this deterministic even on a fully prepared controller.
        tasks = yaml.safe_load(PYTHON.read_text())
        tasks[0]['vars']['control_node_python_catalog'][1]['requirements'] = ['homelab-missing-client>=1.0']
        fixture = self.root / 'missing.yml'
        fixture.write_text(yaml.safe_dump(tasks, sort_keys=False))
        for mode, dry_run in (('check', False), ('auto', True)):
            with self.subTest(mode=mode, dry_run=dry_run):
                status, output = self.run_python(['community.hashi_vault'], mode, dry_run=dry_run, tasks=fixture)
                self.assertNotEqual(status, 0, output)
                self.assertIn('Dependency check mode never installs Python libraries', output)
                self.assertNotIn('TASK [Install controller clients', output)
                self.assertFalse(self.marker.exists())

    def test_prepared_crypto_checks_real_imports_in_ansibles_interpreter(self):
        status, output = self.run_python(['community.crypto'], dry_run=True)
        self.assertEqual(status, 0, output)
        self.assertIn('Verify selected Python clients really import before deployment', output)
        self.assertIn('changed=1', output)  # Only the final disposable deployment task predicts a change.
        self.assertFalse(self.marker.exists())

    def test_broken_import_fails_even_with_satisfied_distribution_metadata(self):
        tasks = yaml.safe_load(PYTHON.read_text())
        tasks[0]['vars']['control_node_python_catalog'][2]['imports'] = ['homelab_broken_crypto_import']
        fixture = self.root / 'broken-import.yml'
        fixture.write_text(yaml.safe_dump(tasks, sort_keys=False))
        status, output = self.run_python(['community.crypto'], tasks=fixture)
        self.assertNotEqual(status, 0, output)
        self.assertIn('cannot import homelab_broken_crypto_import', output)
        self.assertFalse(self.marker.exists())

    def test_native_tool_failure_stops_before_changes_even_in_ansible_check(self):
        names = ['Check selected native deployment tools without acquiring binaries',
                 'Require approved native tools before deployment changes']
        tasks = [deepcopy(next(t for t in PLAY['tasks'] if t['name'] == name)) for name in names]
        variables = dict(ansible_python_interpreter='{{ ansible_playbook_python }}', control_node_selected_setup='probe',
                         control_node_setup_tool_commands=dict(probe=[['/missing-approved-helm', 'version']]))
        status, output = self.run_play([dict(hosts='localhost', connection='local', gather_facts=False,
                                            vars=variables, tasks=tasks)], dry_run=True)
        self.assertNotEqual(status, 0, output)
        self.assertIn('Prepare this tool through the approved bootstrap', output)
        self.assertIn('changed=0', output)

    def test_direct_import_checks_missing_collections_before_loading_the_role(self):
        shared = self.root / 'shared/ansible/playbooks'
        deployment = self.root / 'tier-0/ansible/playbooks/deployment'
        shared.mkdir(parents=True)
        deployment.mkdir(parents=True)
        names = ['Validate selected setup precheck mapping', 'Resolve required collections for selected setup',
                 'Check required Ansible collections', 'Track missing Ansible collections',
                 'Require preinstalled collections in check mode']
        play = deepcopy(PLAY)
        play['tasks'] = [t for name in names for t in play['tasks'] if t['name'] == name]
        (shared / 'control-node.yml').write_text(yaml.safe_dump([play], sort_keys=False))
        for relative in ('control-node.yml', 'deployment/cluster-platform.yml'):
            shutil.copyfile(UPSTREAM / 'tier-0/ansible/playbooks' / relative, deployment.parent / relative)
        role = deployment.parent.parent / 'roles/cluster_platform/tasks'
        role.mkdir(parents=True)
        (role / 'main.yml').write_text('- absent.collection.module: {}\n')
        tools = self.root / 'bin'
        tools.mkdir()
        galaxy = tools / 'ansible-galaxy'
        galaxy.write_text('#!/bin/sh\nexit 0\n')
        galaxy.chmod(0o755)
        self.env.update(PATH=f'{tools}:{self.env["PATH"]}', CONTROL_NODE_COLLECTIONS_MODE='check',
                        ANSIBLE_ROLES_PATH=str(role.parents[1]))
        result = subprocess.run([str(self.launcher), '-i', 'localhost,',
                                 str(deployment / 'cluster-platform.yml'), '--check'],
                                env=self.env, cwd=self.root, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing collections:', result.stdout + result.stderr)
        self.assertNotIn('couldn\'t resolve module', result.stdout + result.stderr)

    def test_system_package_branches_never_use_pip(self):
        library = self.root / 'library'
        library.mkdir()
        installed = self.root / 'native-package-installed'
        (library / 'probe_info.py').write_text(
            'import os\nfrom pathlib import Path\nfrom ansible.module_utils.basic import AnsibleModule\n'
            'm=AnsibleModule(argument_spec=dict(dependencies=dict(type="list",elements="str")))\n'
            'if os.environ.get("PROBE_METADATA_MISSING") == "1" and not '
            'Path(os.environ["PROBE_INSTALLED"]).exists():\n'
            '    m.fail_json(msg="Metadata provider unavailable")\n'
            'm.exit_json(changed=False,mismatched={},not_found=[] if '
            'Path(os.environ["PROBE_INSTALLED"]).exists() else ["cryptography"])\n')
        (library / 'probe_package.py').write_text(
            'import os\nfrom pathlib import Path\nfrom ansible.module_utils.basic import AnsibleModule\n'
            'm=AnsibleModule(argument_spec=dict(name=dict(type="list"),state=dict(type="str")))\n'
            'expected={"python3-cryptography"}\n'
            'if os.environ.get("PROBE_METADATA_MISSING") == "1": expected.add("python3-setuptools")\n'
            'assert set(m.params["name"]) == expected\n'
            'Path(os.environ["PROBE_INSTALLED"]).touch()\nm.exit_json(changed=True)\n')
        tasks = yaml.safe_load(PYTHON.read_text())
        for task in tasks[0]['block']:
            if 'community.general.python_requirements_info' in task:
                task['probe_info'] = task.pop('community.general.python_requirements_info')
            for child in task.get('block', []):
                if 'ansible.builtin.package' in child:
                    child['probe_package'] = child.pop('ansible.builtin.package')
                    child['become'] = False
                if 'ansible.builtin.pip' in child:
                    child['ansible.builtin.fail'] = dict(msg='System Python must never use pip')
                    del child['ansible.builtin.pip']
        fixture = self.root / 'native-packages.yml'
        fixture.write_text(yaml.safe_dump(tasks, sort_keys=False))
        self.env.update(ANSIBLE_LIBRARY=str(library), PROBE_INSTALLED=str(installed))
        for family in ('Debian', 'RedHat'):
            for metadata_missing in ('0', '1'):
                installed.unlink(missing_ok=True)
                self.env['PROBE_METADATA_MISSING'] = metadata_missing
                status, output = self.run_python(['community.crypto'], 'auto',
                                                 python=self.runtime['base_python'], tasks=fixture, family=family)
                self.assertEqual(status, 0, output)
                self.assertTrue(installed.exists())

    @unittest.skipUnless(os.getenv('CONTROL_NODE_TEST_WHEELHOUSE'), 'Requires prepared local controller wheels')
    def test_existing_venv_converges_offline_and_pip_inherits_proxy(self):
        runtime = self.root / 'venv'
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(runtime)
        python = runtime / 'bin/python'
        hook = self.root / 'hook'
        hook.mkdir()
        proxy_record = self.root / 'pip-environment.json'
        (hook / 'sitecustomize.py').write_text(
            'import json,os,sys\nfrom pathlib import Path\n'
            'if Path(sys.argv[0]).name.startswith("pip"):\n'
            '    Path(os.environ["PROBE_PROXY_RECORD"]).write_text(json.dumps(dict('
            'prefix=sys.prefix,http_proxy=os.getenv("http_proxy"),https_proxy=os.getenv("https_proxy"))))\n')
        self.env.update(PIP_FIND_LINKS=os.environ['CONTROL_NODE_TEST_WHEELHOUSE'],
                        PYTHONPATH=os.pathsep.join([str(hook), str(self.engine)]),
                        PROBE_PROXY_RECORD=str(proxy_record), VIRTUAL_ENV='/not-the-active-venv')
        for mode in ('auto', 'auto', 'check'):
            prepared = self.marker.exists()
            status, output = self.run_python(['kubernetes.core', 'community.hashi_vault'], mode, python)
            self.assertEqual(status, 0, output)
            if prepared:
                self.assertIn('changed=0', output)
            self.assertTrue(self.marker.exists())
        record = json.loads(proxy_record.read_text())
        self.assertEqual(record, dict(prefix=str(runtime), http_proxy=self.env['http_proxy'],
                                      https_proxy=self.env['https_proxy']))
        result = subprocess.run([str(python), '-c', 'import kubernetes,jsonpatch,yaml,hvac'],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
