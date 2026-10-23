# Step 3b: Redundant protected intake

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence), when the required failure contract exceeds a single collector.
**Change:** Add independently placed receivers and verify durable handoff, not merely endpoint failover.
**Return:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence) to record the demonstrated failure envelope.
**Design:** [durability and availability](../../architecture/operations/security-logging.md#durability-and-availability).
**Prerequisites:** functioning intake, independent backup/key custody and supported receiver/storage integration.

## 1. Add capacity and failure domains

Enable `log-2` in Tier 0's local `terraform/deployments/syslog/terraform.tfvars`;
add matching inventory/IP entries. Place receivers on distinct physical failure domains.
Add further capacity as demand requires. Receiver count alone does not establish storage redundancy.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Sources["Approved producers / owning tiers<br/>Durable local queues"]
  subgraph T0[" "]
    direction TB
    T0Title["Tier 0 / Control layer"]
    subgraph Placement[" "]
      direction LR
      subgraph PVE1["Proxmox host A"]
        direction LR
        VM1["log-1<br/>TLS receiver"]
        Disk1[("Local data disk / queues")]
        VM1 --> Disk1
      end
      subgraph PVE2["Proxmox host B"]
        direction LR
        VM2["log-2 / optional<br/>TLS receiver"]
        Disk2[("Separate local disk / queues")]
        VM2 --> Disk2
      end
      PVE1 ~~~ PVE2
    end
    T0Title ~~~ Placement
  end
  subgraph Custody["Independent archive custody / selected integration"]
    direction LR
    Commit["Required durable handoff<br/>Not installed by adding a VM"]
    Copies[("Retained copies / independent backup")]
    Commit --> Copies
  end
  Sources -->|Selected sender routing| T0
  T0 -->|Selected durable handoff| Custody
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class PVE1,PVE2 boundary
  class Sources actor
  class T0,VM1,VM2 control
  class T0Title,Placement controlHeading
  class Disk1,Disk2,Copies data
  class Custody,Commit custody
```

**IaC:** Tier 0 [optional VM definition](../../../tier-0/terraform/deployments/syslog/terraform.tfvars.example),
[inventory](../../../tier-0/ansible/inventory/hosts.yml.example) and
[IP map](../../../tier-0/ansible/group_vars/syslog.yml.example).
Both receivers use the same [receiver recipe](../../../tier-0/ansible/playbooks/deployment/foundation-logging.yml);
sender failover and the stronger durable-handoff contract remain selected integrations.

## 2. Review and apply the same state root

Run `bash scripts/deploy.sh syslog --plan-only`, review added hosts/disks, then run
`bash scripts/deploy.sh syslog --terraform-only`. Keep existing hosts and state; no
replacement archive or second Terraform owner is introduced. Prepare each new data
mount and its host-specific UUID/TLS inputs using the [receiver guide](receiver.md),
then run `bash scripts/deploy.sh syslog --ansible-only`. This installs independent
receivers, not replication or an immutable archive.

Configure supported sender failover/dual submission, persistent queues, durable
copies and governed retention in project-owned automation. A VIP does not establish
replication or durable acceptance. Record when senders may release an event.

## 3. Verify the declared failure contract

| Test | Acceptance |
| --- | --- |
| Receiver/process/physical host loss | Accepted event sequence survives; upstream queues replay and duplicates are accounted for |
| Power loss or archive-target outage | Flush/commit behavior matches the contract; no upstream release before required durable protection |
| Partition, bounded outage and peak load | Failure domains, backpressure and headroom match the declared envelope; loss is not hidden |
| Independent restore and key recovery | Retained events remain inspectable without Tier 1, normal SSO or the original collector |

Use numbered events and source/receiver/archive counts. Record remaining source
gaps separately from loss of accepted records; do not claim exactly-once delivery.
Return to [Stage 2 acceptance](README.md#capability-available).
