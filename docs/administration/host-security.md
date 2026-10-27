# Linux Host Security Operations

Maintain the opt-in `linux-host-v1` profile on the selected tier's Linux leaf hosts.
The [deployment procedure](../deployment/foundation/procedures/host-security.md)
owns supported systems, inputs, configuration boundaries and first-run acceptance.
Keep the approved inputs, external public-key files and independent console
credentials available without Kubernetes, SSO or higher-tier services.

## Table of Contents

- [Reconcile](#reconcile)
- [Change Access or Services](#change-access-or-services)
- [Inspect](#inspect)
- [Recover from Access Loss](#recover-from-access-loss)
- [Audit and Logging](#audit-and-logging)

## Reconcile

From the consuming generated tier's `ansible/` directory, rerun the same role
through the maintenance recipe, with the same tested access acknowledgements:

```bash
ansible-playbook playbooks/maintenance/host-security.yml --limit pilot-1 \
  -e @/home/operator/private/host-security.yml \
  -e host_security_acknowledgement=apply-linux-host-v1
```

Reconciliation can install missing packages, replace owned configuration, reload
SSH/firewalld and restart chrony. It is not a read-only inspection or an upgrade
window. A chrony restart can step time under the selected startup policy.
Plan around sensitive applications. Use `host_security_action=render` for review;
apply in Ansible check mode is rejected.

The recipe checks source/user/listener access before changes, reconnects after SSH
and firewall activation, verifies time synchronization and checks audit status.
Investigate a failed run before expanding scope; earlier changes may already be
active. No rollback is automatic and a health failure does not undo configuration.

## Change Access or Services

| Change | Procedure |
| --- | --- |
| Rotate an operator key | Add the new external public-key file to the same user's list; reconcile, test a separate new-key connection, then remove the old file and reconcile again |
| Remove an SSH user | Keep the current automation/recovery users; remove the retired user from the approved list; `AllowUsers` denies it even if its old managed key file remains |
| Move the controller/jump path | Add the new observed source CIDR, reconcile from the old path, verify the new path, then remove the old CIDR from the new path |
| Change SSH port | A separate console migration is required; the profile refuses to change the port of its current session |
| Add/change a listener | Add every required source/port/protocol allow before deploying the listener; reconcile, test allowed and denied sources |
| Retire a listener | Stop the service, remove its allows, reconcile and retest denial |
| Change NTP source | Verify reachability first; replace approved servers, reconcile, inspect synchronization and clock impact |
| Add/change a keepalived peer | Supply each remote peer source in `host_security_vrrp_peers` as a `/32` or `/128`, reconcile serially, then test single VIP ownership and failover |
| Adopt SSO/SSH CA, routing or containers | Review ownership and compatibility first; existing firewall/service exceptions are replaced, and broader policies may be refused |

Public-key files are controller inputs. The role batches all keys for a user in
one exclusive authorization operation. Files in users' home `.ssh/` directories
remain on disk but are not used by this profile. SSH and chrony backups are created
when their owned configuration changes; keep protected independent copies as well.

Run this profile after any cache/VIP service recipe that manages firewalld: those
recipes can re-add their broader service rules. Reconciliation replaces them with
the approved source-scoped port and VRRP rules. Keep peer inputs per host; do not
restore an unrestricted protocol allow to make failover pass. Omitting peers on a
running or enabled keepalived host is rejected before configuration changes.

## Inspect

These commands read the current host state from its console or approved session:

```bash
sudo sshd -T
sudo firewall-cmd --get-default-zone
sudo firewall-cmd --list-all-zones
chronyc tracking
chronyc sources -v
sudo auditctl -s
sudo auditctl -l
sudo ausearch -k host_security_ssh -ts recent
```

Confirm `public` has target `DROP`, only the approved rich-rule allows, and no broad
services, ports, source zones or alternate interface zones. Also inspect persistent
configuration and reboot behavior: runtime success does not prove boot persistence.
Rerun scoped service allow/deny tests for IPv4 and IPv6 whenever policy changes.
Outbound traffic remains allowed; enforce outbound destination restrictions at the
approved network boundary.

## Recover from Access Loss

Use the independent console. Record the failed run and preserve relevant logs
before changing policy. Restore the last approved configuration, keeping temporary
access limited to the recovery source.

| Failure | Console Action |
| --- | --- |
| Key or SSH policy | Restore the approved `/etc/ssh/sshd_config` backup and required authorization files; run `sshd -t`, then reload `sshd` on EL or `ssh` on Debian |
| Firewall allowlist | Correct the operator rich rule in `/etc/firewalld/zones/public.xml`; run `firewall-offline-cmd --check-config`, then `firewall-cmd --reload` |
| Wrong active/default zone | Restore approved NetworkManager/interface assignments and `DefaultZone=public`; inspect every active zone before reloading |
| Time synchronization | Restore approved chrony sources, check DNS/routing/UDP 123, restart the correct distro service, then verify `chronyc tracking` |
| Audit rule load | Preserve existing fragments and logs; correct the profile fragment, run `augenrules --load` and inspect `auditctl -s`/`auditctl -l` |

Do not disable the firewall broadly to regain access. Test a fresh connection and
sudo before leaving the console. Correct the private inputs and reconcile once
the independent access path works. Setting `host_security_enabled: false` or removing
the role prevents further apply runs; it does not uninstall policy already applied.
Deliberate retirement restores reviewed SSH/time/firewall policy and removes only
the profile's audit fragment, followed by native validation and acceptance tests.

## Audit and Logging

The role retains the OS journal/logger and auditd's existing log, rotation and
plugin configuration. It neither stops logging services nor redirects the audit
file away from an existing forwarder. The supplied rules observe selected account,
configuration, time and privilege activity; they are not a complete audit benchmark.

Review storage/rotation thresholds in the existing auditd configuration, backlog,
lost records and local disk capacity alongside
[security logging operations](security-logging.md). Watch for audit `never,task`
suppression rules and immutable policy; the role refuses adoption until those are
resolved through an explicit operator decision. It never silently clears them.

The role loads rules only when its persistent fragment changes. If runtime audit
rules were changed out of band, restore all approved persistent fragments with
`sudo augenrules --load` and verify the resulting rules. Do not clear the kernel
rule set or reset lost counters to make an acceptance check pass. Verify a known
local event also reaches the separately commissioned protected receiver.
