# Observability operations

Operate diagnostics, infrastructure health and scoped telemetry. Protected originals
remain under [protected logging](protected-logging.md); search projections have separate retention.

<a id="figure-observability-operating-scope"></a>

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":12,"rankSpacing":4,"padding":8,"subGraphTitleMargin":{"top":2,"bottom":8}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1["Tier 1 / Kubernetes selection"]
    subgraph Cluster["Existing platform Kubernetes"]
      direction TB
      subgraph Serving["Signal and query services"]
        direction LR
        subgraph Readers["Reader-facing services"]
          direction TB
          UIs["grafana / dashboards<br/>Two replicas each"]
          Query{{"metrics-query x2<br/>vmauth / selected read members"}}
          UIs ~~~ Query
        end
        subgraph Processing["Ingestion services"]
          direction TB
          Gateway{{"otel-gateway x2<br/>Separate persistent queues"}}
          Prepper["data-prepper x2<br/>Scoped log / trace pipelines"]
          Gateway -->|Logs / traces| Prepper
        end
        subgraph Backends["Persistent backend services"]
          direction TB
          Metrics["metrics-1 / metrics-2<br/>Separate PVCs"]
          Search["opensearch x3 / own PVCs"]
          DB["grafana-db / PostgreSQL x3<br/>Live block PVCs"]
          Metrics ~~~ Search ~~~ DB
        end
        Readers -->|Queries / Grafana SQL| Backends
        Processing -->|Metrics / scoped logs and traces| Backends
        Readers ~~~ Processing
      end
      subgraph Diagnostics["Netdata diagnostics / persistent parent history"]
        direction LR
        subgraph Parents["Diagnostic parents"]
          direction TB
          N1["netdata-1"]
          N2["netdata-2"]
          N1 ~~~ N2
        end
        Agents["netdata-1 chart agents<br/>Node children / k8sState collector"]
        Bridge["netdata-metrics / selected bridge<br/>One parent / exact metric allowlist"]
        Agents -->|Authenticated streams| Parents
        Bridge -->|Read selected metrics| Parents
      end
      Serving ~~~ Diagnostics
    end
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef replicas fill:#f5f6f7,stroke:#89939e,color:#273340,stroke-dasharray:5 4
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class UIs,Prepper,Metrics,Search,DB,N1,N2,Agents,Bridge services
  class Parents replicas
  classDef group fill:#f5f6f7,stroke:#89939e,color:#273340
  class Backends,Diagnostics,Processing,Readers,Serving group
  classDef kubernetes fill:#e8eef6,stroke:#6b83a3,color:#263d59
  class Cluster kubernetes
  classDef traffic fill:#e1f3f5,stroke:#4c7f88,color:#214a52
  class Query,Gateway traffic
  classDef tier1 fill:#e9e2d8,stroke:#968976,color:#44382a
  class T1 tier1
```

**IaC / Integration:** *Figure: The Kubernetes main-path signal, query, database and diagnostic workload set.
Backend boxes aggregate native members and their attached persistence; replica counts alone are not availability evidence.
The diagnostic bridge supplies allowlisted metrics to the ingestion group; the overview separates their placement.*
In **`<prefix>-tier-1/`**, [platform inputs](../../../tier-1/ansible/group_vars/observability_platform.yml.example),
[release composition](../../../tier-1/ansible/roles/observability_platform/templates/releases.yml.j2),
[database resources](../../../tier-1/ansible/roles/observability_platform/templates/grafana-database.yml.j2) and the
[installer](../../../tier-1/ansible/playbooks/deployment/observability-platform.yml) own this scope.
[Netdata values](../../../tier-1/ansible/roles/observability_platform/templates/netdata-values.yml.j2)
enable node/state collection only in the `netdata-1` release; the metric bridge is selected by its allowlist.
The [VM selection](#figure-observability-vm-operations) replaces these Kubernetes workloads.
[Tier 0 infrastructure collection](../../03-deployment/stage-8-observability/step-13-infrastructure-monitoring.md),
[optional protected-log projections](../../03-deployment/stage-8-observability/step-14b-protected-log-search.md) and
[database backups](backups/postgresql.md) retain separate inputs and acceptance.

**Design:** [Observability](../../01-architecture/11-operations/03-observability.md).
**Install and acceptance:** [Stage 8](../../03-deployment/stage-8-observability/README.md).

## Table of contents

- [Find the configuration](#find-the-configuration)
- [Reconcile dedicated VMs](#how-are-dedicated-vms-reconciled)
- [Maintain VM diagnostics](#how-are-vm-diagnostics-maintained)
- [Render and apply Kubernetes configuration](#how-is-accepted-configuration-reapplied)
- [Choose maintenance or recovery](#which-maintenance-or-recovery-task-applies)

## Find the configuration

In **`<prefix>-tier-1/`**, edit the inputs for the selected runtime:

| Runtime | File | Purpose |
| --- | --- | --- |
| Kubernetes | `ansible/group_vars/observability_platform.yml` | Cluster/context, source scopes, chart pins, storage, access and recovery |
| Kubernetes | `ansible/group_vars/observability_platform_secrets.yml` | Protected credentials, service identities and Netdata stream keys |
| Kubernetes | [Platform defaults](../../../tier-1/ansible/roles/observability_platform/defaults/main.yml) | Available settings |
| Dedicated VMs | `ansible/group_vars/observability.yml` | Guest endpoints, image pins, source scopes, diagnostic access and metric-bridge selection |
| Dedicated VMs | Protected file selected by `observability_vm_private_vars_file` | Credentials, SSO secrets and separate Netdata child/peer stream keys |
| Dedicated VMs | [VM defaults](../../../tier-1/ansible/roles/observability_vm/defaults/main.yml) | Available settings, resource ceilings and history budgets |

The [native Ansible installer](../../../tier-1/ansible/playbooks/deployment/observability-platform.yml)
renders and applies the selected stack. The cluster directory is a separate integration
starter. The [dedicated-VM installer](../../../tier-1/ansible/playbooks/deployment/telemetry-hosts.yml)
owns the alternative Podman/systemd products and their guarded persistent disks.
It also installs two Netdata parents on `otel-1/2` and children on the five metrics/search guests.

## How are dedicated VMs reconciled?

<a id="figure-observability-vm-operations"></a>

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":12,"rankSpacing":4,"padding":8,"subGraphTitleMargin":{"top":2,"bottom":8}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1["Tier 1 / dedicated-VM replacement selection"]
    subgraph PVE["Existing Proxmox / observability network"]
      direction TB
      subgraph Services["Native Podman / systemd runtimes"]
        direction LR
        subgraph Gateways["Gateway / frontend guests"]
          direction TB
          O1["otel-1<br/>Collector / Prepper / vmauth<br/>Dashboards / Grafana / Netdata parent"]
          O2["otel-2<br/>Collector / Prepper / vmauth<br/>Dashboards / Netdata parent"]
          O1 ~~~ O2
        end
        subgraph Metrics["Independent metric stores"]
          direction TB
          M1["metric-1 / Netdata child"]
          M2["metric-2 / Netdata child"]
          M1 ~~~ M2
        end
        subgraph Search["OpenSearch members"]
          direction TB
          S1["search-1 / Netdata child"]
          S2["search-2 / Netdata child"]
          S3["search-3 / Netdata child"]
          S1 ~~~ S2 ~~~ S3
        end
        Gateways -->|Write both / query selected stores| Metrics
        Gateways -->|Scoped ingest / queries| Search
        Metrics ~~~ Search
      end
      Disks[("One scsi1 data disk per guest<br/>Queues / backends / Netdata identity and history<br/>Grafana SQLite on otel-1 only")]
      Services -->|Guest-local persistence| Disks
    end
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef replicas fill:#f5f6f7,stroke:#89939e,color:#273340,stroke-dasharray:5 4
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class O1,O2,M1,M2,S1,S2,S3 services
  class PVE boundary
  classDef group fill:#f5f6f7,stroke:#89939e,color:#273340
  class Services,Gateways,Metrics group
  class Search replicas
  class Disks data
  classDef tier1 fill:#e9e2d8,stroke:#968976,color:#44382a
  class T1 tier1
```

**IaC:** *Figure: All seven guests in the VM selection, with co-located processing, query and diagnostic services.
The data-disk shape aggregates seven separate local disks; it is not shared backend storage.*
Tier 1's [VM inputs](../../../tier-1/terraform/deployments/observability/terraform.tfvars.example),
[service inputs](../../../tier-1/ansible/group_vars/observability.yml.example),
[service composition](../../../tier-1/ansible/roles/observability_vm/tasks/main.yml) and
[Netdata installer](../../../tier-1/ansible/roles/observability_vm/tasks/netdata.yml) own this alternative.
Children stream to the two parents, parents peer-stream, and only the selected parent supplies bridge metrics.
The single Grafana/SQLite instance and per-store metrics copies retain their documented recovery limits.

Review the existing VM inputs and private file; keep `observability_vm_search_bootstrap: false`
after commissioning. Supply the accepted Vault password through the controller secret owner.

Run from **`<prefix>-tier-1/` on the controller**:

```bash
bash scripts/deploy.sh observability --ansible-only
```

Use the complete seven-host inventory. The recipe configures all members, starts the Netdata
parents and children, then reconciles backends, search policy and gateways/frontends. It checks
verified TLS, seven reachable identities on each parent and samples for selected bridge metrics.
Repeat the [VM acceptance checks](../../03-deployment/stage-8-observability/step-1b-dedicated-vms.md#step-4-integrate-and-accept-the-services)
and retained-data recovery tests; installation checks do not establish catch-up completeness or HA.

## How are VM diagnostics maintained?

1. Keep diagnostics on the selected administrator network. Native Netdata reads use HTTPS on
   `observability_vm_netdata_diagnostics_port` (default `20000`), restricted by
   `observability_vm_netdata_admin_allow_from`. Parent port `19999` accepts authenticated TLS
   streams only. Keep these endpoints outside tenant Grafana/Dashboards routes.
2. Preserve the distinct child and peer stream keys and each guest's issued TLS identity.
   Children list both parents; each parent streams to its peer. Review image pins and shared
   gateway capacity with the [VM installation inputs](../../03-deployment/stage-8-observability/step-1b-dedicated-vms.md#step-1-configure-the-hosts)
   before reconciliation. The [native Netdata installer](../../../tier-1/ansible/roles/observability_vm/tasks/netdata.yml)
   owns configuration and the [Quadlet](../../../tier-1/ansible/roles/observability_vm/templates/netdata.container.j2)
   generating `obs-netdata.service` on all seven guests.
3. Keep one collection owner: `observability_vm_netdata_scrape_parent` selects the parent whose
   native Prometheus export enters the existing Collector pipeline. Change it only after checking
   catch-up; `observability_vm_netdata_scrape_metrics` remains an exact metric-name allowlist.
   Reconcile the VM recipe after changing these inputs. Do not scrape both parents in parallel.
4. Back up and restore both VM disks and original inputs. Preserve the per-guest Netdata identity
   in `/srv/observability/netdata/lib` and history in `/srv/observability/netdata/cache`; never clone
   another guest's identity directory. Follow the [VM backup procedure](backups/virtual-machines.md)
   and test streaming reconnection, retained history and administrator-versus-tenant denial.

Tier 1 diagnostic health notifications are disabled. Independent Tier 0 alerts and hardware/API
collection remain separately owned; the VM installer receives no Tier 0 collector credentials.

## How is accepted configuration reapplied?

For the **Kubernetes runtime**, use its render/review/apply workflow:

1. Review the existing context, source allowlists, access policy and recovery copies using
   the [configuration procedure](../../03-deployment/stage-8-observability/procedures/observability-platform.md).
   Keep `observability_search_bootstrap: false` on an established search cluster.
2. In **`<prefix>-tier-1/`**, render the selected inputs. Supply the existing Vault password:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
     ansible/playbooks/deployment/observability-platform.yml \
     -e @ansible/group_vars/observability_platform.yml \
     -e @ansible/group_vars/observability_platform_secrets.yml --ask-vault-pass \
     -e observability_action=render
   ```

3. Review the output, then apply from **`<prefix>-tier-1/`**:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
     ansible/playbooks/deployment/observability-platform.yml \
     -e @ansible/group_vars/observability_platform.yml \
     -e @ansible/group_vars/observability_platform_secrets.yml --ask-vault-pass \
     -e observability_action=apply
   ```

   Repeat Stage 8's readiness, source-to-query and scoped-access checks before recording completion.

## Which maintenance or recovery task applies?

| Task | Procedure |
| --- | --- |
| Plan a product upgrade | [Upgrade gate](../01-hosting/maintenance.md#upgrade-gate) |
| Check VM maintenance scope | [Recipe map](../01-hosting/ansible-recipes.md#recipe-map) |
| Protect PostgreSQL data | [PostgreSQL backups](backups/postgresql.md) |
| Restore shared product data | [Tier 1 recovery](recovery/tier-1-products.md) |
| Check node, Proxmox, IPMI and Netdata source coverage | [Stage 8 checks](../../03-deployment/stage-8-observability/README.md#main-path) |

Configuration reconciliation does not replace version-specific database or search migrations.
