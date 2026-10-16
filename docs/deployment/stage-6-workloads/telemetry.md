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
flowchart LR
  Runtime["Existing VMs / workload cluster"] --> Agents["New host agents / cluster collectors"]
  Apps["Application instrumentation"] --> Agents --> Queue["Bounded durable buffers"]
```

1. Identify source owners and required security, application, metric and trace streams.
2. Add supported agent/collector roles or reviewed manifests in the owning tier.
   Set source credentials, disk permissions, buffer capacity and retry limits.
3. Verify local collection, source identity and missing-source detection. Supplied
   VM/cluster provisioning does not install these products automatically.

## Step 2: Connect the authorized destinations

```mermaid
flowchart LR
  Collect["Tier 2 collection"] -->|Security / audit submissions| Evidence["Tier 0 protected intake"]
  Collect -->|Application logs / metrics / traces| Analytics["Tier 1 shared interfaces"]
  Owner["Application owner"] -->|Read own approved view| Analytics
```

1. Route security/audit events to scoped Tier 0 intake and ordinary application
   telemetry to the approved Tier 1 interfaces.
2. Configure trusted ownership from authenticated routing, not arbitrary labels.
   Producers receive no raw-archive query or administration credentials.
3. Submit sample events and verify the matching application view and protected evidence.

## Step 3: Verify buffering and reader isolation

```mermaid
flowchart LR
  Source["Workload events during bounded outage"] --> Buffer["Local durable buffers"]
  Buffer -->|Replay after recovery| Backend["Tier 1 backends"]
  Backend --> View["Approved application read scope"]
```

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
