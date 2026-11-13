# Key-protection options

The choice is the key-custody boundary, not a compulsory sequence of products.
Software providers, USB devices and hardware security modules (HSMs) can expose cryptographic functions
to an issuer or signing service, but provide different isolation and recovery properties.
The parent [cryptography design](README.md) defines the supplied services;
the [variant map](../02-organization/README.md#selected-design) relates this choice to other independent decisions.

## Table of contents

- [Completed designs](#completed-designs): [A: Software](#a-software), [B: Single USB](#b-single-usb),
  [C: Replicated USB gateways](#c-replicated-usb-gateways), [D: Network HSM](#d-network-hsm)
- [Options A-D](#options-a-d)
- [Selection criteria](#selection-criteria)
- [Assurance requirements](#assurance-requirements)
- [Interfaces and limits](#interfaces-and-limits)
- [References](#references)

## Completed designs

Each view places a selected online-key provider behind the same consumer-facing
issuer or signing interface. Offline root custody remains a separate choice under
the [certificate hierarchy](../03-reference-platform.md#certificate-trust). Dashed
connections represent separately authorized recovery transfers, not normal network
dependencies. Application-state backups accompany the selected key-recovery method.

### A: Software

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 1
    T0Title["Tier 0 / platform key protection"]
    block:Host
      columns 2
      HostTitle["Authorized service host"]:2
      Service["Issuer / signing service"]
      Provider["Software key store<br/>or software provider"]
    end
    Recovery["Offline recovery custody / independently held backups<br/>Not an online root CA"]
  end
  Service --> Provider
  Recovery -.-> Provider
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,Host control
  class T0Title,HostTitle controlHeading
  class Provider,Recovery custody
```
*Figure: The signing service uses a software key provider, with independent offline custody for recovery.*

Key custody shares the host's compromise boundary. This arrangement has one
application/provider path; recovery from host loss uses independently retained
key and application backups. Software interface rehearsal does not establish
hardware isolation. [1]

### B: Single USB

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 2
    T0Title["Tier 0 / platform key protection"]:2
    block:Host
      columns 1
      HostTitle["Authorized host / local USB"]
      Service["Issuer / signing service"]
    end
    Provider["Single local USB HSM"]
    Recovery["Offline recovery custody / independently held backups<br/>Not an online root CA"]:2
  end
  Service --> Provider
  Recovery -.-> Provider
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,Host control
  class T0Title,HostTitle controlHeading
  class Provider,Recovery custody
```
*Figure: The signing service uses one local USB HSM, with independent offline custody for recovery.*

The local token supplies the key-custody boundary; the host still owns application
state and permitted requests. Host or device loss interrupts this single path.
Recovery depends on the selected device's supported backup policy and retained
application state, not on the presence of a replacement device alone. [2][3]

### C: Replicated USB gateways

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 2
    T0Title["Tier 0 / replicated USB service"]:2
    block:HostA
      columns 1
      GatewayA["Provider / host A<br/>Private authenticated endpoint"]
      TokenA["Local USB HSM"]
    end
    block:HostB
      columns 1
      GatewayB["Providers / additional hosts<br/>Private authenticated endpoints"]
      TokenB["One local USB HSM per host"]
    end
    Recovery["Offline backup custody / key and wrapping material"]:2
  end
  GatewayA --> TokenA
  GatewayB --> TokenB
  Recovery -.-> HostA
  Recovery -.-> HostB
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0 control
  class T0Title controlHeading
  class HostA,HostB replicas
  class TokenA,TokenB,Recovery custody
```
*Figure: Each provider host uses its own USB HSM. Dashed transfers come from independent offline
custody; the devices do not replicate keys or application state through this arrangement.*

The service routes operations through a supported application integration; each
gateway accesses only its local token. Service-level failover depends on validated
routing, compatible key material and surviving capacity. Key replication is
separately governed: the tokens provide no native cluster or automatic key-state
synchronization. Recovery custody remains independent of all active hosts.
The [service detail](04-usb-hsm.md) separates restricted PKCS#11 remoting from a
policy-enforcing signing API. Separate frontend VMs or Tier 1/2 runtimes are not
prerequisites for device access. Keep replicated keys within one qualified device
family unless cross-vendor transfer and recovery have been separately verified.

### D: Network HSM

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 2
    T0Title["Tier 0 / network key service"]:2
    block:Host
      columns 1
      Service["Authorized service host<br/>Issuer / signing service"]
      Client["Vendor client"]
    end
    block:Appliances
      columns 1
      PartitionA["Selected HSM partition"]
      PartitionB["Optional vendor HA member"]
    end
    Recovery["Offline recovery custody / backups and domain material"]:2
  end
  Service --> Client
  Client --> PartitionA
  Client --> PartitionB
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,Host control
  class T0Title controlHeading
  class Appliances boundary
  class PartitionA,PartitionB,Recovery custody
```
*Figure: The signing service accesses selected network HSM partitions through a vendor client; an additional
HA member is optional and recovery custody is separate.*

Custody resides in the selected appliance partitions, with client authorization
and management permissions separated. A second member is optional; replication
and failover follow the selected product's supported HA model. Independent backup
and recovery material remain necessary for loss beyond the active members. [4]
The [network HSM detail](05-network-hsm.md) defines the client, partition and failure
contracts.

<a id="purpose"></a>
<a id="use-and-scale-matrix"></a>
<a id="how-to-read-the-matrix"></a>

## Options A-D

The four figures change where key custody sits while retaining the issuer or
signing service's outward contract. Compare the compromise boundary first, then
the acceptable outage and independent restore. An existing approved provider can
satisfy any applicable option.

| Option | Design shape | Suitable purpose | Limit and operating responsibility |
| --- | --- | --- | --- |
| A: Software | Application keystore or software PKCS#11 provider; SoftHSM is an example [1] | Accepted software-custody deployment or interface rehearsal | Host access can expose key material; not hardware isolation |
| B: Single USB | One authorized host and one local device, with a separate recovery arrangement | Offline custody, low-concurrency issuer or signing service | Host/device loss interrupts service; availability depends on restore |
| C: Shared USB providers | Independent device hosts, restricted remoting and separately governed backups | Shared key operations with qualified reconnect/failover | Application sessions and approved key replication remain separate; not a native HSM cluster |
| D: Network HSM | Authorized clients use appliance partitions through the vendor client/HA model | Shared hardware service with product-supported partitions and resilience | Separate management, client trust, backup and vendor compatibility obligations |

B and C are both hardware-backed options. Pico HSM and YubiHSM 2 are device
examples, not interchangeable security or certification claims. Their documented
PKCS#11 and backup capabilities require validation against the selected firmware,
mechanisms and consumer. [2][3] The [USB gateway design](04-usb-hsm.md) expands C;
the [network HSM design](05-network-hsm.md) expands D.

<a id="start-with-the-right-problem"></a>
<a id="certification-and-reality"></a>

## Selection criteria

| Requirement | Architectural implication |
| --- | --- |
| Which key is protected? | Root, issuing, code-signing and seal keys have different consumers and custody requirements |
| Host compromise | A hardware boundary may reduce extraction risk; an authorized compromised client can still misuse allowed operations |
| Availability | Define the tolerated outage and failure domains; two devices alone do not establish HA |
| Scale | Measure the actual algorithms, request concurrency and client path; developer count is not a throughput guarantee |
| Recovery | Supported export/backup policy, wrapping material, custodians and independent restore must match the selected product |
| Compliance | Verify the exact model, firmware, operating mode and required certification; price or product family is not evidence |

Historical price and team-size estimates are not design guarantees.
The simplest variant meeting the selected risk and availability requirements is valid.

<a id="repository-path"></a>

<a id="maturity-and-stages"></a>

## Assurance requirements

The selected design defines permitted operations, key-extraction boundaries,
failure tolerance and independent recovery. A change of provider requires review
of those properties and consumer compatibility; A-D are not an upgrade ladder.
Software rehearsal can validate protocols but cannot demonstrate hardware isolation.

<a id="what-usb-hsm-active-active-solves"></a>
<a id="read-more"></a>

## Interfaces and limits

PKCS#11 compatibility does not establish support for every algorithm, key attribute,
backup mechanism or application integration. C uses application-level failover;
D follows the selected vendor's client/partition model. For example, Luna's HA
model groups compatible partitions; this is not equivalent to a generic HTTP proxy. [4]

Certificate signing and secret-service unseal are separate integrations:
[seal design](06-vault-seal.md). Procedure selection belongs in
[the trust-stage decision](../../03-deployment/stage-3-trust/README.md#step-1-prepare-issuer-and-key-custody).

## References

Sources checked 2026-10-09.

1. [SoftHSM project](https://www.softhsm.org/)
2. [Pico HSM capability map](https://docs.picokeys.com/picohsm/features/)
3. [YubiHSM PKCS#11 module](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html)
4. [Thales Luna redundancy and reliability](https://thalesdocs.com/gphsm/luna/7/docs/network/Content/Product_Overview/redundancy_and_reliability.htm)
