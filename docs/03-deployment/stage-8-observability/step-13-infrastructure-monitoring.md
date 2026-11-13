# Step 13: Extend infrastructure monitoring

**Continue from:** [Stage 8, Step 13](README.md#step-13-extend-infrastructure-collection), after the selected
Tier 1 signal stack works.
**Return:** [Step 14 source enrollment](README.md#step-14-enroll-selected-sources).
**Working repositories:** `<prefix>-tier-0` owns infrastructure collection and credentials;
`<prefix>-tier-1` owns signal/query services. Shared owns neither inventory nor state.

The [infrastructure figure](README.md#figure-infrastructure-metrics) shows this extension:
the accepted Tier 0 monitor keeps local diagnostics/critical alerts and pushes only approved metrics.
Tier 1 Netdata parents and their local bridge were already installed by the selected observability path.
No monitor VM, search cluster or diagnostic parent is created again here.

**Prerequisites:** accepted [independent Tier 0 monitoring](../stage-6-secrets/procedures/independent-monitoring.md),
selected Tier 1 intake, metric client identity, trust and approved firewall path.
If that earlier monitoring option was not selected, install it once before this extension.
Proxmox host agents, IPMI and device-specific exporters remain separately qualified integrations;
the supplied Tier 0 role installs the native Netdata parent, Proxmox API exporter, Redfish jobs and bridge.

## Actions

1. [Register the selected sources](#1-register-the-selected-sources)
2. [Edit the existing monitor inputs](#2-edit-the-existing-monitor-inputs)
3. [Render and review the extension](#3-render-and-review-the-extension)
4. [Apply to the existing monitor](#4-apply-to-the-existing-monitor)
5. [Verify coverage and failure behavior](#5-verify-coverage-and-failure-behavior)

<a id="infrastructure-monitoring"></a>
<a id="step-1-register-sources-and-access"></a>

## 1. Register the selected sources

Record source ownership, actual host/BMC endpoints, physical dependencies and read-only collection identity
in **Tier 0's inventory and monitoring inputs**. The empty `hypervisors` group discovers no hardware.
Keep tokens/passwords in the encrypted private file, not inventory.

| Source | Select and qualify |
| --- | --- |
| Proxmox API | Fixed read-only targets through the Tier 0-local API exporter; no mutation/power privileges [2] |
| Proxmox host diagnostics | Existing reviewed host agents for CPU/disk/network/cgroups; an agent inside a VM cannot replace them [1] |
| Redfish | Native jobs with a dedicated read-only BMC account, verified TLS and explicit device coverage [3] |
| IPMI, network, storage, UPS | Product-specific IPMI/API/SNMPv3 integration; record unsupported signals explicitly [4] |

Do not introduce direct management polling from Tier 1. The metric bridge filters approved names/labels
before pushing; native Netdata streaming, Prometheus scraping and OTLP are distinct interfaces.

<a id="step-2-connect-diagnostics-and-metric-history"></a>

## 2. Edit the existing monitor inputs

Edit in **`<prefix>-tier-0/`**:

- `ansible/group_vars/infrastructure_monitoring.yml`: selected Proxmox/Redfish jobs, exact metric
  names/labels and `infrastructure_monitoring_export_endpoint` for the accepted private metrics listener.
- `ansible/group_vars/infrastructure_monitoring_secrets.yml`: encrypted private-file map supplying
  export client certificate/key and gateway CA, plus retained existing target/notification inputs.

Keep local history, health rules and independent notifications enabled. The bridge receives no BMC/Proxmox
credentials and gives Tier 1 no target-selection, configuration or power authority.

Tier 1's diagnostics are already installed. If its settings need changing, edit the existing
`observability_platform.yml` (Kubernetes) or `observability.yml` (VMs), retaining search bootstrap false.
Use the accepted [Kubernetes reconciliation](procedures/observability-platform.md#reconcile-an-accepted-installation)
or [VM reconciliation](../../05-operations/06-resilience/observability.md#how-are-dedicated-vms-reconciled)
once before continuing. Do not add another diagnostic deployment merely to review its configuration.

## 3. Render and review the extension

Run from **`<prefix>-tier-0/`**, selecting the already commissioned monitor:

```bash
read -r -p 'Existing monitoring inventory host (for example mon-1): ' MONITOR_HOST
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  --limit "${MONITOR_HOST:?Select the existing monitor}" \
  ansible/playbooks/deployment/infrastructure-monitoring.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/infrastructure_monitoring.yml \
  -e @ansible/group_vars/infrastructure_monitoring_secrets.yml --ask-vault-pass \
  -e infrastructure_monitoring_action=render
```

Review the private output: same host, retained local alerts, exact read-only targets, filtered metric
scope, gateway endpoint and TLS identity. No VM or Tier 1 release is changed by this render.

For a separately accepted existing host, append `-e "@ansible/host_vars/$MONITOR_HOST.yml"` with its actual
connection override file. For named environments load approved `all.<env>.yml` and complete
`foundation.<env>.yml` after their base files in both commands. Preserve the full foundation IP map;
a monitor-only extra-vars map replaces it rather than merging it.

## 4. Apply to the existing monitor

Use the same host, files and any environment/host overrides reviewed above.
Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  --limit "${MONITOR_HOST:?Select the existing monitor}" \
  ansible/playbooks/deployment/infrastructure-monitoring.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/foundation.yml \
  -e @ansible/group_vars/infrastructure_monitoring.yml \
  -e @ansible/group_vars/infrastructure_monitoring_secrets.yml --ask-vault-pass \
  -e infrastructure_monitoring_action=apply
```

**Expected:** existing local diagnostics/alerts remain available and the selected authenticated metric bridge
is reconciled. Apply changes that host without another prompt. Approved unattended execution supplies
an Ansible Vault identity instead of `--ask-vault-pass`.

<a id="step-3-verify-coverage-and-failure-behavior"></a>

## 5. Verify coverage and failure behavior

| Check | Required evidence |
| --- | --- |
| Host/guest coverage | Current samples for every selected source; migration preserves distinguishable host/guest identities |
| Hardware | Selected sensors match BMC values; absent/stale sources are unknown, not healthy zeroes |
| Least privilege | Pollers cannot mutate/power-cycle targets; Tier 1 cannot access credentials or expand the source scope |
| Pipeline | Approved metrics reach both accepted stores; endpoint outage, queues/replay and catch-up meet declared limits |
| Diagnostics | Parent loss triggers supported reconnect/failover; history catch-up is measured, not inferred from two pods [5][6] |
| Independent detection | Tier 0 critical alerts still arrive while Tier 1, hosted source control or normal SSO is unavailable |
| Recovery | Clean-target history/metrics recovery works; protected evidence remains unchanged |

Record blind spots, tested thresholds and alert acknowledgement ownership. Raw Netdata, Functions and
BMC diagnostics are administrator interfaces, not tenant portals. Return to
[Stage 8 Action 14](README.md#step-14-enroll-selected-sources); no first-install step is repeated.

## References


Sources checked 2026-10-22; qualify collectors and chart values against pinned releases.

1. [Netdata Proxmox host monitoring](https://learn.netdata.cloud/docs/collecting-metrics/collectors/containers-and-vms/proxmox-ve-monitoring)
2. [Proxmox VE Prometheus exporter](https://github.com/prometheus-pve/prometheus-pve-exporter)
3. [Netdata Redfish collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/redfish)
4. [Netdata FreeIPMI collector](https://learn.netdata.cloud/docs/collecting-metrics/collectors/hardware-and-sensors/intelligent-platform-management-interface-ipmi)
5. [Netdata Kubernetes Helm chart](https://learn.netdata.cloud/docs/netdata-agent/installation/kubernetes-helm-chart-reference)
6. [Netdata parent clustering and failover](https://learn.netdata.cloud/docs/netdata-parents/metrics-centralization-points/clustering-and-high-availability-of-netdata-parents)
7. [Netdata Prometheus export](https://learn.netdata.cloud/docs/exporting-metrics/prometheus)
