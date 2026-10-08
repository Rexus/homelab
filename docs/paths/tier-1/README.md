# Tier 1

Tier 1 owns shared platform services: edge access, caches, source control,
runners, registries, telemetry, and optional platform Kubernetes. It consumes
Tier 0 infrastructure; it does not own hypervisors or template publication.
Approved IDs and titles come from the [shared template catalog](../../reference/template-catalog.md),
loaded by the shared helper; only workload selections and service tags belong here.

The staged reference design reaches this platform at
[Delivery and handover](../../deployment/stage-5-delivery/README.md).
Early edge services may be prepared independently when their prerequisites exist.
The protected infrastructure runner remains a separate Tier 0 management VM,
not one of this repository's general runners.

## Deployment order

Choose the required capabilities. Existing approved services are valid
prerequisites; this is not a requirement to deploy every example.

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Confirm foundations | Read project conventions and obtain Tier 0-approved templates, networks, storage, and scoped operator access | Inputs are recorded locally; any identity/DNS/PKI prerequisites in the selected service guide exist |
| 2. Add access services | Deploy [edge](../../deployment/stage-5-delivery/procedures/edge-proxy.md) and optional [cache](../../deployment/stage-1-foundation/step-3b-outbound-cache.md) | Intended traffic works and forbidden traffic is rejected |
| 3. Create a platform cluster, if needed | Follow the shared [Kubernetes guide](../../deployment/stage-3-identity-runtime/procedures/kubernetes.md) with Tier 1 inputs; Talos is the current installation example | Nodes/API are healthy and recovery is tested |
| 4. Add development services | Follow [source control](../../deployment/stage-5-delivery/step-1b-source-control-vm.md), [runners](../../deployment/stage-5-delivery/step-1c-podman-runner.md), and [registry](../../deployment/stage-5-delivery/procedures/registry.md) guides | Selected services have identity, certificates, backups, and restricted credentials |
| 5. Add telemetry | Follow the [telemetry procedure](../../deployment/stage-4-control-services/step-2d-telemetry-vm.md) | Hosts and services report health; alerts and recovery checks work |

The Linux setups and the optional Kubernetes path are separate. Source control
on a Linux VM does not require step 3. Cluster service directories are starter
locations, not working deployments; check each capability guide's implementation
scope before planning a rollout.

## Getting started

From `homelab-iac/homelab-tier-1`, initialize the edge VM example:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup edge --env test
```

Replace `homelab` with the prefix. Choose another `--setup` from
`.deployment-setups`; omit `--env test` for production. Edit the local files
using the [edge guide](../../deployment/stage-5-delivery/procedures/edge-proxy.md), then review a plan:

```bash
bash ../homelab-shared/scripts/deploy.sh edge --env test --plan-only
```

Remove `--plan-only` only after review. These are operator-run workflows, not
workload-user access to Tier 0 credentials. For VM mobility, confirm the
[cluster placement contract](../../deployment/stage-1-foundation/step-1b-cluster-ha.md#terraform-against-the-cluster).

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Inputs, state, and available setups | [Repository scripts](../../reference/repository-scripts.md) |
| Shared prerequisites | [Shared services](../../reference/implementation-support.md) |
| Platform Kubernetes design | [Kubernetes platform](../../deployment/stage-5-delivery/procedures/platform-cluster.md) |
| Ownership and privileged execution | [Infrastructure control](../../architecture/compute/provisioning.md) |
| Refresh and project records | [Project documentation](../../development/project-documentation.md) |
