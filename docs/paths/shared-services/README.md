# Shared services path

## Table of contents

- [Purpose](#purpose)
- [Recommended order](#recommended-order)
- [Path guides](#path-guides)
- [Related docs](#related-docs)

## Purpose

Use this section for the shared services that other paths can consume.

This is where you either deploy the repository reference services or connect
later paths to services you already operate.

Every setup that installs software needs trusted repository/update access
before it can converge. That can be direct egress, an existing mirror, offline
repos, or the cache path in this section.

The shared services are:

- private domain, DNS, and identity
- PKI with an issuing CA and optional offline root CA
- hardware-backed user authentication when operators are ready for it
- edge load balancing and controlled north-south proxying
- cache services for controlled outbound repository/update access
- Vault for shared secrets and later dynamic credentials
- Windows or AD-compatible support when the environment needs it

The identity path is the current reference starting point after repository
access exists, but it is not a hard requirement for every repo user. If you
already have identity, DNS, PKI, or Vault, treat those systems as prerequisites
and configure the other paths to consume them. Use the system-control path for
shared telemetry, syslog, metrics, traces, and log/event search.

## Recommended order

Use this order:

1. Repository/update access, either from existing egress, mirrors, offline
   repos, or the [Cache path](cache.md) when restricted systems need controlled
   software supply access
2. [Identity foundation path](identity.md)
3. [Edge proxy path](edge.md)
4. [Vault foundation deployment](vault.md)
5. [Hardware-backed user authentication](hardware-keys.md), when privileged
   users are ready for it
6. [System control path](../system-control/README.md)
7. [Windows and AD support](windows-support.md), when the environment needs it
8. [Secret strategy](../../security/secret-strategy.md)
9. [Private cloud maturity path](../private-cloud-maturity.md)

## Path guides

- [Identity foundation path](identity.md) - first managed
  private-domain hosts for `FreeIPA`, DNS, and the first PKI path
- [Edge proxy path](edge.md) - shared edge load-balancer pair with horizontal
  expansion for ingress, egress, and service backends
- [Cache path](cache.md) - `Squid` cache pair for controlled outbound
  repository/update access from restricted systems before other software
  installation paths run
- [Hardware-backed user authentication](hardware-keys.md) - optional YubiKey,
  OTP, and PIV hardening after the identity foundation works
- [Windows and AD support](windows-support.md) - optional Windows support
  path after the identity foundation exists
- [Vault foundation deployment](vault.md) - first Vault
  deployment after the identity and PKI layer exists
- [System control path](../system-control/README.md) - telemetry backbone,
  syslog, metrics, traces, and log/event search after Vault

## Related docs

- [Local setup](../../getting-started/local-setup.md)
- [Reader paths](../README.md)
- [Shared services model](../../architecture/shared-services.md)
- [Private cloud maturity path](../private-cloud-maturity.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Architecture overview](../../architecture/overview.md)
