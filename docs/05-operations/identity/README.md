# Identity operations

Manage access through the existing directory and federation boundaries.

**Related:** [Architecture](../../01-architecture/18-identity/README.md) ·
[Stage 5: Identity](../../03-deployment/stage-5-identity/README.md).

| Task | Guide |
| --- | --- |
| Add or remove household or team access | [Access lifecycle](../access-lifecycle.md) |
| Inspect directory service and API health | [Directory health checks](../ansible-recipes.md#choose-a-recipe) |
| Restore directory and CA identity | [FreeIPA and CA recovery](../recovery/freeipa-ca.md) |
| Restore identity federation | [Keycloak recovery](../recovery/keycloak.md) |
| Protect or restore the federation database | [PostgreSQL backups](../backups/postgresql.md), [product recovery](../recovery/README.md#service-data-and-identities) |

These tasks do not constitute a complete directory or federation lifecycle runbook.
Use Stage 5's access and recovery checks and record actual acceptance.
