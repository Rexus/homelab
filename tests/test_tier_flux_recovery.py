"""Independent native-Git recovery checks and Ansible API simulations, without live infrastructure."""

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-1/ansible/roles/platform_recovery'
sys.path.insert(0, str(ROOT / 'tier-1/scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load('flux_recovery_run', ROOT / 'tier-1/scripts/flux_recovery_run.py')
PACKAGE = load('native_recovery_package', ROOT / 'tier-1/scripts/flux-recovery.py')
sys.modules['flux_recovery_run'] = RUNNER
PAYLOAD = load('recovery_payload', ROOT / 'tier-1/scripts/recovery_payload.py')
FENCE = load('spinnaker_recovery_fence', ROLE / 'files/spinnaker_fence.py')
VERIFY = load('recovery_verify_product', ROLE / 'files/verify_product.py')
TALOS = load('recovery_talos', ROOT / 'tier-1/scripts/recovery_talos.py')
sys.modules['recovery_talos'] = TALOS


class RecoveryInputs(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='native-recovery-')))
        self.plan = {'version': 1, 'scope': 'tier1', 'recovery_id': 'restore-2026-01',
            'package': {'directory': str(self.root / 'package'), 'manifest_sha256': 'a' * 64,
                'artifact_lock_sha256': 'b' * 64,
                'sources': {name: 'c' * 40 for name in ('platform', 'tier1-platform', 'tier1-applications')}},
            'automation': {}, 'inventory': 'tier-1/ansible/inventory/recovery.yml',
            'recovery_git_inputs': 'tier-1/secrets/recovery-git.yml',
            'artifact_supply': [{'kind': 'oci', 'path': 'pinned-image.tar', 'digest': 'd' * 64,
                'destination': 'independent.test/recovery-image', 'auth_file': 'tier-1/secrets/supply-auth.json'}],
            'virtual_machines': [{'tier': 1, 'node': 'pve01', 'vmid': 1301,
                'backup': 'backup:backup/vzdump-qemu-1301-2026_01_01-00_00_00.vma.zst',
                'backup_config_sha256': 'd' * 64, 'storage': 'local-zfs', 'recovery_bridge': 'vmbr9',
                'network': {'net0': 'virtio=02:00:00:00:00:01,bridge=vmbr9,firewall=1'},
                'role': 'prerequisite', 'health_checks': [{'kind': 'tcp', 'host': '192.0.2.30', 'port': 443}]}],
            'clusters': [{'tier': 1, 'kubeconfig': 'tier-1/secrets/talos/kubeconfig', 'mode': 'clean',
                'context': 'recovery', 'api_server': 'https://192.0.2.1:6443', 'previous_namespace_uid': 'old-cluster-uid',
                'canary_sha256': 'a' * 64,
                'bootstrap_inputs': 'tier-1/secrets/bootstrap.yml', 'recovery_bridge': 'vmbr9',
                'provider_environment': 'tier-1/secrets/provider.env', 'restore_resources': 'tier-1/secrets/resources.yml',
                'restore_engines': 'tier-1/secrets/engines.yml',
                'restore_engine_health': [{'name': 'velero', 'namespace': 'velero'}],
                'bootstrap_images': ['independent.test/bootstrap@sha256:' + 'd' * 64],
                'nodes': [{'name': 'cp-1', 'node': 'pve01', 'vmid': 1101}]}],
            'products': [{'kind': 'harbor', 'name': 'harbor', 'namespace': 'harbor',
                'data_claims': ['harbor-data'],
                'namespace_uid': 'harbor-uid', 'backup_id': 'retained-harbor', 'backup_uid': 'backup-uid',
                'secrets_file': 'tier-1/secrets/product.yml', 'backup_spec_sha256': 'e' * 64,
                'writers': [{'kind': 'Deployment', 'name': 'harbor-core'}],
                'python_image': 'registry.test/python@sha256:' + 'e' * 64,
                'verification_ca_secret': 'recovery-ca', 'verification_headers_secret': 'recovery-auth',
                'checks': [{'url': 'https://registry.test/retained', 'status': 200, 'content_sha256': 'f' * 64},
                           {'url': 'https://registry.test/denied', 'status': 403}]}]}
        for name in ('tier-1', 'shared'):
            directory = self.root / name
            directory.mkdir()
            self.git(directory, 'init', '--quiet')
            (directory / 'tracked.yml').write_text('accepted: true\n')
            self.git(directory, 'add', '.')
            self.git(directory, '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                     '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'fixture')
            source = {'directory': str(directory), 'commit': self.git(directory, 'rev-parse', 'HEAD'),
                      'private_files': []}
            paths = ['ansible/inventory/recovery.yml', 'secrets/recovery-git.yml', 'secrets/kubeconfig',
                     'secrets/bootstrap.yml', 'secrets/product.yml', 'secrets/provider.env',
                     'secrets/resources.yml', 'secrets/engines.yml', 'secrets/supply-auth.json',
                     'secrets/source-identity', 'secrets/source-known-hosts', 'secrets/source.yml',
                     '.terraform/state/talos/terraform.tfstate',
                     '.terraform/state/cluster/prod/terraform.tfstate'] if name == 'tier-1' else []
            for path in paths:
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('retained-private-input\n')
                if path == 'secrets/bootstrap.yml':
                    target.write_text(yaml.safe_dump({'cluster_platform_action': 'apply',
                        'cluster_platform_flux_recovery': True, 'cluster_platform_flux_applications_suspended': True,
                        'cluster_platform_flux_commit': 'c' * 40, 'cluster_platform_flux_platform_commit': 'c' * 40}))
                if path == 'secrets/resources.yml':
                    target.write_text('apiVersion: v1\nkind: Namespace\nmetadata: {name: harbor}\n')
                if path == 'secrets/engines.yml':
                    target.write_text(yaml.safe_dump({'apiVersion': 'apps/v1', 'kind': 'Deployment',
                        'metadata': {'name': 'velero', 'namespace': 'velero'},
                        'spec': {'template': {'spec': {'containers': [{'name': 'velero', 'image': 'retained@sha256:' + 'e' * 64}]}}}}))
                if path == '.terraform/state/talos/terraform.tfstate':
                    target.write_text(json.dumps({'version': 4, 'resources': [
                        {'type': 'talos_machine_secrets', 'name': 'cluster', 'instances': [{'attributes': {
                            'machine_secrets': {'original': 'retained'}, 'client_configuration': {'original': 'retained'}}}]}]}))
                source['private_files'].append({'path': path, 'sha256': RUNNER.checksum(target)})
            self.plan['automation'][name] = source
        self.path = self.root / 'plan.json'

    @staticmethod
    def git(path, *arguments):
        return subprocess.run(['git', '-C', str(path), *arguments], check=True,
                              capture_output=True, text=True).stdout.strip()

    def accepted(self):
        self.path.write_text(json.dumps(self.plan))
        return self.path, RUNNER.checksum(self.path)

    def retained_yaml(self, relative, documents):
        target = self.root / 'tier-1' / relative
        target.write_text(yaml.safe_dump_all(documents))
        for entry in self.plan['automation']['tier-1']['private_files']:
            if entry['path'] == relative:
                entry['sha256'] = RUNNER.checksum(target)

    def test_accepts_exact_independent_sources_and_original_state(self):
        path, digest = self.accepted()
        self.assertEqual(RUNNER.read_plan(path, digest)['scope'], 'tier1')
        source = self.plan['automation']['tier-1']
        original = Path(source['directory']) / '.terraform/state/cluster/prod/terraform.tfstate'
        before = original.read_bytes()
        target = self.root / 'recovered'
        RUNNER.stage_repository(source, target)
        RUNNER.stage_repository(source, target)
        self.assertEqual(original.read_bytes(), before)
        self.assertEqual((target / '.terraform/state/cluster/prod/terraform.tfstate').read_bytes(), before)

    def test_gitlab_requires_retained_api_authority_and_fenced_background_workers(self):
        product = self.plan['products'][0]
        product.update(kind='gitlab', image='retained@sha256:' + 'a' * 64, toolbox='gitlab-toolbox',
                       edition='ce', writers=[{'kind': 'Deployment', 'name': 'gitlab-sidekiq'}])
        product.pop('data_claims')
        source = self.plan['automation']['tier-1']
        checksums = {}
        for name in ('gitlab-ca.pem', 'gitlab-admin.json'):
            relative = 'secrets/' + name
            target = Path(source['directory']) / relative
            target.write_text('retained independent native API input')
            source['private_files'].append({'path': relative, 'sha256': RUNNER.checksum(target)})
            checksums[name] = RUNNER.checksum(target)
        native = product['gitlab_recovery'] = {
            'api_url': 'https://git.internal.example.com',
            'ca_file': 'tier-1/secrets/gitlab-ca.pem', 'ca_sha256': checksums['gitlab-ca.pem'],
            'admin_headers_file': 'tier-1/secrets/gitlab-admin.json',
            'admin_headers_sha256': checksums['gitlab-admin.json'],
            'sidekiq_workloads': [{'kind': 'Deployment', 'name': 'gitlab-sidekiq'}]}
        RUNNER.read_plan(*self.accepted())
        for field, value in [('api_url', 'http://git.internal.example.com'),
                             ('ca_sha256', 'b' * 64), ('admin_headers_file', 'tier-1/secrets/missing'),
                             ('sidekiq_workloads', []),
                             ('sidekiq_workloads', [{'kind': 'Deployment', 'name': 'other'}])]:
            original = native[field]
            native[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                RUNNER.read_plan(*self.accepted())
            native[field] = original
        product['verification_workloads'] = [{'kind': 'Deployment', 'name': 'gitlab-sidekiq', 'replicas': 1}]
        with self.assertRaisesRegex(ValueError, 'outside normal verification'):
            RUNNER.read_plan(*self.accepted())

    def test_rejects_wrong_plan_revision_private_input_and_changed_working_copy(self):
        path, digest = self.accepted()
        with self.assertRaises(ValueError):
            RUNNER.read_plan(path, '0' * 64)
        self.plan['automation']['tier-1']['commit'] = '0' * 40
        path, digest = self.accepted()
        with self.assertRaises(ValueError):
            RUNNER.read_plan(path, digest)
        source = self.plan['automation']['shared']
        staged = self.root / 'staged'
        RUNNER.stage_repository(source, staged)
        (staged / 'tracked.yml').write_text('unexpected: mutation\n')
        with self.assertRaises(ValueError):
            RUNNER.stage_repository(source, staged)

    def test_staging_rechecks_original_private_bytes_after_plan_acceptance(self):
        RUNNER.read_plan(*self.accepted())
        source = self.plan['automation']['tier-1']
        entry = source['private_files'][0]
        (Path(source['directory']) / entry['path']).write_bytes(b'changed after acceptance')
        target = self.root / 'staged'
        with self.assertRaisesRegex(ValueError, 'changed before staging'):
            RUNNER.stage_repository(source, target)
        self.assertFalse((target / entry['path']).exists())

    @unittest.skipUnless(os.name == 'posix', 'Native symlink confinement uses POSIX links')
    def test_staging_refuses_linked_files_and_parent_directories(self):
        source = self.plan['automation']['tier-1']
        outside = self.root / 'outside'
        outside.mkdir()
        retained = outside / 'tracked.yml'
        retained.write_text('accepted: true\n')
        for relative in ('tracked.yml', 'secrets'):
            with self.subTest(relative=relative):
                target = self.root / ('staged-' + relative.replace('.', '-'))
                target.mkdir()
                (target / relative).symlink_to(retained if relative == 'tracked.yml' else outside,
                                               target_is_directory=relative == 'secrets')
                with self.assertRaisesRegex(ValueError, 'linked'):
                    RUNNER.stage_repository(source, target)
                self.assertEqual(retained.read_text(), 'accepted: true\n')
                self.assertEqual(sorted(path.name for path in outside.iterdir()), ['tracked.yml'])

    @unittest.skipUnless(os.name == 'posix', 'Native symlink confinement uses POSIX links')
    def test_package_confines_links_inside_its_root_before_resolution(self):
        package = self.root / 'package'
        package.mkdir()
        actual = package / 'actual'
        actual.mkdir()
        (actual / 'image.tar').write_bytes(b'accepted artifact')
        (package / 'linked-file').symlink_to(actual / 'image.tar')
        (package / 'linked-directory').symlink_to(actual, target_is_directory=True)
        for relative in ('linked-file', 'linked-directory/image.tar'):
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'linked'):
                PACKAGE.confined(package, relative)
        self.assertEqual(PACKAGE.confined(package, 'actual/image.tar'), actual / 'image.tar')

    def test_rejects_scope_escape_wrong_nic_and_missing_backup_identity(self):
        for change in ('tier', 'network', 'backup_config_sha256'):
            with self.subTest(change=change):
                saved = copy.deepcopy(self.plan)
                vm = self.plan['virtual_machines'][0]
                vm[change] = {'tier': 0, 'network': {'net0': 'virtio=02:00:00:00:00:01,bridge=vmbr0'},
                              'backup_config_sha256': 'unbound'}[change]
                path, digest = self.accepted()
                with self.assertRaises(ValueError):
                    RUNNER.read_plan(path, digest)
                self.plan = saved

    def test_full_loss_requires_tier_zero_inputs_and_prerequisite_targets(self):
        self.plan['scope'] = 'all-vms'
        path, digest = self.accepted()
        with self.assertRaises(ValueError):
            RUNNER.read_plan(path, digest)

    def test_engine_inputs_reject_initializers_live_products_and_unpinned_containers(self):
        engine = yaml.safe_load((self.root / 'tier-1/secrets/engines.yml').read_text())
        variants = []
        for kind, name in [('Job', 'initialize'), ('StatefulSet', 'database'), ('Deployment', 'unselected')]:
            candidate = copy.deepcopy(engine)
            candidate['kind'] = kind
            candidate['metadata']['name'] = name
            variants.append(candidate)
        for field in ('containers', 'initContainers'):
            candidate = copy.deepcopy(engine)
            candidate['spec']['template']['spec'][field] = [{'name': 'mutable', 'image': 'registry.test/tool:latest'}]
            variants.append(candidate)
        for index, candidate in enumerate(variants):
            with self.subTest(variant=index):
                self.retained_yaml('secrets/engines.yml', [candidate])
                path, digest = self.accepted()
                with self.assertRaisesRegex(ValueError, 'Restore.engine'):
                    RUNNER.read_plan(path, digest)
        self.retained_yaml('secrets/engines.yml', [engine])
        path, digest = self.accepted()
        RUNNER.read_plan(path, digest)

    def test_prerequisite_readiness_is_required_bounded_and_uses_retained_tls_inputs(self):
        vm = self.plan['virtual_machines'][0]
        accepted = copy.deepcopy(vm['health_checks'])
        invalid = [[], [{'kind': 'shell'}], [{'kind': 'tcp', 'host': 'private', 'port': 0}],
            [{'kind': 'tcp', 'host': 'private', 'port': 443, 'timeout': 901}],
            [{'kind': 'https', 'url': 'http://private', 'status': 200}],
            [{'kind': 'https', 'url': 'https://private', 'status': 403}],
            [{'kind': 'https', 'url': 'https://private', 'status': 200, 'ca_path': 'unretained/ca.pem'}]]
        for checks in invalid:
            with self.subTest(checks=checks):
                vm['health_checks'] = checks
                path, digest = self.accepted()
                with self.assertRaises(ValueError):
                    RUNNER.read_plan(path, digest)
        vm['health_checks'] = accepted
        path, digest = self.accepted()
        RUNNER.read_plan(path, digest)

    def test_unpaused_reconcilers_and_live_consumers_are_not_restore_prerequisites(self):
        for kind, spec in [('Deployment', {'replicas': 1}), ('StatefulSet', {}),
                           ('Kustomization', {'suspend': False}), ('HelmRelease', {})]:
            with self.subTest(kind=kind):
                self.retained_yaml('secrets/resources.yml', [{'apiVersion': 'fixture/v1', 'kind': kind,
                    'metadata': {'name': 'unsafe'}, 'spec': spec}])
                path, digest = self.accepted()
                with self.assertRaisesRegex(ValueError, 'zero replicas|suspended'):
                    RUNNER.read_plan(path, digest)

    def test_all_vms_binds_distinct_tier_zero_sources_and_cutover(self):
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
            cutover={'resume_roots': ['platform'], 'health_checks': [{'kind': 'Deployment', 'name': 'core'}],
                     'sources': {'platform': {'url': 'ssh://git@core.test/platform', 'ref': 'refs/heads/recovery',
                         'secret_name': 'tier0-source', 'identity_file': 'tier-0/secrets/source-identity',
                         'known_hosts_file': 'tier-0/secrets/source-known-hosts', 'secret_file': 'tier-0/secrets/source.yml'}}})
        cluster['package']['sources']['platform'] = 'd' * 40
        self.plan['clusters'].insert(0, cluster)
        self.plan['template_rebuild'] = {'catalog': 'tier-0/secrets/resources.yml',
            'provider_environment': 'tier-0/secrets/provider.env', 'assets': {'talos': 'talos.raw'}}
        def update(owner, relative, content):
            repository = self.plan['automation'][owner]
            target = Path(repository['directory']) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            repository['private_files'] = [item for item in repository['private_files'] if item['path'] != relative]
            repository['private_files'].append({'path': relative, 'sha256': RUNNER.checksum(target)})
        update('tier-0', '.terraform/state/proxmox-templates/terraform.tfstate', '{"version":4,"lineage":"retained"}')
        update('tier-0', 'secrets/bootstrap.yml', yaml.safe_dump({'cluster_platform_action': 'apply',
            'cluster_platform_flux_recovery': True, 'cluster_platform_flux_commit': 'd' * 40}))
        for tier in (0, 1):
            update(f'tier-{tier}', 'secrets/recovery-git.yml', yaml.safe_dump({
                'flux_recovery_git_user': f'recovery-tier{tier}', 'flux_recovery_git_root': f'/srv/recovery/tier{tier}'}))
        path, digest = self.accepted()
        result = RUNNER.read_plan(path, digest)
        self.assertEqual(result['clusters'][0]['package']['sources']['platform'], 'd' * 40)
        self.assertEqual(result['clusters'][1]['package']['sources']['platform'], 'c' * 40)
        self.assertEqual(result['clusters'][0]['cutover']['resume_roots'], ['platform'])
        cluster['cutover']['sources']['platform']['secret_file'] = 'missing/unbound-key'
        path, digest = self.accepted()
        with self.assertRaisesRegex(ValueError, 'trust and credentials'):
            RUNNER.read_plan(path, digest)

    def test_cutover_cannot_address_an_unrestored_vm_or_change_nic_membership(self):
        sources = {name: {'url': 'ssh://git@git.internal.example.com/' + name,
            'ref': 'refs/heads/accepted', 'secret_name': name + '-git', 'identity_file': 'tier-1/secrets/source-identity',
            'known_hosts_file': 'tier-1/secrets/source-known-hosts', 'secret_file': 'tier-1/secrets/source.yml'}
            for name in ('platform', 'tier1-platform', 'tier1-applications')}
        self.plan['cutover'] = {'resume_roots': ['platform', 'tier1-platform'], 'sources': sources,
            'health_checks': [{'kind': 'Deployment', 'name': 'harbor-core'}], 'virtual_machines': [
            {'vmid': 9999, 'node': 'pve01', 'network': [{'name': 'net0', 'configuration': 'virtio,bridge=vmbr0'}]}]}
        path, digest = self.accepted()
        with self.assertRaisesRegex(ValueError, 'restored VM'):
            RUNNER.read_plan(path, digest)
        self.plan['cutover']['virtual_machines'][0]['vmid'] = 1301
        self.plan['cutover']['virtual_machines'][0]['network'][0]['name'] = 'net1'
        path, digest = self.accepted()
        with self.assertRaisesRegex(ValueError, 'NIC inventory'):
            RUNNER.read_plan(path, digest)

    def test_old_kubernetes_backups_and_initializer_payloads_fail_before_provisioning(self):
        self.plan['virtual_machines'][0]['role'] = 'control-plane'
        path, digest = self.accepted()
        with self.assertRaises(ValueError):
            RUNNER.read_plan(path, digest)
        self.plan['virtual_machines'][0]['role'] = 'prerequisite'
        resources = self.root / 'tier-1/secrets/resources.yml'
        resources.write_text('apiVersion: batch/v1\nkind: Job\nmetadata: {name: old-initializer}\n')
        for entry in self.plan['automation']['tier-1']['private_files']:
            if entry['path'] == 'secrets/resources.yml':
                entry['sha256'] = RUNNER.checksum(resources)
        path, digest = self.accepted()
        with self.assertRaises(ValueError):
            RUNNER.read_plan(path, digest)

    def test_native_preparation_is_registered_before_the_recovery_role(self):
        control = yaml.safe_load((ROOT / 'tier-1/ansible/playbooks/control-node.yml').read_text())[0]['vars']
        self.assertEqual(control['control_node_setup_collection_names']['platform-recovery'], ['kubernetes.core'])
        tools = control['control_node_setup_tool_commands']['platform-recovery']
        self.assertIn(['restic', 'version'], tools)
        entry = yaml.safe_load((ROOT / 'tier-1/ansible/playbooks/maintenance/platform-recovery.yml').read_text())
        self.assertEqual(entry[0]['ansible.builtin.import_playbook'], '../control-node.yml')
        self.assertEqual(entry[0]['vars']['control_node_setup'], 'platform-recovery')

    def test_unknown_products_missing_content_and_denials_are_rejected(self):
        for field, value in [('kind', 'external-hook'), ('checks', [{'url': 'https://test', 'status': 200}])]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.plan['products'][0])
                self.plan['products'][0][field] = value
                path, digest = self.accepted()
                with self.assertRaises(ValueError):
                    RUNNER.read_plan(path, digest)
                self.plan['products'][0] = original


class OperatingPayload(unittest.TestCase):
    def setUp(self):
        self.product = {'namespace': 'spinnaker', 'operating_component': 'clusters/tier1/delivery'}
        self.resources = []
        for name in PAYLOAD.SERVICES:
            self.resources.append({'apiVersion': 'apps/v1', 'kind': 'Deployment',
                'metadata': {'name': name, 'namespace': 'spinnaker'},
                'spec': {'replicas': 1, 'template': {'spec': {'containers': [{'name': name, 'image': name + '@sha256:' + 'a' * 64}]}}}})
        self.resources.append({'apiVersion': 'networking.k8s.io/v1', 'kind': 'Ingress',
            'metadata': {'name': 'spinnaker', 'namespace': 'spinnaker'}, 'spec': {'rules': []}})
        for database in ('mysql', 'redis'):
            self.resources.append({'apiVersion': 'batch/v1', 'kind': 'Job',
                'metadata': {'name': 'spinnaker-data-' + database + '-adopt-accepted', 'namespace': 'spinnaker'},
                'spec': {'template': {'spec': {'containers': [{'name': 'verify'}], 'volumes': []}}}})
        self.resources.append({'apiVersion': 'batch/v1', 'kind': 'Job',
            'metadata': {'name': 'spinnaker-databases-verify-accepted', 'namespace': 'spinnaker'},
            'spec': {'template': {'spec': {'containers': [{'name': 'verify',
                'env': [{'name': 'SPINNAKER_DATABASE_ACTION', 'value': 'verify'}]}]}}}})

    def inspect(self):
        from unittest.mock import patch
        graph = [{'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization',
            'spec': {'sourceRef': {'name': 'tier1-platform'}, 'path': './clusters/tier1/delivery/stages/operating'}}]
        with patch.object(PAYLOAD, 'render', side_effect=[graph, self.resources]):
            return PAYLOAD.inspect_component(Path('/accepted'), self.product)

    def test_adopt_requires_running_consumers_normal_ingress_and_network_guards(self):
        observed = self.inspect()
        self.assertEqual({item['name'] for item in observed if item['kind'] == 'Deployment'}, PAYLOAD.SERVICES)
        self.assertEqual(sum(item['kind'] == 'Ingress' for item in observed), 1)
        for kind in ('recover', 'fresh'):
            with self.subTest(lifecycle=kind):
                original = copy.deepcopy(self.resources)
                for item in self.resources:
                    if item['kind'] == 'Job':
                        item['metadata']['name'] = item['metadata']['name'].replace('-adopt-', '-' + kind + '-')
                with self.assertRaisesRegex(ValueError, 'adopt'):
                    self.inspect()
                self.resources = original

    def test_fresh_initializer_zero_replicas_missing_ingress_and_rwo_guard_block_cutover(self):
        original = copy.deepcopy(self.resources)
        self.resources[-1]['spec']['template']['spec']['containers'][0]['env'][0]['value'] = 'initialize'
        with self.assertRaisesRegex(ValueError, 'verify existing SQL'):
            self.inspect()
        self.resources = copy.deepcopy(original)
        self.resources[0]['spec']['replicas'] = 0
        with self.assertRaisesRegex(ValueError, 'consumer'):
            self.inspect()
        self.resources = [item for item in copy.deepcopy(original) if item['kind'] != 'Ingress']
        with self.assertRaisesRegex(ValueError, 'ingress'):
            self.inspect()
        self.resources = copy.deepcopy(original)
        self.resources[-2]['spec']['template']['spec']['volumes'] = [{'persistentVolumeClaim': {'claimName': 'redis'}}]
        with self.assertRaisesRegex(ValueError, 'network guards'):
            self.inspect()

    def test_native_cutover_keeps_databases_and_checks_operation_before_nic_reconnect(self):
        tasks = yaml.safe_load((ROLE / 'tasks/cutover.yml').read_text())
        includes = [item.get('ansible.builtin.include_tasks') for item in tasks]
        self.assertNotIn('release-spinnaker-volumes.yml', includes)
        checks = next(index for index, item in enumerate(tasks) if item.get('ansible.builtin.include_tasks') == 'cutover-cluster.yml')
        reconnect = next(index for index, item in enumerate(tasks) if 'ansible.builtin.command' in item)
        self.assertLess(checks, reconnect)


class NativeSpinnakerFencing(unittest.TestCase):
    def test_cancels_orphaned_pipeline_and_task_then_rechecks_all_terminal(self):
        states = {'/pipelines/old-pipeline': 'RUNNING', '/tasks/old-task': 'SUSPENDED'}
        events = []

        def request(method, path):
            events.append((method, path))
            if method == 'PUT':
                states['/pipelines/old-pipeline' if 'PIPELINE' in path else '/tasks/old-task'] = 'CANCELED'
                return {}
            return {'status': states[path]}

        result = FENCE.fence('PIPELINE\told-pipeline\nORCHESTRATION\told-task\n', request)
        self.assertEqual(result['verified_execution_count'], 2)
        self.assertEqual(sum(method == 'PUT' for method, _ in events), 2)
        self.assertEqual(sum(method == 'GET' for method, _ in events), 4)

    def test_successful_history_is_preserved_and_repeated_fencing_is_idempotent(self):
        states = {'/pipelines/successful': 'SUCCEEDED', '/tasks/stale': 'RUNNING'}
        writes = []
        data_changes = []

        def request(method, path):
            if method == 'PUT':
                writes.append(path)
                identity = '/pipelines/successful' if 'PIPELINE' in path else '/tasks/stale'
                if states[identity] not in FENCE.TERMINAL:
                    states[identity] = 'CANCELED'
                    data_changes.append(identity)
                return {}
            return {'status': states[path]}

        inventory = 'PIPELINE\tsuccessful\nORCHESTRATION\tstale\n'
        FENCE.fence(inventory, request)
        FENCE.fence(inventory, request)
        self.assertEqual(len(writes), 4)
        self.assertEqual(data_changes, ['/tasks/stale'])
        self.assertEqual(states['/pipelines/successful'], 'SUCCEEDED')

    def test_unavailable_service_failed_cancellation_and_changed_state_block_cutover(self):
        def down(method, path):
            raise OSError('independent admin API is unavailable')
        with self.assertRaises(OSError):
            FENCE.fence('PIPELINE\told\n', down)
        with self.assertRaises(ValueError):
            FENCE.fence('PIPELINE\told\n', lambda method, path: {'status': 'RUNNING'})
        with self.assertRaises(ValueError):
            FENCE.fence('PIPELINE\t../../arbitrary\n', down)

    def test_retained_content_and_negative_authorization_are_both_required(self):
        content = b'retained artifact bytes'
        checks = [{'url': 'https://private/content', 'status': 200,
                   'content_sha256': hashlib.sha256(content).hexdigest()},
                  {'url': 'https://private/denied', 'status': 403}]
        self.assertEqual(VERIFY.verify(checks, lambda check: (check['status'], content)), 2)
        with self.assertRaises(ValueError):
            VERIFY.verify(checks, lambda check: (200, content))
        with self.assertRaises(ValueError):
            VERIFY.verify(checks, lambda check: (check['status'], b'wrong backup content'))


class MetricsTargetGuard(unittest.TestCase):
    def test_native_restore_empty_target_guard_preserves_existing_files(self):
        from unittest.mock import patch
        tasks = yaml.safe_load((ROLE / 'tasks/victoriametrics.yml').read_text())
        rendered = next(item['ansible.builtin.set_fact']['recovery_job']
                        for item in tasks if 'recovery_job' in item.get('ansible.builtin.set_fact', {}))
        pod = rendered['spec']['template']['spec']
        guard = pod['initContainers'][0]
        self.assertEqual(guard['volumeMounts'], [{'name': 'data', 'mountPath': '/data', 'readOnly': True}])
        self.assertIn('RECOVERY_PVC_UID', {item['name'] for item in pod['containers'][0]['env']})
        target = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='metrics-empty-target-')))
        native_scandir = os.scandir
        def selected_directory(path):
            self.assertEqual(path, '/data')
            with native_scandir(target) as entries:
                return iter(list(entries))
        with patch.object(os, 'scandir', side_effect=selected_directory):
            exec(compile(guard['command'][2], '<native-metrics-target-guard>', 'exec'), {})
            (target / 'lost+found').mkdir()
            exec(compile(guard['command'][2], '<native-metrics-target-guard>', 'exec'), {})
            retained = target / 'existing-native-data'
            retained.write_bytes(b'production dataset must survive')
            with self.assertRaisesRegex(AssertionError, 'empty target'):
                exec(compile(guard['command'][2], '<native-metrics-target-guard>', 'exec'), {})
            self.assertEqual(retained.read_bytes(), b'production dataset must survive')


class CleanTalosRecovery(unittest.TestCase):
    def test_only_runtime_bindings_are_removed_and_original_secrets_are_retained(self):
        state = {'resources': [
            {'mode': 'managed', 'type': 'talos_machine_secrets', 'name': 'cluster',
             'instances': [{'attributes': {'machine_secrets': {'cluster': 'original'},
                                           'client_configuration': {'ca_certificate': 'original-ca'}}}]},
            {'mode': 'managed', 'type': 'proxmox_virtual_environment_vm', 'name': 'node',
             'instances': [{'index_key': 'cp-1'}]},
            {'mode': 'managed', 'type': 'talos_machine_bootstrap', 'name': 'cluster', 'instances': [{}]}]}
        identity = TALOS.secrets_identity(state)
        addresses = TALOS.runtime_addresses(state)
        self.assertEqual(addresses, ['proxmox_virtual_environment_vm.node["cp-1"]', 'talos_machine_bootstrap.cluster'])
        self.assertEqual(TALOS.secrets_identity(state), identity)
        state['resources'][0]['instances'][0]['attributes']['machine_secrets']['cluster'] = 'new-root'
        self.assertNotEqual(TALOS.secrets_identity(state), identity)

    def test_saved_plan_rejects_wrong_vm_network_new_secrets_and_destruction(self):
        cluster = {'nodes': [{'name': 'cp-1', 'vmid': 1101, 'node': 'pve01'}], 'recovery_bridge': 'vmbr9'}
        plan = {'resource_changes': [
            {'type': 'talos_machine_secrets', 'change': {'actions': ['no-op']}},
            {'type': 'proxmox_virtual_environment_vm', 'change': {'actions': ['create'],
                'after': {'name': 'cp-1', 'vm_id': 1101, 'node_name': 'pve01',
                          'network_device': [{'bridge': 'vmbr9'}]}}}]}
        TALOS.validate_plan(plan, cluster)
        for mutation in ('vmid', 'bridge', 'secrets', 'destroy'):
            candidate = copy.deepcopy(plan)
            if mutation == 'vmid':
                candidate['resource_changes'][1]['change']['after']['vm_id'] = 9999
            elif mutation == 'bridge':
                candidate['resource_changes'][1]['change']['after']['network_device'][0]['bridge'] = 'vmbr0'
            elif mutation == 'secrets':
                candidate['resource_changes'][0]['change']['actions'] = ['create']
            else:
                candidate['resource_changes'][1]['change']['actions'] = ['delete', 'create']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                TALOS.validate_plan(candidate, cluster)

    @unittest.skipUnless(os.name != 'nt', 'Native Bash fixture requires Linux')
    def test_native_adapter_preserves_original_identity_and_applies_only_validated_saved_plan(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='clean-talos-fixture-')))
        workspace = directory / 'workspace'
        repo = workspace / 'tier-1'
        state_file = repo / '.terraform/state/talos/terraform.tfstate'
        state_file.parent.mkdir(parents=True)
        original = {'version': 4, 'lineage': 'original', 'serial': 1, 'resources': [
            {'mode': 'managed', 'type': 'talos_machine_secrets', 'name': 'cluster',
             'instances': [{'attributes': {'machine_secrets': {'cluster': 'original'},
                                          'client_configuration': {'ca_certificate': 'original-ca'}}}]},
            {'mode': 'managed', 'type': 'proxmox_virtual_environment_vm', 'name': 'node',
             'instances': [{'index_key': 'cp-1', 'attributes': {'id': '1101'}}]}]}
        state_file.write_text(json.dumps(original))
        custody = directory / 'original-state.json'
        custody.write_bytes(state_file.read_bytes())
        original_bytes = custody.read_bytes()
        (workspace / 'receipts').mkdir(parents=True)
        library = workspace / 'shared/scripts/lib/provider-environment.sh'
        library.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'shared/scripts/lib/provider-environment.sh', library)
        environment = repo / '.env.local'
        environment.write_text('PROXMOX_API_URL=https://pve.example.invalid:8006/\n'
                               'PROXMOX_API_TOKEN_ID=fixture@pve!recovery\nPROXMOX_API_TOKEN_SECRET=fixture\n')
        tools = directory / 'tools'
        tools.mkdir()
        terraform = tools / 'terraform'
        terraform.write_text('#!/usr/bin/env python3\nimport json,pathlib,sys\n'
            'root=pathlib.Path.cwd(); state=root/".terraform/state/talos/terraform.tfstate"\n'
            'arguments=sys.argv[2:]\n'
            'if arguments[:2]==["state","pull"]: print(state.read_text())\n'
            'elif arguments[:2]==["state","rm"]:\n'
            ' data=json.loads(state.read_text()); data["resources"]=[r for r in data["resources"] if r["type"]=="talos_machine_secrets"]; state.write_text(json.dumps(data))\n'
            'elif arguments[:2]==["show","-json"]: print((root/"fixture-plan.json").read_text())\n')
        terraform.chmod(0o700)
        script = repo / 'scripts/kubernetes-cluster.sh'
        script.parent.mkdir(parents=True)
        script.write_text('#!/bin/bash\nset -eu\nmkdir -p .terraform/plans secrets/talos\n'
            'case "$1" in\n'
            'plan) printf accepted-saved-plan > .terraform/plans/talos.tfplan ;;\n'
            'apply) test "$(cat .terraform/plans/talos.tfplan)" = accepted-saved-plan; printf applied > applied ;;\n'
            'credentials) printf retained-identity > secrets/talos/kubeconfig ;;\n'
            'esac\n')
        cluster = {'tier': 1, 'mode': 'clean', 'provider_environment': 'tier-1/.env.local',
                   'recovery_bridge': 'vmbr9', 'nodes': [{'name': 'cp-1', 'node': 'pve01', 'vmid': 1101}]}
        proposed = {'resource_changes': [
            {'type': 'talos_machine_secrets', 'change': {'actions': ['no-op']}},
            {'type': 'proxmox_virtual_environment_vm', 'change': {'actions': ['create'],
                'after': {'name': 'cp-1', 'vm_id': 1101, 'node_name': 'pve01', 'network_device': [{'bridge': 'vmbr9'}]}}}]}
        (repo / 'fixture-plan.json').write_text(json.dumps(proposed))
        inputs = workspace / 'inputs.json'
        inputs.write_text(json.dumps({'platform_recovery': {'workspace': str(workspace),
            'plan_sha256': 'a' * 64, 'clusters': [cluster]}}))
        from unittest.mock import patch
        owned = {'name': 'cp-1', 'description': 'recovery=' + 'a' * 64, 'vmgenid': 'native-generation'}
        def native_vm(environment, node):
            return owned if (repo / 'applied').exists() else None
        with patch.dict(os.environ, {'PATH': str(tools) + os.pathsep + os.environ['PATH']}), \
                patch.object(TALOS, 'proxmox_configuration', side_effect=native_vm):
            TALOS.recover(argparse.Namespace(inputs=inputs, tier=1))
            TALOS.recover(argparse.Namespace(inputs=inputs, tier=1))
        self.assertEqual(custody.read_bytes(), original_bytes)
        self.assertEqual(TALOS.secrets_identity(json.loads(state_file.read_text())), TALOS.secrets_identity(original))
        self.assertEqual((repo / 'applied').read_text(), 'applied')
        self.assertTrue((workspace / 'receipts/tier-1-reconstruction.before.tfstate').is_file())
        self.assertTrue((workspace / 'receipts/tier-1-reconstruction.native.log').is_file())


API_MODULE = r'''
import json
from pathlib import Path
from ansible.module_utils.basic import AnsibleModule
module = AnsibleModule(argument_spec=dict(kubeconfig=dict(type='str'), context=dict(type='str'),
 validate_certs=dict(type='bool'), api_version=dict(type='str'), kind=dict(type='str'),
 namespace=dict(type='str'), name=dict(type='str'), state=dict(type='str'), definition=dict(type='dict')))
path = Path(module.params['kubeconfig'])
state = json.loads(path.read_text())
definition = module.params.get('definition')
if definition:
 state['creates'] += 1
 state['object'] = definition
 state['object']['metadata']['uid'] = 'actual-restore-uid'
 state['object']['status'] = {'succeeded': 1, 'conditions': [{'type': 'Complete', 'status': 'True'}]}
 path.write_text(json.dumps(state))
 module.exit_json(changed=True, result=state['object'])
module.exit_json(changed=False, resources=[state['object']] if state.get('object') else [])
'''


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
class NativeRecoveryJobs(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='recovery-jobs-')))
        modules = self.root / 'collections/ansible_collections/kubernetes/core/plugins/modules'
        modules.mkdir(parents=True)
        for name in ('k8s', 'k8s_info'):
            (modules / (name + '.py')).write_text(API_MODULE)
        self.api = self.root / 'api.json'
        self.api.write_text(json.dumps({'creates': 0}))
        (self.root / 'receipts').mkdir()
        self.variables = {'recovery_kubeconfig': str(self.api), 'recovery_context': 'isolated',
            'platform_recovery': {'plan_sha256': 'a' * 64, 'recovery_id': 'accepted', 'workspace': str(self.root)},
            'recovery_job': {'apiVersion': 'batch/v1', 'kind': 'Job',
                'metadata': {'name': 'actual-native-restore', 'namespace': 'isolated'},
                'spec': {'backoffLimit': 0, 'template': {'spec': {'restartPolicy': 'Never',
                    'containers': [{'name': 'native', 'image': 'independent@sha256:' + 'b' * 64}]}}}}}

    def play(self, success=True):
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': self.variables, 'tasks': [{'ansible.builtin.include_tasks': str(ROLE / 'tasks/native-job.yml')}]}]))
        environment = dict(os.environ, ANSIBLE_COLLECTIONS_PATH=str(self.root / 'collections'),
                           ANSIBLE_FILTER_PLUGINS=str(ROLE / 'filter_plugins'),
                           ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp'))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                env=environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_success_is_reobserved_after_interruption_without_recreating_restore(self):
        self.play()
        journal = next((self.root / 'receipts').glob('job-*.json'))
        observed = json.loads(journal.read_text())
        self.assertEqual(observed['phase'], 'uid-bound')
        self.assertEqual(observed['uid'], 'actual-restore-uid')
        self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
        self.play()
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_operating_gate_requires_running_current_consumers_and_normal_source_owner(self):
        module = self.root / 'collections/ansible_collections/kubernetes/core/plugins/modules/k8s_info.py'
        module.write_text('''from ansible.module_utils.basic import AnsibleModule
import json
from pathlib import Path
module = AnsibleModule(argument_spec={name: {'type': 'str'} for name in
 ['kubeconfig','context','api_version','kind','namespace','name']} | {'validate_certs': {'type': 'bool'}})
objects = json.loads(Path(module.params['kubeconfig']).read_text())
value = objects.get(module.params['kind'] + ':' + module.params['name'])
module.exit_json(changed=False, resources=[value] if value else [])
''')
        expected = {'replicas': 1, 'template': {'spec': {'containers': [{'name': 'gate', 'image': 'retained@sha256:' + 'b' * 64}]}}}
        objects = {'Deployment:gate': {'metadata': {'generation': 2}, 'spec': expected,
            'status': {'observedGeneration': 2, 'replicas': 1, 'updatedReplicas': 1, 'readyReplicas': 1, 'availableReplicas': 1}},
            'GitRepository:platform': {'spec': {'url': 'ssh://git@restored.test/platform', 'secretRef': {'name': 'restored-git'}},
                'status': {'artifact': {'revision': 'recovery@sha1:' + 'c' * 40},
                           'conditions': [{'type': 'Ready', 'status': 'True'}]}}}
        variables = {'recovery_health_retries': 1, 'recovery_health_delay': 0,
            'platform_recovery': {'workspace': str(self.root), 'plan_sha256': 'a' * 64},
            'recovery_cutover_cluster': {'tier': 1, 'kubeconfig': 'api.json', 'context': 'isolated'},
            'recovery_scope_cutover': {'sources': {'platform': {'url': 'ssh://git@restored.test/platform', 'secret_name': 'restored-git'}}},
            'recovery_scope_package': {'sources': {'platform': 'c' * 40}},
            'recovery_operating_payload': {'plan_sha256': 'a' * 64, 'resources': [
                {'tier': 1, 'kind': 'Deployment', 'namespace': 'spinnaker', 'name': 'gate', 'spec': expected}]}}
        play = self.root / 'operating.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': [{'ansible.builtin.include_tasks': str(ROLE / 'tasks/operating-health.yml')}]}]))
        environment = dict(os.environ, ANSIBLE_COLLECTIONS_PATH=str(self.root / 'collections'),
                           ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp'))
        for change in ('healthy', 'zero', 'old-generation', 'wrong-owner'):
            with self.subTest(change=change):
                current = copy.deepcopy(objects)
                if change == 'zero':
                    current['Deployment:gate']['status']['readyReplicas'] = 0
                if change == 'old-generation':
                    current['Deployment:gate']['status']['observedGeneration'] = 1
                if change == 'wrong-owner':
                    current['GitRepository:platform']['spec']['url'] = 'ssh://git@temporary.test/platform'
                self.api.write_text(json.dumps(current))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                    env=environment, capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode == 0, change == 'healthy', result.stdout + result.stderr)

    def test_native_resume_contract_uses_the_owning_cluster_package_and_job_uids(self):
        source = yaml.safe_load((ROLE / 'tasks/cutover-cluster.yml').read_text())
        resume = next(item for item in source if 'ansible.builtin.include_role' in item)
        for tier in (0, 1):
            path = self.root / f'receipts/flux-{tier}-platform/scope-receipt.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'resources': {'root': {'kind': 'Kustomization',
                'namespace': 'flux-system', 'name': 'platform', 'uid': f'tier{tier}-root', 'previous_suspend': True}}}))
        for tier in (0, 1):
            with self.subTest(tier=tier):
                package = {'directory': f'/independent/tier{tier}', 'sources': {'platform': str(tier) * 40},
                           'artifact_lock_sha256': str(tier) * 64}
                cluster = {'tier': tier, 'package': package, 'context': f'tier{tier}', 'kubeconfig': f'tier-{tier}/kubeconfig',
                    'canary_sha256': str(tier) * 64, 'cutover': {'sources': {'platform': {'ref': 'refs/heads/recovery'}},
                    'resume_roots': ['platform'], 'health_checks': [{'kind': 'Deployment', 'name': f'tier{tier}-service'}]}}
                variables = {'platform_recovery': {'workspace': str(self.root), 'package': {}, 'cutover': {}},
                    'recovery_cutover_cluster': cluster, 'recovery_resume_root': 'platform',
                    'recovery_verification_jobs': [{'tier': current, 'uid': f'tier{current}-actual-job'} for current in (0, 1)]}
                play = self.root / 'scope.yml'
                output = self.root / f'scope-{tier}.json'
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                    'vars': variables, 'tasks': [source[0], {'ansible.builtin.copy': {
                        'dest': str(output), 'content': '{{ contract | to_json }}'},
                        'vars': {'contract': resume['vars']}}]}]))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                    capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                observed = json.loads(output.read_text())
                self.assertEqual(observed['flux_maintenance_revision'], str(tier) * 40)
                self.assertEqual(observed['flux_maintenance_recovery_directory'], f'/independent/tier{tier}')
                self.assertEqual(observed['flux_maintenance_resume_checks'], [{'tier': tier, 'uid': f'tier{tier}-actual-job'}])
                self.assertEqual(observed['flux_maintenance_resume_suspended_uids'], [f'tier{tier}-root'])

    def test_changed_payload_and_failed_native_restore_prevent_replay(self):
        self.play()
        self.variables['recovery_job']['spec']['activeDeadlineSeconds'] = 10
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)
        self.variables['recovery_job']['spec'].pop('activeDeadlineSeconds')
        state = json.loads(self.api.read_text())
        state['object']['status'] = {'failed': 1}
        self.api.write_text(json.dumps(state))
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_deleted_or_replaced_native_job_cannot_restart_destructive_restoration(self):
        self.play()
        original = json.loads(self.api.read_text())
        missing = copy.deepcopy(original)
        missing.pop('object')
        self.api.write_text(json.dumps(missing))
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)
        replacement = copy.deepcopy(original)
        replacement['object']['metadata']['uid'] = 'replacement-native-uid'
        self.api.write_text(json.dumps(replacement))
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_planned_intent_binds_created_native_job_after_interruption_without_replay(self):
        self.play()
        journal = next((self.root / 'receipts').glob('job-*.json'))
        intent = json.loads(journal.read_text())
        intent.pop('uid')
        intent['phase'] = 'planned'
        journal.write_text(json.dumps(intent))
        self.play()
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)
        self.assertEqual(json.loads(journal.read_text())['uid'], 'actual-restore-uid')

    def test_planned_intent_with_no_native_object_creates_once_and_unjournaled_job_is_rejected(self):
        self.play()
        original = json.loads(self.api.read_text())
        journal = next((self.root / 'receipts').glob('job-*.json'))
        intent = json.loads(journal.read_text())
        intent.pop('uid')
        intent['phase'] = 'planned'
        journal.write_text(json.dumps(intent))
        self.api.write_text(json.dumps({'creates': 0}))
        self.play()
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)
        journal.unlink()
        self.api.write_text(json.dumps(original))
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_api_defaults_are_allowed_but_changed_live_job_body_is_rejected(self):
        self.play()
        original = json.loads(self.api.read_text())
        defaults = copy.deepcopy(original)
        defaults['object']['spec']['template']['spec']['dnsPolicy'] = 'ClusterFirst'
        self.api.write_text(json.dumps(defaults))
        self.play()
        for mutation in ('image', 'annotation'):
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(original)
                if mutation == 'image':
                    candidate['object']['spec']['template']['spec']['containers'][0]['image'] = 'unaccepted:latest'
                else:
                    candidate['object']['metadata']['annotations']['recovery.homelab/plan-sha256'] = '0' * 64
                self.api.write_text(json.dumps(candidate))
                self.play(success=False)
                self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_completed_verification_never_recreates_a_missing_job_or_local_journal(self):
        self.play()
        original = json.loads(self.api.read_text())
        self.variables['platform_recovery']['phase'] = 'verify'
        self.play()
        self.api.write_text(json.dumps({'creates': original['creates']}))
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)
        self.api.write_text(json.dumps(original))
        next((self.root / 'receipts').glob('job-*.json')).unlink()
        self.play(success=False)
        self.assertEqual(json.loads(self.api.read_text())['creates'], 1)

    def test_all_recovery_task_files_pass_native_ansible_task_parsing(self):
        for name in ('k8s_scale', 'k8s_json_patch'):
            modules = self.root / 'collections/ansible_collections/kubernetes/core/plugins/modules'
            (modules / (name + '.py')).write_text(API_MODULE)
        play = self.root / 'syntax.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False,
            'tasks': [{'ansible.builtin.import_tasks': str(path)} for path in (ROLE / 'tasks').glob('*.yml')]}]))
        environment = dict(os.environ, ANSIBLE_COLLECTIONS_PATH=str(self.root / 'collections'),
            ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-temp'),
            ANSIBLE_ROLES_PATH=os.pathsep.join([str(ROLE.parent), str(ROOT / 'shared/ansible/roles')]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play), '--syntax-check'],
                                env=environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_each_spinnaker_restore_job_mounts_only_its_own_rwo_data_claim(self):
        play = self.root / 'render.yml'
        source = ROLE / 'templates/spinnaker-restore.yml.j2'
        variables = {'platform_recovery': {'recovery_id': 'accepted'},
            'recovery_database_claim': {'resources': [{'metadata': {'uid': 'native-claim-uid'}}]},
            'recovery_product': {'name': 'spinnaker', 'namespace': 'spinnaker', 'backup_id': 'a' * 64,
                'restic_image': 'independent/restic@sha256:' + 'b' * 64, 'restic_secret': 'original-restic',
                'python_image': 'independent/python@sha256:' + 'b' * 64,
                'orca_url': 'https://orca.spinnaker.svc', 'admin_headers_secret': 'original-administrator',
                'mysql': {'image': 'independent/mysql@sha256:' + 'c' * 64, 'claim': 'mysql-data',
                          'path': '/backup/set/mysql.sql.gz', 'sha256': 'd' * 64},
                'redis': {'image': 'independent/redis@sha256:' + 'e' * 64, 'claim': 'redis-data',
                          'path': '/backup/set/redis.rdb', 'sha256': 'f' * 64}}}
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': [{'ansible.builtin.copy': {
                'content': "{{ lookup('ansible.builtin.template', '" + str(source) + "') }}",
                'dest': str(self.root / '{{ recovery_database }}.yml')},
                'loop': ['mysql', 'redis'], 'loop_control': {'loop_var': 'recovery_database'}},
                {'ansible.builtin.copy': {'content': "{{ lookup('ansible.builtin.template', '" +
                    str(ROLE / 'templates/spinnaker-fence.yml.j2') + "') }}", 'dest': str(self.root / 'fence.yml')}}]}]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for database in ('mysql', 'redis'):
            document = yaml.safe_load((self.root / (database + '.yml')).read_text())
            claims = [volume['persistentVolumeClaim']['claimName']
                      for volume in document['spec']['template']['spec']['volumes'] if 'persistentVolumeClaim' in volume]
            self.assertEqual(claims, [database + '-data'])
            self.assertEqual(document['spec']['backoffLimit'], 0)
        for name in ('mysql', 'redis', 'fence'):
            pod = yaml.safe_load((self.root / (name + '.yml')).read_text())['spec']['template']['spec']
            self.assertTrue(pod['securityContext']['runAsNonRoot'])
            self.assertGreater(pod['securityContext']['runAsUser'], 0)
            self.assertEqual(pod['securityContext']['seccompProfile']['type'], 'RuntimeDefault')
            self.assertFalse(pod['automountServiceAccountToken'])
            for container in pod['containers'] + pod.get('initContainers', []):
                with self.subTest(job=name, container=container['name']):
                    self.assertFalse(container['securityContext']['allowPrivilegeEscalation'])
                    self.assertIn('ALL', container['securityContext']['capabilities']['drop'])
