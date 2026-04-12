# Security principles

## Table of contents

- [Baseline posture](#baseline-posture)
- [Identity and access](#identity-and-access)
- [Secrets handling](#secrets-handling)
- [Platform hardening](#platform-hardening)
- [Automation guardrails](#automation-guardrails)

## Baseline posture

This repository assumes:

- zero-trust thinking between zones and systems
- least privilege for users, tokens, and services
- secure-by-default configuration
- rebuild-first or immutable patterns where practical
- public code with private runtime data

## Identity and access

Preferred access methods, in order:

1. short-lived credentials from a trusted secret system
2. scoped API tokens
3. SSH keys with controlled distribution
4. passwords only where bootstrapping requires them

Guidance:

- separate human and machine identities
- avoid shared administrator credentials
- restrict management interfaces to dedicated paths
- rotate trust material after scope or ownership changes

## Secrets handling

Keep secrets out of Git and move shared or long-lived secret material to a
secret system early.

Read more in [Secret strategy](secret-strategy.md).

## Platform hardening

Security expectations for the baseline:

- harden the platform foundation before broad automation use
- isolate management, edge, workload, and sensitive services
- patch and minimize templates before cloning
- prefer SSH keys over password login
- keep administrative actions auditable

## Automation guardrails

- separate image build, provisioning, and configuration concerns
- review plans before applying in shared or sensitive environments
- keep defaults extensive and environment overrides focused
- store significant architectural choices in the decision log
- prefer small, composable changes over broad mixed updates
