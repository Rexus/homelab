# Policy proxy

[Up: Software intake](../README.md) · Level 2 · `L-Proxy` / `DEF-proxy`

Admit accepted clients, destinations and ports; forward permitted requests and reuse eligible HTTP
objects. HTTPS CONNECT carries the source TLS session without inspecting or caching its payload.

[Contract view](../../../views/software-intake/policy-proxy/contract.svg) · [Typed-use change impact](../../../views/software-intake/policy-proxy/change-impact.svg).

[definition.sysml](definition.sysml) owns the reusable contract. The parent composes this same part
with the [object cache](../object-cache/README.md), clients and sources in its [logical view](../logical.md).

| Interface / dependency | Connected design or evidence |
| --- | --- |
| Listener and upstream exchange | [HTTP/HTTPS expected behavior](../../../../docs/01-architecture/07-software-intake/README.md#cache-request-and-response) |
| Rebuildable cache access | [Object cache](../object-cache/README.md) |
| Execution, attachment and storage | [Shared platform](../../platform/README.md), through the [selected deployment](../deployment.md) |
| Functions and scenario obligations | [Functional model](../../../functions/software-intake/README.md), [use case](../../../use-cases/software-intake/README.md) |
| Product and verification | [Squid role](../../../../tier-2/ansible/roles/cache_proxy/tasks/squid.yml), [test entry](../../../test/software-intake/README.md) |

Consumer signature verification and independent egress enforcement keep their own owners. A successful
proxy response is not release approval. Change this contract through its parent design and check consumers.

<!-- BEGIN DESIGN CONTEXT -->
## Connected views

[Owning documentation](../logical.md).

The proxy owns its allocated behavior. Client verification and independent egress enforcement are related interaction obligations, not proxy features.
<!-- END DESIGN CONTEXT -->
