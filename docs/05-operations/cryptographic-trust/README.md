# Cryptographic trust operations

Maintain the selected certificate authority, signing custody and issuer recovery.
Verified repository and artifact publication is an optional Stage 3 addition;
its operating tasks are in [software intake](../software-intake/README.md).

**Related:** [Architecture](../../01-architecture/15-cryptographic-trust/README.md) ·
[Stage 3: Cryptographic trust](../../03-deployment/stage-3-trust/README.md).

| Task | Guide |
| --- | --- |
| Maintain CA policy, renewal and publication | [CA operations](../cryptography/certificate-authority.md) |
| Restore the issuing CA | [Issuer recovery](../cryptography/issuer-recovery.md) |
| Maintain a USB HSM host or key replica | [USB HSM operations](../cryptography/usb-hsm.md) |
| Change an existing signing backend | [Hardware migration](../cryptography/hardware-migration.md) |
| Review custody and security controls | [Security controls](../cryptography/security-controls.md) |
| Trust or rotate the Proxmox API certificate | [Proxmox TLS](../hosts/proxmox-tls.md) |

Use the [CA acceptance matrix](../cryptography/certificate-authority.md#acceptance-evidence)
and selected deployment option; configured components do not prove live acceptance or recovery.
