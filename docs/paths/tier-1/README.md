# Tier 1

Tier 1 owns shared platform services: edge access, caches, source control,
runners, registries, telemetry, and optional platform Kubernetes. It consumes
Tier 0 infrastructure; it does not own hypervisors or template publication.
Approved IDs and titles come from the [shared template catalog](../../platforms/proxmox/template-catalog.md),
loaded by the shared helper; only workload selections and service tags belong here.

## Deployment order

Choose the capabilities you need. Existing approved services are valid
prerequisites; this is not a requirement to deploy every example.

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Confirm foundations | Read project conventions and obtain Tier 0-approved templates, networks, storage, and scoped operator access | Inputs are recorded locally; any identity/DNS/PKI prerequisites in the selected service guide exist |
| 2. Add access services | Deploy [edge](../shared-services/edge.md) and optional [cache](../shared-services/cache.md) | Intended traffic works and forbidden traffic is rejected |
| 3. Create a platform cluster, if needed | Follow the shared [Kubernetes guide](../../platforms/kubernetes/README.md) with Tier 1 inputs; Talos is the current installation example | Nodes/API are healthy and recovery is tested |
| 4. Add development services | Follow [source control](../application-platform/development.md), [runners](../application-platform/podman-runner.md), and [registry](../application-platform/registry.md) guides | Selected services have identity, certificates, backups, and restricted credentials |
| 5. Add telemetry | Follow [system control](../system-control/README.md) | Hosts and services report health; alerts and recovery checks work |

The Linux setups and the optional Kubernetes path are separate. Source control
on a Linux VM does not require step 3. Cluster service directories are starter
locations, not working deployments; check each capability guide's implementation
scope before planning a rollout.

## Getting started

From `homelab-iac/homelab-tier-1`, initialize the edge VM example:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup edge --env test
```

Replace `homelab` with your prefix. Choose another `--setup` from
`.deployment-setups`; omit `--env test` for production. Edit the local files
using the [edge guide](../shared-services/edge.md), then review a plan:

```bash
bash ../homelab-shared/scripts/deploy.sh edge --env test --plan-only
```

Remove `--plan-only` only after review. These are operator-run workflows, not
workload-user access to Tier 0 credentials. For VM mobility, confirm the
[cluster placement contract](../../platforms/proxmox/cluster-ha.md#terraform-against-the-cluster).

## Find your way

| Need | Guide |
| --- | --- |
| Inputs, state, and available setups | [Repository scripts](../../reference/repository-scripts.md) |
| Shared prerequisites | [Shared services](../shared-services/README.md) |
| Platform Kubernetes design | [Kubernetes platform](../application-platform/kubernetes.md) |
| Ownership and privileged execution | [Infrastructure control](../../architecture/infrastructure-control.md) |
| Refresh and project records | [Project documentation](../../reference/project-documentation.md) |
