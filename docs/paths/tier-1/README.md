# Tier 1

Tier 1 owns shared platform services: source control, authoritative mirrors,
general runners, registries, telemetry, and optional platform Kubernetes. It consumes
Tier 0 infrastructure; it does not own hypervisors or template publication.
Approved IDs and titles come from the [shared template catalog](../../reference/template-catalog.md),
loaded by the shared helper; only workload selections and service tags belong here.

The staged reference design reaches this platform at
[Delivery and handover](../../deployment/stage-5-delivery/README.md).
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
| 2. Confirm publication and supply | Obtain approved Tier 2 edge endpoints if needed; select authoritative mirrors and Tier 1 DMZ runner access | Named interfaces work; direct administrative and peer access is denied |
| 3. Create a platform cluster, if needed | Run `bash scripts/kubernetes-cluster.sh init` from Tier 1; follow the [Kubernetes guide](../../deployment/stage-3-identity/procedures/kubernetes.md) and select [Argo CD or Spinnaker](../../architecture/delivery/controllers.md) separately | Nodes/API and selected delivery are verified; recovery is tested |
| 4. Add development services | Follow [source control](../../deployment/stage-5-delivery/step-1b-source-control-vm.md), [runners](../../deployment/stage-5-delivery/step-1c-podman-runner.md), and [registry](../../deployment/stage-5-delivery/procedures/registry.md) guides | Selected services have identity, certificates, backups, and restricted credentials |
| 5. Add Observability | Follow the [deployment](../../deployment/stage-6-observability/README.md) in Kubernetes with separate workload budgets; dedicated VMs are an alternative | Netdata, OpenTelemetry, metrics and OpenSearch; infrastructure/application health and scoped queries; Tier 0 retains control credentials and evidence |

The Linux setups and the optional Kubernetes path are separate. Source control
on a Linux VM does not require step 3. Cluster service directories are starter
locations, not working deployments; check each capability guide's implementation
scope before planning a rollout.

## Getting started

From `homelab-iac/homelab-tier-1`, initialize the source-control VM example:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup development --env test
```

Replace `homelab` with the prefix. Choose another `--setup` from
`.deployment-setups`; omit `--env test` for production. Edit the local files
using the [source-control guide](../../deployment/stage-5-delivery/step-1b-source-control-vm.md), then review a plan:

```bash
bash ../homelab-shared/scripts/deploy.sh development --env test --plan-only
```

Remove `--plan-only` only after review. These are operator-run workflows, not
workload-user access to Tier 0 credentials. For VM mobility, confirm the
[cluster placement contract](../../deployment/foundation/step-1b-cluster-ha.md#terraform-against-the-cluster).

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Inputs, state, and available setups | [Repository scripts](../../reference/repository-scripts.md) |
| Shared prerequisites | [Shared services](../../reference/implementation-support.md) |
| Platform Kubernetes design | [Kubernetes platform](../../deployment/stage-5-delivery/procedures/platform-cluster.md) |
| Ownership and privileged execution | [Infrastructure control](../../architecture/compute/provisioning.md) |
| Refresh and project records | [Project documentation](../../development/project-documentation.md) |
