# ${title} architecture

This project-owned record maps the selected design to its implementation.
Replace the draft selections with reviewed project decisions. Upstream patterns
are references, not evidence that a service has been deployed.

## Scope

${scope}

The [platform architecture](${docs}/architecture/README.md) connects the
[technical domains](${docs}/architecture/README.md#technical-domains) and their
implementation choices. Project-wide conventions and topology belong in the
[architecture repository](../../../${prefix}-architecture/docs/architecture/README.md).

## Selected design

| Domain / capability | Selected pattern | Implementation and verification |
| --- | --- | --- |
${selections}

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
