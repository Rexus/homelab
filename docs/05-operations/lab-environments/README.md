# Lab environments operations

Maintain and recover the selected Tier 2 workload runtime within its approved scope.

**Related:** [Architecture](../../01-architecture/23-lab-environments/README.md) ·
[Stage 10: Lab environments](../../03-deployment/stage-10-lab-environments/README.md).

| Task | Guide |
| --- | --- |
| Recover a workload VM | [VM recovery](../recovery/virtual-machines.md) |
| Back up a VM | [VM backup tasks](../backups/virtual-machines.md) |
| Find lab maintenance scope | [Ansible recipe map](../ansible-recipes.md#recipe-map) |
| Add or reserve Kubernetes workers | [Worker pools](../kubernetes-pools.md) |
| Review runtime, application and telemetry choices | [Stage 10 main path](../../03-deployment/stage-10-lab-environments/README.md#main-path) |

VM and cluster tasks are general coverage, not a complete lab application operations
runbook. A bounded self-service dispatcher is project-owned and is not supplied; use
Stage 10's selected isolation, application and recovery checks for acceptance.
