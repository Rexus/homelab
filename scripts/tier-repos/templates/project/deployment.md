# ${title} deployment

Project-owned procedures for realizing the [selected architecture](../architecture/README.md).
Select the capability stage, then record the local main path and any option branches.
Existing services can satisfy verified prerequisites.

| Stage | Selected variant / local procedure | Acceptance evidence | Reference |
| --- | --- | --- | --- |
| Foundation prerequisites | Record hosts, networks, templates, provisioning access and independent recovery | Pending review | [Foundation](${docs}/deployment/foundation/README.md) |
| 1: Software intake | Record approved sources, early proxy/cache, later repository/OCI services and target-tier patch authority | Pending review | [Software intake](${docs}/deployment/stage-1-software-intake/README.md) |
| 2: Protected logging | Record collector deployment, protected evidence, offline inspection and selected failure contract | Pending review | [Logging](${docs}/deployment/stage-2-logging/README.md) |
| 3: Cryptographic trust | Record root custody and issuer selection | Pending review | [Trust](${docs}/deployment/stage-3-trust/README.md) |
| 4: Kubernetes | Record the cluster owner, bootstrap, add-ons, audit forwarding and recovery | Pending review | [Kubernetes](${docs}/deployment/stage-4-kubernetes/README.md) |
| 5: Identity | Record directory, federation and OIDC integration on the accepted cluster | Pending review | [Identity](${docs}/deployment/stage-5-identity/README.md) |
| 6: Secrets | Record secret storage, auditing, unseal/recovery and supporting control integrations | Pending review | [Secrets](${docs}/deployment/stage-6-secrets/README.md), [monitoring](${docs}/deployment/stage-6-secrets/monitoring.md) |
| 7: Delivery | Record the Tier 1 controller and approved artifact supply | Pending review | [Delivery](${docs}/deployment/stage-7-delivery/README.md) |
| 8: Observability | Record Netdata, Proxmox/BMC coverage, separate workload budgets, replicated backends and scoped reads | Pending review | [Observability](${docs}/deployment/stage-8-observability/README.md) |
| 9: Development platform | Record GitLab, SSO, general job pods, direct-CI trust, Vault and original-state handover | Pending review | [Development platform](${docs}/deployment/stage-9-development/README.md) |
| 10: Lab environments | Record isolation, profiles, authorization, lifecycle and missing dispatcher work | Pending review | [Lab environments](${docs}/deployment/stage-10-lab-environments/README.md) |

Only work owned by this repository is executed here. Other steps record consumed
dependencies and their owners; stage and step numbers do not transfer resource or state ownership.
Use the upstream [repository map](${docs}/deployment/README.md#repository-locations)
to locate reference IaC. Each local procedure records its working repository and
repository-relative input/code paths, including any Shared helper it calls.

Add local instructions under the relevant capability folder, such as
`stage-3-trust/`. Its README explains numbered steps with diagrams and the
resulting design. Keep options beside it, for example `step-1b-usb-hsm.md`, stating
the decision, changed deployment and return point. Link upstream procedures instead
of copying them.
Follow the [diagram contract](${docs}/development/diagrams.md#abstraction-and-implementation):
draw the selected local guest names/counts and link their inputs and execution code.
Mark existing, manual and project-integration components separately. Update local
views with local IaC changes; refreshed auto-docs still describe upstream examples.

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
