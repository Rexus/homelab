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
| D-003 | Treat Proxmox as the current reference platform, not the repository identity | Accepted | Keeps the baseline reusable for other homelab or small datacenter foundations | Provider-specific guidance lives under `platforms/` | If a second platform is added or the default platform changes |
| D-004 | Treat this repository as a curated upstream reference, not the destination for operational changes | Accepted | Reduces accidental publication of live configuration and secrets | Users continue development in private forks, mirrors, or local copies | If the repository ownership or collaboration model changes |
| D-005 | Prefer secure defaults and segmented network design | Accepted | Reduces accidental overexposure and drift | Some environments require explicit exceptions | If operational needs require broader trust |
| D-006 | Use modular deployment building blocks with logical compute and storage abstractions | Accepted | Keeps deployment interfaces reusable, separates compute size from storage placement and capacity, and hides platform-specific details behind modules and mappings | Environment inputs stay stable while implementation details remain replaceable | If the module interface model or workload abstractions change |
| D-007 | Use an enterprise-grade Linux operating system for managed general-purpose instances | Accepted | Gives managed workloads a durable and predictable operating system strategy without coupling the architecture to one vendor, distribution, version, or image source | Platform guides can document the current implementation while the architectural decision remains portable | If the baseline guest operating system strategy changes |
| D-008 | Bootstrap a dedicated Vault node before broader platform deployment | Accepted | Shortens the exposure window for bootstrap-only secret handling and makes the secret platform part of the initial foundation | The first managed VM, inventory, and bootstrap playbook must reserve an early path for Vault installation and operator initialization work | If a different secret platform or bootstrap order becomes the repository default |

## Review triggers

Review relevant decisions when changes affect:

- repository structure
- trust boundaries
- secret handling
- supported platforms
- automation workflow ownership
