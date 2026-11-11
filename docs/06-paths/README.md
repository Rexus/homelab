# Repository paths

These short checklists answer what to do from each repository. The manual's
design, installation, code and operations guides live in `01-architecture/`,
`03-deployment/`, `04-development/` and `05-operations/` respectively.

<a id="choose-your-repository"></a>

## Choose a repository

To follow one capability across the whole manual, use the [capability index](capabilities.md).

| Repository | Checklist | Responsibility |
| --- | --- | --- |
| Tier 0 | [Infrastructure and trust](tier-0/README.md) | Hosts, networks, templates, control cluster and trust services |
| Tier 1 | [Shared platform](tier-1/README.md) | Verified intake, delivery, observability and development services |
| Tier 2 | [Edge and lab environments](tier-2/README.md) | Public edge/cache, applications and isolated labs |
| Shared | [Common automation](shared/README.md) | Reusable execution and references; no inventory or state |
| Architecture | [Project records](../04-development/project-documentation.md) | Selected platform architecture, decisions and cross-repository procedures |

Use the [repository map](../03-deployment/README.md#repository-locations) to translate
these owners into generated checkout names and upstream source paths.

## Follow the model

[Platform architecture](../01-architecture/README.md) ->
[domain choice](../01-architecture/README.md#foundational-capabilities) ->
[deployment stage](../03-deployment/README.md) ->
[implementation](../03-deployment/README.md) ->
[operations](../05-operations/README.md).

<a id="purpose"></a>
<a id="capability-groups"></a>
<a id="paths"></a>
<a id="how-to-use-paths"></a>
