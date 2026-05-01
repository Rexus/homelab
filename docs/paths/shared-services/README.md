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

The shared services are:

- private domain, DNS, and identity
- PKI with an issuing CA and optional offline root CA
- Vault for shared secrets and later dynamic credentials
- observability, syslog, metrics, traces, and log/event search
- Windows or AD-compatible support when the environment needs it

The identity path is the current reference starting point, but it is not a
hard requirement for every repo user. If you already have identity, DNS, PKI,
Vault, or telemetry, treat those systems as prerequisites and configure the
other paths to consume them.

## Recommended order

Use this order:

1. [Identity foundation path](identity.md)
2. [Vault foundation deployment](vault.md)
3. [Observability path](../observability.md)
4. [Windows and AD support](windows-support.md), when the environment needs it
5. [Secret strategy](../../security/secret-strategy.md)
6. [Private cloud maturity path](../private-cloud-maturity.md)

## Path guides

- [Identity foundation path](identity.md) - first managed
  private-domain hosts for `FreeIPA`, DNS, and the first PKI path
- [Windows and AD support](windows-support.md) - optional Windows support
  path after the identity foundation exists
- [Vault foundation deployment](vault.md) - first Vault
  deployment after the identity and PKI layer exists
- [Observability path](../observability.md) - telemetry backbone, syslog,
  metrics, traces, and log/event search path after Vault

## Related docs

- [Local setup](../../getting-started/local-setup.md)
- [Reader paths](../README.md)
- [Shared services model](../../architecture/shared-services.md)
- [Private cloud maturity path](../private-cloud-maturity.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Architecture overview](../../architecture/overview.md)
