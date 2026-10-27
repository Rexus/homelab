# Observability Configuration

The Tier 1 `observability_platform` role owns native product values, source routing,
OpenSearch policy/bootstrap and readiness checks. Shared executes the pinned charts.
Start with the [Stage 8 main path](README.md). All filled inputs and render outputs are private.

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`).

## Contents

- [Inputs and execution](#inputs-and-execution)
- [Secrets and trust](#secrets-and-trust)
- [Private cross-cluster intake](#private-cross-cluster-intake)
- [Approved search projections](#approved-search-projections)
- [Storage and recovery](#storage-and-recovery)
- [Verification](#verification)
- [References](#references)

## Inputs and Execution

Source ownership remains in
[`ansible/roles/observability_platform/`](../../../tier-1/ansible/roles/observability_platform).
Prepare ignored local copies of the
[platform](../../../tier-1/ansible/group_vars/observability_platform.yml.example) and
[private inputs](../../../tier-1/ansible/group_vars/observability_platform_secrets.yml.example).
Run from its `ansible/` directory on the prepared Linux controller:

```bash
ansible-playbook playbooks/deployment/observability-platform.yml \
  -e @group_vars/observability_platform.yml \
  -e @group_vars/observability_platform_secrets.yml
```

The default action is `render`: no kubeconfig, namespace changes or live API is required.
It writes private values/manifests under `secrets/observability-platform/` in the tier root.
`-e observability_action=apply` explicitly selects convergence, with the supplied kubeconfig/context.
Do not run both this recipe and a delivery controller as concurrent owners of the same releases.

| Input | Contract |
| --- | --- |
| `observability_charts` | Exact native chart versions and HTTPS repositories; defaults are the reviewed pin set |
| `observability_storage_class` | Existing retained RWO block storage with qualified failover and backups |
| Live Grafana database | Proxmox/Ceph-backed block volumes; separate from the NAS backup PVC |
| `observability_topology_key`, `observability_failure_domains` | Real physical-host mapping; three distinct domains, verified independently of VM names |
| `observability_resources`, replica/size settings | Separate component budgets; surviving capacity must be tested |
| `observability_search_bootstrap` | True only for the initial empty cluster; false after first green acceptance and for all restarts, scaling and recovery |
| `observability_log_scopes` | Per-source name, application/projection kind, listener, NodePort and explicit reader backend roles |
| `observability_telemetry_cidrs`, `observability_egress` | Exact source networks and required database/API/kubelet destinations |
| Database backup method | Scheduled verified full copies to a separate NAS file PVC, or the existing object/WAL option; [storage prerequisites](../foundation/storage/README.md) install no gateway |
| `observability_backup_mode`, `observability_backup_files_phase` | Fresh examples use `files` / `prepare`; [commission the NAS destination](../../administration/backups/postgresql.md), then select `backup` to enable copies and continue installation |
| `observability_database_storage_class` | Explicit live Proxmox/Ceph-backed block class, independent of the NAS backup claim |
| `observability_backup_destination`, `observability_backup_endpoint` | Object/WAL option only: Grafana database backup prefix and HTTPS S3-compatible endpoint, with scoped tenant keys and independent custody |
| `observability_manage_secrets` | False by default; an existing secret owner supplies native Kubernetes Secrets |
| `observability_secrets` | Optional explicitly managed `namespace/name` to `stringData`, passed privately |
| `observability_netdata_child_key`, `observability_netdata_peer_key` | Distinct private UUIDs; Helm stores streaming configuration as Secrets |

For disconnected Ansible rendering, point each `observability_charts.*.repository` at a
trusted private HTTPS mirror containing the exact pinned packages, with its CA trusted by
Helm on the controller. No live Kubernetes cluster is required. Cached packages can also
be rendered directly with `helm template`. The regression suite exercises Shared's real
HTTPS contract using a temporary loopback mirror, without external network access.

For a **new empty OpenSearch cluster**, explicitly set
`observability_search_bootstrap: true` for the first install. This generates the
exact initial cluster-manager names from the selected StatefulSet replica count.
The chart's discovery service is explicitly `opensearch-headless`, matching the
release rather than its unrelated chart default. After the first green membership
check, set the flag to **false** and reapply to remove the bootstrap list. Never
enable it to repair, scale or restore an existing cluster, or to form a new cluster
over reused data volumes. Preserve the established cluster UUID and use its recovery
procedure instead. [13]

## Secrets and Trust

All names below are namespace-local. Certificates need the exact service names used by
their clients in SANs. Use a separate client-signing authority per source scope; sharing
those CAs would let one source impersonate another scope. The apply gate parses validity,
CA constraints and fingerprints, and rejects shared authorities or multi-certificate bundles.
Issuer keys never enter Tier 1.

Netdata's native chart creates the service account but not its broad default RBAC.
The role supplies a read-only ClusterRole/binding for `netdata-1` in its diagnostic
namespace, including `nodes/metrics`, `nodes/stats` and cluster-state reads. It grants
no Secret reads, exec, node proxy or mutation rights, and no Tier 0 access. Native
render tests match the binding subject to the chart's service account and pods. [6]

The pinned Netdata web ACL also controls Prometheus API reads. Its reviewed private
source patterns must include the metric bridge and operator proxy, not only child
streamers. NetworkPolicy admits only the owned monitoring namespaces and the operator
namespace; management/MCP/config access stays localhost-only. Netdata has no browser
OIDC configuration here: use an existing authenticated operator proxy or an authorized
cluster tunnel, never a direct public UI. Accept that access path separately. [12]

| Namespace | Secret | Required keys / meaning |
| --- | --- | --- |
| `observability` | `metrics-1-tls`, `metrics-2-tls` | `tls.crt`, `tls.key`, `ca.crt`; backend service SANs |
| `observability` | `metrics-auth` | `username`, `password`, `basic-auth`; last value is base64 of `username:password`, used only by vmauth |
| `observability` | `gateway-tls` | `tls.crt`, `tls.key`, `ca.crt`; gateway Service and private worker DNS SANs, backend trust bundle |
| `observability` | `metrics-clients-ca` | `ca.crt`; only approved metric-export client issuers |
| `observability` | `<scope>-clients-ca` | `ca.crt`; distinct scoped application or approved-copy client issuer |
| `observability` | `gateway-client-tls` | `tls.crt`, `tls.key`, `ca.crt`; local Netdata metric bridge client |
| `observability` | `search-tls` | `tls.crt`, `tls.key`, `ca.crt`; Service and every configured pod/headless DNS SAN; PKCS#8 node key |
| `observability` | `search-admin-tls` | `tls.crt`, `tls.key`, `ca.crt`; dedicated bootstrap certificate/DN, never a reader identity |
| `observability` | `search-users` | `internal_users.yml`; native metadata and bcrypt hashes, including `data-prepper` and `dashboards-server` |
| `observability` | `prepper-tls` | `tls.crt`, `tls.key`, `ca.crt`; `data-prepper` server certificate and search trust |
| `observability` | `prepper-auth` | `username`, `password`; Collector-to-ingestion identity |
| `observability` | `prepper-search-auth` | `username: data-prepper`, matching private password/hash |
| `observability` | `dashboards-tls`, `dashboards-auth` | TLS triplet; separate `username: dashboards-server` and matching password |
| `observability` | `oidc-ca`, `dashboards-oidc`, `grafana-oidc` | Provider trust `ca.crt`; separate confidential-client `client-secret` values |
| `observability` | `query-tls`, `metrics-reader` | TLS triplet; separate read-only query `username`/`password` |
| `observability` | `grafana-tls`, `grafana-admin` | TLS triplet including database CA; private local administrator `username`/`password` |
| `observability` | `grafana-database` | `username: grafana`, `password`, common `secret-key`; restricted native PostgreSQL identity |
| `observability` | `grafana-db-server-tls`, `grafana-db-ca` | Server TLS key/certificate; separate CA bundle with `ca.crt`; SAN `grafana-db-rw` and its namespace DNS |
| `observability` | `grafana-backup-ca`, `grafana-backup-auth` | Object/WAL option only: HTTPS CA `ca.crt` and restricted `access-key`/`secret-key` |
| `netdata-1` | `netdata-1-tls` | TLS triplet plus `kubelet-ca.crt`; Netdata service DNS and approved kubelet trust |
| `netdata-2` | `netdata-2-tls` | TLS triplet; independent parent service identity |

Custom namespace prefixes change these locations. OpenSearch policy maps fixed users and
reader backend roles. Human login uses the existing Keycloak issuer through native OIDC;
only signed `groups` claims map to reader roles. Data Prepper and the Dashboards backend
retain separate basic service identities. Do not grant readers extra index-management or write roles.
No anonymous UI or basic browser-login fallback is enabled. [9][10]

Provision the two confidential IdP clients with exact redirects:
`<observability_dashboards_url>/auth/openid/login` and
`<observability_grafana_url>/login/generic_oauth`. Include the intended client audience and
immutable `sub` plus approved groups in tokens. OpenSearch validates issuer/audience and
the provider TLS CA. Grafana verifies ID-token signatures, uses PKCE and permits only the
configured operator group as `Viewer`; unmatched groups are denied. Grafana's endpoints
follow the selected Keycloak realm; secure `SameSite=Lax` cookies permit OAuth callbacks. [11]
Complete the existing
[service SSO gate](../stage-5-identity/procedures/service-sso.md), including denied groups,
provider outage, cookie handling and signing-key rotation. Configuration is not a live-login test.

Data Prepper receives literal credentials in its native pipeline Secret. The role reads
externally owned ingestion Secrets on apply, or uses explicitly managed inputs. It does
not depend on environment substitution unsupported by the selected native parser.
Helm release state and render output therefore need secret-level custody.

## Private Cross-Cluster Intake

| Signal | Private worker NodePort | Gateway port | Source identity |
| --- | --- | --- | --- |
| Approved metrics | `30317` | `4317` | Metrics client CA |
| Example application logs/traces | `30400` | `4400` | `application-a-clients-ca` |
| Example approved Tier 0 copies | `30401` | `4401` | `approved-security-clients-ca`; logs only |

These are configurable inputs, not a second inventory. Services use `externalTrafficPolicy: Local`.
Provide a reviewed private TCP load balancer with node-local endpoint health checks, or a
client routing configuration that uses the private workers currently hosting gateway pods.
A DNS list alone does not establish exporter failover. Keep this endpoint contract aligned
with [Tier 2 workload collection](../stage-10-lab-environments/telemetry.md).

Firewall rules admit only approved source CIDRs to the selected private worker NodePorts.
No public edge route is created. Verify the CNI's NodePort/source-IP behavior against the
pod NetworkPolicy. Operator proxies in the selected `operations` namespace can reach query
UIs; database/API/kubelet egress is explicit. Netdata and Tier 0 management APIs are not
application endpoints. The Data Prepper management port `4900` is not exposed by its Service
or ingress policy; native chart probes use its pod-local HTTP API. Ingestion itself uses TLS/auth.

## Approved Search Projections

Tier 0 supplies the [approved-copy publisher and native Collector exporter](protected-log-search.md).
The Observability recipe does not install them or acquire original-archive access.
Until the separate Tier 0 export recipe is installed and accepted, projection search
is configured but receives no evidence copies.

The adapter reads only the approved view through its separately authorized export identity,
redacts before transfer and sends OTLP logs using its projection client certificate to the
projection NodePort. It must retain a durable cursor/queue and a stable event ID, and qualify
replay, duplicates, source coverage and revocation. Its identity has no archive write/delete,
retention, signing, snapshot or backup authority. Never place control credentials or original
archive mounts in the observability namespace.

The source listener selects a fixed Data Prepper pipeline/index; submitted resource labels
cannot choose an index or reader scope. Projection listeners have no trace or metric pipeline.
OpenSearch readers receive only their explicit index prefix. Dashboard tenants are not the
data authorization boundary. Tier 1 index deletion/rebuild affects only derived copies.

## Storage and Recovery

| Component | Selected persistence and recovery boundary |
| --- | --- |
| Gateways | StatefulSet per-pod bounded persistent queues; independent exporters write metrics to both stores |
| Metrics | Two single-store releases on separate domains/PVCs; no load-balanced write Service |
| Query routing | `observability_metrics_read_members` explicitly admits caught-up copies, initially only `metrics-1`; `first_available` is not a freshness detector |
| Search | Three manager/data members, hard physical-domain anti-affinity, one replica shard in each scoped template |
| Data Prepper | Replicated stateless source-to-index pipelines, bounded in-memory buffers; no stateful service-map aggregation |
| Netdata | Two namespaces, parent DB/alarm PVCs, child failover and parent synchronization; one approved scrape owner |
| Grafana | Native `grafana-db` CNPG Cluster has three instances, TLS and Proxmox/Ceph-backed live PVCs; backup copies go to the selected independent destination; UI pod disk is disposable |

The database bootstrap identity must be `grafana`; Stage 4 supplies CNPG. Scheduled
verified full file backups write to a distinct NAS backup PVC, not the live database
volume. They recover only to the latest completed set, with no later PITR promise.
The object/WAL option additionally uses Barman Cloud, `ObjectStore` and
`ScheduledBackup` resources for continuous transaction archiving. [8]
The role gates the selected resources, database readiness and a completed backup.
A completed backup is not a tested restore. Retain database/password/encryption
secrets independently and qualify the actual recovery point and elapsed restore time.
Use [NAS-file recovery](../../administration/recovery/cnpg-files.md) for scheduled file
sets; the Barman recovery procedure applies only to the object/WAL variant.

The initial Grafana/vmauth metrics view is for platform operators. It is one approved
dataset, not per-application metric isolation. Application readers use their scoped
OpenSearch roles; exposing a metrics dataset to them requires a separately enforced scope.

OTLP acknowledgement, bounded buffers and queue volume persistence do not establish zero
tail loss. Declare accepted loss and restore times; test retries and Data Prepper crash behavior.
Promoting a stale metrics copy is an operator action after comparison/backfill. Replicas and
PVCs do not replace independently retained backups.

## Verification

`tests/test_tier_observability_platform.py` renders exact cached native charts when
`HELM_BINARY` and `OBSERVABILITY_CHART_CACHE` are set. `OTELCOL_BINARY` adds real Collector
`validate`; `DATA_PREPPER_HOME` adds native packaged Data Prepper configuration conversion
and Bean Validation using its bundled JDK. It starts no ingestion service or cluster.
`CNPG_CRD_CACHE` adds official CNPG/Barman schema checks. `ANSIBLE_PLAYBOOK` enables complete
native Ansible render checks against both the source and generated tier repositories,
inspecting real output and controller file permissions rather than simulated Jinja alone.

Apply waits for native workloads and checks the security bootstrap's authenticated search
health, membership and allocated shards before starting Data Prepper. Policy, user-hash or
membership changes create a new policy-bootstrap Job. These are installation gates. Worker/physical-host
loss, metric catch-up, parent replication, certificate/credential failures, denied direct APIs,
forged scope, queue replay, index rebuild with unchanged Tier 0 originals, and clean restores
remain required [Stage 8 acceptance](README.md#capability-available).

## References

Primary sources checked 2026-10-26; exact release pins live in role defaults and values.

1. [Official Collector chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector)
2. [VictoriaMetrics OTLP intake](https://docs.victoriametrics.com/victoriametrics/integrations/opentelemetry/)
3. [vmauth routing and authorization](https://docs.victoriametrics.com/victoriametrics/vmauth/)
4. [Official OpenSearch charts](https://github.com/opensearch-project/helm-charts)
5. [Data Prepper plugin configuration validation](https://github.com/opensearch-project/data-prepper/blob/2.14.1/data-prepper-plugin-framework/src/main/java/org/opensearch/dataprepper/plugin/PluginConfigurationConverter.java)
6. [Netdata chart](https://github.com/netdata/helmchart)
7. [Grafana shared database for availability](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-for-high-availability/)
8. [Barman Cloud plugin object stores](https://cloudnative-pg.io/plugin-barman-cloud/docs/next/object_stores/)
9. [OpenSearch and Dashboards native OIDC](https://docs.opensearch.org/latest/security/authentication-backends/openid-connect/)
10. [Grafana native OAuth/OIDC authorization](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/)
11. [Grafana secure OAuth cookies](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-security-hardening/)
12. [Netdata native web access controls](https://github.com/netdata/netdata/blob/v2.12.2/src/web/server/README.md)
13. [OpenSearch discovery and cluster formation](https://docs.opensearch.org/latest/tuning-your-cluster/discovery-cluster-formation/settings/)
