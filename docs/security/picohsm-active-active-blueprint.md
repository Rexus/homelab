# Pico HSM Active-Active Blueprint

## Table of contents

- [Purpose](#purpose)
- [Target topology](#target-topology)
- [What active-active means here](#what-active-active-means-here)
- [What this gives you](#what-this-gives-you)
- [What it does not give you](#what-it-does-not-give-you)
- [Where this fits with Vault and OpenBao](#where-this-fits-with-vault-and-openbao)
- [Network planning](#network-planning)
- [Host roles](#host-roles)
- [Tools](#tools)
- [Reader setup path](#reader-setup-path)
- [Repository automation path](#repository-automation-path)
- [Software-only lab track](#software-only-lab-track)
- [Provisioning and replication flow](#provisioning-and-replication-flow)
- [Operational model](#operational-model)
- [Comparison to enterprise HSM designs](#comparison-to-enterprise-hsm-designs)
- [When to use fewer or more devices](#when-to-use-fewer-or-more-devices)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this guide to plan a practical open-source HSM design with:

- `2` active hosts
- `2` Pico HSM devices per host
- `1` offline backup Pico HSM

Use this after [HSM getting started](hsm-planning-and-comparison.md) when you
already know you want the repository's concrete USB HSM deployment pattern.

This is a good fit when you want:

- a serious homelab HSM pattern
- an open-source-first PKCS#11 workflow
- active-active service continuity at the application layer
- a design that teaches real operator habits for later PKI or signing systems

This guide is the real-world USB HSM example for the repository. It shows what
this pattern solves, where it helps, and where its limits still matter.

## Target topology

Use this as the reference topology:

```mermaid
flowchart TD
  Client[Clients or internal callers]
  LB[HAProxy or Envoy]

  subgraph HostA[Host A]
    GW1[Signer or gateway A1]
    GW2[Signer or gateway A2]
    H1[Pico HSM A1]
    H2[Pico HSM A2]
    GW1 --> H1
    GW2 --> H2
  end

  subgraph HostB[Host B]
    GW3[Signer or gateway B1]
    GW4[Signer or gateway B2]
    H3[Pico HSM B1]
    H4[Pico HSM B2]
    GW3 --> H3
    GW4 --> H4
  end

  Backup[Offline backup Pico HSM]

  Client --> LB
  LB --> GW1
  LB --> GW2
  LB --> GW3
  LB --> GW4
```

Figure: four active Pico HSM replicas behind stateless gateways, plus one
offline recovery device.

Repository recommendation:

- keep one gateway process pinned to one local Pico HSM
- avoid pretending the four HSMs are one native cluster
- keep the backup Pico HSM offline except during restore tests or controlled
  backup refresh

This is the default reference shape, not a hard platform limit. The repository
IaC can scale this pattern down or up by changing the `vm_instances` map in the
HSM lab environment, while keeping the same role names and network references.

## What active-active means here

In this design, "active-active" means:

- the same approved exportable key material is restored onto four independent
  Pico HSM devices
- four stateless gateway instances can serve requests in parallel
- the load balancer routes traffic only to healthy gateways whose local HSMs
  have the expected key inventory

It does not mean:

- native HSM clustering
- automatic multi-device replication
- shared sessions across devices
- one write instantly appearing on all HSMs

This is active-active at the service layer, not at the HSM fabric layer.

## What this gives you

This improves a homelab meaningfully:

- one host can fail and service can continue on the other host
- one Pico HSM can fail and the remaining replicas can keep serving traffic
- parallel request capacity is better than a single-device design
- you can practice controlled key rollout, restore, failover, and recovery
- you get a credible hardware-backed PKCS#11 platform without enterprise HSM
  cost

## What it does not give you

Be explicit about the limits:

- no native clustered HSM guarantees
- no built-in quorum replication between the four active devices
- no automatic consistency management
- no compliance-equivalent story to major enterprise network HSM platforms

If you need those guarantees, this design is the wrong target. Use a real
enterprise HSM platform or a vendor-supported native HSM cluster model.

## Where this fits with Vault and OpenBao

For this repository, use this Pico HSM design in one of these ways:

- later PKI, signing, or bootstrap protection
- recovery or bootstrap protection for `Vault A` in a `Vault A` plus `Vault B`
  Transit auto-unseal design

Do not treat this topology as the direct Day 1 Vault Community Edition seal
path.

Open-source platform guidance:

- `Vault Community Edition`: use Shamir first, then use Pico HSM for later
  bootstrap or PKI hardening
- `Vault Community Edition` later hardening: use Pico HSM to protect recovery or
  bootstrap material for `Vault A`, while `Vault B` uses Transit auto-unseal
- `OpenBao`: if native open-source PKCS#11 seal is a hard requirement, evaluate
  OpenBao as a separate platform decision

## Network planning

Keep the network simple and deliberate.

Start with
[Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md).
Use the same zone keys here so the diagram, the Terraform variables, and the
host placement all point back to one shared network model.

Use these repository network references in this pattern:

| Zone key | In this pattern | Typical IaC use |
| --- | --- | --- |
| `management` | operator SSH, automation, metrics, helper access | helper VMs and admin reachability |
| `service` | proxy-to-gateway and internal caller traffic | most gateway VMs |
| `hsm` | optional restricted helper or recovery path | helper VMs when you split them from management |
| `dmz` | optional ingress-facing proxy path | proxy VMs |

Use this separation model:

```mermaid
flowchart LR
  subgraph Mgmt["management"]
    Ops[Operators and automation]
  end

  subgraph DMZ["dmz"]
    Proxy[1-3 proxy VMs]
  end

  subgraph Service["service"]
    Gateway[1-8 gateway VMs]
  end

  subgraph HSM["hsm"]
    Helper[0+ helper or recovery VMs]
  end

  Pico[Pico HSM devices<br/>host-local USB only]

  Ops --> Proxy
  Ops --> Gateway
  Ops --> Helper
  Proxy --> Gateway
  Helper -. restricted recovery or rollout path .-> Gateway
  Gateway -. local USB access only .-> Pico
```

Figure: proxies and gateways can use routed networks, but Pico HSM access stays
host-local and never becomes a network service.

Use at least these paths in the live environment:

| Network | Purpose | Should carry |
| --- | --- | --- |
| `management` | admin SSH, configuration, metrics | operator access, automation |
| `service` | client traffic to gateways | TLS or mTLS application traffic |
| `hsm` or restricted recovery path | optional maintenance and custody workflows | restore drills, backup refresh, helper access |
| `dmz` | optional ingress-facing proxy traffic | reverse proxy or edge entry only |

Design rules:

- do not expose raw USB devices over the network
- do not expose a generic PKCS#11 endpoint directly to callers
- keep HSM access host-local through OpenSC or equivalent middleware
- expose only the gateway or signer service to the rest of the environment
- keep the offline backup device off the network and disconnected by default
- protect gateway traffic with TLS, and prefer mTLS for internal callers when
  the service is security-critical

## Host roles

Use these roles:

| Role | Count | Purpose |
| --- | --- | --- |
| proxy VMs | `1-3` | health checks and traffic distribution |
| gateway or signer VMs | `1-8` | run signer or PKI application instances |
| helper VMs | `0+` | bootstrap, restore, recovery, or operator ceremony support |
| local Pico HSM devices | usually `1` per gateway process | keep one device local to one signer or gateway instance |
| offline backup device | `1` | recovery and backup validation only |

Guidance:

- do not attach one Pico HSM to multiple hosts
- keep each active device local to one host
- keep one source-of-truth HSM for provisioning and rollout

## Tools

Use open-source tools wherever possible.

Recommended host-side tools:

- `pcscd` for smart-card service access
- `OpenSC` for PKCS#11 integration and utilities
- `pkcs11-tool` for object inspection, import, export, wrap, and restore
- `openssl` for key and certificate validation
- `p11tool` when useful for extra PKCS#11 inspection and testing
- `HAProxy` or `Envoy` for app-aware load balancing
- `systemd` to keep gateway processes deterministic

Useful verification commands:

```bash
opensc-tool -l
pkcs11-tool --list-slots
pkcs11-tool --list-objects --pin <PIN>
openssl x509 -in cert.pem -text -noout
```

For Pico HSM, prefer standard middleware and tools instead of inventing custom
host tooling unless you have a very specific application need.

## Reader setup path

Use this order when you want to build the lab from this repository:

1. Read [HSM getting started](hsm-planning-and-comparison.md) and decide
   whether you are learning the pattern first or protecting real keys now.
2. Provision the host layout from
   [`terraform/environments/hsm-lab/`](../../terraform/environments/hsm-lab/README.md).
   Fill in `network_zones` and `vm_instances` so your proxy, gateway, and
   helper VMs map cleanly back to the shared architecture reference.
3. Apply the baseline host configuration from
   [`ansible/playbooks/site.yml`](../../ansible/playbooks/site.yml).
4. Use the hardware-backed track when you have Pico HSM devices ready to attach
   to the intended gateway and helper hosts.
5. Use the software-only track when you want to rehearse the same service
   pattern with a software PKCS#11 implementation such as `SoftHSM` first [1].
6. Validate local PKCS#11 access on every gateway or helper host before adding
   any load balancer or signer traffic.
7. Run the provisioning and replication flow in this guide.
8. Test host loss, device loss, and restore from the offline backup before you
   treat the pattern as trusted.

This keeps the topology, host naming, and operator flow stable even when you
start without hardware and switch to Pico HSM later.

## Repository automation path

Use the repository automation in layers:

| Layer | What the repository can automate | What stays manual |
| --- | --- | --- |
| [`terraform/environments/hsm-lab/`](../../terraform/environments/hsm-lab/README.md) | proxy, gateway, and helper VMs with shared `network_zones` references and stable role tagging | physical USB attachment, passthrough choices, and token insertion |
| [`ansible/playbooks/site.yml`](../../ansible/playbooks/site.yml) | baseline OS preparation and shared host hardening | PKCS#11 middleware installation, signer process setup, and token initialization |
| [`ansible/roles/vault/`](../../ansible/roles/vault/) | later Vault host configuration when you use the `Vault A` plus `Vault B` pattern | direct Pico HSM gateway management and key ceremony steps |

Treat IaC here as host and service preparation, not as a replacement for HSM
custody, wrap-key handling, or device-specific rollout checks.

## Software-only lab track

If you do not have hardware yet, keep the same host layout and rehearse the
same service pattern with a software PKCS#11 token such as `SoftHSM` [1].

Good uses for this track:

- learn the PKCS#11 tooling and inventory checks
- validate load balancer health checks and gateway routing
- rehearse service rollout, failover, and drift detection
- keep CI or throwaway lab runs close to the real host topology

Do not treat this as equivalent to hardware-backed custody. It does not replace
physical device handling, removable backup media, or the operator discipline
that comes with real HSMs.

When hardware arrives, keep the host layout and service wiring the same and
replace the local software token on each host with the intended Pico HSM
attachment and key ceremony.

## Provisioning and replication flow

Use one-way controlled replication.

1. Choose one active device as the source-of-truth HSM.
2. Initialize the source device with the intended PIN, labels, domains, and key
   policy.
3. Generate or import the production keys on the source device.
4. Create the DKEK or wrap-key material and split custody as required.
5. Export the approved objects under wrap.
6. Restore the wrapped objects onto the other three active devices.
7. Restore the same approved objects onto the offline backup Pico HSM.
8. Verify IDs, labels, and required objects on all five devices.
9. Only then place the four active gateways into service.

Treat this as release management for keys, not as organic cluster sync.

## Operational model

Run the service as stateless request handling.

Safe routing rules:

- route requests only to healthy gateway instances
- mark a gateway unhealthy if its local HSM is missing required objects
- fail over only among nodes whose inventories are verified equal
- keep sessions local to the gateway and local HSM pair

Safe change rules:

- make key changes on the source-of-truth HSM
- export under wrap
- restore to peers
- verify inventories
- then switch or broaden traffic

Operational risks to plan for:

- key drift between replicas
- partial rollout of new key inventory
- shared operator credentials across too many hosts
- losing both active and backup custody material at the same time

## Comparison to enterprise HSM designs

This Pico HSM pattern is valuable, but it is not the same as enterprise network
HSM architecture.

| Topic | Pico HSM active-active pattern | Enterprise network HSM |
| --- | --- | --- |
| Cost | low | high |
| Tooling | open-source-heavy | vendor-heavy |
| Key replication | orchestrated by you | often supported by vendor workflow |
| HA semantics | service-layer failover | usually stronger built-in HA features |
| Compliance story | practical, but limited | much stronger formal certification posture |
| Learning value | excellent | excellent, but expensive |

This is the right way to frame the gain:

- for a homelab, it is a serious improvement over one USB HSM on one host
- it builds operator skill that transfers to larger environments
- it gives you real hardware-backed custody and failure handling
- it does not give you enterprise HSM guarantees just because four devices are
  active

## When to use fewer or more devices

Use this rough sizing rule:

| Shape | Good fit |
| --- | --- |
| `1` active plus `1` offline backup | learning, offline CA, very small lab |
| `2` active plus `1` offline backup | small service or small PKI |
| `4` active across `2` hosts plus `1` offline backup | serious homelab active-active design |
| more than `4` active USB HSMs | only when measured throughput or separation-of-duty needs justify the extra complexity |

For most homelabs, `4` active plus `1` offline backup is already the upper end
of what is worth operating before enterprise network HSM tradeoffs start to look
more attractive.

## Read more

- [HSM getting started](hsm-planning-and-comparison.md)
- [Vault HSM hardening options](vault-hsm-hardening-options.md)
- [Vault bootstrap](../getting-started/vault-bootstrap.md)

## References

1. [SoftHSM](https://www.softhsm.org/) (accessed 2026-04-19)
