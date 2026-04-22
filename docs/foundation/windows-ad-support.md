# Windows and AD support

## Table of contents

- [Purpose](#purpose)
- [Position in the repo](#position-in-the-repo)
- [Current design direction](#current-design-direction)
- [Boundaries](#boundaries)
- [Read more](#read-more)

## Purpose

Use this path only when the environment needs Windows support after the domain
foundation already exists.

This is a secondary layer. It is not part of the default foundation deployment
that prepares DNS, PKI, and Vault prerequisites.

## Position in the repo

Use this order:

1. deploy the domain foundation first
2. stabilize identity, DNS, certificate handling, and baseline operations
3. add Windows or AD support only when Windows clients or GPO requirements
   justify it

## Current design direction

The repository direction is:

- keep the default authority design as the primary identity model
- use `FreeIPA` as the current reference direction for that primary authority
- treat `Samba AD` as the current Windows support extension
- keep Windows-specific domain join, GPO, and logon handling in this secondary
  path instead of the default domain foundation path

## Boundaries

- do not make the default domain foundation path depend on Windows support
- do not make Vault deployment wait on a Windows-specific layer
- keep Windows support as an optional compatibility and operations layer, not
  the primary repo identity model

## Read more

- [Domain foundation path](foundation-and-domain-path.md)
- [Vault foundation deployment](vault-foundation-deployment.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Design decision log](../decisions/README.md)
