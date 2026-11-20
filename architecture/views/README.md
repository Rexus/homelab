# Architecture views

Styled SVGs and native SysON views use the same model selections and stable view identities.
Folders follow Design ownership. This is the deliberately selected engineering view set.
Supporting scenario details, inspection reports and evidence remain linked assets; their pages
are not automatically additional native views.
Git owns semantic edits. SysON is a generated review snapshot; publication records actual
element and relationship coverage and must not call an incomplete rendering equivalent.

[System Overall](system-overall.svg) · [Authoring and publication](../../docs/04-development/syson.md)

| View | Owner | Model elements | Selected relationships |
| --- | --- | ---: | ---: |
| [Homelab  /  Functions](functions.svg) | . | 8 | 6 |
| [Clone a Git repository over HTTPS](platform/hosting/clone-repository.svg) | platform/hosting | 4 | 3 |
| [Shared platform  /  resource providers and backing](platform/overview.svg) | platform | 8 | 16 |
| [Policy proxy contract](software-intake/policy-proxy/contract.svg) | software-intake/policy-proxy | 1 | 0 |
| [Homelab  /  Requirements](requirements.svg) | . | 4 | 0 |
| [Software intake  /  Functions](software-intake/functions.svg) | software-intake | 8 | 6 |
| [Connected software intake and its consumers](software-intake/logical.svg) | software-intake | 8 | 7 |
| [Cache services and update requests](software-intake/placement.svg) | software-intake | 12 | 13 |
| [Software intake  /  Requirements](software-intake/requirements.svg) | software-intake | 4 | 0 |
| [Software intake and its shared resource dependencies](software-intake/resource-dependencies.svg) | software-intake | 15 | 19 |
| [Retrieve or revalidate HTTP content](software-intake/scenario-views.svg#SC-http-miss) | software-intake | 16 | 3 |
| [Retrieve through source TLS](software-intake/scenario-views.svg#SC-https) | software-intake | 14 | 6 |
| [Software intake  /  Tests and obligations](software-intake/tests.svg) | software-intake | 23 | 19 |
| [Retrieve and verify software](software-intake/use-cases.svg) | software-intake | 12 | 11 |
| [Homelab  /  System Overall](system-overall.svg) | . | 5 | 9 |
| [Homelab  /  Use cases](use-cases.svg) | . | 8 | 6 |
