# Forward cluster security logs to protected intake

**Working repository:** the cluster owner's `<prefix>-tier-0`, `<prefix>-tier-1`
or `<prefix>-tier-2` (source: matching `tier-N/`); run Ansible from its `ansible/`.
Shared owns the stateless
[cluster_security_logging role](../../../../shared/ansible/roles/cluster_security_logging).
Each tier owns node selections, release pins, credentials and local inputs.

This required cluster-foundation step installs native Fluent Bit collectors,
one selected DaemonSet per node with a distinct client identity. Collectors accept
Talos JSON on host loopback, tail API audit files on control planes and pod
stdout/stderr on all selected nodes, then submit RFC5424 over TCP with mTLS to
the existing Tier 0 protected receiver. It supplies no metrics backend or OTLP
application-metrics routing, and makes no zero-loss or deployment claim.

## Table of contents

- [Prerequisites and trust](#prerequisites-and-trust)
- [Configure and render](#configure-and-render)
- [Prepare Talos](#prepare-talos)
- [Enroll node streams](#enroll-node-streams)
- [Install collectors](#install-collectors)
- [Accept the complete path](#accept-the-complete-path)
- [Queues and maintenance](#queues-and-maintenance)
- [References](#references)

## Prerequisites and trust

- Working cluster API/CNI, approved image access, independent DNS/time and an
  execution host outside the cluster; no directory, Vault or hosted delivery dependency.
- Existing [protected Tier 0 intake](../../stage-2-logging/receiver.md), its trusted
  server identity and network access from each receiver-observed node/NAT address.
- Independently issued **client-auth leaf** certificate and matching private key
  per node, plus the public receiver/client CA bundle. Obtain these through the
  [independent producer authority](../../stage-2-logging/producer-trust.md) or an
  accepted equivalent. The role generates no certificates, keys or tokens.
- Native `kubernetes.core`, `ansible.utils` and `community.crypto` collections;
  Helm, `kubernetes`, `jsonpatch`, PyYAML, `netaddr` and `cryptography` on the execution host.
- Exact compatible Fluent chart/image pins and explicit repository approvals.
  Accept the selected releases before applying; native test pins do not approve
  a production release.

Each collector mounts only its own client Secret. Receiver enrollment binds the
observed IP, exact certificate subject and CN/stream name to a server-owned
archive path. This authenticates the **enrolled collector stream and network
origin**, not node attestation or every process/pod influencing its inputs.
Claimed HOST/app/structured data remain assertions.
Talos-to-collector traffic stays on loopback without TLS; trusted host-network
workloads and host administrators can inject there. Restrict that trust boundary.

Unlike the Linux producer's host-generated private key, this installer consumes
an externally issued key imported into a Kubernetes Secret. Cluster administrators,
Secret readers, actors able to create pods in this namespace, and privileged
node/runtime components can obtain or use that key. Restrict namespace access,
encrypt Secrets at rest and protect control-plane backups; a read-only mount is
not non-exportable custody. Never share a client certificate between nodes. [11]

Collectors run as privileged root for host log access, with `/var/log` read-only,
one dedicated writable queue directory and read-only leaf-key mounts. The namespace
allows privileged pods; the container has no Kubernetes service-account token or
cluster RBAC. Approve host access deliberately; this is a trusted node agent. [1][2]

## Configure and render

```bash
cp -n group_vars/cluster_security_logging.yml.example group_vars/cluster_security_logging.yml
ansible-playbook -i localhost, playbooks/deployment/cluster-security-logging.yml \
  -e @group_vars/cluster_security_logging.yml -e cluster_security_logging_action=render
```

Fill the copied example before rendering. Include **every actual node**, with
`control_plane: true` on API-server nodes and false on workers. Each entry needs
its node name, unique stream/CN, unique TLS Secret, exact approved `tls_dn`, and
IPv4 address as observed by intake. Names in examples match each tier's starter
inventory, not discovered/live deployment. Add local workers explicitly.
Required node affinity matches the API object's `metadata.name`, not a mutable
hostname label. This is placement only; authentication comes from the enrolled
certificate and receiver-observed IPv4, never labels or submitted metadata. [12]

| Input | Required decision |
| --- | --- |
| `cluster`, `tier`, `nodes` | Tier-owned logical identity, numeric 0/1/2 and actual node/stream mappings; use the `cluster_security_logging_` prefix |
| `chart_version`, `image_tag`, optional `image_digest` | Exact chart/image versions; no latest/ranges; digest retains the version tag |
| `approved_repositories`, `approved_image_repositories` | Explicitly approve official Fluent repositories or qualified mirrors |
| `receiver`, `receiver_name`, `receiver_port` | Connection target, expected certificate DNS/IP SAN and protected TCP port, default 6514 |
| `talos_schema` | `v1.13` legacy fields or `v1.14` configuration documents, matching the actual Talos release |
| `listener_port`, `metrics_port` | Unused host-loopback TCP ports, default 6050 and 2020 |
| `queue_mib_per_output` | 16-4096 MiB per output per node; default 128, three outputs |
| `kubeconfig`, `context` | Explicit apply target; context defaults to that kubeconfig's selected context |

All table keys have the `cluster_security_logging_` prefix. The example owns the
complete input names. Review the native values/manifests and these private
artifacts under the tier's `secrets/cluster-security-logging/`:

| Artifact | Operator action |
| --- | --- |
| `talos-system-logging.patch.yml` | Merge the loopback destination into every node's machine configuration |
| `talos-api-audit.patch.yml` | Merge native API policy/path settings into control-plane configuration |
| `receiver-sources.yml` | Merge entries into the existing Tier 0 `syslog_ng_sources` catalogue |
| `security-log-*-values.yml`, `*-manifests.yml` | Review each node affinity, mounts, TLS, queues and image before apply |

Rendering fetches pinned charts but never contacts Kubernetes. Files are `0600`,
directories `0700`; verify Windows ACLs on WSL-mounted storage. Secret names are
rendered, private credential contents are not exported as manifests.

## Prepare Talos

Preserve existing CNI, proxy, mirror and logging settings. The system patch uses
the supported native `machine.logging` destination in both schemas: [3]

```yaml
machine:
  logging:
    destinations:
      - endpoint: tcp://127.0.0.1:6050/
        format: json_lines
---
apiVersion: v1alpha1
kind: KmsgLogConfig
name: security-logging
url: tcp://127.0.0.1:6050/
```

The separate `KmsgLogConfig` enables kernel messages; service destinations alone
do not enable kernel forwarding. [3]

For Talos v1.13 the generated API patch uses these native fields: [4]

```yaml
cluster:
  apiServer:
    auditPolicy:
      apiVersion: audit.k8s.io/v1
      kind: Policy
      omitStages: [RequestReceived]
      rules:
        - level: Metadata
    extraArgs:
      audit-log-path: /var/log/audit/kube/kube-apiserver.log
      audit-log-maxage: "30"
      audit-log-maxbackup: "10"
      audit-log-maxsize: "100"
```

For Talos v1.14, audit policy moves to a separate configuration document, and
API arguments use `KubeAPIServerConfig.extraArgs`: [5][6]

```yaml
apiVersion: v1alpha1
kind: KubeAuditPolicyConfig
configuration:
  apiVersion: audit.k8s.io/v1
  kind: Policy
  omitStages: [RequestReceived]
  rules:
    - level: Metadata
---
apiVersion: v1alpha1
kind: KubeAPIServerConfig
extraArgs:
  audit-log-path: /var/log/audit/kube/kube-apiserver.log
  audit-log-maxage: "30"
  audit-log-maxbackup: "10"
  audit-log-maxsize: "100"
```

Talos supplies the audit policy file and host mount itself; do not add a second
policy-file writer or relocate the log. The selected path and rotation values
match the v1.13 native defaults. Some releases ignore audit argument overrides:
inspect actual API-server commands/mounts rather than relying on patch acceptance. [7]
Metadata-level auditing avoids request/response bodies, including Secret data;
URIs and other metadata can still be sensitive. [8]

For Terraform-owned clusters, append reviewed patch strings to that tier's
existing `machine_config_patches`, preserving the other ordered entries. In
`.tfvars`, use YAML heredoc strings rather than function calls. Review the plan
and API-server rollout; do not run a second manual configuration owner against
Terraform-managed nodes. Manual clusters can use matching `talosctl machineconfig
patch`, offline `validate --mode metal`, and their established apply procedure.
Validate the **complete merged configuration** with the matching Talos CLI.

Before installation, verify the API is healthy and the expected audit file is
written on each control plane. Early loopback logs cannot be delivered until the
collector starts; Talos's first hop is not a durable acknowledged queue. Set
`cluster_security_logging_talos_configured: true` after checking those settings.

## Enroll node streams

Merge the rendered `receiver-sources.yml` entries into Tier 0's existing
catalogue, then use the [receiver procedure](../../stage-2-logging/receiver.md).
**Do not load that partial file as replacement extra-vars for the whole source
catalogue.** Preserve other producers. Confirm node/NAT origins, CN and exact
certificate subjects; narrow network rules for these observed addresses.
The current receiver accepts one scalar observed IPv4 per stream, not an IP list.
Each node has a distinct stream/CN and Secret, even behind shared NAT. If a node's
observed address changes, update that enrollment before accepting its delivery.
No receiver catalogue extension or shared multi-node identity is assumed.

Prepare each namespaced node Secret with `ca.crt`, `tls.crt` and `tls.key`.
`tls.crt` starts with the enrolled client-auth leaf, followed by intermediates;
`ca.crt` contains public trust anchors. No CA private key belongs in the cluster.
The default `manage_secrets: false` requires existing Secrets. For explicit
bootstrap ownership, privately complete **every node entry** from the secrets
example, encrypt it using `ansible-vault`, and pass it with `--ask-vault-pass
-e @group_vars/cluster_security_logging_secrets.yml`.

Before installing any agents, native certificate modules check current leaf/CA
validity, non-CA/client-auth leaf purpose, stream CN and leaf/key matching.
Receiver-side chain/revocation/subject checks remain authoritative. Set
`cluster_security_logging_receiver_enrolled: true` after enrollment and
`cluster_security_logging_host_access_accepted: true` after approving host mounts.

## Install collectors

```bash
ansible-playbook -i localhost, playbooks/deployment/cluster-security-logging.yml \
  -e @group_vars/cluster_security_logging.yml -e cluster_security_logging_action=apply
```

The shared native executor gates required Secrets and Helm readiness. The role
then requires the current DaemonSet generation with exactly one scheduled,
updated, ready instance on each selected node. No Talos SSH, shell installer,
disk formatting, PVC provisioning or physical storage replacement occurs.

The local JSON listener and HTTP health/metrics endpoints bind only `127.0.0.1`.
The liveness probe checks process uptime; readiness checks output health, so a
receiver outage can degrade readiness without making liveness restart the agent.
Application metrics/OTLP follow their own deployment path, not this syslog output.

## Accept the complete path

| Check | Required live evidence |
| --- | --- |
| Talos service event | A known native service/kernel event reaches the enrolled node stream with raw JSON intact |
| API audit | Generate a harmless API request with a unique query marker; inspect its audit file and matching protected intake record |
| Pod logs | Emit a unique marker from a disposable pod on each node; confirm raw CRI line and source-file metadata at intake |
| Authentication | Receiver records expected peer CN/IP; wrong client/subject/origin is rejected, and wrong receiver name/CA fails at the collector |
| Outage/restart | Interrupt only the test destination; observe bounded backlog, resume, restart and account for gaps/duplicates |
| Custody | Continue Stage 2 evidence/checkpoint/archive checks; TCP acceptance is not an archive commit receipt |

Collectors preserve raw lines rather than selecting a single JSON message field.
RFC5424 app names distinguish `talos`, `kube-audit` and `kube-pods`; structured
metadata includes the collector, node, cluster/tier and source file where present.
The receiver still chooses classification and storage using its authenticated
catalogue, never these submitted fields. [9]

Pod collection includes container stdout/stderr under `/var/log/containers/`;
application-private files require separate approved collection. Collector-own
pod logs are excluded to avoid a forwarding feedback loop. No workload annotation
can opt out of collection. Raw CRI fragments remain separate records.

## Queues and maintenance

The dedicated host directory holds per-input SQLite cursors and filesystem
chunks. Each output has its own bounded backlog (default 128 MiB, 384 MiB per
node total, plus cursor/chunk overhead). Full synchronization/checksums improve
local replay; retries continue while capacity permits. At a full output queue,
Fluent Bit discards oldest chunks. It does not reserve disk capacity. [10]

Inputs cap individual lines at 32 KiB; oversized tail lines are skipped and TCP
buffer limits can discard/disconnect oversized input. Syslog frames allow up to
64 KiB by default, matching the receiver's default ceiling. Test maximum records
and multiline/fragments against the selected pins. Rotation can overtake readers;
node disk/OS loss, loopback downtime and bounded queues can lose data.

Do not delete queues/cursors on reruns or rotate stream identities/destination
ownership while backlog is undrained. Preserve the directory through upgrades;
node reinstallation or disk loss is not protected by a hostPath. Rotate externally
issued leafs/CA bundles under the established trust procedure and restart affected
releases to load changed TLS files. No CA-key transfer, automatic renewal, archive
retention deletion or exactly-once claim is supplied.

## References

Official interfaces checked 2026-10-26; use documentation matching selected pins.

1. [Fluent native chart values](https://github.com/fluent/helm-charts/blob/main/charts/fluent-bit/values.yaml).
2. [Fluent Bit tail input, cursors and rotation](https://docs.fluentbit.io/manual/4.2/data-pipeline/inputs/tail).
3. [Talos service log forwarding](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/logging-and-telemetry/logging).
4. [Talos v1.13 machine/API configuration](https://docs.siderolabs.com/talos/v1.13/reference/configuration/v1alpha1/config).
5. [Talos v1.14 audit policy document](https://docs.siderolabs.com/talos/v1.14/reference/configuration/kubernetes/kubeauditpolicyconfig).
6. [Talos v1.14 API-server document](https://docs.siderolabs.com/talos/v1.14/reference/configuration/kubernetes/kubeapiserverconfig).
7. [Talos v1.13 API-server command and audit mount implementation](https://github.com/siderolabs/talos/blob/v1.13.0/internal/app/machined/pkg/controllers/k8s/control_plane_static_pod.go).
8. [Kubernetes audit policy levels and stages](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/).
9. [Fluent Bit syslog and TLS](https://docs.fluentbit.io/manual/4.2/data-pipeline/outputs/syslog), [hostname verification](https://docs.fluentbit.io/manual/4.2/administration/transport-security).
10. [Fluent Bit bounded filesystem buffering](https://docs.fluentbit.io/manual/4.2/data-pipeline/buffering).
11. [Kubernetes Secret custody and least privilege](https://kubernetes.io/docs/concepts/security/secrets-good-practices/).
12. [DaemonSet node affinity and scheduling](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/).
