# Kubernetes worker pools

Use explicit node definitions for capacity and Kubernetes scheduling controls for
placement. [Topology design](../../architecture/compute/kubernetes.md) defines the
boundaries; [cluster provisioning](../../deployment/stage-4-kubernetes/procedures/talos-terraform.md)
owns hardware, inventory and state. No autoscaler or rolling node-upgrade controller is supplied.

## Table of contents

- [Add capacity](#add-capacity)
- [Reserve a pool](#reserve-a-pool)
- [Dedicated control planes](#dedicated-control-planes)
- [References](#references)

## Add capacity

1. Work in the owning tier. Add the worker to `talos_workers.hosts`, its fixed IP
   to `ansible/group_vars/talos.yml`, and its hardware to the Kubernetes root's
   `nodes` map. Reserve the MAC/IP externally. Add `pool = "compute"`, for example,
   to emit the `node-pool=compute` label.
2. Run `bash scripts/kubernetes-cluster.sh plan`. Review the saved plan for the
   intended additions only. Stop on replacement, bootstrap or secret changes.
3. Apply the reviewed plan, verify node/system health, and inspect labels using
   `kubectl get nodes -L node-pool`. Test placement and persistence before use.

Tier 1 may use infrastructure, stateful and compute pools; Tier 2 may use development,
testing and lab pools. Names describe scheduling intent, not a permission boundary.
Keep untrusted build execution off sensitive infrastructure hosts.

## Reserve a pool

Talos accepts node labels in machine configuration. Default worker admission policy
does not permit workers to modify their own taints; an authorized Kubernetes
administrator owns those changes. [1] Use the owning cluster's protected kubeconfig.

```bash
read -r -p "Worker node to reserve: " NODE
kubectl taint node "$NODE" dedicated=compute:NoSchedule --overwrite
```

For a compute workload, set both a selector and the matching toleration in its
project-owned manifest. A toleration permits placement; the selector requests it. [2]

```yaml
spec:
  nodeSelector:
    node-pool: compute
  tolerations:
    - key: dedicated
      operator: Equal
      value: compute
      effect: NoSchedule
```

Install required CNI, storage and monitoring agents with appropriate tolerations.
`NoSchedule` does not evict existing pods. Adding a taint after node registration
also leaves an initial scheduling window; keep untrusted workloads disabled until
the reservation is verified. This is not a secure multi-tenant runner installer.

## Dedicated control planes

Add and verify sufficient workers first. Review system tolerations, workload
selectors, persistent-volume placement and remaining capacity after a node failure.
Then change `cluster.allow_scheduling_on_control_planes` to false and review the
configuration plan. Configuration apply is not a health-gated rolling controller;
use the pinned Talos release's maintenance procedure where a reboot is required.

Cordon/drain control planes one at a time using Kubernetes disruption-budget and
storage checks; disabling scheduling alone does not move existing workloads.
Verify service continuity after each move. Never remove nodes, regenerate secrets
or replace state to match a newer starter example.

## References

1. [Talos machine configuration](https://docs.siderolabs.com/talos/v1.12/reference/configuration/v1alpha1/config).
2. [Kubernetes taints and tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).
