# Isolated Kubernetes labs

**Working repositories:** `<prefix>-tier-2` for profiles/definitions/state;
`<prefix>-tier-0` for privileged execution.
**Branch from:** [Stage 10, Step 1](README.md#step-1-define-the-approved-request).
**Design:** [workload isolation](../../architecture/compute/workload-isolation.md).
**Scope:** operator-first deployment and the future bounded request contract.
No multi-cluster allocator, expiry controller or portal is installed by this path.

## Step 1: Select the isolation profile

Use dedicated VM-backed clusters for unsafe OS, add-on or privileged application
experiments. Trusted teams may select namespaces; virtual clusters are a separately
qualified alternative, not equivalent isolation.
Review [example profiles](../../../tier-2/workloads/cluster-profiles.json.example).
They reference Shared sizing but remain Tier 2 choices, never shared inventory.
Profiles separate control-plane and worker capacity. The current single-cluster
command does not consume them. Do not replace existing nodes to match an `xs` profile.

## Step 2: Deploy the first operator-owned cluster

Follow [Tier 2 Kubernetes](README.md#step-2-provision-the-workload-runtime) with
its inventory, native image access, approved templates, unique allocations,
private API and original state. Accept the cluster/add-ons before tenant access.
Grant only the selected workload/cluster role through the existing IdP.
Keep Talos, hypervisor, lifecycle state and platform credentials private.
Verify that another tenant and the new cluster cannot reach Control/other tenants;
returning a DNS name alone establishes neither routing nor authorization.

## Step 3: Introduce bounded automation

Implement and test the missing dispatcher before accepting automated requests:

| Input/result | Required handling |
| --- | --- |
| Identity | Verify the caller; derive owner/project from authenticated claims |
| Request | Operation, cluster ID, approved profile/image and TTL; no shell/IaC/provider paths |
| Admission | Ownership, quotas, capacity, isolation and explicit destructive authorization |
| Allocation | Unique IDs/MACs, subnet/policy, API/DNS, storage and separate inventory/state |
| Execution | Tier 0-reviewed code, one writer per cluster, protected plans/secrets |
| Readiness | Actual API/worker/add-on health, images, SSO/RBAC and logging |
| Result | Owner-scoped DNS/status/access; never raw state or infrastructure credentials |
| Expiry/delete | Authorized event and tested cleanup; absence/outage is not deletion intent |

GitLab can carry requests/status; trusted CI executes approved dispatcher code.
Never run users' `.gitlab-ci.yml`, Terraform modules/providers or hooks on `iac-1`.
A future external web service can consume this interface without administering it.
No public endpoint or portal implementation is supplied here.
Measure creation time: seconds require qualified warm capacity or another realization,
not an assumption about fresh VM bootstrap.
**Return:** [Stage 10, Step 2](README.md#step-2-provision-the-workload-runtime).
