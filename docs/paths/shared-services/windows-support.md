# Windows support

## Table of contents

- [Purpose](#purpose)
- [Position in the repo](#position-in-the-repo)
- [Current design direction](#current-design-direction)
- [Support modes](#support-modes)
- [Boundaries](#boundaries)
- [Read more](#read-more)
- [References](#references)

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
- use `FreeIPA` with Kerberos as the current reference direction for that
  primary authority
- keep the default PKI split as `FreeIPA` and DNS in `identity`, the issuing CA
  in `cryptography`, and the offline root CA in `ceremony`
- treat Samba and Windows support as compatibility layers
- keep Windows-specific domain join, GPO, and logon handling in this secondary
  path instead of the default identity foundation path

## Support modes

Use the smallest Windows support layer that solves the real requirement.

| Mode | Use it when | Notes |
| --- | --- | --- |
| FreeIPA Kerberos interoperability | Windows clients only need access to selected Kerberos-backed services, such as Samba shares | This can avoid a full Windows domain for small environments, but test the exact client behavior carefully. |
| Samba AD extension | Windows clients need domain join, GPO, or native Windows domain behavior | Keep users and groups anchored to the primary identity model where possible. |

The blog walkthrough linked below is useful as a practical example of Rocky
Linux, FreeIPA, Samba, and Windows Kerberos interoperability. Treat it as a lab
pattern to validate, not as the default identity foundation deployment.[1]

FreeIPA and Red Hat documentation also point out Samba and IdM limitations,
especially around Windows clients, NTLM behavior, and domain-member support.
Use those limitations as the reason this remains an optional path.[2][3][4]

## Boundaries

- do not make the default identity foundation path depend on Windows support
- do not make Vault deployment wait on a Windows-specific layer
- keep Windows support as an optional compatibility and operations layer, not
  the primary repo identity model
- do not move primary identity ownership into Windows support unless the whole
  environment intentionally changes authority model

## Read more

- [Identity foundation path](identity.md)
- [Hardware-backed user authentication](hardware-keys.md)
- [Vault foundation deployment](vault.md)
- [Private cloud maturity path](../private-cloud-maturity.md)
- [Design decision log](../../decisions/README.md)

## References

1. [Configuring Rocky Linux, FreeIPA and Samba for Kerberos Support on Windows Clients](https://lachlan.nz/blog/rocky-freeipa-samba-windows/)
2. [FreeIPA Samba file server integration](https://www.freeipa.org/page/Howto/Integrating_a_Samba_File_Server_With_IPA.html)
3. [FreeIPA NTLMSSP Samba note](https://www.freeipa.org/page/Howto/Integrating_a_Samba_File_Server_With_IPA/NTMLSSP)
4. [Red Hat, setting up Samba on an IdM domain member](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_external_red_hat_utilities_with_identity_management/setting-up-samba-on-an-idm-domain-member)
