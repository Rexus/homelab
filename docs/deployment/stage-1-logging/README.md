# Stage 1: Protected logging

Deploy independent Tier 0 log intake before PKI, FreeIPA or Kubernetes. This capability
retains security/syslog/audit evidence now; monitoring and searchable copies extend it later.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
Run repository scripts from this root; Shared is execution code, not an evidence owner.
**Design:** [protected security logging](../../architecture/operations/security-logging.md).
**Prerequisites:** verified [foundation](../foundation/README.md): approved Linux templates, Control networking, local tools/state,
independent bootstrap credentials and protected storage. Kubernetes, FreeIPA,
Keycloak, Vault and Tier 1 analytics are not prerequisites.

## Main path

1. [Provision the log host](#step-1-provision-the-log-host)
2. [Enable protected collection](#step-2-enable-protected-collection)
3. [Protect and verify retained evidence](#step-3-protect-and-verify-retained-evidence)

The IaC provisions hosts/disks, installs the isolated receiver, configures supported
Linux producers and publishes NAS checkpoints with independent encrypted backups.
Storage preparation, NAS-owned snapshots and live acceptance remain explicit gates;
this asynchronous main path has declared durability limits, not lossless HA.
At Step 3, use [NAS-backed retention](step-3c-nas-archive.md) for a trusted-admin
homelab or [retention locks](step-3d-retention-lock.md) for protection from privileged
deletion. These are alternatives, not mandatory consecutive deployments.

<a id="1-provision-the-bootstrap-receiver"></a>

## Step 1: Provision the log host

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 3
    T0Title["Tier 0 / Control layer"]:3
    block:Infrastructure
      columns 1
      InfraTitle["Existing network devices"]
      Devices["Gateway / switches<br/>Retain local logs"]
    end
    space
    block:PVE
      columns 3
      HostTitle["Existing Proxmox host"]:3
      Template["Approved<br/>Linux template"]
      space
      VM["foundation-log-1<br/>New VM / OS disk"]
      Host["Hypervisor logs<br/>Retain locally"]
      space
      Data[("Local data disk<br/>Allocated, not mounted")]
    end
  end
  Template -- "Clone" --> VM
  VM --> Data
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef heading fill:none,stroke:none,color:#1f2937
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class T0,Infrastructure,PVE boundary
  class T0Title,InfraTitle,HostTitle heading
  class Template,Data data
  class VM control
  class Devices,Host actor
```

Tier 0 is the ownership boundary; **Stage 1** is the deployment capability, not Tier 1.
The main path adds one VM. The [redundant-intake option](step-3b-redundant-intake.md)
adds `foundation-log-2` on a different physical host; it does not automatically provide HA.

Before this VM exists, retain persistent local host logs and supported device buffers
from first boot. Preserve and import/export those records when intake is ready, retaining
their original timestamps and source identity. Record any earlier unbuffered gap.

1. Initialize local inputs from the Tier 0 repository root:

   ```bash
   bash scripts/init-local-files.sh --setup syslog
   ```

2. Edit the local inputs; do not edit examples or store secrets in Git:

   | Tier 0 file | Set |
   | --- | --- |
   | `terraform/deployments/syslog/terraform.tfvars` | Hosts, VMIDs, size, placement and data-disk capacity |
   | `ansible/inventory/hosts.yml` | Matching `foundation_logging` hosts |
   | `ansible/group_vars/syslog.yml` | Matching host IPs and selected host settings |
   | `terraform/common.tfvars` | Tier-local management network; verify independent credentials/state separately |

3. Plan, review all VM/disk changes, then deploy:

   ```bash
   bash scripts/deploy.sh syslog --plan-only
   ```

   After review:

   ```bash
   bash scripts/deploy.sh syslog --terraform-only
   ```

Edit the local files seeded from examples. The starter creates `foundation-log-1`
outside Kubernetes with an OS disk and a separate log-data disk. This Terraform-only
step does not configure the receiver or format/mount that disk. Size storage from measured rate/retention,
not from the starter's example capacity.

**Result:** a reachable log host and allocated data disk, not yet a working collector.
An existing independently operated receiver is also valid.
The single-host bootstrap is not accepted as lossless/HA security logging.
Start collecting before PKI and FreeIPA with the independent trust described below;
record the bootstrap failure window rather than delaying intake for later services.

<a id="2-integrate-protected-intake-and-storage"></a>

## Step 2: Enable protected collection

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 3
  Sources["Other approved producers<br/>Tier 1 / Tier 2 as added"]
  space:2
  block:T0:3
    columns 3
    T0Title["Tier 0 / Control layer"]:3
    block:Infrastructure
      columns 1
      InfraTitle["Existing devices / access"]
      Devices["Gateway / switches<br/>Device-native export"]
      Admin["Authorized security reader"]
    end
    space
    block:PVE
      columns 1
      HostTitle["Proxmox host / management subnet"]
      Host["Hypervisor OS / audit logs"]
      VM["foundation-log-1<br/>syslog-ng / TLS 6514"]
      Records[("Local data disk<br/>JSONL / delivery queues")]
    end
  end
  Sources -- "Scoped TLS" --> VM
  Devices -- "Approved export" --> VM
  Host -- "TLS" --> VM
  VM --> Records
  Admin -- "Read / audit" --> Records
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef heading fill:none,stroke:none,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class T0,Infrastructure,PVE boundary
  class T0Title,InfraTitle,HostTitle heading
  class Sources,Devices,Host,Admin actor
  class VM control
  class Records data
```

1. Follow [receiver setup, Steps 1-3](receiver.md): prepare the data mount,
   [independent producer trust](producer-trust.md) and source catalogue, then run the Tier 0 recipe. It leaves the
   OS logger intact and refuses missing storage or trust inputs.
2. Follow [source preparation and installation](sources.md) in each owning tier,
   including the collector's own OS and audit streams. A listener alone collects nothing.
3. Submit numbered test events and verify source identity, timestamps and offline-readable
   records. Preserve early local records; configure the remaining controls below before acceptance.

| Configure | Required result |
| --- | --- |
| Data volume and queues | Protected mount/quota separate from OS capacity; deliberate flush, crash-recovery and archive-commit semantics |
| Receiver and source identities | Authenticated encrypted submission where supported; producer can append only to its assigned stream |
| Bootstrap trust | Independently provisioned/pinned bootstrap trust and local credentials; do not wait for future PKI or disable certificate verification |
| Network policy | Narrow source-to-intake rules from every tier; no producer route to archive query/admin APIs; bounded rate/message size |
| Raw archive | Tier 0 custody, selected NAS/locked-retention model, independent copies and keys; no producer overwrite/read/delete access |
| Offline format | Portable text/JSON Lines, source catalogue and integrity metadata on the data volume; tested reader kit and separately held recovery keys |
| Backups | Include the separate data disk or use a verified archive-level backup; apply the [backup policy](../../administration/compute/backup-restore.md#backup-policy), not only VM snapshots |
| Readers | Explicit system-administrator/security-reader roles; queries and exports audited; no general developer access to raw evidence |
| Unsupported sources | Document any UDP or unauthenticated first-hop exception and local relay; do not claim end-to-end zero loss |

The default receiver writes local JSON Lines and reliable delivery queues; neither
is independently locked retention. An existing rsyslog receiver can satisfy the same
contract instead; do not run two listeners on the same address/port.
The [design](../../architecture/operations/security-logging.md#durability-and-availability)
owns acknowledgement and failure requirements; neither TCP nor a VIP proves them.
The [software PKI policy](../stage-2-trust/procedures/software-pki.md#decisions-and-recovery-kit)
issues TLS-server certificates only, not producer client-auth certificates. Retain
the independent producer authority until a suitable client-auth profile and renewal
path are qualified. Rotate trust only under a tested continuity plan; Stage 2
completion alone does not replace producer trust.
Keep independently retained evidence outside the collector VM's destruction lifecycle;
rebuilding a receiver must not delete its archive or all recovery copies.

**Result:** approved sources can append evidence and authorized readers can investigate
it without identity services or a cluster. A single collector still has a declared failure risk.

<a id="3-accept-the-security-logging-contract"></a>

## Step 3: Protect and verify retained evidence

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 3
  space:2
  block:T1
    columns 1
    T1Title["Tier 1 / later Stage 5"]
    Search["Scoped analytics<br/>Approved copies only"]
  end
  block:T0:3
    columns 3
    T0Title["Tier 0 / Control layer"]:3
    block:PVE
      columns 1
      HostTitle["Existing Proxmox host"]
      VM["foundation-log-1<br/>Receiver / checkpoint job"]
      Records[("Local data disk<br/>JSONL / queues")]
    end
    space
    block:NAS
      columns 1
      NASTitle["Independent NAS / storage custody"]
      Evidence[("Create-only archive<br/>Chunks / manifests")]
      Snapshots[("NAS-owned snapshots")]
    end
  end
  block:Recovery:3
    columns 3
    RecoveryTitle["Independent recovery / separate credentials"]:3
    Backup["Tier 0 recovery host<br/>logging_recovery group"]
    space
    Copy[("Encrypted restic repository<br/>Independent storage")]
    space:2
    Offline["Offline inspection kit<br/>Separately held keys"]
  end
  VM -- "Append" --> Records
  VM -- "SMB checkpoints" --> Evidence
  Evidence --> Snapshots
  Backup -- "Read-only NAS identity" --> Evidence
  Backup -- "Backup" --> Copy
  Copy -- "Restore" --> Offline
  Evidence -. "Later approved copies" .-> Search
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef heading fill:none,stroke:none,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  class T1,T0,PVE boundary
  class T0Title,T1Title,HostTitle,NASTitle,RecoveryTitle heading
  class VM control
  class Records,Evidence,Snapshots,Copy data
  class NAS,Recovery,Backup,Offline custody
  class Search services
```

The view expands the NAS main path: the NAS is not the receiver's live data disk,
and recovery storage is outside the NAS/collector failure domain. The recovery host
is Tier 0-owned but has independent credentials. Choice B replaces or supplements
the NAS custody boundary with qualified retention-locked storage.

1. Select [A: NAS snapshots/backups](step-3c-nas-archive.md) or
   [B: retention locks](step-3d-retention-lock.md), then establish independent backups
   and reader/writer/custodian credentials. One homelab operator may hold all roles
   under A's trusted-admin assumption; record that boundary explicitly.
2. Test offline inspection, restoration and denied access using the matrix below.
3. Record the achieved [readiness](../readiness.md#readiness-levels) and residual gaps.
   Record NAS checkpoint/snapshot/backup lag and the transport-release limit. Select
   [3b: redundant intake](step-3b-redundant-intake.md) if replicated intake/HA is required;
   the asynchronous main path does not claim that stronger contract.

| Test | Acceptance |
| --- | --- |
| Append and segmented access | Expected source accepted; forged source, cross-namespace reads, overwrite and deletion denied |
| Peak load and bounded outage | Queue/storage headroom remains within the target; exhaustion triggers independent alerts and the declared backpressure policy |
| Tier 1, control cluster and SSO unavailable | Tier 0 intake, evidence investigation and independent recovery still work |
| Only the log-data volume and offline kit survive | Authorized read-only inspection identifies sources and event times without Proxmox, FreeIPA, Vault, PBS or a search backend running |
| Retention and restore | A: writer cannot administer recovery snapshots/backups, trusted-admin risk and checkpoint lag recorded; B: protected versions cannot be deleted or shortened early; independent restore verified in both |

Prove this with numbered synthetic events and source/receiver/archive counts,
not just an open port or a successful Terraform apply. Record unavoidable source
gaps separately from loss of already accepted records.
Follow the [numbered fault and restore drill](../../administration/logging-drill.md).
It supplies synthetic record reconciliation and a project-owned acceptance record;
real faults, retention denials and independent backup restoration still require the
selected receiver/storage implementation. Offline checker tests do not accept this stage.

## IaC locations

| Repository | Location inside that repository | Supplied behavior |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/syslog/](../../../tier-0/terraform/deployments/syslog/) | Receiver VM/disk provisioning only; separate `syslog` state |
| Tier 0 | [ansible/inventory/hosts.yml.example](../../../tier-0/ansible/inventory/hosts.yml.example) and [ansible/group_vars/syslog.yml.example](../../../tier-0/ansible/group_vars/syslog.yml.example) | `foundation_logging` hosts and shared Terraform/Ansible IP inputs |
| Tier 0 | [ansible/playbooks/deployment/foundation-logging.yml](../../../tier-0/ansible/playbooks/deployment/foundation-logging.yml) and [ansible/roles/syslog_ng/](../../../tier-0/ansible/roles/syslog_ng/) | OS baseline and isolated TLS receiver; no filesystem creation, HA or WORM installation |
| Shared | [scripts/deploy.sh](../../../shared/scripts/deploy.sh) and [ansible/roles/baseline/](../../../shared/ansible/roles/baseline/) | Reusable execution and host preparation using Tier 0 inputs |

The [pipeline map](../../reference/logging-pipeline.md#ownership-and-entry-points)
lists the tier-owned authority/archive/backup recipes and Shared forwarding implementation.

Existing generated projects preserve owned `.deployment-setups` and local inventory.
After refresh, deliberately register `syslog` and add its new hosts/IPs before
initialization. Existing baseline-only installations must prepare receiver inputs
before rerunning Ansible; it now fails closed instead of reporting baseline-only success.
Do not move Tier 1 observability state or reuse a VM under two states.

## Capability available

**Result:** protected logging realizes the [evidence design](../../architecture/operations/security-logging.md)
at its recorded readiness, before PKI or identity. Add sources as each tier appears.
Continue with [Stage 2: Cryptographic trust](../stage-2-trust/README.md).
Later [monitoring](../stage-4-control-services/monitoring.md) and
[shared analytics](../stage-5-delivery/analytics.md) extend visibility without replacing the archive.
