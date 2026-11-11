# Observability operations

Operate diagnostics, infrastructure health and scoped telemetry. Protected evidence
remains owned by [Stage 2 operations](../protected-logging/README.md); protected-log search
copies are an optional Stage 8 integration.

**Related:** [Architecture](../../01-architecture/21-observability/README.md) ·
[Stage 8: Observability](../../03-deployment/stage-8-observability/README.md).

| Task | Guide |
| --- | --- |
| Plan service maintenance and upgrades | [General maintenance](../maintenance.md) |
| Find observability maintenance scope | [Ansible recipe map](../ansible-recipes.md#recipe-map) |
| Protect PostgreSQL data | [PostgreSQL backups](../backups/postgresql.md) |
| Recover shared product data | [Tier 1 product recovery](../recovery/tier-1-products.md) |
| Check infrastructure monitoring and scoped views | [Stage 8 main path](../../03-deployment/stage-8-observability/README.md#main-path) |

The linked maintenance guidance is general; no complete observability product lifecycle
runbook is supplied here. Dedicated-VM IaC is an OS baseline, and the cluster integration
directory is a starter. Follow Stage 8's source-to-query, access and recovery checks.
