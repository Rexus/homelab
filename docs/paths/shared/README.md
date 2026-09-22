# Shared automation

This repository deploys no services by itself. It provides cross-tier guest
modules, baseline Ansible roles, and local execution helpers. Every deployment
still belongs to a tier and uses that tier's inventory, credentials, and state.

## Getting started

1. Keep the generated shared repo beside the three tier repos.
2. Prepare [local tooling](../../getting-started/local-setup.md) and retain a
   reviewed shared revision plus its dependencies for recovery.
3. Work from the owning tier's root and follow its deployment guide:
   [Tier 0](../tier-0/README.md), [Tier 1](../tier-1/README.md), or [Tier 2](../tier-2/README.md).
4. Test shared changes against every consuming tier before adopting them.

Do not run deployment commands from the shared root or add live inventory here.
Tier 0 owns template creation and updates; shared code does not publish images.
It exposes [one consumer catalog](../../platforms/proxmox/template-catalog.md) for
approved IDs, titles, source nodes, and image tags. That project-owned file is
maintained through Tier 0 review, not overwritten by upstream refresh.

## Find your way

| Need | Guide |
| --- | --- |
| Commands, inputs, and side effects | [Repository scripts](../../reference/repository-scripts.md) |
| Module and role locations | [Automation layout](../../reference/infrastructure-automation-layout.md) |
| Upstream changes without replacing local work | [Refresh contract](../../reference/generated-repository-model.md#refresh-and-local-ownership) |
| Project choices and recovery | [Project documentation](../../reference/project-documentation.md) |
