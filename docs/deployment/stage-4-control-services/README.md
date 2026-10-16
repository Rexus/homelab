# Stage 4: Control services

Deploy the Tier 0 operational applications into the accepted Kubernetes platform.
FreeIPA and the issuing CA remain dedicated external services; Flux adds the identity
broker, secrets, inventory documentation and operational tools.

**Prerequisites:** accepted [identity and runtime](../stage-3-identity-runtime/README.md),
service storage/backups and independent recovery inputs.
**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
The telemetry VM option uses `<prefix>-tier-1` instead.
**Design:** [identity](../../architecture/identity/README.md),
[secrets](../../architecture/cryptography/README.md) and [operations](../../architecture/operations/README.md).

## Main path

1. [Deploy identity federation](#step-1-deploy-identity-federation)
2. [Deploy operational services](#step-2-deploy-operational-services)
3. [Integrate access and recovery](#step-3-integrate-access-and-recovery)

```mermaid
flowchart TB
  subgraph Existing["Existing Tier 0 prerequisites"]
    direction LR
    Directory["FreeIPA primary + replica<br/>Dedicated VMs"]
    Issuer["Issuing CA<br/>Optional HSM gateway"]
    Base["Flux, cert-manager, storage<br/>CloudNativePG HA"]
    Directory ~~~ Issuer ~~~ Base
  end
  subgraph Added["New Tier 0 Kubernetes workloads"]
    direction LR
    Keycloak["Keycloak<br/>Directory federation, OIDC / MFA"]
    Vault["Vault<br/>Secrets / supported PKI integration"]
    Ops["NetBox, Headlamp<br/>Critical monitoring integration"]
    Keycloak ~~~ Vault ~~~ Ops
  end
  Existing -->|Flux deploys reviewed service manifests| Added
```

| Existing interface | New consumer |
| --- | --- |
| FreeIPA directory | Keycloak federation |
| CloudNativePG | Keycloak and NetBox databases |
| Issuing CA | cert-manager requests; Vault integration only through a supported provider |
| Cluster API | Headlamp with scoped RBAC |

## Step 1: Deploy identity federation

Add reviewed Keycloak manifests in Tier 0's
[clusters/tier0/applications/keycloak/](../../../tier-0/clusters/tier0/applications/keycloak/).
Configure its database,
TLS and FreeIPA federation; verify group mappings before granting administrative
roles. The directory remains independent of its broker.

The source folders are editable starters, not complete application installers.
Service manifests and integration remain project work; see the
[support map](../../reference/implementation-support.md).

## Step 2: Deploy operational services

Keep control-service manifests in Tier 0's
[clusters/tier0/applications/](../../../tier-0/clusters/tier0/applications/),
not in Shared. These paths are starters for project integration.

Deploy Vault with its own persistent storage, initialization, audit and protected
unseal/recovery material. It does not use CloudNativePG as its storage backend.
**Alternative:** [2b: dedicated Vault VM](step-2b-vault-vm.md) replaces the cluster instance.
[2c: seal integration](step-2c-seal-integration.md) changes unseal/recovery, not PKI signing.

Add NetBox with its database/cache dependencies and Headlamp with scoped permissions.
Extend the existing Tier 0 log capability with
[critical monitoring](procedures/observability.md#1-add-independent-foundation-monitoring).
Required cluster-loss detection stays outside the observed cluster. Shared analytics
is added with the Tier 1 platform, not as a prerequisite for Tier 0 operation.
[2d: telemetry VMs](step-2d-telemetry-vm.md) is its explicit VM alternative.

NetBox documents inventory. It never supplies the inventory needed to bootstrap
its own platform. Test backups and restoration before other tiers depend on these services.

## Step 3: Integrate access and recovery

Configure OIDC clients and service roles where supported. Test permitted and denied
access, then rehearse privileged recovery without normal directory or broker login.

Optional [3b: hardware-backed authentication](step-3b-hardware-authentication.md)
adds stronger operator login after recovery is working. Restrict routine bootstrap
credentials only after independent break-glass access and recovery custody are verified.

## Capability available

**Result:** the control services in the
[reference platform](../../architecture/reference-platform.md#service-placement)
provide federated access, secrets, inventory documentation and visibility.
Record access, backup/restore and external failure-detection evidence.

Continue with [Stage 5: Delivery and handover](../stage-5-delivery/README.md).
