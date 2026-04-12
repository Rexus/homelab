# Proxmox network prerequisites

## Table of contents

- [Purpose](#purpose)
- [Design intent](#design-intent)
- [Required external capabilities](#required-external-capabilities)
- [Suggested network segments](#suggested-network-segments)
- [Responsibility boundary](#responsibility-boundary)
- [Validation checklist](#validation-checklist)

## Purpose

Proxmox can present bridges and VLAN-tagged networks to guests, but it does not
replace the external network design needed to make segmentation work. This
repository assumes switching, routing, and firewalling already support the
chosen design.

## Design intent

Use the private-cloud network model described in the architecture overview.

Read more in [Architecture overview](../../docs/architecture/overview.md).

## Required external capabilities

The surrounding network should provide:

- VLAN-aware switching
- routing between allowed segments
- firewall policy between trust zones
- gateway or router support for north-south and east-west traffic
- DNS and DHCP aligned with the selected segmentation model

## Suggested network segments

```mermaid
flowchart LR
    Router[Router or firewall]
    Switch[Managed switch]
    Mgmt[Management VLAN]
    Edge[Edge or DMZ VLAN]
    Shared[Shared services VLAN]
    LabA[Lab A VLAN]
    LabB[Lab B VLAN]
    Secure[Restricted VLAN]
    Storage[Storage VLAN]
    Proxmox[Proxmox bridges and guests]

    Router --> Switch
    Switch --> Mgmt
    Switch --> Edge
    Switch --> Shared
    Switch --> LabA
    Switch --> LabB
    Switch --> Secure
    Switch --> Storage
    Mgmt --> Proxmox
    Edge --> Proxmox
    Shared --> Proxmox
    LabA --> Proxmox
    LabB --> Proxmox
    Secure --> Proxmox
    Storage --> Proxmox
```

Keep the model simple at first. The important part is predictable separation,
not maximum network complexity.

## Responsibility boundary

Current scope of this repository:

- consume existing Proxmox bridges and VLAN-backed networks
- place guests into the intended segments
- document the network assumptions clearly

Current out-of-scope areas:

- programming the external router or firewall
- managing switch VLAN configuration
- creating DHCP, DNS, or upstream routing policies automatically

Future integrations may automate parts of this boundary, but they are not
assumed today.

## Validation checklist

Before running automation, confirm:

- VLANs exist end-to-end on the external network
- routed paths exist only where intended
- firewall rules reflect trust boundaries
- management access is restricted to trusted sources
- guest networks can reach only the services they are meant to reach
