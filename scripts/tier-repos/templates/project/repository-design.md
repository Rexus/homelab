# ${title} architecture

This project-owned record expands the part of the completed platform owned by
this repository and maps its selected design to implementation. Replace the
draft selections with reviewed project decisions. Upstream patterns supply
alternatives; deployment records establish which results have been verified.

## Scope

${scope}

Start with the selected [platform architecture](../../../${prefix}-architecture/docs/architecture/README.md)
and its [technical domains](../../../${prefix}-architecture/docs/architecture/README.md#technical-domains),
then use this record to inspect the owned components. Project-wide conventions
and topology belong in that architecture repository. The
[upstream platform reference](${docs}/architecture/README.md) explains reusable
patterns rather than the site's selected composition.

## Resulting owned design

Show the owned components and their relationships in a diagram of the completed design.
Retain the names and interfaces used in the parent domain views. Include external
providers and consumers at the boundary, with the owner and authority of each
connection. Shared records describe the automation and reference-data contract;
they do not claim deployed resources.
Use stable capability and role labels in architecture. Put exact guest names and
deployment progress in the linked deployment views, following the
[diagram conventions](${docs}/development/diagrams.md#abstraction-and-implementation).

| Platform function / domain | Owned component or contract | Supplied interface | Consumed dependency and owner |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Selected design

| Domain / capability | Selected pattern | Implementation and acceptance reference |
| --- | --- | --- |
${selections}

Expand complex selections in focused design records under `architecture/`.
Each record identifies its parent domain, the resulting topology, selected
variant, alternatives, and required guarantees. Follow the
[variant contract](${docs}/architecture/variants.md); a changed consumer interface
or trust boundary also requires an update to the affected parent views.

## Boundaries

| Type | Standard | Comments |
| --- | --- | --- |
| Dependencies | Record required services and recovery alternatives | Include ownership and permitted flows |
| Networks | Record selected purpose-based networks and zones | Reference inventory and local network inputs; do not duplicate IP lists |
| Access | Record administration and service identities | Store credential locations, never credentials |
| Recovery | Record independence, recovery objectives and custodians | Link administration runbooks; keep procedures out of architecture |

## Required guarantees

Record the required properties of the selected design, not deployment progress.
Current readiness and acceptance evidence belong in [deployment](../deployment/README.md).

| Capability / selected option | Availability and isolation | Recovery requirement | Review trigger |
| --- | --- | --- | --- |
| Record the chosen pattern and reason | Define tolerated failures and access boundaries | Define independence and recovery objectives | Record conditions invalidating this choice |

## Implementation

Follow the [repository entry points](../../README.md) for code and commands.
Terraform roots describe complete deployments with independent state, not an
ordered list of stages. Ansible recipes compose roles for supported operations.
Shared references do not transfer inventory, resource, or state ownership.

Record execution procedures in [deployment](../deployment/README.md), including
any differences from the upstream deployment stages.
