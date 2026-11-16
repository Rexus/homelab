# Proxmox access and hardening tasks

**Working repository:** `<prefix>-tier-0` for policy/inputs; host actions run in the
Proxmox GUI or an authorized host shell. Keep independent console access available.
**Why:** [security principles](../../01-architecture/01-background/01-principles.md) and
[network enforcement](../../01-architecture/05-networking/01-firewall-policy.md).

**First use from bootstrap:** complete [host-management setup](README.md) to initialize the local files,
register existing hosts and test SSH/Ansible before running host recipes.

<a id="table-of-contents"></a>

## Find the task

- [How is management access restricted?](#how-is-management-access-restricted)
- [How is automation access reviewed?](#how-is-automation-access-reviewed)
- [How are host Secure Boot and TPM enabled?](#host-boot-security)
- [How is host health checked before a change?](#how-is-host-health-checked-before-a-change)
- [What must pass before routine automation?](#what-must-pass-before-routine-automation)

<a id="purpose"></a>
<a id="baseline-posture"></a>
<a id="host-management-access"></a>

## How is management access restricted?

1. Record the management subnet, approved administrator source ranges, emergency
   console path and required cluster/storage traffic in the project network plan.
2. Apply the [foundation firewall procedure](../../03-deployment/foundation/network/firewall.md)
   using the selected gateway and Proxmox backend. Establish the administrative
   allow rules before enabling a restrictive policy. [1]
3. Keep the console open. From an approved administrator workstation, test a new
   SSH session and verified HTTPS to the private Proxmox API/UI.
4. From an unapproved source, confirm those paths are denied. Keep host management
   off public edge paths; use the approved remote-entry/jump path when required.
5. Record the tests. If legitimate access fails, restore the prior rule through the
   console and investigate before closing the maintenance window.
6. Under **Datacenter > Permissions > Two Factor**, enroll human administrator accounts using
   an accepted TOTP/WebAuthn method and retain recovery codes independently. Test a separate new
   login before ending the original session. UI/API-login MFA does not protect SSH or API tokens;
   keep their key/scoped-token controls. No future IdP is needed for local Proxmox enrollment. [2]

**Expected:** approved administration and cluster traffic work; unrelated networks
cannot administer hosts. Enabling a firewall alone does not establish this result.

<a id="api-and-identity"></a>

## How is automation access reviewed?

1. In **Datacenter > Permissions**, review the selected user/group, API token and
   the effective roles on VM, storage and network paths.
2. Compare them with the [API permission contract](../../03-deployment/foundation/proxmox/api-access.md).
   Distinguish ordinary provisioning from Tier 0 template-upload authority.
3. Test the required plan/read operation using that token and verified TLS. A
   privilege-separated token needs both the user's and token's effective rights.
4. Remove obsolete grants only after the intended operation passes and independent
   recovery remains available. Rotate or retire credentials through the
   [secret runbook](../03-cryptography/secret-handling.md), not through source control.

**Expected:** one scoped automation identity per accepted authority; ordinary
workloads and general runners have no host-administration credentials.

<a id="host-boot-security"></a>

## How are host Secure Boot and TPM enabled?

Follow [physical host boot security](proxmox-host-boot-security.md) for firmware preparation,
the supported signed Proxmox boot chain, TPM 2.0 activation and controller-run verification.
This is part of [Foundation Step 11](../../03-deployment/foundation/proxmox/step-11-host-security.md).
Guest vTPMs and USB HSMs keep their separate identities; enabling the server TPM does not
configure guest TPMs or enroll a disk-encryption key.

<a id="host-and-cluster-hygiene"></a>

## How is host health checked before a change?

1. On each affected Proxmox host, run these read-only checks:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   pveversion -v
   pvesm status
   systemctl --failed
   timedatectl status
   journalctl -p err -b --no-pager
   ```

2. On a clustered host, also inspect quorum:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   pvecm status
   ```

3. Resolve failed storage, unexpected services, time errors or quorum loss before
   updating the host. Use the [maintenance runbook](maintenance.md) for version
   changes and [update access](../02-software-intake/host-updates.md) for approved package sources.
4. Check certificate expiry/trust with the [TLS runbook](proxmox-tls.md). Confirm
   early host/security events still reach the protected logging path.

**Stop:** degraded quorum, unavailable live storage, unexplained errors or no
independent recovery path. Do not combine backend, network and upgrade experiments
into the same routine change.

<a id="before-automation"></a>

## What must pass before routine automation?

| Check | Required result |
| --- | --- |
| Access | Approved SSH/API path works; unauthorized sources are denied |
| API | Intended scoped token can perform the required operation over verified TLS |
| Compute | Actual nodes, storage and bridges match the selected inputs |
| Recovery | Independent console, original inputs/state, backups and keys are usable |
| Host boot/key hardware | Signed boot and physical TPM checks pass where supported; exceptions and any enrolled consumer's recovery method are recorded |
| Logs and time | Time is synchronized and protected events are available |

Return to [template operations](templates/template-lifecycle.md) or the selected deployment
only after these checks pass. The table is an acceptance gate, not an installer.

## References

1. [Proxmox firewall rules and backend behavior](https://github.com/proxmox/pve-docs/blob/master/pve-firewall.adoc).
2. [Proxmox two-factor methods and recovery](https://github.com/proxmox/pve-docs/blob/master/pveum.adoc#two-factor-authentication).
