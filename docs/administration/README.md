# Administration

Operate an existing platform using its selected architecture and verified local
runbooks. Maintenance is separate from first deployment and does not imply
automatic upgrades or recovery procedures.

Use the selected [domain design](../architecture/README.md#technical-domains) as
the operating contract and retain its [acceptance evidence](../deployment/readiness.md).
A routine change that alters trust, placement, interfaces
or recovery dependencies requires a design review before execution.

| Task | Guide |
| --- | --- |
| Reconcile supported host configuration | [Ansible recipes](ansible-recipes.md) |
| Recover independently of hosted services | [Recovery](recovery.md) |
| Test VM backup and restore | [Backup foundation](compute/backup-restore.md) |
| Maintain hypervisor access and posture | [Hardening](compute/hardening.md), [update access](compute/update-access.md) |
| Establish API trust and transition to platform PKI | [Proxmox TLS](compute/proxmox-tls.md) |
| Publish, test and promote image revisions | [Template lifecycle](compute/template-lifecycle.md) |
| Add cluster capacity and reserve worker pools | [Kubernetes pools](compute/kubernetes-pools.md) |
| Maintain signing gateways and key replicas | [USB HSM maintenance](cryptography/usb-hsm.md) |
| Maintain CA policy, publication and recovery | [Certificate authority operations](cryptography/certificate-authority.md) |
| Change an existing issuer's signing custody | [Hardware migration](cryptography/hardware-migration.md) |
| Verify security evidence, reader scopes and durability | [Security logging](security-logging.md) |
| Exercise collector failures and independent restoration | [Logging drill](logging-drill.md) |
| Protect bootstrap and runtime secrets | [Secret strategy](secret-handling/strategy.md), [Ansible Vault](secret-handling/ansible-vault.md) |

Record approvals, schedules, restore evidence and rollback procedures in the
owning project's administration folder. Use [deployment guides](../deployment/README.md)
for installation, not as a substitute for service-specific upgrade instructions.
