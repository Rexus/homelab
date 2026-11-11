# Kubernetes

Kubernetes provides orchestration within independently owned tier runtimes. The
cluster design, platform services and workload isolation are separate decisions.

```mermaid
block-beta
  columns 2
  T2["Tier 2 / workloads"] C2["Independent API and etcd<br/>Workload services"]
  T1["Tier 1 / shared platform"] C1["Independent API and etcd<br/>Shared services"]
  T0["Tier 0 / control"] C0["Independent API and etcd<br/>Control services"]
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  class T2,T1,T0 boundary
  class C2,C1 services
  class C0 runtime
```

*Figure: Each tier owns a cluster with its own API and etcd; the view does not establish physical isolation or
application availability.*

| View | Guide |
| --- | --- |
| Cluster topology, scheduling and ownership | [Kubernetes design](../10-hosting/04-kubernetes.md) |
| Hosting and recovery boundaries | [Hosting and orchestration](../10-hosting/README.md) |
| Workload isolation | [Lab isolation](../10-hosting/05-workload-isolation.md) |
| Deploy the control cluster and basic platform | [Kubernetes deployment](../../03-deployment/stage-4-kubernetes/README.md) |
| Operate clusters and worker capacity | [Kubernetes operations](../../05-operations/kubernetes/README.md) |
