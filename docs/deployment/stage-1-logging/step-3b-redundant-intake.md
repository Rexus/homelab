# Step 3b: Redundant protected intake

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence), when the required failure contract exceeds a single collector.
**Change:** Add independently placed receivers and verify durable handoff, not merely endpoint failover.
**Return:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence) to record the demonstrated failure envelope.
**Design:** [durability and availability](../../architecture/operations/security-logging.md#durability-and-availability).
**Prerequisites:** functioning intake, independent backup/key custody and supported receiver/storage integration.

## 1. Add capacity and failure domains

Enable `foundation-log-2` in Tier 0's local `terraform/deployments/syslog/terraform.tfvars`;
add matching inventory/IP entries. Place receivers on distinct physical failure domains.
Add further capacity as demand requires. Receiver count alone does not establish storage redundancy.

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  Sources["Approved producers / owning tiers<br/>Durable local queues"]
  block:T0
    columns 3
    T0Title["Tier 0 / Control layer"]:3
    block:PVE1
      columns 1
      Host1Title["Proxmox host A / failure domain A"]
      VM1["foundation-log-1<br/>TLS receiver"]
      Disk1[("Local data disk / queues")]
    end
    space
    block:PVE2
      columns 1
      Host2Title["Proxmox host B / failure domain B"]
      VM2["foundation-log-2 / optional<br/>TLS receiver"]
      Disk2[("Separate local disk / queues")]
    end
  end
  block:Custody
    columns 1
    CustodyTitle["Independently protected archive / selected integration"]
    Commit["Required durable handoff<br/>Not installed by adding a VM"]
    Copies[("Retained copies / independent backup")]
  end
  Sources -- "Selected sender routing" --> VM1
  Sources -- "Selected sender routing" --> VM2
  VM1 --> Disk1
  VM2 --> Disk2
  Disk1 --> Commit
  Disk2 --> Commit
  Commit --> Copies
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef heading fill:none,stroke:none,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,PVE1,PVE2 boundary
  class T0Title,Host1Title,Host2Title,CustodyTitle heading
  class Sources actor
  class VM1,VM2 control
  class Disk1,Disk2,Copies data
  class Custody,Commit custody
```

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
Return to [Stage 1 acceptance](README.md#capability-available).
