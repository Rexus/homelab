"""Bounded Flux payload rendering, ownership and native SOPS round-trip checks."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, FileSystemLoader, StrictUndefined, pass_context
import yaml

from test_tier_observability_platform import platform_inputs
from native_chart_test_support import make_test_certificate
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'shared/ansible/roles/flux_payload'
OBSERVABILITY = UPSTREAM / 'tier-1/ansible/roles/observability_platform'


def render(role, template, inputs):
    environment = Environment(loader=FileSystemLoader(role / 'templates'),
                              undefined=StrictUndefined, trim_blocks=True)
    environment.filters.update(
        to_json=json.dumps,
        to_nice_yaml=lambda value: yaml.safe_dump(value, sort_keys=False),
        from_yaml=yaml.safe_load,
        from_yaml_all=lambda value: list(yaml.safe_load_all(value)),
        combine=lambda left, right: dict(left, **right),
        bool=bool,
        hash=lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest(),
    )

    @pass_context
    def lookup(context, plugin, path):
        if plugin == 'ansible.builtin.file':
            return Path(path).read_text()
        if plugin == 'ansible.builtin.template':
            return environment.get_template(path).render(context.get_all())
        raise ValueError(plugin)

    environment.globals['lookup'] = lookup
    return environment.get_template(template).render(inputs)


def payload_inputs(releases, **overrides):
    inputs = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
    inputs.update(flux_payload_component='platform/base', flux_payload_releases=releases)
    inputs.update(overrides)
    return inputs


def release_fixture():
    return dict(name='gitlab', namespace='gitlab', repository='https://charts.gitlab.io',
                chart='gitlab', version='10.5.0', values={'private': 'stable-private-value'},
                required_secrets=[dict(name='gitlab-root', keys=['password'])],
                health=[dict(api_version='apps/v1', kind='Deployment', name='gitlab-web', namespace='gitlab')],
                after=[dict(apiVersion='batch/v1', kind='Job', metadata=dict(name='initialize-v1', namespace='gitlab'),
                            spec=dict(backoffLimit=0, template=dict(spec=dict(restartPolicy='Never',
                                      containers=[dict(name='initialize', image='example.test/tool:1.0.0')]))))])


class FluxPayloadContracts(unittest.TestCase):
    def test_long_release_stage_names_preserve_helm_identity_without_metadata_collisions(self):
        release = release_fixture()
        release['name'] = 'security-log-' + 'a' * 39
        values = payload_inputs([release], flux_payload_component='platform/security-logging',
                                flux_payload_secrets={'gitlab/gitlab-root': {'password': 'retained-fixture'}})
        graph = yaml.safe_load(render(ROLE, 'graph.yml.j2', values))
        identities = [stage['name'] for stage in graph]
        self.assertTrue(all(len(name) <= 63 for name in identities))
        stage = next(item for item in graph if item['name'].endswith('-release'))
        manifest = stage['resources'][0]
        self.assertEqual(manifest['spec']['releaseName'], release['name'])
        inputs = graph[0]['resources']
        source = next(item for item in inputs if item['kind'] == 'HelmRepository')
        self.assertEqual(source['metadata']['name'], manifest['spec']['chart']['spec']['sourceRef']['name'])

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'Requires native Bash')
    def test_native_search_health_rejects_timeouts_and_incomplete_membership(self):
        inputs = platform_inputs()
        resources = yaml.safe_load(render(OBSERVABILITY, 'search-bootstrap.yml.j2', inputs))
        script = resources[0]['spec']['template']['spec']['containers'][0]['args'][0]
        syntax = subprocess.run(['bash', '-n'], input=script, capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        validation = 'health=$HEALTH_RESULT\n' + script[script.index("pattern='"):]
        healthy = dict(timed_out=False, status='green', number_of_nodes=3,
                       number_of_data_nodes=3, unassigned_shards=0)
        for change in ({}, {'timed_out': True}, {'status': 'yellow'}, {'number_of_nodes': 2},
                       {'number_of_data_nodes': 2}, {'unassigned_shards': 1}):
            with self.subTest(change=change):
                environment = dict(os.environ, HEALTH_RESULT=json.dumps(dict(healthy, **change)))
                result = subprocess.run(['bash', '-ec', validation], env=environment,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, not change, result.stdout + result.stderr)

    def test_helm_identity_rbac_values_and_native_health_are_preserved(self):
        release = release_fixture()
        inputs = payload_inputs([release], flux_payload_secrets={'gitlab/gitlab-root': {'password': 'retained'}})
        graph = yaml.safe_load(render(ROLE, 'graph.yml.j2', inputs))
        stages = {stage['name']: stage for stage in graph}
        native = stages['platform-base-gitlab-release']['resources'][0]
        self.assertEqual(native['metadata']['namespace'], 'flux-system')
        spec = native['spec']
        self.assertEqual((spec['releaseName'], spec['targetNamespace'], spec['storageNamespace']),
                         ('gitlab', 'gitlab', 'gitlab'))
        self.assertEqual(spec['serviceAccountName'], 'platform-reconciler')
        self.assertEqual(spec['driftDetection'], {'mode': 'enabled'})
        self.assertNotIn('values', spec)
        self.assertEqual(spec['chart']['spec']['version'], release['version'])
        resources = stages['platform-base-inputs']['resources']
        values = next(item for item in resources if item['metadata']['name'].endswith('-values'))
        self.assertEqual(values['metadata']['namespace'], 'flux-system')
        self.assertEqual(yaml.safe_load(values['stringData']['values.yaml']), release['values'])
        credentials = next(item for item in resources if item['metadata']['name'] == 'gitlab-root')
        self.assertEqual(credentials['metadata']['namespace'], 'gitlab')
        rendered = list(yaml.safe_load_all(render(ROLE, 'reconciliation.yml.j2',
                        dict(inputs, flux_payload_graph=graph))))
        reconciliations = {item['metadata']['name']: item for item in rendered if item}
        health = reconciliations['platform-base-gitlab-release']['spec']['healthChecks']
        self.assertEqual({item['kind'] for item in health}, {'HelmRelease', 'Deployment'})
        self.assertEqual(health[1]['apiVersion'], 'apps/v1')
        for item in reconciliations.values():
            self.assertEqual(item['spec']['sourceRef']['name'], 'tier1-platform')
            self.assertEqual(item['spec']['serviceAccountName'], 'platform-reconciler')
            self.assertEqual(item['spec']['decryption']['secretRef']['name'], 'platform-sops-age')
            self.assertIs(item['spec']['prune'], False)
            self.assertEqual(item['spec']['deletionPolicy'], 'Orphan')
            self.assertIs(item['spec']['force'], False)
        after = stages['platform-base-gitlab-after']
        self.assertEqual(after['depends_on'], [{'name': 'platform-base-gitlab-release'}])
        self.assertEqual(after['health'][0]['kind'], 'Job')

    def test_sensitive_native_objects_are_retained(self):
        resources = [dict(apiVersion='v1', kind=kind, metadata=dict(name='retained'))
                     for kind in ('Namespace', 'PersistentVolume', 'PersistentVolumeClaim', 'Secret', 'Job')]
        rendered = render(ROLE, 'resources.yml.j2', dict(flux_payload_stage={'resources': resources}))
        for item in yaml.safe_load_all(rendered):
            if item:
                self.assertEqual(item['metadata']['annotations']['kustomize.toolkit.fluxcd.io/prune'], 'disabled')
                self.assertEqual(item['metadata']['annotations']['helm.sh/resource-policy'], 'keep')

    def test_observability_preserves_search_bootstrap_database_and_backup_order(self):
        inputs = platform_inputs()
        inputs['observability_releases'] = yaml.safe_load(render(OBSERVABILITY, 'releases.yml.j2', inputs))
        contract = yaml.safe_load(render(OBSERVABILITY, 'flux-graph.yml.j2', inputs))
        releases = {item['name']: item for item in contract['releases']}
        stages = {item['name']: item for item in contract['stages']}
        self.assertIs(releases['opensearch']['disable_wait'], True)
        self.assertEqual(releases['opensearch']['after_health'][0]['kind'], 'Job')
        for name in ('data-prepper', 'otel-gateway', 'dashboards'):
            self.assertEqual(releases[name]['depends_on'], [{'name': 'platform-observability-opensearch-after'}])
        self.assertEqual(releases['grafana']['depends_on'], [{'name': 'platform-observability-backup'}])
        database = stages['platform-observability-grafana-before']
        self.assertIn('status.readyInstances == 3', database['health_check_exprs'][0]['current'])
        self.assertEqual({item['kind'] for item in database['resources']}, {'Cluster', 'ObjectStore', 'ScheduledBackup'})
        backup = stages['platform-observability-backup']
        self.assertEqual(backup['resources'][0]['kind'], 'Backup')
        self.assertIn('completed', backup['health_check_exprs'][0]['current'])
        script = releases['opensearch']['after'][0]['spec']['template']['spec']['containers'][0]['args'][0]
        self.assertIn('number_of_data_nodes', script)
        self.assertIn('unassigned_shards', script)
        self.assertNotIn('ttlSecondsAfterFinished', str(releases['opensearch']['after']))

    def test_legacy_inputs_keep_ansible_and_fresh_examples_select_flux(self):
        for name, prefix in [('observability_platform', 'observability'),
                             ('development_platform', 'development_platform')]:
            role = UPSTREAM / 'tier-1/ansible/roles' / name
            defaults = yaml.safe_load((role / 'defaults/main.yml').read_text())
            self.assertEqual(defaults[prefix + '_owner'], 'ansible')
            self.assertEqual(defaults[prefix + '_flux_migration'], '')
            self.assertIs(defaults[prefix + '_previous_writer_disabled'], False)
            main = (role / 'tasks/main.yml').read_text()
            self.assertIn(prefix + "_owner != 'flux' or " + prefix + "_action == 'render'", main)
            self.assertIn(prefix + "_owner == 'ansible'", main)
            example = yaml.safe_load((UPSTREAM / 'tier-1/ansible/group_vars' / (name + '.yml.example')).read_text())
            self.assertEqual(example[prefix + '_owner'], 'flux')
            self.assertEqual(example[prefix + '_flux_migration'], 'fresh')

    def test_database_only_and_nas_backup_phases_remain_separate(self):
        inputs = platform_inputs()
        inputs.update(observability_backup_mode='files', observability_backup_files_phase='prepare')
        inputs['observability_releases'] = yaml.safe_load(render(OBSERVABILITY, 'releases.yml.j2', inputs))
        grafana = next(item for item in inputs['observability_releases'] if item['name'] == 'grafana')
        inputs['observability_secrets'] = {
            'observability/' + secret['name']: {key: 'retained' for key in secret['keys']}
            for secret in grafana['required_secrets']
        }
        contract = yaml.safe_load(render(OBSERVABILITY, 'flux-graph.yml.j2', inputs))
        self.assertEqual(contract['releases'], [])
        self.assertEqual(len(contract['stages']), 1)
        resources = contract['stages'][0]['resources']
        self.assertEqual({item['kind'] for item in resources}, {'Cluster', 'Namespace', 'Secret'})
        self.assertNotIn('grafana-admin', {item['metadata']['name'] for item in resources})

        backup = dict(cluster='grafana-db', namespace='observability', claim='backup-claim',
                      volume_name='retained-nas-pv', volume_handle='nas-handle',
                      source_id='tier-1/observability/grafana-db', tls_secret='grafana-db-file-backup',
                      image=inputs['observability_database_image'], system_identifier='1234567890123456',
                      marker='a' * 24, schedule='0 2 * * *')
        backup_role = UPSTREAM / 'shared/ansible/roles/postgresql_file_backup'
        manifests = render(backup_role, 'resources.yml.j2', {'postgresql_file_backup_target': backup})
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / 'grafana-db-files.yml').write_text(manifests)
            inputs.update(observability_backup_files_phase='backup', observability_output=temporary,
                          observability_backup_files=backup)
            contract = yaml.safe_load(render(OBSERVABILITY, 'flux-graph.yml.j2', inputs))
        stages = {stage['name']: stage for stage in contract['stages']}
        storage = stages['platform-observability-backup-storage']
        self.assertIn('nas-handle', storage['health_check_exprs'][0]['current'])
        self.assertIn('1234567890123456', storage['health_check_exprs'][1]['current'])
        self.assertEqual(stages['platform-observability-backup']['depends_on'],
                         [{'name': 'platform-observability-backup-storage'}])
        job = next(item for item in stages['platform-observability-backup']['resources'] if item['kind'] == 'Job')
        self.assertEqual(job['spec']['backoffLimit'], 0)
        self.assertNotIn('ttlSecondsAfterFinished', job['spec'])


@unittest.skipUnless(os.name != 'nt' and all(shutil.which(tool) for tool in ('ansible-playbook', 'sops', 'age-keygen')),
                     'Requires native Ansible, SOPS and age-keygen')
class FluxPayloadNative(TierRepositoryTestCase):
    @unittest.skipUnless(shutil.which('kustomize'), 'Requires native Kustomize')
    def test_helm_pvc_retention_patch_preserves_names_and_existing_annotations(self):
        release = release_fixture()
        inputs = payload_inputs([release], flux_payload_secrets={'gitlab/gitlab-root': {'password': 'retained'}})
        graph = yaml.safe_load(render(ROLE, 'graph.yml.j2', inputs))
        helm = next(stage for stage in graph if stage['name'].endswith('-release'))['resources'][0]
        renderer = helm['spec']['postRenderers'][0]['kustomize']
        directory = Path(self.temp.name) / 'post-render'
        directory.mkdir()
        resources = [dict(apiVersion='v1', kind='PersistentVolumeClaim',
                          metadata=dict(name='data-' + str(index), annotations={'storage.test/accepted': 'true'}),
                          spec=dict(accessModes=['ReadWriteOnce'], resources=dict(requests=dict(storage='1Gi'))))
                     for index in (1, 2)]
        (directory / 'claims.yaml').write_text(yaml.safe_dump_all(resources))
        (directory / 'kustomization.yaml').write_text(yaml.safe_dump(dict(
            apiVersion='kustomize.config.k8s.io/v1beta1', kind='Kustomization',
            resources=['claims.yaml'], **renderer)))
        result = subprocess.run(['kustomize', 'build', str(directory)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        claims = list(yaml.safe_load_all(result.stdout))
        self.assertEqual({claim['metadata']['name'] for claim in claims}, {'data-1', 'data-2'})
        for claim in claims:
            self.assertEqual(claim['metadata']['annotations']['helm.sh/resource-policy'], 'keep')
            self.assertEqual(claim['metadata']['annotations']['storage.test/accepted'], 'true')

    def test_product_roles_render_native_lifecycles_without_cluster_access(self):
        checkout = Path(self.temp.name) / 'platform'
        checkout.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(checkout)], check=True, capture_output=True)
        cluster = checkout / 'clusters/tier1'
        cluster.mkdir(parents=True)
        key = Path(self.temp.name) / 'age-key.txt'
        subprocess.run(['age-keygen', '-o', str(key)], check=True, capture_output=True)
        recipient = subprocess.run(['age-keygen', '-y', str(key)], check=True, capture_output=True, text=True).stdout.strip()
        development = dict(
            development_platform_owner='flux', development_platform_flux_migration='fresh',
            development_platform_flux_root=str(cluster), development_platform_flux_age_recipients=[recipient],
            development_platform_components=['gitlab', 'runners'], development_platform_host='gitlab.test',
            development_platform_domain='test', development_platform_ingress_class='accepted',
            development_platform_gitlab_version='10.5.0', development_platform_runner_version='0.84.0',
            development_platform_database_host='postgres.test', development_platform_redis_host='redis.test',
            development_platform_gitaly_host='gitaly.test', development_platform_oidc_issuer='https://sso.test/realm',
            development_platform_output=str(Path(self.temp.name) / 'development-review'),
            development_platform_runner_image='build.test/image@sha256:' + 'a' * 64,
            development_platform_runner_helper_image='build.test/helper@sha256:' + 'b' * 64,
            development_platform_runner_allowed_cidrs=['192.0.2.1/32'],
            development_platform_runner_api_cidrs=['192.0.2.2/32'],
        )
        secrets = yaml.safe_load((UPSTREAM / 'tier-1/ansible/group_vars/development_platform_secrets.yml.example').read_text())
        development['development_platform_secrets'] = {
            name: {field: 'retained-private-value' for field in fields}
            for name, fields in secrets['development_platform_secrets'].items()
        }
        development['development_platform_secrets']['gitlab-runner-ca'] = {'gitlab.test.crt': 'retained-ca'}
        development['development_platform_secrets']['gitlab-rails-secret']['secrets.yml'] = yaml.safe_dump(dict(production=dict(
            secret_key_base='retained-private-value', otp_key_base='retained-private-value',
            db_key_base='retained-private-value', encrypted_settings_key_base='retained-private-value',
            openid_connect_signing_key='retained-private-value', active_record_encryption_primary_key=['retained-private-value'],
            active_record_encryption_deterministic_key=['retained-private-value'],
            active_record_encryption_key_derivation_salt='retained-private-value')))
        development['development_platform_secrets']['gitlab-oidc']['provider'] = yaml.safe_dump(dict(
            name='openid_connect', args=dict(issuer='https://sso.test/realm', uid_field='sub', discovery=True,
                 client_options=dict(redirect_uri='https://gitlab.test/users/auth/openid_connect/callback'))))
        observability = platform_inputs()
        observability.update(observability_owner='flux', observability_flux_migration='fresh',
            observability_flux_root=str(cluster), observability_flux_age_recipients=[recipient],
            observability_output=str(Path(self.temp.name) / 'observability-review'),
            observability_netdata_host_access_approved=True, observability_network_policy_verified=True,
            observability_search_kernel_verified=True)
        releases = yaml.safe_load(render(OBSERVABILITY, 'releases.yml.j2', observability))
        observability['observability_secrets'] = {
            release['namespace'] + '/' + secret['name']: {field: 'retained-private-value' for field in secret['keys']}
            for release in releases for secret in release['required_secrets']
        }
        observability['observability_secrets']['observability/prepper-search-auth']['username'] = 'data-prepper'
        for name in ('metrics-clients-ca', 'app-a-clients-ca', 'approved-clients-ca'):
            _, certificate = make_test_certificate(name)
            observability['observability_secrets']['observability/' + name]['ca.crt'] = certificate.decode()
        for name, variables in (('development_platform', development), ('observability_platform', observability)):
            with self.subTest(name=name):
                play = Path(self.temp.name) / 'products.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                     roles=[str(UPSTREAM / 'tier-1/ansible/roles' / name)], vars=variables)]))
                environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(UPSTREAM / 'shared/ansible/roles'),
                                   KUBECONFIG='/does-not-exist', SOPS_AGE_KEY_FILE=str(key))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                        env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for component in ('observability', 'source-control', 'ci-runners'):
            self.assertTrue((cluster / 'platform' / component / 'reconciliation.yaml').is_file())
        encrypted = cluster / 'platform/source-control/stages/platform-source-control-inputs/resources.yaml'
        decrypted = subprocess.run(['sops', '--decrypt', str(encrypted)], env=environment,
                                  check=True, capture_output=True, text=True).stdout
        resources = [item for item in yaml.safe_load_all(decrypted) if item]
        values = next(item for item in resources if item['metadata']['name'] == 'platform-source-control-gitlab-values')
        values = yaml.safe_load(values['stringData']['values.yaml'])
        self.assertIs(values['shared-secrets']['enabled'], False)
        self.assertEqual(values['global']['railsSecrets']['secret'], 'gitlab-rails-secret')
        self.assertIn('gitlab-gitlab-shell-host-keys', {item['metadata']['name'] for item in resources})
        self.assertIn('gitlab-rails-secret', {item['metadata']['name'] for item in resources})
        for path in (cluster / 'platform').rglob('*.yaml'):
            self.assertNotIn('retained-private-value', path.read_text())

    def test_ownership_guards_reject_implicit_adoption_and_apply(self):
        for name, prefix in [('observability_platform', 'observability'),
                             ('development_platform', 'development_platform')]:
            for overrides in ({}, {prefix + '_flux_migration': 'adopt'},
                              {prefix + '_flux_migration': 'fresh', prefix + '_action': 'apply'}):
                with self.subTest(name=name, overrides=overrides):
                    variables = {prefix + '_owner': 'flux', **overrides}
                    play = Path(self.temp.name) / 'guard.yml'
                    play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                        roles=[str(UPSTREAM / 'tier-1/ansible/roles' / name)], vars=variables)]))
                    result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('Require one explicit ongoing deployment owner', result.stdout)
                    self.assertNotIn('Prepare private', result.stdout)

    def test_private_source_and_generated_payload_encrypt_without_cluster_access(self):
        self.generate()
        key = Path(self.temp.name) / 'age-key.txt'
        subprocess.run(['age-keygen', '-o', str(key)], check=True, capture_output=True, text=True)
        recipient = subprocess.run(['age-keygen', '-y', str(key)], check=True, capture_output=True, text=True).stdout.strip()
        for role in (ROLE, self.root / 'verify-shared/ansible/roles/flux_payload'):
            with self.subTest(role=role):
                checkout = Path(self.temp.name) / ('source' if role == ROLE else 'generated')
                checkout.mkdir()
                subprocess.run(['git', 'init', '--quiet', str(checkout)], check=True, capture_output=True)
                cluster = checkout / 'clusters/tier1'
                cluster.mkdir(parents=True)
                fixture = payload_inputs([release_fixture()], flux_payload_root=str(cluster),
                          flux_payload_age_recipients=[recipient],
                          flux_payload_secrets={'gitlab/gitlab-root': {'password': 'retained-private-password'}})
                play = Path(self.temp.name) / 'render.yml'
                play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                      roles=[str(role)], vars=fixture)]))
                environment = dict(os.environ, KUBECONFIG='/does-not-exist',
                                   SOPS_AGE_KEY_FILE=str(key), ANSIBLE_LOCAL_TEMP=str(Path(self.temp.name) / 'ansible'))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                                        env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                directory = cluster / 'platform/base'
                inputs = directory / 'stages/platform-base-inputs/resources.yaml'
                encrypted = inputs.read_text()
                self.assertIn('ENC[AES256_GCM', encrypted)
                self.assertNotIn('retained-private-password', encrypted)
                self.assertNotIn('stable-private-value', encrypted)
                decrypted = subprocess.run(['sops', '--decrypt', str(inputs)], env=environment,
                                          check=True, capture_output=True, text=True).stdout
                documents = [item for item in yaml.safe_load_all(decrypted) if item]
                secret = next(item for item in documents if item['metadata']['name'] == 'gitlab-root')
                self.assertEqual(secret['stringData']['password'], 'retained-private-password')
                index = yaml.safe_load((directory / 'kustomization.yaml').read_text())
                self.assertEqual(index['resources'], ['reconciliation.yaml'])
                accepted = yaml.safe_load((directory / 'accepted/kustomization.yaml').read_text())
                self.assertEqual(accepted['resources'], [])
                reconciliations = [item for item in yaml.safe_load_all((directory / 'reconciliation.yaml').read_text()) if item]
                aggregate = next(item for item in reconciliations if item['metadata']['name'] == 'platform-base')
                children = {item['metadata']['name'] for item in reconciliations if item != aggregate}
                self.assertEqual({item['name'] for item in aggregate['spec']['dependsOn']}, children)
                self.assertTrue(aggregate['spec']['path'].endswith('/platform/base/accepted'))
                self.assertFalse((cluster / 'kustomization.yaml').exists())
                status = subprocess.run(['git', '-C', str(checkout), 'diff', '--cached', '--name-only'],
                                        check=True, capture_output=True, text=True).stdout
                self.assertEqual(status, '')


if __name__ == '__main__':
    unittest.main()
