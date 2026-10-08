# Repository paths

These short checklists answer what to do from each repository. Design lives in
`architecture/`, detailed installation in `deployment/`, code guidance in
`development/`, and ongoing operations in `administration/`.

<a id="choose-your-repository"></a>

## Choose a repository

| Repository | Checklist | Responsibility |
| --- | --- | --- |
| Tier 0 | [Infrastructure and trust](tier-0/README.md) | Hosts, networks, templates, control cluster and trust services |
| Tier 1 | [Shared platform](tier-1/README.md) | Delivery, access services and platform telemetry |
| Tier 2 | [Workloads](tier-2/README.md) | Applications, project resources and labs |
| Shared | [Common automation](shared/README.md) | Reusable execution and references; no inventory or state |
| Architecture | [Project records](../development/project-documentation.md) | Selected platform architecture, decisions and cross-repository procedures |

## Follow the model

[Platform architecture](../architecture/README.md) ->
[domain choice](../architecture/README.md#technical-domains) ->
[deployment stage](../deployment/README.md) ->
[implementation](../deployment/README.md) ->
[administration](../administration/README.md).

<a id="purpose"></a>
<a id="capability-groups"></a>
<a id="paths"></a>
<a id="how-to-use-paths"></a>
