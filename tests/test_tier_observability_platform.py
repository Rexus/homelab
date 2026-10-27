"""Render product-owned native values; optionally render exact cached Helm packages.

Set HELM_BINARY and OBSERVABILITY_CHART_CACHE (directory of pinned .tgz packages)
to run native rendering without a cluster or network. No secrets are loaded.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from jinja2 import Environment, FileSystemLoader, StrictUndefined, pass_context
import yaml

from tier_repo_test_support import TierRepositoryTestCase
from native_chart_test_support import cached_https_repository, make_test_certificate


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "tier-1/ansible/roles/observability_platform"
MONITORING = ROOT / "tier-0/ansible/roles/infrastructure_monitoring"


DATA_PREPPER_CHECK = r'''
package org.opensearch.dataprepper.plugin;
import java.io.File;
import java.util.Map;
import java.util.Set;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Validation;
import org.apache.commons.text.similarity.LevenshteinDistance;
import org.opensearch.dataprepper.model.configuration.PluginSetting;
import org.opensearch.dataprepper.model.event.EventKeyFactory;
import org.opensearch.dataprepper.pipeline.parser.DataPrepperDeserializationProblemHandler;

public class DataPrepperConfigCheck {
    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        var factory = new ObjectMapperConfiguration();
        var handler = new DataPrepperDeserializationProblemHandler();
        var extensionMapper = factory.extensionPluginConfigObjectMapper(handler);
        var keyConstructor = Class.forName("org.opensearch.dataprepper.event.DefaultEventKeyFactory")
            .getDeclaredConstructor();
        keyConstructor.setAccessible(true);
        var keys = (EventKeyFactory) keyConstructor.newInstance();
        var mapper = factory.pluginConfigObjectMapper(new VariableExpander(extensionMapper, Set.of()), keys, handler);
        var validatorFactory = Validation.byDefaultProvider().configure()
            .messageInterpolator(new org.hibernate.validator.messageinterpolation.ParameterMessageInterpolator())
            .buildValidatorFactory();
        var converter = new PluginConfigurationConverter(validatorFactory.getValidator(), mapper,
            new PluginConfigurationErrorHandler(new LevenshteinDistance()));
        var types = Map.of(
            "otel_logs_source", "org.opensearch.dataprepper.plugins.source.otellogs.OTelLogsSourceConfig",
            "otel_trace_source", "org.opensearch.dataprepper.plugins.source.oteltrace.OTelTraceSourceConfig",
            "bounded_blocking", "org.opensearch.dataprepper.plugins.buffer.blockingbuffer.BlockingBufferConfig",
            "opensearch", "org.opensearch.dataprepper.plugins.sink.opensearch.configuration.OpenSearchSinkConfig",
            "http_basic", "org.opensearch.dataprepper.armeria.authentication.HttpBasicAuthenticationConfig");
        Map<String, Object> pipelines = new ObjectMapper().readValue(new File(args[0]), Map.class);
        int checked = 0;
        for (var entry : pipelines.entrySet()) {
            Map<String, Object> pipeline = (Map<String, Object>) entry.getValue();
            for (String phase : new String[]{"source", "buffer", "sink"}) {
                Object value = pipeline.get(phase);
                var settings = value instanceof java.util.List ? (java.util.List<?>) value : java.util.List.of(value);
                for (Object object : settings) {
                    Map<String, Object> plugins = (Map<String, Object>) object;
                    for (var plugin : plugins.entrySet()) {
                        var config = (Map<String, Object>) plugin.getValue();
                        converter.convert(Class.forName(types.get(plugin.getKey())),
                            new PluginSetting(plugin.getKey(), config));
                        checked++;
                        if (config.containsKey("authentication")) {
                            Map<String, Object> auth = (Map<String, Object>) config.get("authentication");
                            converter.convert(Class.forName(types.get("http_basic")),
                                new PluginSetting("http_basic", (Map<String, Object>) auth.get("http_basic")));
                            checked++;
                        }
                    }
                }
            }
        }
        validatorFactory.close();
        System.out.println("Native Data Prepper plugin configurations accepted: " + checked);
    }
}
'''


def render_template(role, name, variables):
    env = Environment(loader=FileSystemLoader(role / 'templates'), undefined=StrictUndefined,
                      trim_blocks=True)
    env.filters.update(
        to_json=json.dumps,
        to_nice_yaml=lambda value: yaml.safe_dump(value, sort_keys=False),
        combine=lambda left, right: dict(left, **right),
        hash=lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest(),
    )

    @pass_context
    def lookup(context, plugin, path):
        if plugin != "ansible.builtin.template":
            raise ValueError(plugin)
        return env.from_string((role / "templates" / path).read_text()).render(context.get_all())

    env.globals["lookup"] = lookup
    return env.from_string((role / "templates" / name).read_text()).render(variables)


def platform_inputs():
    values = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    values.update(
        observability_search_bootstrap=True,
        observability_storage_class="test-retained",
        observability_failure_domains=["host-a", "host-b", "host-c"],
        observability_backup_destination="s3://test-backups/grafana-db",
        observability_backup_endpoint="https://backup.test",
        observability_grafana_url="https://grafana.test",
        observability_dashboards_url="https://dashboards.test",
        observability_oidc_issuer="https://sso.test/realms/platform",
        observability_search_node_dns=["CN=search.test"],
        observability_search_admin_dns=["CN=admin.test"],
        observability_netdata_child_key="11111111-2222-4333-8444-555555555555",
        observability_netdata_peer_key="21111111-2222-4333-8444-555555555555",
        observability_netdata_allow_from="10.20.*",
        observability_netdata_scrape_metrics=["netdata_system_cpu_percentage_average"],
        observability_log_scopes=[
            dict(name="app-a", kind="application", port=4400, node_port=30400,
                 reader_backend_roles=["app-a-readers"]),
            dict(name="approved", kind="projection", port=4401, node_port=30401,
                 reader_backend_roles=["security-readers"]),
        ],
    )
    return values


class ObservabilityNativeValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = platform_inputs()
        cls.releases = yaml.safe_load(render_template(ROLE, "releases.yml.j2", cls.inputs))
        cls.by_name = {release["name"]: release for release in cls.releases}

    def test_dual_writes_do_not_balance_independent_stores(self):
        config = self.by_name["otel-gateway"]["values"]["config"]
        pipeline = config["service"]["pipelines"]["metrics"]
        self.assertEqual(pipeline["exporters"], ["otlphttp/metrics-1", "otlphttp/metrics-2"])
        for member in ("metrics-1", "metrics-2"):
            exporter = config["exporters"]["otlphttp/" + member]
            self.assertEqual(exporter["metrics_endpoint"],
                             f"https://{member}:8428/opentelemetry/v1/metrics")
            self.assertEqual(exporter["sending_queue"]["storage"], "file_storage")
            self.assertEqual(self.by_name[member]["values"]["server"]["replicaCount"], 1)
        selectors = [self.by_name[member]["values"]["server"]["nodeSelector"]
                     for member in ("metrics-1", "metrics-2")]
        self.assertNotEqual(selectors[0], selectors[1])

    def test_source_identity_selects_fixed_index_not_submitted_attributes(self):
        gateway = self.by_name["otel-gateway"]["values"]["config"]
        pipelines = gateway["service"]["pipelines"]
        self.assertIsNone(pipelines["logs"])
        self.assertNotIn("traces/approved", pipelines)
        self.assertEqual(pipelines["logs/approved"]["receivers"], ["otlp/approved"])
        receivers = gateway["receivers"]
        self.assertNotEqual(receivers["otlp/app-a"], receivers["otlp/approved"])
        prepper = self.by_name["data-prepper"]["values"]["pipelineConfig"]["config"]
        self.assertNotIn("approved-traces", prepper)
        self.assertEqual(prepper["approved-logs"]["sink"][0]["opensearch"]["index"],
                         "projection-approved-logs-%{yyyy.MM.dd}")
        for name, pipeline in prepper.items():
            processors = pipeline.get("processor", [])
            fields = ['body', 'body/record'] if name == 'approved-logs' else []
            self.assertEqual([list(processor) for processor in processors], [['parse_json']] * len(fields))
            self.assertEqual([processor['parse_json']['source'] for processor in processors], fields)
            self.assertEqual([processor['parse_json']['destination'] for processor in processors], fields)
            self.assertTrue(all(processor['parse_json']['overwrite_if_destination_exists']
                                for processor in processors))
            self.assertFalse(pipeline["sink"][0]["opensearch"]["insecure"])

    def test_reader_role_has_no_write_or_management_action(self):
        policy = self.by_name["opensearch"]["values"]["securityConfig"]["config"]["data"]
        for scope in self.inputs["observability_log_scopes"]:
            role = policy["roles.yml"]["read_" + scope["name"]]
            self.assertEqual(role["index_permissions"][0]["allowed_actions"], ["read"])
            self.assertEqual(role["index_permissions"][0]["index_patterns"],
                             [f"{scope['kind']}-{scope['name']}-*"])
        users = self.by_name["opensearch"]["required_secrets"]
        self.assertIn(dict(name="search-users", keys=["internal_users.yml"]), users)

    def test_native_oidc_has_signed_groups_and_no_anonymous_ui_fallback(self):
        policy = self.by_name['opensearch']['values']['securityConfig']['config']['data']['config.yml']
        dynamic = policy['config']['dynamic']
        self.assertFalse(dynamic['http']['anonymous_auth_enabled'])
        domain = dynamic['authc']['openid_auth_domain']
        self.assertEqual(domain['http_authenticator']['type'], 'openid')
        config = domain['http_authenticator']['config']
        self.assertEqual(config['roles_key'], 'groups')
        self.assertEqual(config['required_issuer'], self.inputs['observability_oidc_issuer'])
        self.assertEqual(config['required_audience'], self.inputs['observability_oidc_dashboards_client_id'])
        self.assertTrue(config['openid_connect_idp']['verify_hostnames'])
        self.assertFalse(dynamic['authc']['basic_internal_auth_domain']['http_authenticator']['challenge'])
        dashboards = yaml.safe_load(self.by_name['dashboards']['values']['config']['opensearch_dashboards.yml'])
        self.assertEqual(dashboards['opensearch_security.auth.type'], 'openid')
        self.assertEqual(dashboards['opensearch_security.openid.client_secret'], '${OPENID_CLIENT_SECRET}')
        grafana = self.by_name['grafana']['values']['grafana.ini']
        self.assertFalse(grafana['auth.basic']['enabled'])
        self.assertFalse(grafana['auth.anonymous']['enabled'])
        self.assertTrue(grafana['auth.generic_oauth']['role_attribute_strict'])
        self.assertTrue(grafana['auth.generic_oauth']['validate_id_token'])
        self.assertFalse(grafana['auth.generic_oauth']['allow_assign_grafana_admin'])
        self.assertTrue(grafana['security']['cookie_secure'])
        self.assertEqual(grafana['security']['cookie_samesite'], 'lax')

    def test_parent_identity_and_storage_are_independent(self):
        for member, peer in (("netdata-1", "netdata-2"), ("netdata-2", "netdata-1")):
            values = self.by_name[member]["values"]
            self.assertEqual(values["replicaCount"], 1)
            self.assertTrue(values["parent"]["database"]["persistence"])
            self.assertTrue(values["parent"]["alarms"]["persistence"])
            self.assertEqual(values["parent"]["hostname"], member)
            stream = values["parent"]["configs"]["stream"]
            self.assertEqual(stream["storedType"], "secret")
            self.assertIn(f"destination = {peer}.netdata-{peer[-1]}.svc:19999:SSL", stream["data"])
            self.assertIn("ssl skip certificate verification = no", stream["data"])
            self.assertEqual(values["child"]["enabled"], member == "netdata-1")
            web = values['parent']['configs']['netdata']['data']
            self.assertIn('allow dashboard from = localhost ' + self.inputs['observability_netdata_allow_from'], web)
            self.assertIn('allow management from = localhost', web)
            self.assertIn('allow mcp from = localhost', web)
        bridge = self.by_name["netdata-metrics"]["values"]
        self.assertEqual(bridge["replicaCount"], 1)  # One scrape owner per series.

    def test_native_database_resources_have_storage_tls_and_backups(self):
        resources = self.by_name['grafana']['before']
        cluster = next(resource for resource in resources if resource['kind'] == 'Cluster')
        self.assertEqual(cluster['spec']['instances'], 3)
        self.assertEqual(cluster['spec']['bootstrap']['initdb']['database'], 'grafana')
        self.assertEqual(cluster['spec']['certificates']['serverTLSSecret'], 'grafana-db-server-tls')
        self.assertFalse(cluster['spec']['enableSuperuserAccess'])
        self.assertNotIn('backup', cluster['spec'])
        self.assertEqual(cluster['spec']['plugins'][0]['parameters']['barmanObjectName'], 'grafana-db-backup')
        store = next(resource for resource in resources if resource['kind'] == 'ObjectStore')
        self.assertEqual(store['spec']['configuration']['wal']['encryption'], 'AES256')
        self.assertEqual(cluster['spec']['affinity']['podAntiAffinityType'], 'required')
        schedule = next(resource for resource in resources if resource['kind'] == 'ScheduledBackup')
        self.assertTrue(schedule['spec']['immediate'])
        self.assertEqual(schedule['spec']['method'], 'plugin')

    def test_database_resources_match_official_operator_crd_schemas(self):
        cache = os.environ.get('CNPG_CRD_CACHE')
        if not cache:
            self.skipTest('Set CNPG_CRD_CACHE to official CNPG 1.27.0 CRDs for offline schema validation')
        import jsonschema
        names = {'Cluster': 'postgresql.cnpg.io_clusters.yaml',
                 'ScheduledBackup': 'postgresql.cnpg.io_scheduledbackups.yaml',
                 'ObjectStore': 'barmancloud.cnpg.io_objectstores.yaml'}
        for resource in self.by_name['grafana']['before']:
            crd = yaml.safe_load((Path(cache) / names[resource['kind']]).read_text())
            schema = next(version for version in crd['spec']['versions'] if version['name'] == 'v1')
            jsonschema.validate(resource, schema['schema']['openAPIV3Schema'])


class ObservabilityNativeCharts(ObservabilityNativeValues):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.helm = os.environ.get("HELM_BINARY") or shutil.which("helm")
        cache = os.environ.get("OBSERVABILITY_CHART_CACHE")
        if not cls.helm or not cache:
            raise unittest.SkipTest("Requires Helm and OBSERVABILITY_CHART_CACHE; no network fallback")
        cls.documents = {}
        with tempfile.TemporaryDirectory() as temporary:
            for release in cls.releases:
                component = release["chart"]
                package = Path(cache) / f"{component}-{release['version']}.tgz"
                if not package.is_file():
                    raise AssertionError(f"Missing exact pinned chart: {package}")
                values = Path(temporary) / f"{release['name']}.yaml"
                values.write_text(yaml.safe_dump(release["values"], sort_keys=False))
                result = subprocess.run(
                    [cls.helm, "template", release["name"], str(package), "--namespace",
                     release["namespace"], "--include-crds", "--values", str(values)],
                    capture_output=True, text=True, timeout=90,
                )
                if result.returncode:
                    raise AssertionError(f"{release['name']}: {result.stdout}{result.stderr}")
                cls.documents[release["name"]] = [doc for doc in yaml.safe_load_all(result.stdout) if doc]

    def test_native_stateful_storage_and_quorum(self):
        for name in ("metrics-1", "metrics-2", "otel-gateway", "opensearch"):
            sts = next(doc for doc in self.documents[name] if doc["kind"] == "StatefulSet")
            self.assertTrue(sts["spec"]["volumeClaimTemplates"], name)
        search = next(doc for doc in self.documents["opensearch"] if doc["kind"] == "StatefulSet")
        self.assertEqual(search["spec"]["replicas"], 3)
        container = search["spec"]["template"]["spec"]["containers"][0]
        environment = {item["name"]: item.get("value") for item in container["env"]}
        services = {doc["metadata"]["name"] for doc in self.documents["opensearch"]
                    if doc["kind"] == "Service"}
        self.assertIn(environment["discovery.seed_hosts"], services)
        configmap = next(doc for doc in self.documents["opensearch"] if doc["kind"] == "ConfigMap")
        config = yaml.safe_load(configmap["data"]["opensearch.yml"])
        self.assertEqual(config["cluster.initial_cluster_manager_nodes"],
                         [f'opensearch-{index}' for index in range(search["spec"]["replicas"])])
        self.assertEqual(search["spec"]["template"]["spec"]["affinity"]["podAntiAffinity"]
                         ["requiredDuringSchedulingIgnoredDuringExecution"][0]["topologyKey"],
                         self.inputs["observability_topology_key"])

    def test_existing_search_cluster_omits_initial_manager_bootstrap(self):
        inputs = dict(self.inputs, observability_search_bootstrap=False)
        releases = yaml.safe_load(render_template(ROLE, 'releases.yml.j2', inputs))
        search = next(item for item in releases if item['name'] == 'opensearch')
        config = yaml.safe_load(search['values']['config']['opensearch.yml'])
        self.assertNotIn('cluster.initial_cluster_manager_nodes', config)
        self.assertEqual(search['values']['masterService'], 'opensearch')

    def test_native_parent_claims_and_pinned_images(self):
        claims = []
        for name in ("netdata-1", "netdata-2"):
            claims.extend(doc["metadata"]["name"] for doc in self.documents[name]
                          if doc["kind"] == "PersistentVolumeClaim")
        self.assertEqual(len(claims), 5)  # DB + alarm per parent, one cluster-state identity.
        self.assertEqual(len(set(claims)), 5)
        for name, documents in self.documents.items():
            for doc in documents:
                if doc["kind"] in ("Deployment", "StatefulSet", "DaemonSet"):
                    spec = doc["spec"]["template"]["spec"]
                    for container in spec["containers"] + (spec.get("initContainers") or []):
                        self.assertNotIn(":latest", container["image"], name)

    def test_native_netdata_service_accounts_have_only_readonly_api_access(self):
        release = self.by_name['netdata-1']
        documents = self.documents['netdata-1']
        account = next(doc for doc in documents if doc['kind'] == 'ServiceAccount')
        binding = next(doc for doc in release['before'] if doc['kind'] == 'ClusterRoleBinding')
        role = next(doc for doc in release['before'] if doc['kind'] == 'ClusterRole')
        self.assertFalse(any(doc['kind'] in ('Role', 'ClusterRole', 'RoleBinding', 'ClusterRoleBinding')
                             for doc in documents))
        self.assertEqual(binding['roleRef']['name'], role['metadata']['name'])
        subject = dict(kind='ServiceAccount', name=account['metadata']['name'], namespace=release['namespace'])
        self.assertEqual(binding['subjects'], [subject])
        for doc in documents:
            if doc['kind'] in ('DaemonSet', 'Deployment'):
                self.assertEqual(doc['spec']['template']['spec']['serviceAccountName'], subject['name'])
        resources = {resource for rule in role['rules'] for resource in rule['resources']}
        self.assertTrue({'pods', 'nodes/metrics', 'nodes/stats', 'nodes'}.issubset(resources))
        self.assertTrue(resources.isdisjoint({'secrets', '*', 'pods/exec', 'nodes/proxy'}))
        for rule in role['rules']:
            self.assertTrue(set(rule['verbs']).issubset({'get', 'list', 'watch'}))
        self.assertFalse(any(doc['kind'] in ('Role', 'ClusterRole', 'RoleBinding', 'ClusterRoleBinding')
                             for doc in self.by_name['netdata-2']['before']))

    def test_native_gateway_has_per_pod_queue_and_no_default_receivers(self):
        documents = self.documents["otel-gateway"]
        sts = next(doc for doc in documents if doc["kind"] == "StatefulSet")
        mounts = sts["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
        self.assertIn(dict(name="queue", mountPath="/var/lib/otelcol"), mounts)
        configmap = next(doc for doc in documents if doc["kind"] == "ConfigMap")
        config = yaml.safe_load(configmap["data"]["relay"])
        self.assertNotIn("jaeger", config["receivers"])
        self.assertNotIn("debug", config["exporters"])
        self.assertEqual(set(config["service"]["pipelines"]),
                         {"metrics", "logs/app-a", "traces/app-a", "logs/approved"})
        service = next(doc for doc in documents if doc['kind'] == 'Service'
                       and doc['spec'].get('type') == 'NodePort')
        self.assertEqual(service['spec']['externalTrafficPolicy'], 'Local')
        ports = {port['port']: port['nodePort'] for port in service['spec']['ports']}
        self.assertEqual(ports, {4317: 30317, 4400: 30400, 4401: 30401})

    def test_native_otel_parser_accepts_all_three_collector_configs(self):
        binary = os.environ.get('OTELCOL_BINARY')
        if not binary:
            self.skipTest('Set OTELCOL_BINARY to the pinned contrib 0.163.2 binary')
        configs = {}
        for release in ('otel-gateway', 'netdata-metrics'):
            configmap = next(doc for doc in self.documents[release] if doc['kind'] == 'ConfigMap')
            configs[release] = yaml.safe_load(configmap['data']['relay'])
        inputs = yaml.safe_load((MONITORING / 'defaults/main.yml').read_text())
        inputs.update(infrastructure_monitoring_export_metrics=['netdata_system_cpu_percentage_average'])
        configs['independent'] = yaml.safe_load(render_template(MONITORING, 'collector.yml.j2', inputs))
        with tempfile.TemporaryDirectory() as temporary:
            for name, config in configs.items():
                path = Path(temporary) / (name + '.yaml')
                path.write_text(yaml.safe_dump(config))
                result = subprocess.run([binary, 'validate', '--config', str(path)],
                                        capture_output=True, text=True, timeout=30,
                                        env=dict(os.environ, VM_USERNAME='test', VM_PASSWORD='test',
                                                 DP_USERNAME='test', DP_PASSWORD='test'))
                self.assertEqual(result.returncode, 0, name + '\n' + result.stdout + result.stderr)

    def test_native_data_prepper_configuration_models_and_constraints(self):
        home = os.environ.get('DATA_PREPPER_HOME')
        if not home:
            self.skipTest('Set DATA_PREPPER_HOME to the pinned 2.14.1 distribution with bundled JDK')
        home = Path(home)
        jdk = next((home / 'openjdk').glob('*/bin'))
        classpath = str(home / 'lib' / '*')
        pipelines = self.by_name['data-prepper']['values']['pipelineConfig']['config']
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'DataPrepperConfigCheck.java'
            source.write_text(DATA_PREPPER_CHECK)
            data = Path(temporary) / 'pipelines.json'
            data.write_text(json.dumps(pipelines))
            compile_result = subprocess.run([str(jdk / 'javac'), '-cp', classpath, '-d', temporary,
                                             str(source)], capture_output=True, text=True, timeout=90)
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            result = subprocess.run([str(jdk / 'java'), '-cp', temporary + os.pathsep + classpath,
                                     'org.opensearch.dataprepper.plugin.DataPrepperConfigCheck', str(data)],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('configurations accepted: 12', result.stdout)


class ObservabilityAnsibleRender(TierRepositoryTestCase):
    def test_native_client_ca_gate_accepts_distinct_and_rejects_reused_authorities(self):
        ansible = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
        if not ansible:
            self.skipTest('Requires native Ansible with kubernetes.core and community.crypto')
        inputs = platform_inputs()
        names = [inputs['observability_metrics_client_ca_secret']] + [
            scope['name'] + '-clients-ca' for scope in inputs['observability_log_scopes']]
        secrets = {'observability/' + name: {'ca.crt': make_test_certificate(name)[1].decode()}
                   for name in names}
        inputs.update(observability_action='apply', observability_manage_secrets=True,
                      observability_secrets=secrets, ansible_python_interpreter=sys.executable)
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            play = temporary / 'trust.yml'
            play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                tasks=[{'ansible.builtin.import_tasks': str(ROLE / 'tasks/trust.yml')}])]))
            variables = temporary / 'inputs.json'
            for reused in (False, True):
                with self.subTest(reused=reused):
                    if reused:
                        secrets['observability/' + names[1]] = secrets['observability/' + names[0]]
                    variables.write_text(json.dumps(inputs))
                    result = subprocess.run([ansible, str(play), '-i', 'localhost,', '-e', '@' + str(variables)],
                                            capture_output=True, text=True, timeout=90)
                    if reused:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('Use a distinct dedicated client-signing CA', result.stdout)
                    else:
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_ansible_renders_source_and_generated_roles(self):
        ansible = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
        helm = os.environ.get('HELM_BINARY') or shutil.which('helm')
        cache = os.environ.get('OBSERVABILITY_CHART_CACHE')
        if not ansible or not helm or not cache:
            self.skipTest('Requires native ansible-playbook, collections, Helm and cached pinned packages')
        self.generate()
        with tempfile.TemporaryDirectory() as temporary, cached_https_repository(Path(temporary) / 'charts', cache) as mirror:
            temporary = Path(temporary)
            for collection, prefix in ((ROOT, ''), (self.root, 'verify-')):
                for tier, recipe in (('tier-1', 'observability-platform'),
                                     ('tier-0', 'infrastructure-monitoring')):
                    with self.subTest(collection=prefix or 'source', tier=tier):
                        root = collection / (prefix + tier)
                        output = temporary / (prefix + tier)
                        inputs = platform_inputs() if tier == 'tier-1' else {
                            'infrastructure_monitoring_hosts': 'localhost',
                            'infrastructure_monitoring_action': 'render',
                            'infrastructure_monitoring_output': str(output),
                        }
                        if tier == 'tier-1':
                            inputs.update(observability_output=str(output), observability_action='render',
                                          observability_netdata_host_access_approved=False,
                                          observability_network_policy_verified=False,
                                          observability_search_kernel_verified=False)
                            for chart in inputs['observability_charts'].values():
                                chart['repository'] = mirror[0]
                        variables = temporary / 'inputs.json'
                        variables.write_text(json.dumps(inputs))
                        environment = dict(os.environ)
                        environment.update(
                            ANSIBLE_CONFIG=str(root / 'ansible/ansible.cfg'),
                            ANSIBLE_ROLES_PATH=os.pathsep.join((str(root / 'ansible/roles'),
                                str(collection / (prefix + 'shared') / 'ansible/roles'))),
                            PATH=str(Path(helm).parent) + os.pathsep + os.environ.get('PATH', ''),
                            ANSIBLE_STDOUT_CALLBACK='default',
                            SSL_CERT_FILE=str(mirror[1]),
                        )
                        result = subprocess.run(
                            [ansible, f'playbooks/deployment/{recipe}.yml', '-i', 'localhost,', '-c', 'local',
                             '-e', '@' + str(variables), '-e', 'ansible_python_interpreter=' + sys.executable],
                            cwd=root / 'ansible', env=environment, capture_output=True, text=True, timeout=240)
                        self.assertEqual(result.returncode, 0, '\n'.join((result.stdout + result.stderr).splitlines()[-45:]))
                        if tier == 'tier-1':
                            manifests = list(output.glob('*-manifests.yml'))
                            self.assertEqual(len(manifests), 11)
                            gateway = list(yaml.safe_load_all((output / 'otel-gateway-manifests.yml').read_text()))
                            stateful = next(doc for doc in gateway if doc and doc['kind'] == 'StatefulSet')
                            self.assertEqual(stateful['spec']['replicas'], 2)
                            config = next(doc for doc in gateway if doc and doc['kind'] == 'ConfigMap')
                            pipelines = yaml.safe_load(config['data']['relay'])['service']['pipelines']
                            self.assertNotIn('traces/approved', pipelines)
                            support = list(yaml.safe_load_all((output / 'grafana-before.yml').read_text()))
                            self.assertEqual({item['kind'] for item in support},
                                             {'Cluster', 'ObjectStore', 'ScheduledBackup'})
                            support = list(yaml.safe_load_all((output / 'netdata-1-before.yml').read_text()))
                            binding = next(item for item in support if item['kind'] == 'ClusterRoleBinding')
                            netdata = list(yaml.safe_load_all((output / 'netdata-1-manifests.yml').read_text()))
                            account = next(item for item in netdata if item and item['kind'] == 'ServiceAccount')
                            self.assertEqual(binding['subjects'], [dict(kind='ServiceAccount',
                                name=account['metadata']['name'], namespace=account['metadata']['namespace'])])
                        else:
                            config = yaml.safe_load((output / 'collector.yml').read_text())
                            self.assertEqual(set(config['service']['pipelines']), {'metrics'})
                            self.assertIn('[stream]', (output / 'stream.conf').read_text())
                        if os.name != 'nt':
                            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                            self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600
                                                for path in output.iterdir() if path.is_file()))


if __name__ == "__main__":
    unittest.main()
