# Development platform

Source control owns reviewed code and coordinates CI. Application delivery owns
release/reconciliation. Infrastructure execution owns credentials and state.
These are distinct functions even when one product exposes several interfaces.

**Build:** [Stage 9: development platform](../../03-deployment/stage-9-development/README.md).
**Operate:** [Development platform operations](../../05-operations/development-platform/README.md).

## Contents

- [Service arrangement](#service-arrangement)
- [Privileged CI](#privileged-ci)
- [Identity and secrets](#identity-and-secrets)
- [Failure and recovery](#failure-and-recovery)
- [Realization](#realization)

## Service arrangement

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Source["Source control / reviewed code"]
  CI["General CI / job compute"]
  Delivery["Application delivery"]
  Runtime["Authorized applications"]
  Executor["Infrastructure execution<br/>Optional trusted CI"]
  State[("Tier-owned inventory / state")]
  Source -->|Build inputs| CI
  Delivery -->|Retrieve approved definitions| Source
  Delivery -->|Scoped changes| Runtime
  Executor -->|Approved privileged code| Source
  Executor -->|Execute changes| State
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class CI,Delivery,Runtime services
  class Executor control
  class Source,State data
```

*Figure: General CI builds reviewed code, delivery changes authorized applications, and separate
infrastructure execution uses privileged code and tier-owned state.*

The direct trusted CI path is an explicit opt-in described below.

| Function | Reference realization | Boundary |
| --- | --- | --- |
| Source control | GitLab application in Tier 1 Kubernetes, dedicated Tier 1 database/cache/repository VMs, scoped object storage | Application/dependency lifecycle remains distinct from Tier 0 storage administration |
| General CI | Tier 1 runner manager with Kubernetes job pods | Ephemeral job compute, bounded resources and no infrastructure credentials |
| Application delivery | Tier 1 Argo CD or Spinnaker | Selected application destinations, never Tier 0 infrastructure |
| Control GitOps | Tier 0 Flux | Independently recoverable definitions, source trust and bootstrap keys |
| Infrastructure CI | Separate Tier 0 runner VM | Original tier-local inventory/state and approved privileged code |
| Lab environments | Tier 2 allocated runtime | Tenant access without hypervisor, Talos administrator or infrastructure-state access |

A Kubernetes runner provisions job pods, not an isolated Kubernetes cluster per
job. The supplied runner uses the Tier 1 Services cluster; its namespace and
non-privileged job settings do not reserve isolated build nodes. Worker capacity,
build-node isolation and cluster lifecycle remain separate concerns. Untrusted
builds require the [isolated execution boundary](../10-hosting/04-kubernetes.md#scheduling-and-capacity),
not merely this runner installation. A source-control deployment is not a provisioning service.

## Privileged CI

The selected reference offers **direct trusted CI** as an explicit opt-in.
The dedicated infrastructure project can execute reviewed IaC and read bounded
credentials through Vault. Its maintainers, GitLab administrators and anyone able
to alter GitLab's signing keys, runtime, storage or backups are Tier 0 trusted
principals. Tier 1 runtime placement does not make those administrators lower-trust.
Separating the project from general builds does not remove this transitive trust.

This changes the stricter independently authorized request pattern: branch
protection, a runner tag and JWT claim checks do not protect Tier 0 from a compromised
trusted GitLab control plane. The opt-in must be recorded and reviewed when access,
hosting or organizational ownership changes. Use a separately authorizing executor
instead when Tier 1 administrators must not hold that trust.

Ordinary CI, Argo CD and Spinnaker never receive infrastructure credentials.
Future lab users submit bounded request data to a trusted dispatcher; their code,
Terraform/providers, hooks and job definitions are not executed on the privileged runner.

## Identity and secrets

Keycloak provides normal human SSO; each service owns permission mappings and
independent emergency access. GitLab job ID tokens are a separate workload issuer.
Vault binds exact project/namespace, protected branch, audience and optionally
runner source addresses before granting one secret-read scope.
Short-lived Vault tokens do not make a static backend credential short-lived.

## Failure and recovery

Normal hosted changes may pause if GitLab, Vault or SSO is unavailable. Existing
infrastructure must keep running, and Tier 0 can recover from independent retained
code, artifacts, original state and credentials.
The reference bootstrap executor is a Tier 0 management VM hosted on Proxmox.
It is outside Kubernetes, but cannot be the only recovery environment for its
own hypervisor or storage. Independently retained backups, tools and credentials
must support restoration on an available recovery host. A protected workstation
is an alternative executor; neither placement alone establishes offline custody.
The [bootstrap recovery contract](../../05-operations/recovery/bootstrap.md)
owns that independence.

## Realization

[Delivery](../../03-deployment/stage-7-delivery/README.md) selects the Tier 1 controller.
[Development platform](../../03-deployment/stage-9-development/README.md) installs
GitLab/general runners and configures the direct-CI handover.
[Lab environments](../../03-deployment/stage-10-lab-environments/README.md) consume the accepted
platform without granting users its infrastructure authority.
