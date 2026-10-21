# Stage 3: Identity

Establish directory authority and federated service authentication. Ansible configures
FreeIPA on dedicated VMs; the Tier 0 Kubernetes foundation hosts the identity provider.
Cluster bootstrap and basic services precede the Keycloak/OIDC integration.

**Prerequisites:** approved compute, templates, certificate trust, software supply,
a reachable bootstrap source and independent credentials.
**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Design:** [identity authority](../../architecture/identity/README.md) and
[cluster runtime](../../architecture/compute/README.md).

## Main path

1. [Deploy the directory pair](#step-1-deploy-the-directory-pair)
2. [Create the Kubernetes cluster](#step-2-create-the-kubernetes-cluster)
3. [Establish the basic platform](#step-3-establish-the-basic-platform)
4. [Deploy identity federation](#step-4-deploy-identity-federation)

## Step 1: Deploy the directory pair

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T0[" "]
    direction TB
    T0Title["Tier 0 / Control layer"]
    subgraph PVE["Existing Proxmox hosts"]
      direction LR
      subgraph Identity["identity network / dedicated VMs"]
        direction TB
        Primary["idm-1<br/>FreeIPA primary"]
        Replica["idm-2<br/>FreeIPA replica"]
        Primary <-->|Replication| Replica
      end
      ExistingCA["ca-1<br/>Existing issuer / unchanged"]
      Identity ~~~ ExistingCA
    end
    T0Title ~~~ PVE
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  class T0,Primary,Replica,ExistingCA control
  class T0Title controlHeading
  class PVE,Identity boundary
```

**IaC:** Tier 0 [foundation inputs](../../../tier-0/terraform/deployments/foundation/terraform.tfvars.example) and
[directory recipe](../../../tier-0/ansible/playbooks/deployment/identity-freeipa.yml).
Directory VMs may already be allocated by Stage 2; retain the existing CA and all state.

Follow the [FreeIPA procedure](procedures/freeipa.md). Add the identity VMs to the
Tier 0 [foundation root](../../../tier-0/terraform/deployments/foundation/)
and [inventory](../../../tier-0/ansible/inventory/hosts.yml.example)
without removing the existing issuer definition.
For the sibling FreeIPA CA, the [external-signing integration gate](procedures/freeipa.md#external-ca-integration-gate)
selects the CSR/pause and certificate/completion phases now implemented by the recipe.
Offline signing remains a separate authorized operation.
Verify the primary before joining the replica; test DNS and replication before
replacing temporary bootstrap dependencies.

FreeIPA stays outside Kubernetes. Directory and cluster setup can proceed independently
once their prerequisites exist. Preserve independent administrative credentials.

## Step 2: Create the Kubernetes cluster

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T0["Tier 0 / Control layer"]
    direction LR
    subgraph PVE["Existing Proxmox hosts / control_cluster network"]
      direction TB
      CP1["k8ctl-1<br/>Talos control plane"]
      CP2["k8ctl-2<br/>Talos control plane"]
      CP3["k8ctl-3<br/>Talos control plane"]
      CP1 ~~~ CP2 ~~~ CP3
    end
    API["Existing independent API endpoint<br/>Load balancing / DHCP reservations"]
    API -->|TCP 6443| PVE
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  class T0,API control
  class PVE runtime
  class CP1,CP2,CP3 boundary
```

**IaC:** Tier 0 [Kubernetes inputs](../../../tier-0/terraform/deployments/kubernetes/terraform.tfvars.example)
and [cluster entry point](../../../tier-0/scripts/kubernetes-cluster.sh) create these three VMs and bootstrap Kubernetes.
The API endpoint, DHCP reservations and approved node template already exist.
No workers are active in this starter; application and add-on manifests are separate inputs.

Follow the [common cluster procedure](procedures/kubernetes.md), then the current
[Talos Terraform implementation](procedures/talos-terraform.md). Set the tier-local
inventory, endpoint and state in Tier 0's
[terraform/deployments/kubernetes/](../../../tier-0/terraform/deployments/kubernetes/),
review the plan, and bootstrap the cluster.

**Alternative:** [2b: manual bootstrap](step-2b-manual-cluster.md) replaces that lifecycle;
it does not create a second state owner. Another OS requires its own implementation.
New-cluster inputs provide three schedulable control planes and no workers.
Additional workers are an explicit capacity choice; existing clusters retain their local nodes.

## Step 3: Establish the basic platform

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Source["Existing bootstrap Git / OCI source"]
  subgraph T0[" "]
    direction TB
    T0Title["Tier 0 / Control layer"]
    subgraph Cluster["Existing Kubernetes / k8ctl-1, k8ctl-2, k8ctl-3"]
      direction TB
      subgraph Project["Project integration / cluster starters only"]
        direction LR
        Network["CNI, storage and ingress selection"]
        Flux["Flux / SOPS"]
        Base["cert-manager / CloudNativePG"]
        Base ~~~ Flux ~~~ Network
      end
    end
    T0Title ~~~ Cluster
  end
  Source -. Bootstrap source integration .-> T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T0 control
  class T0Title controlHeading
  class Cluster runtime
  class Project replicas
  class Source actor
```

**Integration:** Tier 0 [cluster starters](../../../tier-0/clusters/tier0/kustomization.yaml)
contain no installer for the dashed add-on group. Supply reviewed manifests and bootstrap Flux explicitly.
The Kubernetes root retains its configured node-OS network defaults until the selected CNI is deliberately integrated.

Follow the [foundation checklist](procedures/kubernetes.md#cluster-foundation) in
dependency order: networking, Flux, SOPS/bootstrap secrets, storage, certificates/ingress
and database readiness. Connect certificate automation to the existing issuer through
a supported integration.
For the OpenXPKI Community reference, the [ACME adapter qualification](../stage-2-trust/procedures/issuer.md#step-3-activate-and-accept-issuance)
is explicit; installing cert-manager does not supply that adapter or authorize enrollment.

Tier 0's [clusters/tier0/](../../../tier-0/clusters/tier0/) add-on folders are starters.
Supply reviewed manifests, verify reconciliation,
decryption, persistence, TLS and database health, and start backups as state appears.
Flux requires a reachable source with independent credentials, not merely a local checkout.

## Step 4: Deploy identity federation

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T0[" "]
    direction TB
    T0Title["Tier 0 / Control layer"]
    subgraph Placement[" "]
      direction LR
      subgraph Cluster["Existing Tier 0 Kubernetes"]
        direction TB
        subgraph Added["Project integration<br/>Not installed"]
          Keycloak["Keycloak / IdP"]
        end
        Data[("Existing CloudNativePG<br/>Identity-provider database")]
        Keycloak -->|Database access| Data
      end
      subgraph Identity["Existing dedicated VMs / identity network"]
        direction TB
        Primary["idm-1<br/>FreeIPA primary"]
        Replica["idm-2<br/>FreeIPA replica"]
        Primary <-->|Replication| Replica
      end
      Cluster -->|Protected LDAP federation| Identity
    end
    T0Title ~~~ Placement
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T0,Keycloak,Primary,Replica control
  class T0Title,Placement controlHeading
  class Cluster runtime
  class Identity boundary
  class Data data
  class Added replicas
```

**Integration:** Tier 0 [Keycloak manifests](../../../tier-0/clusters/tier0/applications/keycloak/kustomization.yaml)
are an empty starter, not an installer. The existing directory comes from the
[FreeIPA recipe](../../../tier-0/ansible/playbooks/deployment/identity-freeipa.yml);
the database must pass [Step 3 readiness](#step-3-establish-the-basic-platform) first.

Add reviewed Keycloak manifests with its database, TLS and FreeIPA federation.
Configure OIDC clients, group mappings and scoped service roles; verify permitted
and denied logins before granting administrative access. Each consumer retains
its own authorization. The directory remains independent of the IdP.

Retain bootstrap credentials and test recovery without normal directory or IdP login.
Later stages register their service-specific clients against this identity provider;
they do not deploy another provider. Service manifests and integration remain project
work; see the [support map](../../reference/implementation-support.md).

## Capability available

**Result:** replicated directory services, a federated identity provider and the
supporting Kubernetes platform realize the
[identity design](../../architecture/identity/README.md). Bootstrap and recovery
remain independent of normal Keycloak login, Vault, GitLab and Harbor.

Record directory, federation, cluster and backup checks. Continue with
[Stage 4: Secrets](../stage-4-secrets/README.md).
