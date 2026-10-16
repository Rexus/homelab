# ${title} deployment

Project-owned procedures for realizing the [selected architecture](../architecture/README.md).
Select the capability stage, then record the local main path and any option branches.
Existing services can satisfy verified prerequisites.

| Stage | Selected variant / local procedure | Acceptance evidence | Reference |
| --- | --- | --- | --- |
| Foundation prerequisites | Record hosts, networks, templates, provisioning access and independent recovery | Pending review | [Foundation](${docs}/deployment/foundation/README.md) |
| 1: Protected logging | Record collector deployment, protected evidence, offline inspection and selected failure contract | Pending review | [Logging](${docs}/deployment/stage-1-logging/README.md) |
| 2: Cryptographic trust | Record root custody and issuer selection | Pending review | [Trust](${docs}/deployment/stage-2-trust/README.md) |
| 3: Identity and Kubernetes | Record directory and cluster procedures | Pending review | [Identity and Kubernetes](${docs}/deployment/stage-3-identity-runtime/README.md) |
| 4: Control services | Record federation, operational services, independent monitoring and access integration | Pending review | [Control services](${docs}/deployment/stage-4-control-services/README.md), [monitoring](${docs}/deployment/stage-4-control-services/monitoring.md) |
| 5: Delivery and handover | Record shared delivery and protected execution handover | Pending review | [Delivery and handover](${docs}/deployment/stage-5-delivery/README.md) |
| 6: Workload provisioning | Record the approved workload lifecycle | Pending review | [Workload provisioning](${docs}/deployment/stage-6-workloads/README.md) |

Only work owned by this repository is executed here. Other steps record consumed
dependencies and their owners; stage and step numbers do not transfer resource or state ownership.
Use the upstream [repository map](${docs}/deployment/README.md#repository-locations)
to locate reference IaC. Each local procedure records its working repository and
repository-relative input/code paths, including any Shared helper it calls.

Add local instructions under the relevant capability folder, such as
`stage-2-trust/`. Its README explains numbered steps with diagrams and the
resulting design. Keep options beside it, for example `step-1b-usb-hsm.md`, stating
the decision, changed deployment and return point. Link upstream procedures instead
of copying them.

Record input locations, commands, rollback and evidence; keep credentials outside
these records. Use [administration](../administration/README.md) for recurring
operation and [development](../development/README.md) for implementation changes.
These records are seeded once and remain project-owned during upstream refresh.

## Readiness

Track progress against the selected design using [deployment readiness](${docs}/deployment/readiness.md).
Completing a step does not change the architecture or prove every capability is assured.

| Capability / selected variant | Current readiness | Required readiness | Evidence / remaining work |
| --- | --- | --- | --- |
| Record the design reference | Level 0: defined | Record the acceptance target | Link checks, results and outstanding work |
