# Hardware-backed user authentication

## Table of contents

- [Purpose](#purpose)
- [Default position](#default-position)
- [Recommended path](#recommended-path)
- [YubiKey OTP path](#yubikey-otp-path)
- [YubiKey PIV path](#yubikey-piv-path)
- [SSH certificate path](#ssh-certificate-path)
- [Credential delegation rule](#credential-delegation-rule)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this guide when you want to harden the identity foundation with hardware
keys such as YubiKeys.

The identity foundation still starts with passwords because the first domain
must be recoverable and easy to validate. Hardware keys are the recommended
operator hardening path once `FreeIPA`, DNS, and PKI are working.

## Default position

The default domain design is:

```text
FreeIPA + Kerberos = core identity authority
PKI = user, host, and service trust anchor
hardware keys = recommended user hardening
passwords = available by default and reduced over time
```

Keep the security model simple:

| Principle | Applied here |
| --- | --- |
| hardware key = identity proof | The token proves the operator's identity. It does not replace the root CA, but it becomes the strongest user root of trust. |
| Kerberos = internal SSO | Kerberos stays the internal login fabric, with delegation limited to explicit service needs. |
| SSH = short-lived or non-delegatable | Admin SSH should move toward OpenSSH user certificates, scoped keys, or credentials that cannot be reused by services. |
| assume every host can be compromised | A compromised host should not expose reusable user passwords, unrestricted tokens, or broad delegation paths. |

Do not make hardware keys a day-one dependency for the repo. Make them the
first hardening step for admins and other privileged users.

## Recommended path

Use these stages:

| Stage | What changes | Use it when |
| --- | --- | --- |
| password | default FreeIPA user password and Kerberos login | first deployment and break-glass access |
| OTP hardware token | password plus OTP from a YubiKey or compatible token | you want a practical MFA step without smart-card rollout |
| PIV smart card | certificate-backed login with the private key on the YubiKey | you want PKI-backed user authentication and stronger phishing resistance |
| SSH user certificate | short-lived OpenSSH certificate issued after user authentication | you want SSH access without reusable credentials on target hosts |

Keep at least one tested break-glass account and recovery process before you
enforce stronger authentication on all administrators.

## YubiKey OTP path

Use this when you want the simplest YubiKey-backed FreeIPA hardening path.
FreeIPA supports OTP token workflows and a YubiKey-specific token enrollment
command where the required tooling is available.[1]

Typical flow:

1. Verify normal password login for the user.
2. Enroll a YubiKey OTP token for the user from the FreeIPA CLI or Web UI.
3. Set the user's authentication type to require OTP.
4. Test login through an SSSD-enrolled Linux client.
5. Document token replacement and lost-token recovery before broader rollout.

Example CLI shape:

```bash
kinit admin
ipa otptoken-add-yubikey --owner alice
ipa user-mod alice --user-auth-type otp
```

Use the exact command variants supported by the FreeIPA version in the target
distribution. Test this on one non-admin user before applying it to operators.

## YubiKey PIV path

Use this when you want certificate-backed login where the user's private key
stays on the hardware key.

YubiKey PIV exposes a smart-card interface where private key operations happen
on the device through standards such as PKCS#11.[2][3] Red Hat IdM supports
smart-card authentication with user certificates issued by the IdM CA or by an
external CA trusted by IdM.[4]

Typical flow:

1. Decide which CA issues user authentication certificates.
2. Generate the PIV key on the YubiKey, normally in slot `9a`.
3. Create a CSR from the YubiKey-held key.
4. Issue the user certificate from the chosen CA.
5. Add the certificate to the FreeIPA user.
6. Configure enrolled Linux clients for smart-card authentication.
7. Test login, lockout, revocation, and lost-key recovery with one pilot user.

Do not start by importing private keys into user hardware keys unless the
certificate policy explicitly allows it. Prefer keys generated on the device.

## SSH certificate path

For SSH, prefer short-lived OpenSSH user certificates over Kerberos/GSSAPI SSH
login when the environment is ready.

Use `FreeIPA` as the identity and policy source:

| Step | Role |
| --- | --- |
| user authentication | the user proves identity with Kerberos, OTP, PIV, or another approved path |
| certificate issuance | an SSH CA workflow signs the user's public key for minutes or hours |
| host trust | managed hosts trust the SSH user CA key |
| SSH login | the target host accepts the short-lived user certificate |

This keeps reusable user passwords and delegatable Kerberos credentials away
from target hosts.

Current boundary: `FreeIPA` and SSSD provide centralized SSH public key
management for users and hosts.[5] OpenSSH user certificates are a separate
SSH certificate model where hosts trust an SSH CA key and the user presents a
signed SSH certificate.[6] Treat this as a stronger hardening path built on
top of the identity foundation, not as the same thing as uploaded SSH public
keys.

## Credential delegation rule

Avoid designs where users give reusable passwords to services so the service
can act as them later.

Prefer these patterns:

| Need | Preferred pattern |
| --- | --- |
| Linux login | Kerberos through SSSD, then hardware-backed OTP or PIV for users |
| service-to-service auth | service principals, keytabs, certificates, or Vault-issued credentials |
| web login | OIDC/SAML through the access layer when that path exists |
| admin access | personal identities, short-lived SSH certificates, hardware-backed auth, sudo policy, and audit logs |

The goal is not to remove every password immediately. The goal is to keep
passwords from becoming the normal delegated credential between systems.

## Read more

- [Identity foundation path](identity.md)
- [Windows and AD support](windows-support.md)
- [Shared services model](../../architecture/shared-services.md)
- [Secret strategy](../../security/secret-strategy.md)

## References

1. [FreeIPA OTP design and token workflows](https://www.freeipa.org/page/V4/OTP)
2. [Yubico PIV smart card overview](https://www.yubico.com/authentication-standards/smart-card/)
3. [YubiKey PIV Tool introduction](https://docs.yubico.com/software/yubikey/tools/pivtool/Introduction.html)
4. [Red Hat IdM smart-card authentication](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_smart_card_authentication/managing_smart_card_authentication)
5. [Red Hat IdM SSH public key management](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_idm_users_groups_hosts_and_access_control_rules/managing-public-ssh-keys-for-users-and-hosts)
6. [OpenSSH certificate key specification](https://www.openssh.org/specs.html)
