# Software intake operations

Choose the deployed service to operate. The proxy/cache controls transport; the
optional verified-intake worker handles quarantine and publication separately.
Verified intake is a Stage 3 option after trust is established, not part of the
Stage 1 cache installation.

**Related:** [Architecture](../../01-architecture/13-software-intake/README.md) ·
[Stage 1: Software intake](../../03-deployment/stage-1-software-intake/README.md) ·
[Stage 3: verified publication option](../../03-deployment/stage-3-trust/README.md#3b-verified-repository-and-artifact-publication--optional).

| Task | Guide |
| --- | --- |
| Reconcile or recover the cache pair | [Cache administration](../cache.md) |
| Operate verified intake and publication | [Verified intake operations](../software-intake.md) |
| Configure Proxmox update access | [Host update access](../hosts/update-access.md) |

The guides cover their named tasks; deployment acceptance and unimplemented integrations
remain subject to the selected stage's checks and [coverage](../../08-reference/implementation-support.md#stage-coverage).
