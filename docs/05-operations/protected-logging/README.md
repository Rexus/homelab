# Protected logging operations

Operate Tier 0 protected evidence and independently held recovery copies. Stage 8
observability can consume approved search copies; it does not own the protected evidence.

**Related:** [Architecture](../../01-architecture/14-protected-logging/README.md) ·
[Stage 2: Protected logging](../../03-deployment/stage-2-logging/README.md).

| Task | Guide |
| --- | --- |
| Check evidence, retention, access and receiver health | [Security logging](../security-logging.md) |
| Exercise faults, replay and restore | [Logging drill](../logging-drill.md) |
| Find the receiver maintenance scope | [Ansible recipe map](../ansible-recipes.md#recipe-map) |
| Sequence recovery after platform loss | [Recovery order](../recovery.md#recovery-order) |

Use the stage's acceptance checks and record actual drill results; configured collection
or a successful recipe is not evidence of a completed restore.
