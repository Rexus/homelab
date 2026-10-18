# Recovery

Recover Tier 0 independently, preserve evidence before rebuilding, then restore
platform services and workloads. Offline investigation does not require a running platform.

## Table of contents

- [Recovery inputs](#recovery-inputs)
- [Recovery order](#recovery-order)

## Recovery inputs

Retain these outside the system being restored:

| Material | Purpose |
| --- | --- |
| Tier/shared code, tools, provider artifacts, images | Bootstrap without hosted source control, CI, or registry |
| State, inventory, network/storage records | Recreate resources without an inventory application |
| Machine configuration, credentials, SOPS and recovery keys | Restore without unavailable identity or secret services |
| etcd and application-data backups | Restore data, not merely empty VMs |
| Protected log-data copies, schema/source catalogue and offline reader/key kit | Investigate a total shutdown without the collector, identity services or search indexes |
| Working API, DNS/time, image access, and runbook | Execute recovery independently of the target |

Record owners, backup locations, and restore results in project-owned runbooks.
Offline custody has no routed access from the connected management network.

## Recovery order

| Order | Action | Acceptance |
| --- | --- | --- |
| 1 | Isolate affected systems and preserve surviving logs/disks before rebuilding | Authorized [offline investigation](security-logging.md#offline-investigation) works from a protected copy; original evidence is unchanged |
| 2 | Recover Tier 0 console/network/storage access and bootstrap tools | Independent local credentials, recovery keys and backup access work without SSO or Tier 1/2 |
| 3 | Restore Tier 0 intake and protected evidence storage | New recovery events are retained; original evidence stays separate; buffered sources replay with gaps accounted for |
| 4 | Restore Tier 0 trust, identity and control services in prerequisite order | Selected PKI, directory and cluster functions verified before dependent consumers |
| 5 | Restore Tier 1 platform and scoped analytics | Search indexes rebuilt from approved copies; no delete authority over Tier 0 evidence |
| 6 | Restore Tier 2 workloads and their integrations | Service data, access scopes and collection verified |

For hardware-only outages, preserve evidence without unnecessarily delaying safe
intake restoration. Suspected compromise requires a clean recovery environment;
reconnecting old disks or credentials must not reintroduce the compromised authority.
Use the [deployment stages](../deployment/README.md) for service-specific prerequisites,
the [backup guide](compute/backup-restore.md) for recovery objectives and restore validation, and
[secret strategy](secret-handling/strategy.md) for protected recovery material.
For the software issuer, follow the [clean-target restore procedure](cryptography/issuer-recovery.md),
not fresh key creation or initial token activation.
