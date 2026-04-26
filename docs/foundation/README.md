# Foundation

## Table of contents

- [Purpose](#purpose)
- [Recommended order](#recommended-order)
- [Foundation guides](#foundation-guides)
- [Related docs](#related-docs)

## Purpose

Use the foundation section for the first platform layers you build after local
setup is ready.

This is where you establish:

- the domain foundation layer
- the first identity and DNS services
- the first PKI path with an issuing CA and an optional offline root CA
- optional Windows or AD support later when you need it
- the first Vault deployment as the secret-platform foundation

## Recommended order

Use this order:

1. [Domain foundation path](foundation-and-domain-path.md)
2. [Vault foundation deployment](vault-foundation-deployment.md)
3. [Windows and AD support](windows-support.md), when the environment needs it
4. [Secret strategy](../security/secret-strategy.md)
5. [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)

## Foundation guides

- [Domain foundation path](foundation-and-domain-path.md) - first managed
  foundation hosts for `FreeIPA`, DNS, and the first PKI path
- [Windows and AD support](windows-support.md) - optional Windows support
  path after the domain foundation exists
- [Vault foundation deployment](vault-foundation-deployment.md) - first Vault
  deployment after the domain foundation layer exists

## Related docs

- [Local setup](../getting-started/local-setup.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Architecture overview](../architecture/overview.md)
