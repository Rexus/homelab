# Step 14b: Redundant protected intake

Extend protected intake with a separately placed receiver; qualify sender routing and archive
handoff for the selected failure contract.

<a id="figure-1-independent-receivers"></a>

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

**IaC:** **Figure 1: Independent receivers.** Tier 0 [optional VM definition](../../../tier-0/terraform/deployments/syslog/terraform.tfvars.example),
[inventory](../../../tier-0/ansible/inventory/hosts.yml.example) and
[IP map](../../../tier-0/ansible/group_vars/syslog.yml.example).
Both receivers use the same [receiver recipe](../../../tier-0/ansible/playbooks/deployment/foundation-logging.yml);
sender failover and the stronger durable-handoff contract remain selected integrations.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 14](README.md#step-14-select-the-receiver-topology), when the required failure contract exceeds a single collector.
**Change:** Add independently placed receivers and verify durable handoff, not merely endpoint failover.
**Return:** [Step 15](README.md#step-15-protect-retained-records) to protect the selected receiver topology.
**Design:** [durability and availability](../../01-architecture/11-operations/01-protected-logging.md#durability-and-availability).
**Prerequisites:** functioning intake, independent backup/key custody and supported receiver/storage integration.

## 1. Add capacity and failure domains

Add the second receiver in [Figure 1](#figure-1-independent-receivers).

Enable `log-2` in Tier 0's local `terraform/deployments/syslog/terraform.tfvars`;
add matching inventory/IP entries. Place receivers on distinct physical failure domains.
Add further capacity as demand requires. Receiver count alone does not establish storage redundancy.

## 2. Review and apply the same state root

From Tier 0, provision after reviewing Terraform's displayed plan and entering `yes`:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/deploy.sh syslog --terraform-only
```

Add `--plan-only` for an optional preview. Keep existing hosts and state; no
replacement archive or second Terraform owner is introduced.

In **Tier 0 `ansible/group_vars/syslog.yml`**, remove `syslog_ng_data_uuid`, even an empty value.
Remove it from any other shared `-e`/`--ansible-vars` file too: extra vars override host vars.
Keep the stable data-device selection only if it matches both receivers' attached disks.
Run the [guarded storage action](README.md#step-4-prepare-and-verify-storage) and save each receiver's
printed UUID in **`ansible/inventory/host_vars/<receiver>.yml`**, beside `inventory/hosts.yml`.
Use a separate UUID for each receiver; never apply one global UUID to both filesystems.

Prepare and approve the new receiver's server identity using
[Steps 6–10](README.md#step-6-prepare-the-receiver-key-and-request), reusing the original authority.
Set each receiver's `syslog_ng_tls_cert_src` and `syslog_ng_tls_key_src` to its own protected
controller files in that same inventory-adjacent host file. Existing `ansible/host_vars` files
are supported only when explicitly loaded for one selected host; the inventory-adjacent files
are automatically discovered for this pair. Keep shared CA/CRL paths common where appropriate.
Then configure:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/deploy.sh syslog --ansible-only
```

This installs independent
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
Continue with [Stage 2, Step 15](README.md#step-15-protect-retained-records).
Complete the selected **15a NAS** or **15b locked-retention** path for the resulting topology,
then the fault/restore checks in Step 16. Adding a receiver does not complete archive protection.
