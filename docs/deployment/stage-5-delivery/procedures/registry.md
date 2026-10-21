# Deploy the selected registry variant

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`).
The cluster variant uses [clusters/tier1/platform/artifact-registry/](../../../../tier-1/clusters/tier1/platform/artifact-registry/);
the integrated source-control variant uses Tier 1's `development` setup.

**Design:** [artifact supply options A-C](../../../architecture/delivery/artifact-supply.md).
**Prerequisites:** approved runtime, storage, TLS/DNS, identity policy and retained
bootstrap artifacts. **Owner:** Tier 1. Registry integration is project-owned;
the repository does not supply a complete Harbor/Dragonfly installer.

## Table of contents

- [Select the procedure](#select-the-procedure)
- [Prepare inputs](#prepare-inputs)
- [Acceptance](#acceptance)
- [References](#references)

<a id="purpose"></a>
<a id="what-a-registry-does"></a>
<a id="gitlab-registry-vs-shared-registry"></a>
<a id="reference-direction"></a>
<a id="harbor-and-dragonfly-roles"></a>

## Select the procedure

| Selected design | Procedure |
| --- | --- |
| A: Integrated registry | Enable/configure the registry in the selected source-control deployment using its supported administrator procedure [1] |
| B: Independent registry | Prepare the chosen runtime and persistent dependencies, then configure the supported registry deployment; Harbor's HA procedure is an example [2] |
| C: Registry plus acceleration | Complete B, then integrate distribution clients and any selected preheat workflow; Dragonfly is an example [3] |
| Existing approved service | Verify the same endpoint, policy and recovery requirements without creating another registry |

These are alternatives, not a mandatory GitLab-to-Harbor-to-Dragonfly sequence.
A new Tier 1 cluster reuses the [common cluster procedure](../../stage-3-identity/procedures/kubernetes.md)
with tier-local inputs and state. Do not retire the bootstrap artifact source until
the new path and independent recovery have been accepted.

<a id="what-to-plan"></a>

## Prepare inputs

| Input | Record or configure |
| --- | --- |
| Endpoints | FQDNs, certificate chain and trust for nodes/runners |
| Storage | Artifact data, database/cache dependencies, retention and backup locations |
| Identity | Scoped operator access, project ownership and robot credentials outside Git |
| Promotion | Accepted provenance, scans/signatures and immutable artifact references |
| Distribution | Direct clients or selected acceleration; a fallback path when required |
| Recovery | Product-supported export/restore, independent artifacts and custodian |

Use the selected product's supported installer or project GitOps manifests.
The presence of a platform-cluster skeleton does not install these services.

<a id="downstream-platforms"></a>

## Acceptance

1. Push and pull a disposable artifact with the intended runner and consumer identities.
2. Verify unauthorized push/pull is denied and promotion policy behaves as selected.
3. Test a clean consumer, retained bootstrap artifacts and restoration of registry data.
4. For C, verify acceleration and failure behavior separately from registry authority.
5. Record evidence and ongoing retention/restore tasks in project administration.

<a id="read-more"></a>

Return to [Step 2: protected execution](../README.md#step-2-enable-protected-execution), or use the accepted service for
[image-based Linux](../step-1d-image-based-linux.md) and workload delivery.

## References

Sources checked 2026-10-08.

1. [GitLab container registry and administration links](https://docs.gitlab.com/user/packages/container_registry/)
2. [Harbor HA deployment](https://goharbor.io/docs/main/install-config/harbor-ha-helm/)
3. [Dragonfly documentation](https://d7y.io/docs/)
