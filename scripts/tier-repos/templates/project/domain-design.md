# ${prefix} ${title} Design

Project-owned ${domain} design within the [platform architecture](../README.md).
Select patterns from the [upstream reference](../../auto-docs/architecture/${domain}/README.md),
then show how the site's chosen components supply the functions named in that
overview. The diagram and contracts describe the resulting domain with its
selected capabilities in place; deployment procedures and evidence have their
own records.

## Purpose and boundaries

| Concern | Project decision |
| --- | --- |
| Functions expanded from the platform overview | TBD |
| Consumers and capabilities supplied | TBD |
| Scope and exclusions | TBD |
| Component owners, tier allocation and security layers | TBD |

## Resulting domain design

Expand the named capabilities from the platform map into their selected
components, VM/cluster/external runtimes and relationships. Preserve each
capability's owning tier and security layer. Include consumers from other tiers
and required external providers, distinguishing service access from administration.
Keep product choices in this view, not in the capability map.

| Interface | Provider | Consumer | Purpose and required behavior |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Components and choices

| Component | Selected pattern and rationale | Interfaces / dependencies | Owning implementation |
| --- | --- | --- | --- |
| TBD | TBD: include alternatives and trade-offs | TBD | Link the tier's design and code |

## Detailed designs and variants

Add focused records for components or relationships that need further detail.
Each record links to this domain view, shows the completed selected design, and
expands alternatives only for the capability that changes. Use the upstream
[variant contract](../../auto-docs/architecture/variants.md) to separate common
interfaces from the properties that vary.

| Detailed design | Selected variant | Stable role and interfaces | Differences and compatibility conditions |
| --- | --- | --- | --- |
| TBD: link a focused design | TBD | TBD | TBD: placement, custody, availability and recovery |

Record selection rationale, required guarantees, and the effect on neighboring
components. If a choice changes the domain's outward contract, update this view
and the affected platform relationships. Preserve valid alternatives as designs
without implying that every alternative has an installer.

## Required guarantees

| Concern | Required property | Design review trigger |
| --- | --- | --- |
| Access and isolation | TBD | TBD |
| Availability and failure behavior | TBD | TBD |
| Recovery independence | TBD | TBD |

## Realization and operations

Link each selected detailed design to the deployment procedure that establishes
it and the acceptance record that verifies the result. Procedures link back to
that design. The existence of an upstream pattern is separate from the site's
deployment evidence.

Use [deployment](../../deployment/README.md) for procedures, readiness and acceptance;
[administration](../../administration/README.md) for recurring operations; and
[development](../../development/README.md) for implementation changes.
