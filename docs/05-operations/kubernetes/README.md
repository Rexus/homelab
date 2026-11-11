# Kubernetes operations

Operate the cluster runtime and its worker pools using the owning tier's inputs and state.

**Related:** [Architecture](../../01-architecture/17-kubernetes/README.md) ·
[Stage 4: Kubernetes](../../03-deployment/stage-4-kubernetes/README.md).

| Task | Guide |
| --- | --- |
| Add a worker or reserve a pool | [Worker pools](../kubernetes-pools.md) |
| Plan node upgrades and maintenance | [General maintenance](../maintenance.md#upgrade-gate) |
| Recover original cluster state and etcd | [Original state and etcd](../recovery/original-state-etcd.md) |
| Restore a cluster VM | [VM recovery](../recovery/virtual-machines.md) |

The maintenance guidance is general and requires release-matched product procedures;
the worker-pool guide does not cover the full cluster lifecycle. Follow the stage's
acceptance checks and record actual recovery results.
