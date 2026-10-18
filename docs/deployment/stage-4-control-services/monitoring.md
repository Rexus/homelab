# Independent foundation monitoring

Add critical health history, diagnostics, rule evaluation and alerts to the existing
protected logging capability. This is the monitoring deployment in Stage 4, not a
prerequisite for the earlier collector.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted [protected logging](../stage-1-logging/README.md), approved
runtime/storage and independent recovery inputs. Tier 1 analytics is not required.
**Design:** [telemetry composition](../../architecture/operations/telemetry.md).

## Main path

1. [Prepare the monitoring runtime](#step-1-prepare-the-monitoring-runtime)
2. [Add critical health and history](#step-2-add-critical-health-and-history)
3. [Enable and verify independent alerts](#step-3-enable-and-verify-independent-alerts)

The repository supplies VM foundations and cluster starters, not a monitoring-stack
installer. Product configuration/manifests and their execution recipe remain project-owned.

## Step 1: Prepare the monitoring runtime

```mermaid
flowchart LR
  Existing["Existing Tier 0 log intake<br/>Protected evidence"] --- Host["Existing independent Tier 0 host<br/>Monitoring capacity selected"]
  Cluster["Tier 0 cluster being observed"] -. Must not host its only outage detector .-> Host
```

1. Select an existing independent host or provision reviewed Tier 0 capacity.
   Reuse the log VM only after evaluating capacity and the shared failure domain;
   it does not independently detect its own complete host loss.
2. Keep required cluster-outage detection outside that cluster. Cluster manifests
   may add internal monitoring, but cannot replace the external detector.
3. Record placement, local access, storage/backups and signal ownership. If changing
   existing `syslog` VM capacity, review `bash scripts/deploy.sh syslog --plan-only`
   before applying; there is no separate supplied `monitoring` setup.

**Result:** a selected runtime that remains available during the required cluster outage.

## Step 2: Add critical health and history

```mermaid
flowchart LR
  Sources["Hosts, storage, network<br/>Log queues and control APIs"] --> Metrics["Tier 0 critical metric history"]
  Agents["Netdata agents"] --> Parent["Tier 0 live diagnostics"]
  Metrics --> Rules["Local rule evaluation"]
```

1. Select a small dataset: host/storage/network health, source coverage, receiver queues,
   evidence writes/replication, capacity, certificate expiry and cluster/API availability.
2. Add supported agents and the selected metric/history/evaluation components using
   project-owned automation. Reference examples are Netdata, VictoriaMetrics and vmalert.
   These functions may share a host; no VM per function is required.
3. Verify sample signals, local reader scopes and retained history. Netdata streaming
   is a separate integration from OpenTelemetry pipelines; do not imply automatic forwarding.

**Result:** foundation diagnostics and critical history are usable without Tier 1 search.

## Step 3: Enable and verify independent alerts

```mermaid
flowchart LR
  Rules["Tier 0 local rules"] --> Routing["Independent notification delivery"] --> Admin["Authorized administrators"]
  Watch["External heartbeat / watchdog"] -->|Collector or monitoring host missing| Admin
  T1["Tier 1 unavailable"] -. No required dependency .-> Rules
```

1. Configure local evaluation and notification routing, such as Alertmanager, with
   independent credentials and an approved external notification path. Keep alert payloads
   minimal; notifications do not grant external access to sensitive raw logs.
2. Test cluster/API failure, missing source, stalled evidence writes, capacity thresholds
   and loss of the monitoring host. The external heartbeat detects failure of the local detector.
3. Repeat required checks without Tier 1, hosted source control, normal SSO or secret services.
   Record delivery, silence/acknowledgement authority, recovery and remaining blind spots.

**Result:** required foundation failures produce independently delivered alerts.

## IaC locations

| Repository | Path inside that repository | Coverage |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/syslog/](../../../tier-0/terraform/deployments/syslog/) | Existing independent log-host resources; reuse does not install monitoring |
| Tier 0 | [clusters/tier0/](../../../tier-0/clusters/tier0/) | Project cluster manifests; no monitoring installer |
| Tier 0 | [ansible/playbooks/deployment/foundation-logging.yml](../../../tier-0/ansible/playbooks/deployment/foundation-logging.yml) | Existing baseline and log receiver; monitoring product roles/recipes must be added explicitly |
| Shared | [ansible/roles/baseline/](../../../shared/ansible/roles/baseline/) | Common OS preparation, not inventory, state or alert authority |

Return to [Stage 4 acceptance](README.md#capability-available). Later
[Tier 1 analytics](../stage-5-delivery/analytics.md) adds shared investigation without
taking ownership of foundation alerts or protected evidence.
