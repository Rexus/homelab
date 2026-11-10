# ${prefix} Platform Record

Record selected paths here; track completed deployments in [the checklist](../deployments.md).
Use auto-docs for the instructions.
Reference choices below are editable placeholders, not an accepted or deployed configuration.
Exact hosts, addresses and resources remain in the owning tier's inputs.

## Contents

- [Selected design](#selected-design)
- [Deployment checklist](#deployment-checklist)
- [Operate and change](#operate-and-change)

## Selected design

The [reference architecture](auto-docs/architecture/README.md) is the baseline:
Tier 2, Tier 1, Tier 0 from top to bottom; Edge, Application, Control left to right.
Record only selected alternatives or local differences, not another copy of that design.
The [foundational capability map](auto-docs/architecture/README.md#foundational-capabilities)
connects these implementation choices to the overall system design.

| Area | Selected path / local exception | Reference |
| --- | --- | --- |
| Standards | Record local names, domains, tags and the zone/VNet network plan | [Platform standards](../platform-standards.md) |
| VMID allocation | Follow the convention; keep individual assignments in tier-local Terraform | [VMID quick reference](auto-docs/conventions/vmid-convention.md) |
| Hosting | Reference: Proxmox VE 9.2+, three hosts, native HA and dynamic rebalancing | [HA and failover](auto-docs/deployment/foundation/proxmox/step-1b-cluster-ha.md) |
| Networks | Reference: VLAN-aware bridges; record SDN selection if used | [Network design](auto-docs/architecture/networking/README.md) |
| Storage | Reference: Proxmox/Ceph live volumes, separate NAS backups | [Storage interfaces](auto-docs/architecture/data/README.md#storage-interfaces) |
| Trust | Reference: software custody; record USB/network HSM selection if used | [Cryptography variants](auto-docs/architecture/cryptography/README.md) |
| Kubernetes | Reference: Talos; retain exact image/schematic in Tier 0 inputs | [Cluster design](auto-docs/architecture/hosting/kubernetes.md) |
| Delivery | Select Argo CD or Spinnaker in Tier 1; Flux in Tier 0 | [Controller choices](auto-docs/architecture/software/controllers.md) |

Check compatibility in the [variant contracts](auto-docs/architecture/variants.md).
The [runtime relationships](auto-docs/architecture/runtime-flows.md) explain cross-tier flows.

## Deployment checklist

Use [deployments.md](../deployments.md) for completed IaC paths and their nested options.
After Terraform and/or Ansible completes the linked installation, check that entry;
strike through unselected options. Terraform-only can leave service configuration pending.
Keep non-secret acceptance/recovery evidence in the operating records below;
generation proves no operational result. Existing accepted services can satisfy prerequisites.

| Repository | Local code and inputs |
| --- | --- |
| [Tier 0](../../${repo_prefix}-tier-0/README.md) | Hardware control, templates, trust, directory and control cluster |
| [Tier 1](../../${repo_prefix}-tier-1/README.md) | Platform cluster, delivery, Observability and development services |
| [Tier 2](../../${repo_prefix}-tier-2/README.md) | Edge/cache and isolated applications/labs |
| [Shared](../../${repo_prefix}-shared/README.md) | Reusable execution and stateless references; never inventory or state |

## Operate and change

| Need | Reference | Local record |
| --- | --- | --- |
| Find a command or input | [Repository scripts](auto-docs/reference/repository-scripts.md) | Tier-owned configuration |
| Back up and recover | [Recovery guides](auto-docs/administration/recovery.md) | Record offline reader/key kit, RPO/RTO and pruning custodian, restore-test dates and evidence links; no secrets |
| Maintain services | [Administration](auto-docs/administration/README.md) | Maintenance owner and schedule |
| Adopt upstream changes | [Refresh contract](auto-docs/development/generated-repositories.md#refresh-and-local-ownership) | Tested revision and exceptions |

`auto-docs/` is the maintained manual. This record and platform standards are seeded
once and never overwritten by refresh. Add a focused local document only when an
exception or runbook needs detail beyond this record, then link it here.
