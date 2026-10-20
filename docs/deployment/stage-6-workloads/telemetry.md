# Scoped workload collection

Connect workload signals to the existing evidence and analytics capabilities.
This adds lightweight collection, not another full observability stack per cluster.

**Working repository:** `<prefix>-tier-2` (source: `tier-2/`).
Other tiers apply the same routing contract using their own inventories and credentials.
**Prerequisites:** approved runtime, [Tier 0 intake](../stage-1-logging/README.md) and the
selected [Tier 1 telemetry interfaces](../stage-5-delivery/analytics.md).
**Design:** [telemetry boundaries](../../architecture/operations/telemetry.md).

## Main path

1. [Prepare local collection](#step-1-prepare-local-collection)
2. [Connect the authorized destinations](#step-2-connect-the-authorized-destinations)
3. [Verify buffering and reader isolation](#step-3-verify-buffering-and-reader-isolation)

## Step 1: Prepare local collection

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  subgraph T2["Tier 2 / existing workload runtime"]
    subgraph VM["lab-1 / Linux VM example"]
      Agents["Shared log_forwarder<br/>OS / audit / selected file streams"]
      Queue[("Local durable queues")]
      Agents --> Queue
    end
    subgraph Project["Project integration / cluster collection"]
      Apps["Application instrumentation<br/>OTel agents / exporters"]
    end
    VM ~~~ Project
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T2,Apps,Agents services
  class Queue data
  class VM boundary
  class Project replicas
```

**IaC:** Tier 2 [producer recipe](../../../tier-2/ansible/playbooks/deployment/logging-producers.yml)
executes Shared's [native sender](../../../shared/ansible/roles/log_forwarder/tasks/main.yml)
on selected existing Linux hosts, such as `lab-1`; it creates no VM.
The [cluster starter](../../../tier-2/clusters/tier2/kustomization.yaml) does not install the dashed OTel/instrumentation group.

1. Identify source owners and required security, application, metric and trace streams.
2. Use the [Linux source recipe](../stage-1-logging/sources.md) for protected log submission.
   Add project roles/manifests for other agents and cluster collectors. Set source credentials,
   disk permissions, buffer capacity and retry limits.
3. Verify local collection, source identity and missing-source detection. Supplied
   VM/cluster provisioning does not install these products automatically.

## Step 2: Connect the authorized destinations

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / existing workload runtime"]
    Collect["lab-1 / Shared log_forwarder"]
    OTel["Project integration / OTel collection"]
    Owner["Application owner"]
  end
  subgraph T1["Tier 1 / project-integrated analytics"]
    Analytics["Approved application views / telemetry intake"]
  end
  subgraph T0["Tier 0 / existing protected intake"]
    Evidence["log-1 / syslog-ng"]
  end
  Collect -->|TLS / catalogued log streams| Evidence
  OTel -->|Selected application telemetry| Analytics
  Owner -->|Read own approved view| Analytics
  T2 ~~~ T1 ~~~ T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T2,T1,Collect,Analytics services
  class T0,Evidence control
  class OTel replicas
  class Owner actor
```

**IaC:** the Tier 2 [producer recipe](../../../tier-2/ansible/playbooks/deployment/logging-producers.yml)
and [local source selections](../../../tier-2/ansible/group_vars/logging_producers.yml.example)
target existing Tier 0 intake. OTel-to-Tier-1 routing and analytics views remain project integration,
not behavior of the Linux sender recipe.

1. Route security/audit events to scoped Tier 0 intake and ordinary application
   telemetry to the approved Tier 1 interfaces.
2. Configure trusted ownership from authenticated routing, not arbitrary labels.
   Producers receive no raw-archive query or administration credentials.
3. Submit sample events and verify the matching application view and protected evidence.

## Step 3: Verify buffering and reader isolation

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  subgraph T2["Tier 2 / existing producer lab-1"]
    Source["Numbered test events"] --> Buffer[("Local durable queues")]
  end
  subgraph T0["Tier 0 / existing log-1 receiver"]
    Backend["Protected intake / retained test records"]
  end
  Buffer -->|Replay after bounded outage| Backend
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  class T2,Source services
  class T0,Backend control
  class Buffer data
```

**Workflow:** verify the installed [Linux sender](../../../shared/ansible/roles/log_forwarder/tasks/main.yml)
against the [Tier 0 receiver](../../../tier-0/ansible/roles/syslog_ng/tasks/main.yml), using the
[fault drill](../../administration/logging-drill.md). Repeat the corresponding tests for project-integrated Tier 1 collectors;
this verification view creates no new service or host.

1. Interrupt Tier 1 connectivity and restart collectors. Verify replay, duplicate/gap
   accounting and capacity/loss alarms against the declared outage window.
2. Test source impersonation, forged ownership and cross-application reads; deny destructive
   query operations and access to Tier 0 originals.
3. Record failure behavior. Tier 2 normally retains collection during Tier 1 outages,
   not independent querying or alerts. Critical workloads explicitly select local retention/evaluation.

## IaC locations

| Repository | Path inside that repository | Coverage |
| --- | --- | --- |
| Tier 2 | [clusters/tier2/](../../../tier-2/clusters/tier2/) | Project collector/instrumentation manifests; no supplied collector installer |
| Tier 2 | [ansible/](../../../tier-2/ansible/) | Tier-local inventory and project host-agent recipes |
| Shared | [ansible/roles/baseline/](../../../shared/ansible/roles/baseline/) | Reusable host preparation only |

**Result:** approved signals reach their scoped destinations without granting workload
users evidence deletion authority. Return to [Stage 6 acceptance](README.md#capability-available).
