# Stage 7: Delivery and handover

Provide shared source control, artifact supply and build execution, then hand routine
infrastructure work to a separate protected Tier 0 runner. Delivery coordinates changes;
it does not gain authority over Tier 0 merely by hosting the repositories.

**Prerequisites:** accepted [Secrets](../stage-6-secrets/README.md),
approved templates, tier-local inputs and an independent bootstrap/recovery environment.
**Working repositories:** `<prefix>-tier-1` for delivery, `<prefix>-tier-2` for public edge,
and `<prefix>-tier-0` for privileged infrastructure execution (source: matching `tier-N/`).
**Automation:** cluster nodes and the linked VM/edge options are supplied. Cluster
applications, registry and protected execution require project integration;
see [coverage](../../reference/implementation-support.md#stage-coverage).

## Working repositories

| Work | Repository | IaC location inside that repository |
| --- | --- | --- |
| Platform cluster and applications | `<prefix>-tier-1` | [terraform/deployments/kubernetes/](../../../tier-1/terraform/deployments/kubernetes/) and [clusters/tier1/](../../../tier-1/clusters/tier1/) |
| Source-control VM and general runners | `<prefix>-tier-1` | [terraform/deployments/](../../../tier-1/terraform/deployments/) and [ansible/playbooks/deployment/](../../../tier-1/ansible/playbooks/deployment/) |
| Public edge | `<prefix>-tier-2` | [terraform/deployments/edge/](../../../tier-2/terraform/deployments/edge/) and [ansible/playbooks/deployment/edge-proxy.yml](../../../tier-2/ansible/playbooks/deployment/edge-proxy.yml) |
| Image builders | `<prefix>-tier-0` | [terraform/deployments/immutable-template/](../../../tier-0/terraform/deployments/immutable-template/) |
| Protected runner and authorization | `<prefix>-tier-0` | Project integration; no complete runner/controller installer is supplied |

Run each procedure from its named repository root. Shared supplies reusable execution
code, not delivery-service inventory or infrastructure state; see [repository locations](../README.md#repository-locations).

## Main path

1. [Deploy shared delivery services](#step-1-deploy-shared-delivery-services)
2. [Enable protected execution](#step-2-enable-protected-execution)

## Step 1: Deploy shared delivery services

The bootstrap environment creates the independent Tier 1 Kubernetes cluster.
The selected delivery platform deploys shared applications; Tier 0 remains on Flux.
Choose Argo CD application GitOps or Spinnaker release pipelines before enabling delivery.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":12,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1["Tier 1 / Application / Services"]
    direction TB
    subgraph PVE["Existing Proxmox cluster"]
      direction TB
      subgraph Platform["Kubernetes / application network"]
        direction LR
        subgraph Apps["Project integration / application starters only"]
          direction TB
          Delivery["Unselected Argo CD or Spinnaker<br/>Optional Rancher / Fleet"]
          Git["GitLab / Harbor"]
          Delivery ~~~ Git
        end
        subgraph Nodes["Cluster node VMs"]
          direction TB
          CP1["platform-k8ctl-1"]
          CP2["platform-k8ctl-2"]
          CP3["platform-k8ctl-3"]
          CP1 ~~~ CP2 ~~~ CP3
        end
        Apps ~~~ Nodes
      end
    end
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef servicesHeading fill:#e7f0fc,stroke:#e7f0fc,color:#203a5b
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T1,Platform,CP1,CP2,CP3 services
  class PVE boundary
  class Apps replicas
```

**IaC:** Tier 1 [cluster inputs](../../../tier-1/terraform/deployments/kubernetes/terraform.tfvars.example)
and [cluster entry point](../../../tier-1/scripts/kubernetes-cluster.sh).
The [Tier 1 application starters](../../../tier-1/clusters/tier1/platform/kustomization.yaml)
do not install the dashed group. General runners and mirrors require a selected option or project implementation.
The [Tier 2 edge view](procedures/edge-proxy.md#default-deployment) shows the separate public-entry deployment.

1. Create the [Tier 1 runtime](procedures/platform-cluster.md), using
   `bash scripts/kubernetes-cluster.sh init` from its root. Review its own inventory,
   credentials and state. Select the [delivery option](procedures/platform-cluster.md#delivery-selection)
   and retain independent bootstrap sources before hosted source control exists.
2. Deploy GitLab, [Harbor or another registry](procedures/registry.md), general runners
   and Rancher/Fleet where needed. Product manifests and integration remain project work.
   Extend the existing [Software intake capability](../stage-1-software-intake/README.md#extend-the-capability-later)
   with OCI supply; reuse its controlled egress rather than deploying a second ordinary proxy.
3. Configure Keycloak OIDC, scoped roles and [Tier 2 edge access](procedures/edge-proxy.md).
   Register new hosts/services with [protected logging](../stage-2-logging/sources.md)
   before general CI use; cluster-native collectors remain integration work.
   Test repository retrieval, artifact publication/pulls and general CI jobs.

**Alternatives:** [1b: source-control VM](step-1b-source-control-vm.md),
[1c: Podman build runner](step-1c-podman-runner.md) and
[1d: image-based Linux](step-1d-image-based-linux.md) change the selected runtime.
Existing delivery services are valid when they meet the same interfaces.

**Result:** the [delivery interfaces](../../architecture/delivery/README.md) supply code,
artifacts and normal builds. General runners still have no Tier 0 credentials.

## Step 2: Enable protected execution

Provision a hardened infrastructure runner as a Tier 0 management VM, outside the
Tier 1 cluster. The bootstrap workstation remains available for independent recovery.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":12,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1["Tier 1 / existing delivery"]
    Git["GitLab / proposed infrastructure job"]
    Sources["Approved Git revisions / OCI artifacts"]
    Git ~~~ Sources
  end
  subgraph T0["Tier 0 / protected infrastructure control"]
    direction LR
      subgraph Entry["Privileged entry / Edge-facing access"]
        Bootstrap["Existing bootstrap workstation / VM"]
      end
      subgraph ControlArea[" "]
        direction LR
      subgraph Cluster["Existing Tier 0 Kubernetes"]
        Flux["Existing Flux<br/>Approved read-only sources"]
      end
      subgraph Management["Control / management network"]
        direction TB
        subgraph Integration["Project integration / not installed"]
          direction TB
          Runner["Protected runner VM<br/>Tier 0 authorization"]
          State[("Tier-local state")]
          Runner <--> State
        end
        PVE["Existing Proxmox / cluster lifecycle"]
        Runner -->|Approved lifecycle| PVE
      end
      Cluster ~~~ Management
      end
      Entry -->|Recovery| ControlArea
  end
  T1 -->|Proposals / separately authorized source retrieval| T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef edge fill:#fce8ec,stroke:#9b4d67,color:#502638
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T1,Git services
  class T0,Management,Runner,PVE control
  class ControlArea controlHeading
  class Cluster runtime
  class Entry edge
  class Bootstrap actor
  class State,Sources data
  class Integration replicas
```

**Integration:** implement the Tier 0 [protected execution contract](../../architecture/compute/provisioning.md).
The existing [Shared executor](../../../shared/scripts/deploy.sh) runs reviewed tier-local code;
it does not deploy the dashed runner/controller group or its authorization policy.

1. Implement the [protected execution policy](../../architecture/compute/provisioning.md)
   and scope credentials to approved operations. General-runner automation is not a
   protected-runner installer. A protected GitLab branch is not sufficient authorization.
2. Test an authorized change and a rejected job. Keep one writer per state root;
   explicitly migrate and test recovery if the state backend changes.
3. Transfer routine execution and approved GitOps source consumption. Retain independent
   copies of code, images, state and recovery credentials; verify recovery while GitLab,
   Harbor and normal identity login are unavailable.

**Result:** routine infrastructure changes use the protected runner under Tier 0 authority.
Source control coordinates them, while GitOps separately reconciles approved applications.

<a id="step-3-deploy-shared-investigation"></a>
<a id="step-3-deploy-observability"></a>

## Capability available

Accept this stage only after the selected delivery and execution portions of the
[reference platform](../../architecture/reference-platform.md#access-and-automation)
are operational and their recovery/access tests pass. A design contract or empty
starter does not transfer execution from the workstation. After an accepted handover,
resource and state ownership have not moved between tiers. Continue with
[Stage 8: Observability](../stage-8-observability/README.md), then workload provisioning.
