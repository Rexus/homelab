# Development

Implementation changes begin with the selected [domain design](../architecture/README.md#technical-domains)
and preserve its interfaces, ownership and recovery guarantees. New variants need
design rationale, an implementation path and acceptance tests; a new product name
alone is not a supported option.

Stages do not replace Terraform lifecycle boundaries or Ansible roles.

| Task | Guide |
| --- | --- |
| Prepare local tooling | [Local setup](local-setup.md) |
| Work with private operational repositories | [Repository workflow](repository-workflow.md) |
| Find and change Terraform or Ansible | [Code layout](code-layout.md) |
| Generate, verify or refresh a collection | [Generated repositories](generated-repositories.md) |
| Maintain selected designs and local runbooks | [Project documentation](project-documentation.md) |
| Review preserved design alternatives | [Design coverage](design-coverage.md) |
| Change shared defaults or tier overrides | [Platform inputs](../reference/platform-inputs.md) |

Validate code and generated output together. The generator's
[offline checks](generated-repositories.md#implementation-scope) cover ownership,
refresh preservation, links and shared input contracts.
