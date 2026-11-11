# Step 3: Connect infrastructure monitoring

<a id="infrastructure-monitoring"></a>

**Continue from:** [Stage 8, Step 3](README.md#step-3-connect-infrastructure-monitoring), after signal intake is ready.
**Return:** [Step 3 acceptance](README.md#step-3-connect-infrastructure-monitoring) after proving local diagnostics, independent alerts and approved metric delivery;
then continue with Step 4 reader access.

Connect IT-system health to [Stage 8, Step 3](README.md#step-3-connect-infrastructure-monitoring):
Netdata live diagnostics plus retained infrastructure metrics and actionable alerts.
This extends earlier Tier 0 monitoring; it does not relocate it into Tier 1.

**Working repositories:** `<prefix>-tier-0` (source: `tier-0/`) and
`<prefix>-tier-1` (source: `tier-1/`). Tier 0 owns Proxmox/BMC targets, credentials,
local collectors and approved exports. Tier 1 owns shared diagnostics, metric history, rules and UIs.
Other tiers own their agents and source inventory. Shared may supply reusable roles,
but never targets, credentials or state.
**Prerequisites:** [independent monitoring](../stage-6-secrets/procedures/independent-monitoring.md),
accepted Tier 1 signal intake from [Stage 8 Step 2](README.md#step-2-deploy-the-signal-pipelines)
or the [dedicated VM integration](step-1b-dedicated-vms.md#step-3-integrate-and-accept-the-services),
approved source inventory, TLS trust, firewall policy and physical failure-domain mapping.
**Design:** [coverage and ownership](../../01-architecture/11-operations/03-observability.md#infrastructure-coverage).
**Automation:** the [Tier 0 role](../../../tier-0/ansible/roles/infrastructure_monitoring)
installs its independent Netdata parent, Redfish jobs, loopback Proxmox exporter and optional
allowlisted metric bridge. The [Tier 1 role](../../../tier-1/ansible/roles/observability_platform)
owns Kubernetes diagnostics and both metrics copies on the main path. The VM alternative
uses the [native VM installer](../../../tier-1/ansible/roles/observability_vm); the cluster starter installs no products.

## Main path

1. [Register sources and access](#step-1-register-sources-and-access)
2. [Connect diagnostics and metric history](#step-2-connect-diagnostics-and-metric-history)
3. [Verify coverage and failure behavior](#step-3-verify-coverage-and-failure-behavior)

## Step 1: Register sources and access

1. Record sources in the owning tier's inventory: host/BMC endpoints, role, physical
   host/rack/power dependencies and selected sensor/API coverage. Tier 0's
   [hypervisors group](../../../tier-0/ansible/inventory/hosts.yml.example) is initially empty;
   it is not a discovered hardware catalogue. Never put passwords or tokens in inventory.
2. Select collection per source, rather than assuming one Kubernetes agent covers hardware:

   | Selection | Configuration and limits |
   | --- | --- |
   | Proxmox host diagnostics | Reviewed Netdata host installation for native CPU, disk, network and VM/LXC cgroup metrics; an agent inside a VM cannot supply host visibility [1] |
   | Proxmox API-only collection | Tier 0-local read-only API exporter, such as the PVE exporter; covers API resource/cluster data, not every host diagnostic [2] |
   | Redfish hardware | Tier 0 Netdata collector with a dedicated read-only BMC account, validated TLS and explicit device jobs [3] |
   | IPMI alternative | Qualify the FreeIPMI collector, BMC privileges and package/host-access requirements; do not assume an unprivileged Kubernetes pod can run it [4] |
   | Storage, network and UPS | Select the device's supported exporter/API or SNMPv3 collector; record unsupported and missing signals explicitly |

3. Keep pollers beside their targets in Tier 0. Store credentials in approved local or
   encrypted secret inputs; grant no power/reset/configuration actions. Restrict exporter
   listeners and target selection to approved local collectors, not Tier 1 clients or
   arbitrary target parameters. Qualify changes to the hypervisor through Tier 0 maintenance.

**Result:** an explicit coverage list and least-privilege collection plan, with known gaps.

## Step 2: Connect diagnostics and metric history

1. For Kubernetes, review the installed, pinned Netdata values [5] in Tier 1's
   [service role](../../../tier-1/ansible/roles/observability_platform/templates/netdata-values.yml.j2).
   Select node children, cluster-state collection and parents; review host mounts,
   capabilities and node-OS compatibility. For dedicated VMs, review the project-owned
   diagnostics configuration and agents. Keep duplicate OTLP/log collection disabled
   unless separately selected; neither path adds a security-log receiver.
2. Verify the selected pair of Tier 1 parents has separate identities, data volumes and
   physical failure domains. Configure child endpoint failover and supported parent
   synchronization; increasing the chart's default single parent replica count is not
   sufficient. On Kubernetes, the role supplies separate namespaces and native Secret configuration.
   Size history for the accepted outage/catch-up window. [5][6]
   Retain the independent Tier 0 parent and critical rules outside the observed cluster;
   Tier 0 child streams do not automatically gain a Tier 1 destination.
3. Configure an explicit Prometheus metric bridge [7]: Tier 0-owned Collectors scrape
   approved local Netdata/exporter metrics, filter names/labels, then push authenticated
   OTLP metrics to the Tier 1 gateways. Tier 1 Collectors may scrape local Netdata parents.
   Gateways write to both accepted metrics stores. Assign one collection
   owner per series; native streaming, Prometheus and OTLP are different interfaces.

On the Kubernetes path, Step 2 already installs the Tier 1 parents and their local bridge.
If this review changes Tier 1 values, render/review/reapply the existing
[Observability installation](procedures/observability-platform.md#8-render-the-complete-platform) before enabling its sources.
Keep `observability_search_bootstrap: false` for that established cluster. On the VM path,
edit **`<prefix>-tier-1/ansible/group_vars/observability.yml`** instead of chart values. Retain the
accepted `observability_vm_netdata_scrape_parent` and exact `observability_vm_netdata_scrape_metrics`
allowlist, then [reconcile the native VM services](../../05-operations/06-resilience/observability.md#how-are-dedicated-vms-reconciled).

The Netdata interface is operator diagnostics, not a multi-tenant application portal.
Do not expose raw Tier 0 views, Functions or BMC credentials through the Tier 1 UI.
Use the scoped metric-query interface for less-privileged readers; hiding a dashboard
or chart is not authorization. Security evidence still follows the
[protected logging path](../stage-2-logging/README.md).

To enable the Tier 0 bridge after the Tier 1 metrics receiver is accepted:

1. Edit these existing files:

   Edit in **`<prefix>-tier-0/`**.

   - `ansible/group_vars/infrastructure_monitoring.yml`: `infrastructure_monitoring_export_endpoint` to the
     accepted private gateway/metrics port. Restrict `infrastructure_monitoring_export_metrics` /
     _export_labels to approved data.
   - `ansible/group_vars/infrastructure_monitoring_secrets.yml`: Encrypted private-file map with scoped
     export.crt/export.key and CA trust.

2. Render/review and reapply the [existing monitoring recipe](../stage-6-secrets/procedures/independent-monitoring.md#step-3-enable-and-verify-independent-alerts).
   It retains local diagnostics/alerts and adds the selected bridge; it grants Tier 1 no poller credentials.
3. Continue the Tier 1 sample/failure checks:

   **Execution context:** `<prefix>-tier-1/`.

**Result:** live diagnostics and retained approved metrics, with separate resource budgets.

## Step 3: Verify coverage and failure behavior

| Check | Required evidence |
| --- | --- |
| Host and guest coverage | Every selected Proxmox node/guest produces current samples; host and guest identities remain distinguishable after migration |
| Hardware | Supported temperature/fan/power/storage sensors match the BMC; missing sensors and failed polls show unknown/stale, not healthy zeroes |
| Actionable alerts | Tested thresholds and notification ownership for resource pressure, storage degradation, loss of quorum, expired certificates and missing sources |
| Least privilege | Poller identities cannot power-cycle or reconfigure targets; Tier 1 cannot connect to management APIs, request arbitrary targets or expand its metric scope |
| Netdata failure | Loss of a parent/worker triggers child failover; surviving capacity suffices, history catches up within the declared window and a lagging parent is not presented as complete [6] |
| Pipeline failure | Gateway/metrics-copy outage, bounded queues, replay and duplicate-series handling meet the accepted RPO/RTO |
| Independent detection | With Tier 1 unavailable, Tier 0 diagnostics and external critical alerts still work without normal SSO |
| Recovery | Parent/metrics backups restore on clean capacity; protected Tier 0 evidence remains unchanged |

Record results in the owning repositories' project administration records. Product
defaults, two pods and a successful scrape are not HA or operational acceptance.
Return to [Stage 8 read authorization](README.md#step-4-publish-and-verify-read-only-views).

## References

Sources checked 2026-10-22; qualify collectors and chart values against pinned releases.

1. [Netdata Proxmox host monitoring](https://learn.netdata.cloud/docs/collecting-metrics/collectors/containers-and-vms/proxmox-ve-monitoring)
2. [Proxmox VE Prometheus exporter](https://github.com/prometheus-pve/prometheus-pve-exporter)
3. [Netdata Redfish collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/redfish)
4. [Netdata FreeIPMI collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/intelligent-platform-management-interface-ipmi)
5. [Netdata Kubernetes Helm chart](https://learn.netdata.cloud/docs/netdata-agent/installation/kubernetes-helm-chart-reference)
6. [Netdata parent clustering and failover](https://learn.netdata.cloud/docs/netdata-parents/metrics-centralization-points/clustering-and-high-availability-of-netdata-parents)
7. [Netdata Prometheus export](https://learn.netdata.cloud/docs/exporting-metrics/prometheus)
