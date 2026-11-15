# Tier 1

Tier 1 owns shared platform services: source control, authoritative mirrors,
general runners, registries, telemetry, and optional platform Kubernetes. It consumes
Tier 0 infrastructure; it does not own hypervisors or template publication.
Approved IDs and titles come from the [shared template catalog](../../08-reference/template-catalog.md),
loaded by the shared helper; only workload selections and service tags belong here.

The first optional Tier 1 deployment is
[Stage 2, option 15b: verified software intake](../../03-deployment/stage-02-trust/README.md#15b-verified-repository-and-artifact-publication-optional),
after issuer acceptance, with persistent local journal/audit records and independent recovery custody.
Stage 3 then enrolls those streams in protected logging. Complete its worker and selected consumer cutover before
leaving Stage 2; it needs no Tier 1 cluster. The main platform runtime arrives at
[Delivery](../../03-deployment/stage-07-delivery/README.md), followed by Observability
and the [Development platform](../../03-deployment/stage-09-development/README.md).
Public edge and ordinary outbound caches belong to [Tier 2](../tier-2/README.md).
Internet-facing runners and mirrors use Tier 1's separate `delivery_edge` DMZ subnet.
The protected infrastructure runner remains a separate Tier 0 management VM,
not one of this repository's general runners.

## Deployment order

Choose the required capabilities. Existing approved services are valid
prerequisites; this is not a requirement to deploy every example.

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Confirm foundations | Read project conventions and obtain Tier 0-approved templates, networks, storage, and scoped operator access | Inputs are recorded locally; any identity/DNS/PKI prerequisites in the selected service guide exist |
| 2. Confirm bootstrap supply | Verify the existing approved Git, image and package sources that work before this platform exists | Cluster and service installation can obtain their artifacts without the future GitLab, registry or build runners |
| 3. Establish Delivery | Follow [Stage 7](../../03-deployment/stage-07-delivery/README.md): bootstrap independent Flux, let it own selected Kubernetes services, commission Spinnaker promotion and artifact supply | Separate sources/identities, exact-revision promotion, old-writer revocation and independent recovery are accepted |
| 4. Add Observability when selected | Follow the [deployment](../../03-deployment/stage-08-observability/README.md) with Flux-owned Kubernetes payloads and separate workload budgets; dedicated VMs retain their native alternative | Netdata, OpenTelemetry, metrics and OpenSearch; scoped queries; Tier 0 retains control credentials and evidence |
| 5. Add development services | Follow [Stage 9](../../03-deployment/stage-09-development/README.md): data services, GitLab/SSO, general runners, then Tier 0 Vault/runner handover | Application backups, bounded job access, real Vault claims and original-state continuity are verified |

The Linux setups and the optional Kubernetes path are separate. Source control
on a Linux VM does not require step 3. Project-owned cluster directories start as guarded integration
locations; native renderers export real pinned service payloads for Flux. Empty directories alone
install nothing. Stage 8/9 remain opt-in later services; existing sites require
[explicit adoption](../../03-deployment/stage-07-delivery/procedures/flux-adoption.md).

## Getting started

Start at [Stage 7, Step 1](../../03-deployment/stage-07-delivery/README.md#step-1-create-or-accept-the-tier-1-runtime)
from **`<prefix>-tier-1/`**. Its cluster procedure owns initialization, configuration, saved-plan
apply, credentials and basic-platform installation; `init` alone installs nothing.
For an existing cluster, verify the same readiness gates without bootstrapping another one,
then continue through Delivery and Observability before Stage 9's development-platform installation.

The [source-control VM](../../03-deployment/stage-09-development/step-1b-source-control-vm.md)
and [Podman runner](../../03-deployment/stage-09-development/step-14b-podman-runner.md) remain alternatives.

These are operator-run workflows, not
workload-user access to Tier 0 credentials. For VM mobility, confirm the
[cluster placement contract](../../03-deployment/foundation/proxmox/step-1b-cluster-ha.md#terraform-against-the-cluster).

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Inputs, state, and available setups | [Repository scripts](../../08-reference/repository-scripts.md) |
| Shared prerequisites | [Shared services](../../08-reference/implementation-support.md) |
| Create the platform cluster | [Tier 1 Kubernetes](../../03-deployment/stage-07-delivery/procedures/platform-cluster.md) |
| Cluster choices and readiness | [Common cluster foundation](../../03-deployment/stage-04-kubernetes/procedures/kubernetes.md) |
| Reconciliation, dependency readiness and release workflow responsibilities | [Logical delivery roles](../../01-architecture/10-delivery/02-controllers.md) |
| Selected Flux sources, promotion authority and alternatives | [Tier 1 implementation](../../08-reference/tier-1-delivery.md) |
| Platform maintenance without Spinnaker | [External maintenance and custody](../../05-operations/05-delivery.md) |
| Whole Tier 1 loss | [Independent rebuild and product recovery](../../05-operations/06-resilience/recovery/tier-1-products.md#rebuild-tier-1-without-its-services) |
| Ownership and privileged execution | [Infrastructure control](../../01-architecture/04-hosting/02-provisioning.md) |
| Refresh and project records | [Project documentation](../../04-development/project-documentation.md) |
