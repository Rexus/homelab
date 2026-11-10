# Tier 1

Tier 1 owns shared platform services: source control, authoritative mirrors,
general runners, registries, telemetry, and optional platform Kubernetes. It consumes
Tier 0 infrastructure; it does not own hypervisors or template publication.
Approved IDs and titles come from the [shared template catalog](../../reference/template-catalog.md),
loaded by the shared helper; only workload selections and service tags belong here.

The first optional Tier 1 deployment is
[Stage 3, option 3b: verified software intake](../../deployment/stage-3-trust/README.md#3b-verified-repository-and-artifact-publication--optional),
after logging and trust are accepted. Complete its worker and selected consumer cutover before
leaving Stage 3; it needs no Tier 1 cluster. The main platform runtime arrives at
[Delivery](../../deployment/stage-7-delivery/README.md), followed by Observability
and the [Development platform](../../deployment/stage-9-development/README.md).
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
| 3. Establish Delivery | Follow [Stage 7](../../deployment/stage-7-delivery/README.md): create or accept the Tier 1 cluster/basic platform, install one controller, then commission artifact supply | Runtime, scoped controller, registry interfaces and independent recovery are accepted |
| 4. Add Observability | Follow the [deployment](../../deployment/stage-8-observability/README.md) in Kubernetes with separate workload budgets; the VM alternative supplies only a host baseline until project integration is implemented | Netdata, OpenTelemetry, metrics and OpenSearch; scoped queries; Tier 0 retains control credentials and evidence |
| 5. Add development services | Follow [Stage 9](../../deployment/stage-9-development/README.md): data services, GitLab/SSO, general runners, then Tier 0 Vault/runner handover | Application backups, bounded job access, real Vault claims and original-state continuity are verified |

The Linux setups and the optional Kubernetes path are separate. Source control
on a Linux VM does not require step 3. Cluster service directories are starter
locations, not working deployments; check each capability guide's implementation
scope before planning a rollout.

## Getting started

Start at [Stage 7, Step 1](../../deployment/stage-7-delivery/README.md#step-1-create-the-platform-runtime)
from **`<prefix>-tier-1/`**. Its cluster procedure owns initialization, configuration, saved-plan
apply, credentials and basic-platform installation; `init` alone installs nothing.
For an existing cluster, verify the same readiness gates without bootstrapping another one,
then continue through Delivery and Observability before Stage 9's development-platform installation.

The [source-control VM](../../deployment/stage-9-development/step-1b-source-control-vm.md)
and [Podman runner](../../deployment/stage-9-development/step-2b-podman-runner.md) remain alternatives.

These are operator-run workflows, not
workload-user access to Tier 0 credentials. For VM mobility, confirm the
[cluster placement contract](../../deployment/foundation/proxmox/step-1b-cluster-ha.md#terraform-against-the-cluster).

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Inputs, state, and available setups | [Repository scripts](../../reference/repository-scripts.md) |
| Shared prerequisites | [Shared services](../../reference/implementation-support.md) |
| Create the platform cluster | [Tier 1 Kubernetes](../../deployment/stage-7-delivery/procedures/platform-cluster.md) |
| Cluster choices and readiness | [Common cluster foundation](../../deployment/stage-4-kubernetes/procedures/kubernetes.md) |
| Ownership and privileged execution | [Infrastructure control](../../architecture/hosting/provisioning.md) |
| Refresh and project records | [Project documentation](../../development/project-documentation.md) |
