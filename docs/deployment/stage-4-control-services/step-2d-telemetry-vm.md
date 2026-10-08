# Step 2d: Telemetry VMs

<a id="deploy-the-telemetry-host-variant"></a>

**Branch from:** [Step 2](README.md#step-2-deploy-operational-services), instead of the selected cluster telemetry components.
**Change:** Use dedicated telemetry hosts in their owning tier.
**Return:** [Step 2](README.md#step-2-deploy-operational-services) to continue with service visibility and external failure detection.

**Design:** [telemetry options A-C](../../architecture/operations/telemetry.md).
**Prerequisites:** selected collector/backend roles, network policy, retention,
software supply and recovery targets. Run the supplied VM workflow from Tier 1.
Control-cluster monitoring is a separate Tier 0 integration.

## Table of contents

- [Procedure](#procedure)
- [IaC defaults](#iac-defaults)
- [Acceptance](#acceptance)

## Procedure

1. Record A (dedicated VMs), B (cluster services) or C (existing service) and the
   shared/isolated boundary in project architecture.
2. For A, initialize the observability setup, select hosts and sizes in Terraform,
   and align their tier-local inventory and IP maps. The shared deployment wrapper
   provisions hosts and applies baseline only.
3. Install selected collectors, backends and dashboards with project-owned service
   automation. B uses cluster manifests; C verifies existing endpoints instead.
4. Configure approved source-to-collector and collector-to-backend routes, TLS,
   authentication, retention, archives and scoped dashboard access.
5. Verify every required signal before connecting dependent consumers.

## IaC defaults

`terraform/deployments/observability/` creates the VM foundations;
`ansible/playbooks/observability.yml` applies the shared `baseline` role.
Neither installs collectors, backends, dashboards, or their integrations.
Add service automation in Tier 1 before treating the stack as operational.
High-availability expansion is represented as commented Terraform instances
and matching commented inventory/IP examples.

Use this matrix for the default Terraform shape:

| Component | Terraform default | Inventory action | Network key |
| --- | --- | --- | --- |
| telemetry gateway | `telemetry-1` active, `telemetry-2` commented | `telemetry-1` present by default | `telemetry_gateway` |
| syslog collector | `syslog-1` active, `syslog-2` commented | `syslog-1` present by default | `security_telemetry` |
| live health | `health-1` active | `health-1` present by default | `observability` |
| metrics store | `metrics-1` active | `metrics-1` present by default | `observability` |
| APM and traces | `apm-1` active | `apm-1` present by default | `observability` |
| log store | `logs-1` active, `logs-2` and `logs-3` commented | `logs-1` present by default | `observability` |
| dashboard entry | `telemetry-ui-1` active | `telemetry-ui-1` present by default | `observability` |
| archive writer | `archive-1` active | `archive-1` present by default | `storage` |

Commented Terraform `vm_instances` are default `0` and should stay commented
until the matching Ansible inventory group and IP entry are enabled.


<a id="reference-stack"></a>
<a id="target-shape"></a>
<a id="network-placement"></a>
<a id="traffic-model"></a>
<a id="vm-roles"></a>
<a id="starting-shape"></a>
<a id="data-routing"></a>
<a id="shared-or-isolated"></a>
<a id="operations-model"></a>
<a id="purpose"></a>

## Acceptance

| Check | Expected result |
| --- | --- |
| Representative metric, trace, log and audit source | Arrives at the selected backend with owner/environment attributes |
| Unauthorized producer or dashboard user | Rejected by the selected policy |
| Collector/backend interruption | Buffered or lost data behavior matches the approved requirement |
| Retention and archive | Expiry, backup and restore are tested with non-sensitive sample records |
| Loss of the control cluster | Independent monitoring still detects the failure |
| Duplicate alerts | Notification routing has an explicit owner and hierarchy |

Adding VM instances alone does not install HA services. Record recurring health,
retention and restore procedures under project administration. Return to
[Step 2](README.md#step-2-deploy-operational-services).
