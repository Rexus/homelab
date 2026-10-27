# Maintenance and hardware replacement

Maintain one bounded component at a time using its native lifecycle procedure and the original
tier-owned configuration/state. Successful convergence is not proof that an upgrade is compatible.
Use [template lifecycle](compute/template-lifecycle.md),
[Ansible recipes](ansible-recipes.md) and the selected product's release documentation for exact commands.

## Contents

- [Routine schedule](#routine-schedule)
- [Upgrade gate](#upgrade-gate)
- [Replace hardware](#replace-hardware)

## Routine schedule

Record actual intervals, owners and evidence in project administration:

| Activity | Review / action |
| --- | --- |
| Backup and intake health | Alert on missing successful jobs, source silence, queue/WAL growth and storage pressure; do not wait for a dashboard review |
| Certificates and credentials | Review expiry/renewal, CA/CRL distribution, service identities, backup access and independent break-glass custody |
| Security updates | Review product advisories, approve artifacts through software intake and schedule a canary/maintenance window |
| Restore drill | Restore one selected recovery set to isolated clean targets and record observed RPO/RTO |
| Capacity/failure domains | Review node/storage growth, real physical placement and single shared NAS/power/network dependencies |
| Access | Review privileged roles, abandoned devices/tokens, source-project protections and logging read scopes |

The proxy/cache controls software access; it is not a patch-selection or automatic reboot controller.
The kit's maintenance recipes cover their documented supported operations, not a universal
distribution/product upgrader. OS/vendor update approval and rolling-upgrade execution remain
explicit operator tasks unless a project supplies a qualified controller.

## Upgrade gate

1. Select the component and target release; read its supported upgrade path, intermediate stops,
   dependencies and rollback restrictions. Record the resolved provider/chart/image/tool versions
   in owned machine-readable inputs and retain their approved artifacts independently.
2. Take a coherent recovery point and verify access to the original state, keys and
   [product restore procedure](recovery/README.md). Pause competing Terraform, Ansible and delivery
   writers. Inspect the plan/rendered manifests; stop on unexpected deletion or replacement.
3. Exercise a canary with separate inputs/state. Upgrade one approved failure domain at a time;
   verify quorum, readiness, application access, audit delivery, queues and storage after each unit.
   A pod count alone is not a service health gate.
4. Continue only after the recorded gate passes. On failure, stop and use the product's supported
   rollback or restore path. Database/schema migrations can make a simple Helm or image rollback
   invalid. Never reinitialize keys, state or cluster identity merely to make convergence pass.

For Kubernetes, retain original machine configuration/secrets and etcd snapshots; use release-matched
Talos lifecycle commands, not fresh Terraform bootstrap, to upgrade nodes. For GitLab, follow its
required upgrade stops and dependency ordering in the
[data-service guide](../deployment/stage-9-development/procedures/data-services.md).
For CA/directory services, preserve the original signing/domain identity and audit continuity.

## Replace hardware

1. Inventory the affected host, guests, disks, bridges/VLANs, storage paths and physical failure
   labels. Verify that surviving capacity can meet the selected quorum/availability contract.
   Preserve incident evidence before reusing disks if compromise is suspected.
2. Prepare the replacement through the [foundation](../deployment/foundation/README.md) and
   [cluster HA procedure](../deployment/foundation/step-1b-cluster-ha.md). Verify API trust, storage,
   networking and recovery access before moving or restoring a guest.
3. Use Proxmox's native migration/backup restore with original guest identities and tier state.
   VM placement inputs are creation-time choices; changing `proxmox_node_name` is not an IaC
   migration command. Do not apply examples over original production resource maps.
4. Reconcile actual node topology/failure labels and storage attachment after moves. Test one
   affected service, SSO/access denial, intake and backups before retiring the old host or media.
   Update project records and preserve a replacement-host restore result.

If the original environment is lost, follow the [tier recovery order](recovery.md), not this planned
maintenance procedure. Qualified hardware/storage failure behavior remains live acceptance work.
