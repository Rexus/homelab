# Software intake functions

Generated from native function contracts and allocations. Product choices remain in [Solution design](../../../../architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml).

| Function | Inputs â†’ outputs | Responsibility | Allocated logical parts | Guardrails |
| --- | --- | --- | --- | --- |
| `F-admit` Check request access | request : Transfer, clientAllowed : Boolean, destinationAllowed : Boolean, portAllowed : Boolean â†’ admitted : Boolean | Check the accepted client, destination and port policy before content access. | `L-Proxy` Policy proxy / HTTP cache | `REQ-policy` |
| `F-cache` Reuse fresh cached content | response : Transfer â†’ eligibleResponse : Transfer | Reuse only eligible fresh responses; respect privacy and freshness directives. Storage remains disposable. | `L-Cache` Rebuildable cache storage, `L-Proxy` Policy proxy / HTTP cache | `REQ-custody` |
| `F-http` Fetch content from source | request : Transfer â†’ response : Transfer | Fetch or conditionally revalidate permitted repository content with its source. | `L-Proxy` Policy proxy / HTTP cache | `REQ-policy` |
| `F-tunnel` Forward HTTPS traffic | request : Transfer â†’ response : Transfer | Establish an admitted tunnel; preserve client-to-source TLS without inspecting or caching encrypted payload. | `L-Proxy` Policy proxy / HTTP cache | `REQ-integrity` |
| `F-verify` Verify before use | response : Transfer â†’ accepted : Boolean | The external client verifies trusted publisher metadata and signatures; failure stops use. | `L-Consumers` Update Consumers | `REQ-integrity` |

`F-verify` is allocated to the external consumer. It is an interaction obligation, not a proxy feature.
Allocation can be many-to-many; it neither creates a service nor establishes implementation conformance.

Follow [scenarios](scenarios.md) for ordered paths and [implementation trace](trace.md) for code, IaC and checks.
