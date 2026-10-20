# Shared observability and investigation

Add Tier 1 search, dashboards, shared metric history and application investigation.
Tier 0 evidence and critical alerts already work independently; this deployment
publishes approved copies rather than moving their authority.

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`).
**Prerequisites:** accepted platform runtime, [protected logging](../stage-1-logging/README.md),
scoped ingestion identities, storage/backups and a selected delivery controller.
**Design:** [telemetry composition](../../architecture/operations/telemetry.md).

## Main path

1. [Prepare the investigation runtime](#step-1-prepare-the-investigation-runtime)
2. [Deploy scoped ingestion and backends](#step-2-deploy-scoped-ingestion-and-backends)
3. [Publish and verify read-only views](#step-3-publish-and-verify-read-only-views)

## Step 1: Prepare the investigation runtime

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  subgraph T1["Tier 1 / Application / Services"]
    subgraph Runtime["Existing platform Kubernetes cluster"]
      subgraph Project["Project integration / observability starter only"]
        New["Selected analytics workloads<br/>Persistent storage / backups"]
      end
    end
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T1,New services
  class Runtime boundary
  class Project replicas
```

**Integration:** Tier 1 [observability starter](../../../tier-1/clusters/tier1/platform/observability/kustomization.yaml)
contains no backend manifests. The [VM option](../stage-4-control-services/step-2d-telemetry-vm.md)
replaces this hosting selection; it is not additional default capacity.

1. Reuse the [platform cluster](procedures/platform-cluster.md) and its selected delivery
   controller. Tier 0 remains on Flux; Tier 1 does not inherit it automatically.
2. Select cluster services, the [VM alternative](../stage-4-control-services/step-2d-telemetry-vm.md)
   or verified existing services. Do not create duplicate resources or state for an existing host.
3. Record placement, capacity, protected storage and restore procedures. Select supported
   releases before adding project manifests; these folders are starters, not installed products.

**Result:** the selected runtime is ready; no backend is installed merely by provisioning VMs.

## Step 2: Deploy scoped ingestion and backends

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart BT
  Workloads["Existing workload producers"]
  subgraph T1[" "]
    direction TB
    T1Title["Tier 1 / selected analytics runtime"]
    subgraph Project["Project integration / no backend installer"]
      Ingest["Data Prepper / authenticated ingestion"]
      Logs["OpenSearch / log and trace analytics"]
      Metrics["Shared metrics / application rules"]
      Ingest --> Logs
      Ingest --> Metrics
    end
    T1Title ~~~ Project
  end
  subgraph T0["Tier 0 / existing protected logging"]
    Evidence["log-1 / protected archive"]
  end
  Workloads -->|Approved telemetry| T1
  T0 -. Approved projections only .-> T1
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef servicesHeading fill:#e7f0fc,stroke:#e7f0fc,color:#203a5b
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T0,Evidence control
  class T1,Logs,Ingest,Metrics services
  class T1Title servicesHeading
  class Workloads actor
  class Project replicas
```

**Integration:** supply Tier 1 [observability manifests](../../../tier-1/clusters/tier1/platform/observability/kustomization.yaml)
or service roles for the selected VM alternative. Neither the starter nor the VM baseline installs the dashed pipeline.
Approved Tier 0 export/redaction remains a separately authorized integration.

1. Deploy the selected backend/ingestion components through reviewed project manifests
   or product roles. The reference uses OpenSearch/Dashboards, supported Data Prepper
   log/trace pipelines and a separate metrics backend/evaluator.
2. Verify independent placement, quorum/replicas, supported schemas, persistent queues,
   capacity and snapshot/restore. A pod count or VM count alone does not establish HA.
3. Configure authenticated ownership routing and approved/redacted Tier 0 projections.
   Tier 1 downtime must never block Tier 0 intake. Keep platform/application alert ownership
   explicit, including duplicate suppression and notification routing.

**Result:** approved telemetry reaches searchable copies and the selected shared backends.

## Step 3: Publish and verify read-only views

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  App["Application owner / security reader<br/>Separately authorized scopes"]
  subgraph T1[" "]
    direction TB
    T1Title["Tier 1 / selected analytics runtime"]
    subgraph Project["Project integration / access and query policy"]
      direction LR
      UI["Investigation views"]
      Copies[("Scoped searchable copies")]
      UI -->|Read-only query roles| Copies
    end
    T1Title ~~~ Project
  end
  subgraph T0["Tier 0 / existing identity service"]
    Auth["Keycloak / IdP"]
  end
  App -->|Authorized read scope| T1
  T1 -->|OIDC integration| T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef servicesHeading fill:#e7f0fc,stroke:#e7f0fc,color:#203a5b
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T0,Auth control
  class T1,UI services
  class T1Title servicesHeading
  class App actor
  class Copies data
  class Project replicas
```

**Integration:** Tier 1 [observability starter](../../../tier-1/clusters/tier1/platform/observability/kustomization.yaml)
does not install dashboards, OIDC clients or permissions. Implement and verify these policies in the selected backend;
the query role receives no Tier 0 archive credentials.

1. Configure federation, separately tested break-glass access, per-application and
   security scopes, and redaction before developer publication. Data permissions enforce
   isolation; dashboard tenant/saved-object settings alone are insufficient.
2. Deny direct update/delete, delete-by-query, index-management, retention and backup
   administration to query roles. Test forged labels, cross-application reads and direct APIs.
3. Test Tier 1/SSO outage, queue replay, backend restore and rebuilding approved copies
   without modifying Tier 0 originals. Record gaps and accepted operating limits.

An app owner receives an application-log view, not raw Tier 0 archive access.

## IaC locations

| Repository | Path inside that repository | Coverage |
| --- | --- | --- |
| Tier 1 | [clusters/tier1/platform/observability/](../../../tier-1/clusters/tier1/platform/observability/) | Empty starter until reviewed product manifests are supplied |
| Tier 1 | [terraform/deployments/observability/](../../../tier-1/terraform/deployments/observability/) | Optional VM resources, not backend/collector installers |
| Tier 1 | [ansible/playbooks/deployment/telemetry-hosts.yml](../../../tier-1/ansible/playbooks/deployment/telemetry-hosts.yml) | VM baseline only |

Do not automatically add a second Netdata parent or SigNoZ/ClickHouse stack.
Return to [Stage 5 acceptance](README.md#capability-available); connect each workload through
the [collection deployment](../stage-6-workloads/telemetry.md) as it appears.
