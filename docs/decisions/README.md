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

## Review triggers

Review relevant decisions when changes affect:

- repository structure
- trust boundaries
- secret handling
- supported platforms
- automation workflow ownership
