# ${prefix} Platform Record

Record selected paths and completion here; use auto-docs for the instructions.
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

| Area | Selected path / local exception | Reference |
| --- | --- | --- |
| Standards | Complete VM names, domains, tags, VMIDs and VLAN conventions | [Naming conventions](naming-conventions.md) |
| Compute | Reference: Proxmox VE 9.2+, three hosts, native HA and dynamic rebalancing | [HA and failover](auto-docs/deployment/foundation/step-1b-cluster-ha.md) |
| Networks | Reference: VLAN-aware bridges; record SDN selection if used | [Network design](auto-docs/architecture/networking/README.md) |
| Storage | Reference: Proxmox/Ceph live volumes, separate NAS backups | [Storage interfaces](auto-docs/architecture/compute/runtime.md#storage-interfaces) |
| Trust | Reference: software custody; record USB/network HSM selection if used | [Cryptography variants](auto-docs/architecture/cryptography/README.md) |
| Kubernetes | Reference: Talos; retain exact image/schematic in Tier 0 inputs | [Cluster design](auto-docs/architecture/compute/kubernetes.md) |
| Delivery | Select Argo CD or Spinnaker in Tier 1; Flux in Tier 0 | [Controller choices](auto-docs/architecture/delivery/controllers.md) |

Check compatibility in the [variant contracts](auto-docs/architecture/variants.md).
The [runtime relationships](auto-docs/architecture/runtime-flows.md) explain cross-tier flows.

## Deployment checklist

Follow the linked main path, selecting adjacent options only where needed. In each
row, replace the reference choice with the actual selection. Check **Deployed** after
installation and **Verified** only after the guide's acceptance checks; an existing
accepted service can satisfy the step without reinstalling it. Link non-secret evidence.
Unchecked boxes are deliberate: generation proves no operational result.

- [ ] **Foundation accepted:** hosts, networks, storage, access/state and approved templates.
  [Preparation](auto-docs/deployment/foundation/README.md).

| Capability | Run from | Selected path / evidence | Deployed | Verified |
| --- | --- | --- | :---: | :---: |
| [1. Software intake](auto-docs/deployment/stage-1-software-intake/README.md) | Tier 2; consumers in every tier | Policy proxy/cache or existing approved supply | &#9744; | &#9744; |
| [2. Protected logging](auto-docs/deployment/stage-2-logging/README.md) | Tier 0 | Syslog receiver, NAS copies and independent backup | &#9744; | &#9744; |
| [3. Trust](auto-docs/deployment/stage-3-trust/README.md) | Tier 0 | Software PKI; [USB HSM option](auto-docs/deployment/stage-3-trust/step-1b-usb-hsm.md) | &#9744; | &#9744; |
| [4. Kubernetes](auto-docs/deployment/stage-4-kubernetes/README.md) | Tier 0 | Control cluster and base platform | &#9744; | &#9744; |
| [5. Identity](auto-docs/deployment/stage-5-identity/README.md) | Tier 0 | Dedicated directory pair and cluster IdP | &#9744; | &#9744; |
| [6. Secrets](auto-docs/deployment/stage-6-secrets/README.md) | Tier 0 | Vault and control applications | &#9744; | &#9744; |
| [7. Delivery](auto-docs/deployment/stage-7-delivery/README.md) | Tier 1; Flux remains Tier 0 | Select Argo CD or Spinnaker; record registry | &#9744; | &#9744; |
| [8. Observability](auto-docs/deployment/stage-8-observability/README.md) | Tier 1; exports from Tier 0/2 | Metrics, traces and searchable log copies | &#9744; | &#9744; |
| [9. Development platform](auto-docs/deployment/stage-9-development/README.md) | Tier 1; protected executor in Tier 0 | GitLab, runners, direct-CI trust, Vault and original-state handover | &#9744; | &#9744; |
| [10. Lab environments](auto-docs/deployment/stage-10-lab-environments/README.md) | Tier 2 | Select isolated VMs or cluster environments | &#9744; | &#9744; |

Replace a table checkbox with `&#9745;` when complete. Record deferred/not-selected
capabilities explicitly; they are not failures or permission to skip prerequisites.
This checklist tracks progress, not resource or state ownership.

| Repository | Local code and inputs |
| --- | --- |
| [Tier 0](../../${prefix}-tier-0/README.md) | Hardware control, templates, trust, directory and control cluster |
| [Tier 1](../../${prefix}-tier-1/README.md) | Platform cluster, delivery, Observability and development services |
| [Tier 2](../../${prefix}-tier-2/README.md) | Edge/cache and isolated applications/labs |
| [Shared](../../${prefix}-shared/README.md) | Reusable execution and stateless references; never inventory or state |

## Operate and change

| Need | Reference | Local record |
| --- | --- | --- |
| Find a command or input | [Repository scripts](auto-docs/reference/repository-scripts.md) | Tier-owned configuration |
| Back up and recover | [Recovery guides](auto-docs/administration/recovery.md) | Record offline reader/key kit, RPO/RTO and pruning custodian, restore-test dates and evidence links; no secrets |
| Maintain services | [Administration](auto-docs/administration/README.md) | Maintenance owner and schedule |
| Adopt upstream changes | [Refresh contract](auto-docs/development/generated-repositories.md#refresh-and-local-ownership) | Tested revision and exceptions |

`auto-docs/` is the maintained manual. This record and naming conventions are seeded
once and never overwritten by refresh. Add a focused local document only when an
exception or runbook needs detail beyond this record, then link it here.
