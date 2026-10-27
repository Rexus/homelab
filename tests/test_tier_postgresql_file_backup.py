"""PostgreSQL NAS destination isolation, native manifests and optional PostgreSQL 17 roundtrip."""

import json
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import tempfile
import unittest

from jinja2 import Environment, FileSystemLoader, StrictUndefined, pass_context
import yaml

from tier_repo_test_support import TierRepositoryTestCase
from test_tier_control_applications import fixture as control_inputs, rendered_releases
from test_tier_observability_platform import ROLE as OBSERVABILITY, platform_inputs, render_template


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'shared/ansible/roles/postgresql_file_backup'


def inputs():
    return {
        'postgresql_file_backup_target': dict(
            cluster='keycloak-db', namespace='keycloak', image='ghcr.io/cloudnative-pg/postgresql:17.6',
            claim='keycloak-db-backups', tls_secret='keycloak-db-file-backup',
            source_id='tier-0/keycloak/keycloak-db', system_identifier='7512345678901234567',
            marker='commissioned-private-marker-12345', volume_handle='nas#private#keycloak',
            schedule='0 2 * * *', accepted=False),
        'postgresql_file_backup_recovery': dict(
            set_id='selected-pod-uid', storage_class='proxmox-block', size='10Gi', database='keycloak',
            secret='keycloak-db', server_tls_secret='files-restore-server', client_ca_secret='keycloak-db-ca',
            certificates=dict(serverCASecret='keycloak-db-ca', clientCASecret='keycloak-db-ca',
                              serverTLSSecret='keycloak-db-server', replicationTLSSecret='keycloak-db-replication')),
    }


def render(name, values=None):
    env = Environment(loader=FileSystemLoader(ROLE / 'templates'), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(to_json=json.dumps, quote=shlex.quote,
                       hash=lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest(),
                       to_nice_yaml=lambda value: yaml.safe_dump(value, sort_keys=False))

    @pass_context
    def lookup(context, plugin, path):
        assert plugin == 'ansible.builtin.template'
        return env.get_template(path).render(context.get_all())

    env.globals['lookup'] = lookup
    return env.get_template(name).render(values or inputs())


class PostgreSQLFileGeneration(TierRepositoryTestCase):
    def test_generated_shared_role_keeps_scripts_and_no_inventory(self):
        self.generate()
        generated = self.root / 'verify-shared/ansible/roles/postgresql_file_backup'
        for source in ROLE.rglob('*'):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (generated / source.relative_to(ROLE)).read_bytes())


class PostgreSQLFileContracts(unittest.TestCase):
    def test_object_mode_and_storage_fallback_remain_the_defaults(self):
        releases = rendered_releases()
        keycloak = next(item for item in releases if item['name'] == 'keycloak')
        cluster = next(item for item in keycloak['before'] if item['kind'] == 'Cluster')
        self.assertTrue(cluster['spec']['plugins'][0]['isWALArchiver'])
        self.assertEqual(cluster['spec']['storage']['storageClass'], 'accepted-storage')
        for tier, prefix, role in [(0, 'control_applications', 'control_applications'),
                                   (1, 'observability', 'observability_platform')]:
            defaults = yaml.safe_load((ROOT / f'tier-{tier}/ansible/roles/{role}/defaults/main.yml').read_text())
            self.assertEqual(defaults[prefix + '_backup_mode'], 'object')
            self.assertFalse(defaults[prefix + '_backup_files_accepted'])

    def test_files_mode_separates_live_block_disks_media_and_nas(self):
        releases = rendered_releases(dict(control_applications_backup_mode='files',
                                         control_applications_database_storage_class='proxmox-block',
                                         control_applications_netbox_media_storage_class='media-rwx'))
        for product in ('keycloak', 'netbox'):
            release = next(item for item in releases if item['name'] == product)
            self.assertEqual([item['kind'] for item in release['before'] if item['kind'] == 'Cluster'], ['Cluster'])
            self.assertFalse(any(item['kind'] in ('ObjectStore', 'ScheduledBackup') for item in release['before']))
            cluster = next(item for item in release['before'] if item['kind'] == 'Cluster')
            self.assertNotIn('plugins', cluster['spec'])
            self.assertEqual(cluster['spec']['storage']['storageClass'], 'proxmox-block')
            self.assertNotIn('backups', json.dumps(cluster))
            self.assertIn(f'cnpg_streaming_replica {product}-db-file-backup streaming_replica',
                          cluster['spec']['postgresql']['pg_ident'])
            self.assertFalse(any(item['kind'] == 'Backup' for item in release['after']))
        netbox = next(item for item in releases if item['name'] == 'netbox')
        self.assertEqual(netbox['values']['persistence']['storageClass'], 'media-rwx')
        values = platform_inputs() | dict(observability_backup_mode='files',
                                         observability_database_storage_class='ceph-rbd')
        clusters = yaml.safe_load(render_template(OBSERVABILITY, 'grafana-database.yml.j2', values))
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]['spec']['storage']['storageClass'], 'ceph-rbd')
        self.assertEqual(clusters[0]['spec']['certificates']['clientCASecret'], 'grafana-db-client-ca')

    def test_native_job_identity_permissions_and_initial_job_share_one_spec(self):
        config, cron, first = list(yaml.safe_load_all(render('resources.yml.j2')))
        self.assertEqual(cron['apiVersion'], 'batch/v1')
        self.assertEqual(cron['metadata']['name'], 'keycloak-db-files')
        self.assertEqual(cron['spec']['concurrencyPolicy'], 'Forbid')
        self.assertEqual(cron['spec']['jobTemplate']['spec'], first['spec'])
        self.assertRegex(first['metadata']['name'], r'^keycloak-db-files-first-[a-f0-9]{10}$')
        changed = inputs()
        changed['postgresql_file_backup_target']['image'] = 'ghcr.io/cloudnative-pg/postgresql:17.7'
        revised = list(yaml.safe_load_all(render('resources.yml.j2', changed)))[2]
        self.assertNotEqual(first['metadata']['name'], revised['metadata']['name'])
        self.assertEqual(first['spec']['backoffLimit'], 0)
        pod = first['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(pod['volumes'][0]['persistentVolumeClaim']['claimName'], 'keycloak-db-backups')
        mounts = pod['containers'][0]['volumeMounts']
        self.assertEqual(next(m for m in mounts if m['name'] == 'repository')['mountPath'], '/repository')
        self.assertTrue(next(m for m in mounts if m['name'] == 'tls')['readOnly'])
        script = config['data']['backup.sh']
        self.assertLess(script.index('IDENTIFY_SYSTEM'), script.index('pg_basebackup --pgdata'))
        self.assertLess(script.index('pg_verifybackup --exit-on-error'), script.index('mv -T'))
        self.assertIn('--no-clean', script)
        self.assertLess(script.index('wal_sender_timeout'), script.index('pg_basebackup --pgdata'))
        self.assertNotIn('pg_dump', script)
        self.assertNotIn('rm ', script)
        self.assertIn('cmp /tmp/expected-source "$root/.postgresql-backup-source"', script)

    def test_prepare_phase_does_not_require_a_guessed_system_identifier(self):
        for tier, prefix, name in [(0, 'control_applications', 'control_applications'),
                                   (1, 'observability', 'observability_platform')]:
            role = ROOT / f'tier-{tier}/ansible/roles/{name}'
            main = yaml.safe_load((role / 'tasks/main.yml').read_text())
            backup = next(t for t in main if t.get('ansible.builtin.include_tasks') == 'database-files.yml' or
                          t.get('ansible.builtin.include_role', {}).get('name') == 'postgresql_file_backup')
            self.assertIn(prefix + "_backup_files_phase == 'backup'", backup['when'])
            prep = (role / 'tasks/database-prepare.yml').read_text()
            self.assertIn('status.systemID', prep)
            self.assertNotIn('marker:', prep)

    def test_restore_keeps_nas_read_only_and_bootstraps_a_fresh_cluster(self):
        objects = list(yaml.safe_load_all(render('restore-source.yml.j2')))
        job = next(o for o in objects if o['kind'] == 'Job')
        pod = job['spec']['template']['spec']
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertTrue(pod['volumes'][0]['persistentVolumeClaim']['readOnly'])
        stage = next(o for o in objects if o['kind'] == 'PersistentVolumeClaim')
        self.assertEqual(stage['spec']['storageClassName'], 'proxmox-block')
        target = yaml.safe_load(render('restore-cluster.yml.j2'))
        self.assertEqual(set(target['spec']['bootstrap']), {'pg_basebackup'})
        self.assertEqual(target['spec']['externalClusters'][0]['connectionParameters']['sslmode'], 'verify-full')
        self.assertNotIn('plugins', target['spec'])
        script = render('restore.sh.j2')
        self.assertLess(script.index('pg_verifybackup'), script.index('cp -a'))
        self.assertIn('find /work -mindepth 1', script)
        self.assertIn('pg_ctl -D /work/pgdata', script)
        config = render('standalone.conf.j2')
        self.assertIn("synchronous_standby_names = ''", config)
        self.assertIn('archive_mode = off', config)

    def test_backup_network_policy_does_not_inherit_broad_namespace_egress(self):
        values = platform_inputs() | dict(observability_backup_mode='files', component='metrics',
                                         selected_namespace='observability')
        policies = yaml.safe_load(render_template(OBSERVABILITY, 'network-policy.yml.j2', values))
        baseline, backup = policies
        self.assertEqual(baseline['spec']['podSelector']['matchExpressions'][0]['values'], ['postgresql-file-backup'])
        self.assertEqual(backup['spec']['ingress'], [])
        self.assertEqual(backup['spec']['egress'][0]['to'],
                         [{'podSelector': {'matchLabels': {'cnpg.io/cluster': 'grafana-db'}}}])
        self.assertEqual(backup['spec']['egress'][0]['ports'], [{'protocol': 'TCP', 'port': 5432}])

    def test_native_ansible_render_and_guard_rejection_without_cluster_access(self):
        extra = os.environ.get('POSTGRESQL_FILES_ANSIBLE_PYTHONPATH')
        if not extra:
            self.skipTest('Set POSTGRESQL_FILES_ANSIBLE_PYTHONPATH to native Ansible Core')
        import sys
        with tempfile.TemporaryDirectory(prefix='postgresql-files-render-') as directory:
            temp = Path(directory)
            values = inputs() | dict(postgresql_file_backup_action='render',
                                    postgresql_file_backup_output=str(temp / 'rendered'))
            variables = temp / 'vars.yml'
            variables.write_text(yaml.safe_dump(values))
            playbook = temp / 'play.yml'
            playbook.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                tasks=[{'ansible.builtin.include_role': {'name': 'postgresql_file_backup'}},
                       {'ansible.builtin.include_role': {'name': 'postgresql_file_backup', 'tasks_from': 'recovery'}}])]))
            env = dict(os.environ, PYTHONPATH=extra + os.pathsep + os.environ.get('PYTHONPATH', ''),
                       ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_LOCAL_TEMP=str(temp / 'ansible'))
            if os.environ.get('POSTGRESQL_FILES_COLLECTIONS'):
                env['ANSIBLE_COLLECTIONS_PATH'] = os.environ['POSTGRESQL_FILES_COLLECTIONS']
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                     str(playbook), '-e', '@' + str(variables)], env=env,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((temp / 'rendered/restore-source.yml').exists())
            prepare_playbook = temp / 'prepare.yml'
            control = control_inputs() | dict(control_applications_action='render',
                control_applications_backup_mode='files', control_applications_backup_files_phase='prepare',
                control_applications_database_storage_class='proxmox-block',
                control_applications_netbox_media_storage_class='media-rwx',
                control_applications_output=str(temp / 'tier0'))
            observability = platform_inputs() | dict(observability_action='render',
                observability_backup_mode='files', observability_backup_files_phase='prepare',
                observability_database_storage_class='ceph-rbd', observability_output=str(temp / 'tier1'))
            prepare_playbook.write_text(yaml.safe_dump([
                dict(hosts='localhost', connection='local', gather_facts=False, vars=prepare_variables,
                     tasks=[{'ansible.builtin.include_role': {'name': name}}])
                for name, prepare_variables in [('control_applications', control), ('observability_platform', observability)]]))
            env['ANSIBLE_ROLES_PATH'] = os.pathsep.join([str(ROLE.parent),
                str(ROOT / 'tier-0/ansible/roles'), str(ROOT / 'tier-1/ansible/roles')])
            prepare = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                      str(prepare_playbook)], env=env, text=True, capture_output=True)
            self.assertEqual(prepare.returncode, 0, prepare.stdout + prepare.stderr)
            self.assertTrue((temp / 'tier0/keycloak-database-prepare.yml').exists())
            self.assertTrue((temp / 'tier1/grafana-database-prepare.yml').exists())
            self.assertFalse(list((temp / 'tier0').glob('*-files.yml')))
            values['postgresql_file_backup_target']['marker'] = ''
            (temp / 'vars.yml').write_text(yaml.safe_dump(values))
            rejected = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                       str(playbook), '-e', '@' + str(temp / 'vars.yml')], env=env,
                                      text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('exact source identity', rejected.stdout)

    def test_file_clusters_and_recovery_match_pinned_cnpg_schema(self):
        cache = Path(os.environ.get('CNPG_CRD_CACHE', ROOT / '.tmp/cnpg-crd-1.27.0'))
        schema_path = cache / 'postgresql.cnpg.io_clusters.yaml'
        if not schema_path.exists():
            self.skipTest('Official CNPG 1.27.0 CRD cache unavailable')
        import jsonschema
        crd = yaml.safe_load(schema_path.read_text())
        schema = next(v for v in crd['spec']['versions'] if v['name'] == 'v1')['schema']['openAPIV3Schema']
        objects = [yaml.safe_load(render('restore-cluster.yml.j2'))]
        values = platform_inputs() | dict(observability_backup_mode='files',
                                         observability_database_storage_class='ceph-rbd')
        objects += yaml.safe_load(render_template(OBSERVABILITY, 'grafana-database.yml.j2', values))
        for obj in objects:
            jsonschema.Draft7Validator(schema).validate(obj)


class PostgreSQLNativeRoundtrip(unittest.TestCase):
    def test_full_backup_wal_verification_standalone_recovery_and_second_clone(self):
        binary = Path(os.environ.get('POSTGRESQL17_BIN', '/usr/pgsql-17/bin'))
        if os.name == 'nt' or not (binary / 'initdb').exists():
            self.skipTest('Set POSTGRESQL17_BIN to native PostgreSQL 17 tools')
        with tempfile.TemporaryDirectory(prefix='postgresql-files-') as directory:
            root = Path(directory)
            data = root / 'source'
            source_port, restore_port = self.free_port(), self.free_port()
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'])

            def run(*args):
                return subprocess.run(args, env=env, text=True, capture_output=True, check=True)

            run('initdb', '-D', str(data), '-A', 'trust', '-U', 'postgres')
            for name, cn in [('server', 'localhost'), ('client', 'keycloak-db-file-backup')]:
                run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=' + cn, '-addext', 'subjectAltName=DNS:' + cn,
                    '-keyout', str(root / (name + '.key')), '-out', str(root / (name + '.crt')))
                (root / (name + '.key')).chmod(0o600)
            with (data / 'postgresql.conf').open('a') as config:
                config.write(f"\nssl=on\nssl_cert_file='{root}/server.crt'\nssl_key_file='{root}/server.key'\n"
                             f"ssl_ca_file='{root}/client.crt'\n")
            (data / 'pg_hba.conf').write_text(
                'local all all trust\n'
                'hostssl postgres streaming_replica 127.0.0.1/32 cert map=cnpg_streaming_replica\n'
                'hostssl replication streaming_replica 127.0.0.1/32 cert map=cnpg_streaming_replica\n')
            (data / 'pg_ident.conf').write_text(
                'cnpg_streaming_replica keycloak-db-file-backup streaming_replica\n')
            started = []
            try:
                run('pg_ctl', '-D', str(data), '-o', f'-h 127.0.0.1 -p {source_port} -k {root}', '-w', 'start',
                    '-l', str(root / 'source.log'))
                started.append(data)
                run('psql', '-h', str(root), '-p', str(source_port), '-U', 'postgres', '-d', 'postgres',
                    '-c', 'CREATE ROLE streaming_replica WITH REPLICATION LOGIN; '
                          'CREATE TABLE recovery_probe AS SELECT 42 AS value')
                env.update(PGSSLMODE='verify-full', PGSSLROOTCERT=str(root / 'server.crt'),
                           PGSSLCERT=str(root / 'client.crt'), PGSSLKEY=str(root / 'client.key'))
                identity = run('psql', '-h', 'localhost', '-p', str(source_port), '-U', 'streaming_replica',
                               '-d', 'replication=true', '-Atc', 'IDENTIFY_SYSTEM')
                self.assertRegex(identity.stdout, r'^\d+\|')
                repository = root / 'repository'
                repository.mkdir()
                for name in ('pending', 'completed'):
                    (repository / name).mkdir()
                target = inputs()['postgresql_file_backup_target']
                identifier = identity.stdout.split('|')[0]
                marker = f"{target['source_id']}\n{identifier}\n{target['marker']}\n"
                (repository / '.postgresql-backup-source').write_text(marker)
                script = render('backup.sh.j2').replace('root=/repository', 'root=' + shlex.quote(str(repository)))
                script = script.replace('/tmp/expected-source', str(root / 'expected-source'))
                # Native database tests use a local directory; CSI mount qualification is a separate live gate.
                script = script.replace(
                    'awk -v path="$root" \'$5 == path { found=1 } END { exit !found }\' /proc/self/mountinfo', ':')
                backup_script = root / 'backup.sh'
                backup_script.write_text(script)
                env.update(PGHOST='localhost', PGPORT=str(source_port), PGUSER='streaming_replica',
                           PGDATABASE='postgres', SOURCE_ID=target['source_id'], SYSTEM_IDENTIFIER=identifier,
                           DESTINATION_MARKER=target['marker'], POSTGRES_IMAGE=target['image'], BACKUP_RUN='native-pass')
                run('bash', str(backup_script))
                backup = repository / 'completed/native-pass/pgdata'
                run('pg_verifybackup', str(backup))
                def set_sender_timeout(value):
                    command = ['psql', '-h', str(root), '-p', str(source_port), '-U', 'postgres', '-d', 'postgres']
                    run(*command, '-c', f"ALTER SYSTEM SET wal_sender_timeout = '{value}'")
                    run(*command, '-c', 'SELECT pg_reload_conf()')
                    expected = '0' if value == '0' else '60000'
                    for _ in range(30):
                        query = "SELECT setting FROM pg_settings WHERE name = 'wal_sender_timeout'"
                        if run(*command, '-Atc', query).stdout.strip() == expected:
                            return
                    self.fail('WAL sender timeout did not reload')

                set_sender_timeout('0')
                env['BACKUP_RUN'] = 'unbounded-wal'
                with self.assertRaises(subprocess.CalledProcessError):
                    run('bash', str(backup_script))
                self.assertFalse((repository / 'pending/unbounded-wal').exists())
                set_sender_timeout('60s')
                env['BACKUP_RUN'] = 'native-pass'
                with self.assertRaises(subprocess.CalledProcessError):
                    run('bash', str(backup_script))
                env['BACKUP_RUN'] = 'wrong-source'
                env['SYSTEM_IDENTIFIER'] = str(int(identifier) + 1)
                (repository / '.postgresql-backup-source').write_text(marker.replace(identifier, env['SYSTEM_IDENTIFIER']))
                with self.assertRaises(subprocess.CalledProcessError):
                    run('bash', str(backup_script))
                self.assertFalse((repository / 'pending/wrong-source').exists())
                env['SYSTEM_IDENTIFIER'] = identifier
                env['BACKUP_RUN'] = 'corrupted'
                (repository / '.postgresql-backup-source').write_text(marker)
                backup_script.write_text(script.replace('pg_verifybackup --exit-on-error',
                    'printf corruption > "$pending/pgdata/base/unexpected-file"\npg_verifybackup --exit-on-error'))
                with self.assertRaises(subprocess.CalledProcessError):
                    run('bash', str(backup_script))
                self.assertTrue((repository / 'pending/corrupted/pgdata').exists())
                self.assertFalse((repository / 'completed/corrupted').exists())
                stage = root / 'stage'
                shutil.copytree(backup, stage)
                run('pg_ctl', '-D', str(stage), '-o', f'-h 127.0.0.1 -p {restore_port} -k {root} -c archive_mode=off',
                    '-w', 'start', '-l', str(root / 'restored.log'))
                started.append(stage)
                query = run('psql', '-h', str(root), '-p', str(restore_port), '-U', 'postgres',
                            '-d', 'postgres', '-Atc', 'SELECT value FROM recovery_probe')
                self.assertEqual(query.stdout.strip(), '42')
                clone = root / 'cnpg-equivalent-clone'
                run('pg_basebackup', '-h', 'localhost', '-p', str(restore_port), '-U', 'streaming_replica',
                    '-D', str(clone), '-Fp', '-Xstream')
                run('pg_verifybackup', str(clone))
                (backup / 'base' / 'unexpected-file').write_text('corruption')
                with self.assertRaises(subprocess.CalledProcessError):
                    run('pg_verifybackup', str(backup))
            finally:
                for started_data in reversed(started):
                    run('pg_ctl', '-D', str(started_data), '-m', 'fast', '-w', 'stop')

    @staticmethod
    def free_port():
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            return listener.getsockname()[1]
