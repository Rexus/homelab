# Architecture views

Styled SVGs and native SysON views use the same model selections and stable view identities.
Native sources live in architecture/models; generated SVGs live separately in architecture/generated.
These are projections of one native model, not another authored design tree.
This is the deliberately selected engineering view set.
Supporting scenario details, inspection reports and evidence remain linked assets; their pages
are not automatically additional native views.
Git holds accepted semantics; reviewed SysON intent changes can return to the owning sources.
Publication records actual
element and relationship coverage and must not call an incomplete rendering equivalent.

[System Overall](../../architecture/generated/HomelabSystemOverview.svg) · [Authoring and publication](../../docs/04-development/syson.md)

| View | Owner | Model elements | Selected relationships |
| --- | --- | ---: | ---: |
| [Homelab  /  Functions](../../architecture/generated/HomelabFunctions.svg) | . | 8 | 6 |
| [Clone a Git repository over HTTPS](../../architecture/generated/platform/hosting/Boot1CloneRepository.svg) | platform/hosting | 4 | 3 |
| [Shared platform  /  resource providers and backing](../../architecture/generated/platform/SharedPlatformOverview.svg) | platform | 8 | 16 |
| [Policy proxy contract](../../architecture/generated/software-intake/policy-proxy/PolicyProxyContract.svg) | software-intake/policy-proxy | 1 | 0 |
| [Software intake  /  Functions](../../architecture/generated/software-intake/SoftwareIntakeFunctions.svg#overview) | software-intake | 8 | 6 |
| [Software intake  /  Logical design](../../architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg) | software-intake | 8 | 7 |
| [Software intake  /  Solution design](../../architecture/generated/software-intake/solution/SoftwareIntakeSolutionDesign.svg) | software-intake/solution | 12 | 13 |
| [Software intake and its shared resource dependencies](../../architecture/generated/software-intake/solution/SoftwareIntakeResources.svg) | software-intake/solution | 15 | 19 |
| [Retrieve or revalidate HTTP content](../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-miss) | software-intake | 16 | 3 |
| [Retrieve through source TLS](../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-https) | software-intake | 14 | 6 |
| [Software intake  /  Use cases](../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#overview) | software-intake | 12 | 11 |
| [Homelab  /  System Overall](../../architecture/generated/HomelabSystemOverview.svg) | . | 5 | 9 |
| [Homelab  /  Use cases](../../architecture/generated/HomelabUseCases.svg) | . | 8 | 6 |
