# ${prefix} Platform Architecture

This project-owned record describes the complete intended environment with its
selected capabilities in place. Start with the platform overview, follow a
function into its technical domain, then inspect the detailed design and selected
variant. Replace `TBD` with reviewed project decisions.

The upstream reference supplies reusable patterns and alternatives. This record
joins the site's selections into one coherent design. Shared standards belong in
[naming conventions](../naming-conventions.md); deployment progress and acceptance
evidence belong in [deployment](../deployment/README.md).

## Purpose and scope

| Concern | Project decision |
| --- | --- |
| Purpose, users and required outcomes | TBD |
| Sites, platform boundary and external dependencies | TBD |
| Tier ownership and administrative authority | TBD |
| Required availability and recovery independence | TBD |
| Exclusions and assumptions | TBD |

## Platform relationships

Add a capability map with Tier 2, Tier 1, Tier 0 from top to bottom and
Edge, Application, Control from left to right. Place each service capability in
its owning tier and security layer. Keep product names and VM/cluster details in
the domain designs; identify external consumers and providers at the boundary.
Use the [platform reference](../auto-docs/architecture/README.md) and
[integrated reference design](../auto-docs/architecture/reference-platform.md)
as starting points. Show the selected composition, with alternatives expanded in
their owning domain designs.

Keep capability names consistent between the map and domain views. Tier ownership
and security layers are separate axes, not one classification. A login interface
does not expose the IdP's administration or change its network placement.
Show offline custody outside the connected layers. Exact hosts and addresses
stay in inventory; interaction diagrams belong below.

| Capability | Owning tier | Security layer | Domain design |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Runtime relationships

Explain how the selected functions cooperate once deployed. Use small flow views
for access, software delivery, privileged changes, and observation or recovery;
link each participant to its domain design. These views describe system behavior,
while deployment stages describe how the components are established. Reference:
[runtime flows](../auto-docs/architecture/runtime-flows.md).

| Flow | Participating functions and interfaces | Authority / failure boundary | Domain designs |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Technical domains

| Domain | Project design |
| --- | --- |
| Networking | [Networks, zones and traffic policy](networking/README.md) |
| Compute | [Hypervisors, images and cluster runtime](compute/README.md) |
| Identity | [Authority, authentication and authorization](identity/README.md) |
| Cryptography | [Trust, key custody and secrets](cryptography/README.md) |
| Delivery | [Endpoints, software supply and artifacts](delivery/README.md) |
| Operations | [Visibility, inventory and recovery](operations/README.md) |

Each domain README expands the functions represented in the platform view,
explains its completed internal design, and links to focused component designs.
Detailed records link back to their parent domain and identify any connections
that cross its boundary.

## Selected variants

Record the selected implementation of each variable capability, with the
alternatives and their resulting topologies in the owning detailed design.
Follow the [variant contract](../auto-docs/architecture/variants.md): the platform
role and consumer interfaces remain stable where the design permits, while
placement, custody and failure behavior are explicit properties of the selection.

| Capability | Selected variant and rationale | Required platform contract | Detailed design |
| --- | --- | --- | --- |
| TBD | TBD | TBD: consumers, interfaces, authority and required guarantees | TBD |

Review the combined selections for compatibility. A variant that changes a
consumer interface, trust boundary or required guarantee also requires updates
to the affected platform and domain views. A list of independent alternatives
does not establish a compatible site design.

## Shared constraints and decisions

| Decision / required property | Rationale and alternatives | Consequences | Review trigger |
| --- | --- | --- | --- |
| TBD: trust, ownership, availability or recovery constraint | TBD | TBD | TBD |

Add focused cross-domain decisions under `decisions/`. Reference patterns:
[principles](../auto-docs/architecture/principles.md),
[tier ownership](../auto-docs/architecture/tier-ownership.md),
[service boundaries](../auto-docs/architecture/service-boundaries.md) and
[reference platform](../auto-docs/architecture/reference-platform.md).
