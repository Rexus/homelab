# Windows support

## Table of contents

- [Purpose](#purpose)
- [Position in the repo](#position-in-the-repo)
- [Current design direction](#current-design-direction)
- [Boundaries](#boundaries)
- [Read more](#read-more)

## Purpose

Use this path only when the environment needs Windows support after the
primary identity and DNS layer already exists.

This is a secondary layer. It is not part of the default shared-service
deployment that prepares DNS, PKI, and Vault prerequisites.

## Position in the repo

Use this order:

1. deploy or connect the primary identity path first
2. stabilize identity, DNS, certificate handling, and baseline operations
3. add Windows support only when Windows clients or GPO requirements
   justify it

## Current design direction

The repository direction is:

- keep the default authority design as the primary identity model
- use `FreeIPA` as the current reference direction for that primary authority
- keep the default PKI split as `FreeIPA` and DNS in `identity`, the issuing CA
  in `cryptography`, and the offline root CA in `ceremony`
- treat `Samba AD` as the current Windows support extension
- keep Windows-specific domain join, GPO, and logon handling in this secondary
  path instead of the default identity foundation path

## Boundaries

- do not make the default identity foundation path depend on Windows support
- do not make Vault deployment wait on a Windows-specific layer
- keep Windows support as an optional compatibility and operations layer, not
  the primary repo identity model

## Read more

- [Identity foundation path](identity.md)
- [Vault foundation deployment](vault.md)
- [Private cloud maturity path](../private-cloud-maturity.md)
- [Design decision log](../../decisions/README.md)
