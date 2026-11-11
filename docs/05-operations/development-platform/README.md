# Development platform operations

Maintain source control, build execution and infrastructure handover. Delivery controllers
and artifact supply belong to [Stage 7 operations](../delivery/README.md).

**Related:** [Architecture](../../01-architecture/22-development-platform/README.md) ·
[Stage 9: Development platform](../../03-deployment/stage-9-development/README.md).

| Task | Guide |
| --- | --- |
| Protect GitLab data VMs | [GitLab data backups](../backups/gitlab-data.md) |
| Recover shared product data | [Tier 1 product recovery](../recovery/tier-1-products.md) |
| Find source-control and runner maintenance scopes | [Ansible recipe map](../ansible-recipes.md#recipe-map) |
| Plan upgrades and version-specific recovery | [General maintenance](../maintenance.md#upgrade-gate) |
| Review source-control, runner and handover acceptance | [Stage 9 main path](../../03-deployment/stage-9-development/README.md#main-path) |

These are scoped tasks and general maintenance, not a complete GitLab or runner lifecycle
runbook. The source-control VM alternative requires project-supplied SSO and backup/restore
integration; record the selected Stage 9 acceptance and recovery results.
