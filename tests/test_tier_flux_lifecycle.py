"""Independent configuration custody and the Tier 1 bootstrap ownership boundary."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipUnless(shutil.which('git'), 'Requires native Git')
class FluxRecovery(TierRepositoryTestCase):
    def command(self, *args, success=True):
        result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, timeout=90)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def package(self):
        directory = Path(self.temp.name)
        helper = UPSTREAM / 'tier-1/scripts/flux-recovery.py'
        sources, arguments = {}, []
        for name in ('platform', 'tier1-platform', 'tier1-applications'):
            repository = directory / name
            repository.mkdir()
            self.command('git', '-C', repository, 'init', '--quiet')
            (repository / 'config.yaml').write_text('apiVersion: v1\nkind: ConfigMap\nmetadata: {name: accepted}\n')
            self.command('git', '-C', repository, 'add', 'config.yaml')
            self.command('git', '-C', repository, '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                         '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'fixture')
            commit = self.command('git', '-C', repository, 'rev-parse', 'HEAD').stdout.strip()
            sources[name] = {'url': f'https://independent.test/{name}.git', 'commit': commit,
                             'ref': {'commit': commit}}
            arguments += ['--repository', f'{name}={repository}']
        record = directory / 'accepted.json'
        record.write_text(json.dumps({'version': 1, 'sources': sources}))
        artifact = directory / 'pinned-chart.tgz'
        artifact.write_bytes(b'approved-chart-fixture\n')
        lock = directory / 'artifacts.json'
        lock.write_text(json.dumps({'sources': {name: source['commit'] for name, source in sources.items()},
                                   'files': [{'path': artifact.name,
                                             'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}]}))
        output = directory / 'independent custody'
        command = [sys.executable, helper, 'export', '--record', record, '--artifacts', lock,
                   '--output', output, *arguments]
        self.command(*command)
        return helper, output, lock, sources, command

    def test_export_verify_restore_preserves_exact_commits_and_is_idempotent(self):
        helper, package, lock, sources, command = self.package()
        digest = hashlib.sha256(lock.read_bytes()).hexdigest()
        self.command(sys.executable, helper, 'verify', '--directory', package,
                     '--expect', f"tier1-platform={sources['tier1-platform']['commit']}", '--expect-lock', digest)
        restored = Path(self.temp.name) / 'recovered repositories'
        restore = [sys.executable, helper, 'restore', '--directory', package, '--output', restored,
                   '--expect-lock', digest]
        self.command(*restore)
        marker = (restored / 'recovery-manifest.sha256').stat().st_mtime_ns
        self.command(*restore)
        self.assertEqual((restored / 'recovery-manifest.sha256').stat().st_mtime_ns, marker)
        for name, source in sources.items():
            actual = self.command('git', '-C', restored / f'{name}.git', 'rev-parse', 'refs/heads/recovery')
            self.assertEqual(actual.stdout.strip(), source['commit'])
        branch = self.command('git', '-C', restored / 'tier1-applications.git', 'rev-parse', 'refs/heads/delivery')
        self.assertEqual(branch.stdout.strip(), sources['tier1-applications']['commit'])
        self.command(*command, success=False)

    def test_wrong_revision_lock_and_changed_artifact_cannot_be_accepted(self):
        helper, package, lock, _, _ = self.package()
        base = [sys.executable, helper, 'verify', '--directory', package]
        self.command(*base, '--expect', 'tier1-platform=' + '0' * 40, success=False)
        self.command(*base, '--expect-lock', '0' * 64, success=False)
        (package / 'artifacts/pinned-chart.tgz').write_bytes(b'changed')
        self.command(*base, success=False)
        manifest = json.loads((package / 'manifest.json').read_text())
        next(item for item in manifest['files'] if item['path'] == 'artifacts/pinned-chart.tgz')['sha256'] = hashlib.sha256(b'changed').hexdigest()
        (package / 'manifest.json').write_text(json.dumps(manifest))
        self.command(*base, '--expect-lock', hashlib.sha256(lock.read_bytes()).hexdigest(), success=False)

    def test_plaintext_secrets_do_not_enter_a_recovery_configuration_package(self):
        helper, package, lock, sources, command = self.package()
        repository = Path(self.temp.name) / 'tier1-platform'
        (repository / 'config.yaml').write_text('apiVersion: v1\nkind: Secret\nmetadata: {name: unsafe}\nstringData: {password: fixture}\n')
        self.command('git', '-C', repository, 'add', 'config.yaml')
        self.command('git', '-C', repository, '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                     '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'unsafe fixture')
        revision = self.command('git', '-C', repository, 'rev-parse', 'HEAD').stdout.strip()
        artifact_lock = json.loads(lock.read_text())
        artifact_lock['sources']['tier1-platform'] = revision
        lock.write_text(json.dumps(artifact_lock))
        replacement = list(command)
        replacement[replacement.index('--output') + 1] = Path(self.temp.name) / 'rejected package'
        self.command(*replacement, '--replace', f'tier1-platform={revision}', success=False)
        self.assertFalse((Path(self.temp.name) / 'rejected package/manifest.json').exists())

    def test_approved_lock_rejects_replaced_valid_git_bundle_and_rewritten_manifest(self):
        helper, package, lock, _, _ = self.package()
        approved = hashlib.sha256(lock.read_bytes()).hexdigest()
        repository = Path(self.temp.name) / 'tier1-platform'
        (repository / 'config.yaml').write_text('apiVersion: v1\nkind: ConfigMap\nmetadata: {name: substituted}\n')
        self.command('git', '-C', repository, 'add', 'config.yaml')
        self.command('git', '-C', repository, '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                     '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet', '-m', 'unapproved')
        revision = self.command('git', '-C', repository, 'rev-parse', 'HEAD').stdout.strip()
        self.command('git', '-C', repository, 'update-ref', 'refs/heads/recovery', revision)
        bundle = package / 'tier1-platform.bundle'
        bundle.unlink()
        self.command('git', '-C', repository, 'bundle', 'create', bundle, 'refs/heads/recovery')
        manifest = json.loads((package / 'manifest.json').read_text())
        manifest['sources']['tier1-platform']['commit'] = revision
        next(item for item in manifest['files'] if item['path'] == bundle.name)['sha256'] = hashlib.sha256(bundle.read_bytes()).hexdigest()
        (package / 'manifest.json').write_text(json.dumps(manifest))
        self.command(sys.executable, helper, 'verify', '--directory', package, '--expect-lock', approved, success=False)


class FluxOwnership(TierRepositoryTestCase):
    def native_tasks(self, tasks, variables, output_name='bootstrap-contract'):
        directory = Path(self.temp.name)
        playbook = directory / f'{output_name}.yml'
        playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                            'gather_facts': False, 'vars': variables, 'tasks': tasks}]))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                              cwd=UPSTREAM / 'tier-1/ansible', capture_output=True, text=True,
                              env=dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / 'tier-1/ansible/ansible.cfg'),
                                       ANSIBLE_LOCAL_TEMP=str(directory / 'native-local')))

    def tier1_inputs(self):
        return {'cluster_platform_management': 'flux', 'cluster_platform_tier': 1,
                'cluster_platform_components': ['flux'], 'cluster_platform_releases': [],
                'cluster_platform_action': 'render', 'cluster_platform_versions': {'flux': '2.16.4'},
                'cluster_platform_approved_repositories': ['https://fluxcd-community.github.io/helm-charts'],
                'cluster_platform_flux_source_approved': True,
                'cluster_platform_flux_url': 'https://recovery.verified.test/bootstrap.git',
                'cluster_platform_flux_commit': 'a' * 40,
                'cluster_platform_flux_path': './clusters/tier1/bootstrap',
                'cluster_platform_flux_canary_sha256': 'c' * 64,
                'cluster_platform_flux_platform_url': 'https://recovery.verified.test/platform.git',
                'cluster_platform_flux_platform_commit': 'b' * 40,
                'cluster_platform_flux_application_url': 'https://recovery.verified.test/apps.git',
                'cluster_platform_flux_application_namespaces': ['applications'],
                'cluster_platform_gitops_age_recipients': ['age1' + 'a' * 58]}

    @unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'helm', 'sops', 'age-keygen')), 'Requires native Flux render tools')
    def test_minimum_bootstrap_render_exports_real_flux_helm_owner_and_bootstrap_rbac(self):
        checkout = Path(self.temp.name) / 'configuration'
        checkout.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(checkout)], check=True, capture_output=True)
        cluster = checkout / 'clusters/tier1'
        (cluster / 'bootstrap').mkdir(parents=True)
        # This fixture represents the independently encrypted, pre-existing canary.
        (cluster / 'bootstrap/canary.sops.yaml').write_text('sops: {fixture: encrypted}\n')
        key = Path(self.temp.name) / 'private-age-key'
        subprocess.run(['age-keygen', '-o', str(key)], check=True, capture_output=True)
        recipient = subprocess.run(['age-keygen', '-y', str(key)], check=True,
                                   capture_output=True, text=True).stdout.strip()
        variables = self.tier1_inputs()
        variables.update(cluster_platform_gitops_root=str(cluster),
                         cluster_platform_output=str(Path(self.temp.name) / 'bootstrap-review'),
                         cluster_platform_gitops_age_recipients=[recipient])
        result = self.native_tasks([{'ansible.builtin.include_role': {'name': 'cluster_platform'}}],
                                   variables, 'real-bootstrap')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        index = yaml.safe_load((cluster / 'bootstrap/kustomization.yaml').read_text())
        self.assertEqual(index['resources'], ['ownership.yaml', 'canary.sops.yaml'])
        stage = cluster / 'platform/base/stages/platform-base-flux2-release/resources.yaml'
        release = next(item for item in yaml.safe_load_all(stage.read_text()) if item)
        self.assertEqual(release['kind'], 'HelmRelease')
        self.assertEqual(release['spec']['releaseName'], 'flux2')
        self.assertEqual(release['spec']['storageNamespace'], 'flux-system')
        self.assertEqual(release['spec']['driftDetection']['mode'], 'enabled')
        self.assertNotIn('TASK [helm_release : Apply', result.stdout)

    @unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in
                         ('ansible-playbook', 'helm', 'sops', 'age-keygen', 'openssl')), 'Requires native encrypted collector tools')
    def test_tier1_security_collectors_keep_node_identity_and_reject_a_second_writer(self):
        from test_tier_cluster_security_logging import settings
        from syslog_receiver_test_support import certificates
        directory = Path(self.temp.name)
        certificates(directory)
        checkout = directory / 'collector-source'
        checkout.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(checkout)], check=True, capture_output=True)
        (checkout / 'clusters/tier1').mkdir(parents=True)
        key = directory / 'collector-age'
        subprocess.run(['age-keygen', '-o', str(key)], check=True, capture_output=True)
        recipient = subprocess.run(['age-keygen', '-y', str(key)], check=True,
                                   capture_output=True, text=True).stdout.strip()
        values = settings(directory / 'review', tier=1)
        values.update(cluster_security_logging_owner='flux', cluster_security_logging_flux_migration='fresh',
                      cluster_security_logging_receiver_enrolled=True,
                      cluster_security_logging_talos_configured=True,
                      cluster_security_logging_host_access_accepted=True,
                      cluster_security_logging_flux_root=str(checkout / 'clusters/tier1'),
                      cluster_security_logging_flux_age_recipients=[recipient],
                      cluster_security_logging_manage_secrets=True,
                      cluster_security_logging_secrets={'security-logging/node-tls': {
                          'ca.crt': (directory / 'tls/ca.pem').read_text(),
                          'tls.crt': (directory / 'tls/producer.pem').read_text(),
                          'tls.key': (directory / 'tls/producer.key').read_text()}})
        task = [{'ansible.builtin.include_role': {'name': 'cluster_security_logging'}}]
        result = self.native_tasks(task, values, 'collectors')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        component = checkout / 'clusters/tier1/platform/security-logging'
        graph = list(yaml.safe_load_all((component / 'reconciliation.yaml').read_text()))
        stage = next(item for item in graph if item['metadata']['name'].endswith('-producer-release'))
        self.assertIn('status.desiredNumberScheduled == 1', stage['spec']['healthCheckExprs'][0]['current'])
        release_path = component / 'stages' / stage['metadata']['name'] / 'resources.yaml'
        release = next(item for item in yaml.safe_load_all(release_path.read_text()) if item)
        self.assertEqual(release['spec']['releaseName'], 'security-log-producer')
        self.assertEqual(release['spec']['storageNamespace'], 'security-logging')
        for path in component.rglob('*.yaml'):
            self.assertNotIn('-----BEGIN PRIVATE KEY-----', path.read_text())
        for override in ({'cluster_security_logging_action': 'apply'},
                         {'cluster_security_logging_tier': 0},
                         {'cluster_security_logging_receiver_enrolled': False},
                         {'cluster_security_logging_flux_migration': 'adopt'}):
            rejected = self.native_tasks(task, dict(values, **override), 'collector-rejection')
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_real_release_assembly_separates_pinned_sources_and_denies_unscoped_reconciliation(self):
        output = Path(self.temp.name) / 'release.json'
        tasks = [{'name': 'Assemble the real shared Flux installer contract', 'ansible.builtin.include_role': {
                     'name': 'cluster_platform', 'tasks_from': 'assemble.yml'},
                  'vars': {'cluster_platform_component': 'flux'}},
                 {'name': 'Retain the actual assembled release', 'ansible.builtin.copy': {
                     'dest': str(output), 'content': '{{ cluster_platform_releases[0] | to_json }}'}}]
        result = self.native_tasks(tasks, self.tier1_inputs())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        release = json.loads(output.read_text())
        self.assertEqual(release['values']['multitenancy']['defaultServiceAccount'], 'default')
        self.assertTrue(release['values']['multitenancy']['enabled'])
        self.assertEqual({item['kind'] for item in release['before']}, {'ServiceAccount', 'ClusterRoleBinding'})
        objects = {(item['kind'], item['metadata']['name']): item for item in release['after']}
        self.assertEqual(objects['GitRepository', 'platform']['spec']['ref'], {'commit': 'a' * 40})
        self.assertEqual(objects['GitRepository', 'tier1-platform']['spec']['ref'], {'commit': 'b' * 40})
        self.assertEqual(objects['GitRepository', 'tier1-applications']['spec']['ref'], {'branch': 'delivery'})
        self.assertEqual(objects['Kustomization', 'platform']['spec']['serviceAccountName'], 'platform-reconciler')
        self.assertEqual(objects['Kustomization', 'tier1-applications']['spec']['serviceAccountName'], 'application-reconciler')
        self.assertTrue(objects['Kustomization', 'tier1-applications']['spec']['suspend'])

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_preflight_keeps_tier0_boundary_and_rejects_privileged_application_aliases(self):
        task = [{'name': 'Validate actual bootstrap preconditions', 'ansible.builtin.include_role': {
            'name': 'cluster_platform', 'tasks_from': 'preflight.yml'}}]
        for index, override in enumerate(({}, {'cluster_platform_tier': 0},
                {'cluster_platform_flux_application_url': 'ssh://git@recovery.verified.test/platform/'},
                {'cluster_platform_flux_application_namespaces': ['observability']},
                {'cluster_platform_flux_application_namespaces': ['spinnaker']},
                {'cluster_platform_flux_application_namespaces': ['custom-platform'],
                 'cluster_platform_flux_additional_platform_namespaces': ['custom-platform']},
                {'cluster_platform_values': {'flux': {'multitenancy': {'enabled': False}}}},
                {'cluster_platform_values': {'flux': {'multitenancy': {'defaultServiceAccount': 'platform-reconciler'}}}})):
            with self.subTest(override=override):
                result = self.native_tasks(task, dict(self.tier1_inputs(), **override), f'preflight-{index}')
                self.assertEqual(result.returncode == 0, not override, result.stdout + result.stderr)

    def test_generated_inputs_payload_extensions_and_owned_refresh_are_preserved(self):
        self.generate()
        tier = self.root / 'verify-tier-1'
        example = yaml.safe_load((tier / 'ansible/group_vars/cluster_platform.yml.example').read_text())
        self.assertEqual(example['cluster_platform_management'], 'flux')
        self.assertEqual(example['cluster_platform_tier'], 1)
        self.assertIn('flux', example['cluster_platform_components'])
        for path in ('scripts/flux-recovery.py', 'ansible/playbooks/deployment/flux-maintenance.yml',
                     'ansible/playbooks/deployment/flux-recovery-git.yml', 'scripts/promotion/Dockerfile',
                     'pipelines/flux-promotion.yml.j2'):
            self.assertTrue((tier / path).is_file(), path)
        local = tier / 'clusters/tier1/platform/kustomization.yaml'
        local.write_text('apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources: []\n# Local ownership\n')
        self.generate('--refresh')
        self.assertIn('# Local ownership', local.read_text())
        initial = yaml.safe_load((UPSTREAM / 'tier-0/ansible/group_vars/cluster_platform.yml.example').read_text())
        self.assertEqual(initial['cluster_platform_flux_path'], './clusters/tier0')
        source = (UPSTREAM / 'shared/ansible/roles/cluster_platform/templates/flux.yml.j2').read_text()
        self.assertIn('commit: {{ cluster_platform_flux_commit | to_json }}', source)
        architecture = self.root / 'verify-architecture'
        canonical = architecture / 'docs/auto-docs/08-reference/diagrams/tier1-flux-ownership.svg'
        self.assertEqual(canonical.read_bytes(),
                         (UPSTREAM / 'docs/08-reference/diagrams/tier1-flux-ownership.svg').read_bytes())
        legacy = architecture / 'docs/auto-docs/reference/diagrams/tier1-flux-ownership.svg'
        self.assertFalse(legacy.exists())
        record = architecture / 'retained-diagram.md'
        record.write_text('[Retained view](docs/auto-docs/reference/diagrams/tier1-flux-ownership.svg)\n')
        self.generate('--refresh')
        self.assertEqual(legacy.read_bytes(), canonical.read_bytes())
        record.unlink()
        self.generate('--refresh')
        self.assertFalse(legacy.exists())
        self.assertTrue(canonical.is_file())

    @unittest.skipUnless(os.name != 'nt', 'Requires native Bash')
    def test_generated_initializer_creates_ansible_only_inputs_and_preserves_private_files(self):
        self.generate()
        tier = self.root / 'verify-tier-1'
        for setup in ('cluster-platform', 'flux-maintenance', 'flux-recovery-git', 'delivery-promotions'):
            result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', setup],
                                    cwd=tier, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        secret = tier / 'ansible/group_vars/cluster_platform_secrets.yml'
        self.assertTrue(secret.is_file())
        secret.write_text('$ANSIBLE_VAULT;1.1;AES256\nretained-encrypted-input\n')
        original = secret.read_bytes()
        result = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'cluster-platform'],
                                cwd=tier, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(secret.read_bytes(), original)
        wrong_tier = subprocess.run(['bash', 'scripts/init-local-files.sh', '--setup', 'delivery-promotions'],
                                   cwd=self.root / 'verify-tier-0', capture_output=True, text=True)
        self.assertNotEqual(wrong_tier.returncode, 0)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_base_dependencies_gate_custom_resources_without_certificate_ingress_deadlock(self):
        from test_tier_cluster_platform import inputs, PINS
        variables = dict(inputs(Path(self.temp.name)), **self.tier1_inputs())
        variables.update(cluster_platform_components=['cilium', 'storage', 'cert_manager', 'ingress',
                                                     'cloudnative_pg', 'barman_cloud', 'flux'],
                         cluster_platform_versions=PINS)
        output = Path(self.temp.name) / 'dependencies.json'
        tasks = [{'ansible.builtin.include_role': {'name': 'cluster_platform', 'tasks_from': 'assemble.yml'},
                  'vars': {'cluster_platform_component': component}}
                 for component in variables['cluster_platform_components']]
        tasks += [{'ansible.builtin.include_role': {'name': 'cluster_platform', 'tasks_from': 'tier1-dependencies.yml'}},
                  {'ansible.builtin.copy': {'dest': str(output),
                   'content': '{{ cluster_platform_flux_releases | to_json }}'}}]
        result = self.native_tasks(tasks, variables, 'dependencies')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        releases = {item['component']: item for item in json.loads(output.read_text())}
        self.assertEqual(releases['cert_manager']['after_depends_on'], [{'name': 'platform-base-traefik-release'}])
        self.assertNotIn({'name': 'platform-base-cert-manager-after'}, releases['ingress']['depends_on'])
        self.assertIn({'name': 'platform-base-csi-driver-nfs-after'}, releases['cloudnative_pg']['after_depends_on'])
        self.assertIn({'name': 'platform-base-cert-manager-release'}, releases['barman_cloud']['depends_on'])
        self.assertIn({'name': 'platform-base-cloudnative-pg-release'}, releases['barman_cloud']['depends_on'])

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_bootstrap_resource_permissions_do_not_give_applications_a_platform_writer(self):
        role = UPSTREAM / 'shared/ansible/roles/cluster_platform'
        directory = Path(self.temp.name)
        output = directory / 'ownership.yml'
        playbook = directory / 'permissions.yml'
        playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': {'cluster_platform_flux_application_namespaces': ['applications']}, 'tasks': [{
                'name': 'Render real bootstrap resource policy', 'ansible.builtin.template': {
                    'src': str(role / 'templates/tier1-bootstrap.yml.j2'), 'dest': str(output)}}]}]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)], capture_output=True,
                                text=True, env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(directory / 'local')))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        documents = list(yaml.safe_load_all(output.read_text()))
        app = next(item for item in documents if item['kind'] == 'Role')
        for rule in app['rules']:
            self.assertNotIn('rbac.authorization.k8s.io', rule['apiGroups'])
            self.assertNotIn('*', rule['resources'])
            self.assertFalse({'gitrepositories', 'kustomizations', 'clusterroles', 'roles', 'serviceaccounts'}
                             & set(rule['resources']))
            if 'persistentvolumeclaims' in rule['resources']:
                self.assertNotIn('delete', rule['verbs'])
        privilege = next(item for item in documents if item['kind'] == 'ClusterRoleBinding')
        self.assertEqual(privilege['subjects'], [{'kind': 'ServiceAccount', 'name': 'platform-reconciler',
                                                 'namespace': 'flux-system'}])


if __name__ == '__main__':
    unittest.main()
