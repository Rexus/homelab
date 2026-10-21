# Network HSM design

Option D from [key protection](hsm-selection.md) separates the cryptographic
provider from issuer/signing hosts. Authorized clients access selected appliance
partitions through the vendor's supported client and transport.

## Components and boundaries

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 2
    T0Title["Tier 0 / protected cryptography"]:2
    block:Runtime
      columns 1
      Consumers["Authorized runtime<br/>Issuer / signing service"]
      Client["Vendor client / partition identity"]
    end
    block:Appliances
      columns 1
      H1["Private appliance<br/>Selected HSM partition"]
      H2["Optional vendor HA member"]
    end
    Admin["Offline recovery custody / separate administration<br/>Approved backups, wrapping and domain material"]:2
  end
  Consumers --> Client
  Client --> H1
  Client --> H2
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,Runtime control
  class T0Title controlHeading
  class Appliances boundary
  class H1,H2,Admin custody
```

This is not the USB gateway service with different hardware. A network appliance
can change client libraries, connection trust, partition ownership, recovery media
and the failover mechanism. Luna, for example, provides client HA groups over
compatible partitions; synchronization has product-specific conditions. [1]

| Design concern | Required property |
| --- | --- |
| Consumer access | Only approved clients and key operations; network reachability is not authorization |
| Administration | Separate management and custody permissions, owned by Tier 0 for platform-wide keys |
| Availability | Selected failure domains and vendor-supported replication/HA behavior |
| Recovery | Independent approved backups and wrapping/domain material; HA is not backup |
| Offline root | Separate custody; an online partition is not an air-gapped root |

An existing enterprise HSM can satisfy this design without creating USB gateway
VMs. Physical/network appliance provisioning is not implemented by the repository.
Cloud-hosted providers require the separately assessed
[external key-custody boundary](../service-boundaries.md#key-custody-and-cloud-boundaries).

<a id="maturity-and-realization"></a>

## Failure and recovery contract

The selected application must support its partition's mechanisms and access model.
The design specifies behavior for member/client loss, rejected operations and
independent restore. No certification is inferred from the word HSM.

The [network HSM procedure](../../deployment/stage-2-trust/step-1c-network-hsm.md)
owns installation and acceptance steps.

## References

1. [Thales Luna redundancy and reliability](https://thalesdocs.com/gphsm/luna/7/docs/network/Content/Product_Overview/redundancy_and_reliability.htm) (checked 2026-10-08)
