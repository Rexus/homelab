# Design decision log

## Table of contents

- [Purpose](#purpose)
- [Current decisions](#current-decisions)
- [Review triggers](#review-triggers)

## Purpose

Use this log to keep architectural decisions concise and durable. Each decision
should record the choice, rationale, consequences, status, and review trigger.

## Current decisions

| ID | Decision | Status | Rationale | Consequence | Review trigger |
| --- | --- | --- | --- | --- | --- |
| D-001 | Use Packer, Terraform, and Ansible as the core workflow | Accepted | Keeps image build, provisioning, and configuration clearly separated | Tool boundaries stay explicit | If one tool is replaced or merged |
| D-002 | Keep the repository public and commit examples only | Accepted | Enables sharing without publishing secrets | Users must create private operational copies | If secret handling or distribution model changes |
| D-003 | Treat Proxmox as the current reference platform, not the repository identity | Accepted | Keeps the baseline reusable for other private-cloud foundations at homelab or small-datacenter scale | Provider-specific guidance lives under `docs/platforms/` | If a second platform is added or the default platform changes |
| D-004 | Treat this repository as a curated upstream reference, not the destination for operational changes | Accepted | Reduces accidental publication of live configuration and secrets | Users continue development in private forks, mirrors, or local copies | If the repository ownership or collaboration model changes |
| D-005 | Prefer secure defaults and segmented network design | Accepted | Reduces accidental overexposure and drift | Some environments require explicit exceptions | If operational needs require broader trust |
| D-006 | Use modular deployment building blocks with logical compute and storage abstractions | Accepted | Keeps deployment interfaces reusable, separates compute size from storage placement and capacity, and hides platform-specific details behind modules and mappings | Environment inputs stay stable while implementation details remain replaceable | If the module interface model or workload abstractions change |
| D-007 | Use an enterprise-grade Linux operating system for managed general-purpose instances | Accepted | Gives managed workloads a durable and predictable operating system strategy without coupling the architecture to one vendor, distribution, version, or image source | Platform guides can document the current implementation while the architectural decision remains portable | If the baseline guest operating system strategy changes |
| D-008 | Keep identity foundation deployment separate from Vault foundation deployment | Accepted | The repository starts from clean Proxmox and network prerequisites only, so the first foundation stage should not assume shared services such as DNS, PKI, or Vault already exist | Early automation stays focused on the first managed identity foundation layer, and Vault keeps its own Terraform environment, inventory, and playbook once those prerequisites are ready | If the foundation scope or early shared-service order becomes the repository default |
| D-009 | Use an edge load balancer in `external_edge` for early north-south traffic and keep a separate internal cluster proxy for later Kubernetes ingress | Accepted | Keeps the early infrastructure edge separate from later cluster-native ingress while preserving a stable network and service model as the platform grows | Architecture and service guides should treat the `external_edge` edge load balancer as an early prerequisite; implementation choices stay in the foundation setup docs rather than the architecture model | If the edge placement model or the later cluster ingress model changes |
| D-010 | Keep the identity foundation path focused on the default authority design and treat Windows or AD support as a secondary extension | Accepted | Keeps the default path focused on identity, DNS, PKI, and Vault prerequisites while avoiding Windows-specific complexity in the first deployment | Identity foundation docs should stay focused on the default authority path; Windows support should have its own path; the current reference direction is FreeIPA as the primary authority with Samba AD as the Windows support extension | If the primary authority model or the Windows support approach changes |
| D-011 | Use `FreeIPA` in `identity` plus a split PKI with an issuing CA in `cryptography` and an offline root CA in `ceremony` for the default identity foundation | Accepted | Keeps the first authority path clear and Linux-native while separating online identity and issuing services from offline root-CA custody | Foundation examples should default to `2` `FreeIPA` hosts in `identity`, `1` issuing CA host in `cryptography`, and an optional offline root CA host in `ceremony`; later HSM backing remains an upgrade path, not a day-one requirement | If the authority platform, PKI split, or HSM-default model changes |
| D-012 | Treat identity, PKI, Vault, and observability as shared services that can be deployed here or consumed from existing infrastructure | Accepted | Keeps the repository modular for clean builds, existing environments, isolated labs, and multi-project use | Reader paths live under `docs/paths/shared-services/` when they create or consume the shared-service backbone; later paths should not deploy duplicate identity or secret systems unless isolation requires it | If shared services become mandatory or a different service ownership model is chosen |
| D-013 | Use OpenTelemetry as the observability backbone with dedicated backends for live health, metrics, traces, logs, and archive | Accepted | Keeps telemetry routing generic while allowing practical reference implementations | The observability path should use generic VM roles and place product choices in service variables, tags, and guide text; sources should send through telemetry gateways or security collectors instead of writing directly to backends | If the observability stack or routing model changes |
| D-014 | Use `FreeIPA` with constrained Kerberos and hardware-backed user identity proof | Accepted | Keeps the first domain recoverable while defining a clear security model: hardware keys prove operator identity, Kerberos provides internal SSO, SSH should use short-lived OpenSSH certificates or non-delegatable credentials, and hosts are treated as compromisable | Identity docs should keep passwords as the default bootstrap path, prefer Kerberos and PKI for long-term trust, avoid credential delegation, and document YubiKey, compatible hardware-key, and SSH certificate hardening separately | If the default authentication model changes or hardware-backed auth becomes mandatory |

## Review triggers

Review relevant decisions when changes affect:

- repository structure
- trust boundaries
- secret handling
- supported platforms
- automation workflow ownership
