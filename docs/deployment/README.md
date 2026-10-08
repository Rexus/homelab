# Deployment

Choose the capability to establish, then follow its main README from Step 1 onward.
Each stage explains the main path with diagrams, names the capability available at
the end, and links back to the architecture it implements.

<a id="deployment-stages"></a>

| Stage | Capability available | Walkthrough |
| --- | --- | --- |
| 1: Compute foundation | Proxmox, networks, VM templates and independent provisioning tools/state | [Foundation](stage-1-foundation/README.md) |
| 2: Cryptographic trust | Offline root custody and an online issuing service | [Trust](stage-2-trust/README.md) |
| 3: Identity and Kubernetes | Dedicated directory pair and the Tier 0 cluster with basic platform services | [Identity and Kubernetes](stage-3-identity-runtime/README.md) |
| 4: Control services | Federated access, secrets, inventory documentation and visibility | [Control services](stage-4-control-services/README.md) |
| 5: Delivery and handover | Source control, artifacts, builds and protected infrastructure execution | [Delivery and handover](stage-5-delivery/README.md) |
| 6: Workload provisioning | Approved Tier 2 runtime and application deployment | [Workload provisioning](stage-6-workloads/README.md) |

For a new installation, follow this order. Existing infrastructure can satisfy a
stage's verified prerequisites; a stage number is not a tier, network or state boundary.

## Follow a stage

1. Read its prerequisites and intended result.
2. Follow the numbered steps in the main README. At a decision, select an adjacent
   option such as Trust's `step-1b-usb-hsm.md`, then return to the stated step.
3. Use linked `procedures/` for configuration and commands. Record selected options
   and acceptance evidence in the project's deployment documents.

The [reference platform](../architecture/reference-platform.md) owns the complete
design. Stages realize parts of it; [readiness](readiness.md) records what is verified.

## Implementation scope

The [support map](../reference/implementation-support.md) distinguishes supplied
automation from project integration. A diagram is not a claim that every component
has an installer. Current wrappers call `terraform`; Terraform / OpenTofu is the
design choice, not a claim of a validated OpenTofu drop-in workflow.

Continue with [administration](../administration/README.md) for recurring operation
and [development](../development/README.md) for implementation changes.
Retain [recovery inputs](../administration/recovery.md) independently of hosted
services. Tier 0 recovery and root ceremonies never depend on normal Tier 1 CI.

Refresh updates references without moving infrastructure or replacing project
decisions; see the [refresh contract](../development/generated-repositories.md#refresh-and-local-ownership).

<a id="purpose"></a>
<a id="current-platforms"></a>
<a id="bootstrap-phases"></a>
<a id="day-0-bootstrap-dependencies"></a>
<a id="day-1-cluster-foundation"></a>
<a id="day-2-service-sequence"></a>
<a id="day-3-operational-handover"></a>
<a id="who-runs-the-deployment"></a>
<a id="working-method"></a>
<a id="automation-paths"></a>
<a id="recovery-rule"></a>
