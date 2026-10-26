# Development platform

Source control owns reviewed code and coordinates CI. Application delivery owns
release/reconciliation. Infrastructure execution owns credentials and state.
These are distinct functions even when one product exposes several interfaces.

## Contents

- [Service arrangement](#service-arrangement)
- [Privileged CI](#privileged-ci)
- [Identity and secrets](#identity-and-secrets)
- [Failure and recovery](#failure-and-recovery)
- [Realization](#realization)

## Service arrangement

| Function | Reference realization | Boundary |
| --- | --- | --- |
| Source control | GitLab application in Tier 1 Kubernetes | Existing independently managed database, queue/cache, repository and object storage |
| General CI | Tier 1 runner manager with Kubernetes job pods | Ephemeral job compute, bounded resources and no infrastructure credentials |
| Application delivery | Tier 1 Argo CD or Spinnaker | Selected application destinations, never Tier 0 infrastructure |
| Control GitOps | Tier 0 Flux | Independently recoverable definitions, source trust and bootstrap keys |
| Infrastructure CI | Separate Tier 0 runner VM | Original tier-local inventory/state and approved privileged code |
| Lab environments | Tier 2 allocated runtime | Tenant access without hypervisor, Talos administrator or infrastructure-state access |

A Kubernetes runner provisions job pods, not an isolated Kubernetes cluster per
job. Worker capacity, build-node isolation and cluster lifecycle remain separate
concerns. A source-control deployment is not a provisioning service.

## Privileged CI

The selected reference offers **direct trusted CI** as an explicit opt-in.
The dedicated infrastructure project can execute reviewed IaC and read bounded
credentials through Vault. Its maintainers, GitLab administrators and anyone able
to alter GitLab's signing keys, runtime, storage or backups are Tier 0 trusted
principals. Tier 1 physical hosting does not make those administrators lower-trust.
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
The bootstrap workstation sits outside hosted runtimes and is disconnected when
idle; it remains a Tier 0 administrative context, not an untrusted client or a new
offline network route. It must be online during actual deployment/recovery.

## Realization

[Delivery](../../deployment/stage-7-delivery/README.md) selects the Tier 1 controller.
[Development platform](../../deployment/stage-9-development/README.md) installs
GitLab/general runners and configures the direct-CI handover.
[Lab environments](../../deployment/stage-10-lab-environments/README.md) consume the accepted
platform without granting users its infrastructure authority.
