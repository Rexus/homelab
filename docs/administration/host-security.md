# Linux Host Security Operations

Maintain the opt-in `linux-host-v1` profile on the selected tier's Linux leaf hosts.
The [deployment procedure](../deployment/foundation/proxmox/host-security.md)
owns supported systems, inputs, configuration boundaries and first-run acceptance.
Keep the approved inputs, external public-key files and independent console
credentials available without Kubernetes, SSO or higher-tier services.

<a id="table-of-contents"></a>

## Find a task

- [How is the accepted host profile reapplied?](#reconcile)
- [How are keys, access or listeners changed?](#change-access-or-services)
- [How is the active policy inspected?](#inspect)
- [What if SSH or firewall access is lost?](#recover-from-access-loss)
- [How is audit delivery checked?](#audit-and-logging)

<a id="reconcile"></a>

## How is the accepted host profile reapplied?

**Work from:** the owning generated tier's **`ansible/` directory** on the approved controller.
**Prerequisites:** the accepted leaf-host profile, external public-key files, working SSH/sudo
and an independently tested console. This profile excludes Proxmox and Kubernetes nodes.

1. Edit the existing private input file from initial deployment,
   `$HOME/.config/homelab/host-security.yml`. Review the pilot host, operator sources,
   complete SSH key lists, service allows, NTP endpoints and keepalived peer addresses.
2. Use the [controller-local render procedure](../deployment/foundation/proxmox/host-security.md#review-and-apply)
   for the actual host OS. Inspect its four output files before changing policy.
   The render role writes on its selected target; the local procedure prevents review files
   from being written onto a managed host.
3. Select that same inventory host and confirm the play targets exactly the accepted pilot.
   `--list-hosts` lists targets without executing the play. [3]

   ```bash
   # Run from the owning tier's ansible/ directory on the execution host:
   # <prefix>-tier-0/ansible/, <prefix>-tier-1/ansible/ or <prefix>-tier-2/ansible/.
   read -r -p "Pilot inventory host matching host_security_hosts: " HOST_SECURITY_HOST
   ansible-playbook playbooks/maintenance/host-security.yml --limit "$HOST_SECURITY_HOST" -e "@$HOME/.config/homelab/host-security.yml" --list-hosts
   ```

4. Retain console access and the prior approved configuration. Apply only after the
   input's console/key/configuration-ownership acknowledgements remain valid:

```bash
# Run from the owning tier's ansible/ directory on the execution host:
# <prefix>-tier-0/ansible/, <prefix>-tier-1/ansible/ or <prefix>-tier-2/ansible/.
ansible-playbook playbooks/maintenance/host-security.yml --limit "$HOST_SECURITY_HOST" -e "@$HOME/.config/homelab/host-security.yml" -e host_security_action=apply -e host_security_acknowledgement=apply-linux-host-v1
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

**Expected:** fresh SSH reconnection, approved firewall access, synchronized time and healthy audit checks.
**Stop:** on any failed gate. Keep the console open and use [access recovery](#recover-from-access-loss)
before adding hosts or retrying policy changes.

<a id="change-access-or-services"></a>

## How are keys, access or listeners changed?

1. Edit only the accepted private input file and its referenced public-key files.
2. Use the operation below, then render/reapply to one pilot using the commands above.
3. Verify a fresh allowed connection and an unrelated denied connection before expanding scope.

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

<a id="inspect"></a>

## How is the active policy inspected?

**Work on:** the managed host's console or approved SSH session. These commands are read-only:

```bash
# Run on the managed Linux host through its approved console or SSH session.
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

<a id="recover-from-access-loss"></a>

## What if SSH or firewall access is lost?

1. Use the independent console; preserve the failed-run output and relevant logs.
2. Restore/correct the last approved configuration using the matching row below.
   Keep temporary access limited to the recovery source.

| Failure | Console Action |
| --- | --- |
| Key or SSH policy | Restore the approved `/etc/ssh/sshd_config` backup and required authorization files; run `sshd -t`, then reload `sshd` on EL or `ssh` on Debian |
| Firewall allowlist | Correct the operator rich rule in `/etc/firewalld/zones/public.xml`; with firewalld running, use `firewall-cmd --check-config`, then `firewall-cmd --reload` [1] |
| Wrong active/default zone | Restore approved NetworkManager/interface assignments and `DefaultZone=public`; inspect every active zone before reloading |
| Time synchronization | Restore approved chrony sources, check DNS/routing/UDP 123, restart the correct distro service, then verify `chronyc tracking` |
| Audit rule load | Preserve existing fragments and logs; correct the profile fragment, run `augenrules --load` and inspect `auditctl -s`/`auditctl -l` |

3. Test a fresh SSH connection and sudo before leaving the console. Correct the private inputs and reconcile once
the independent access path works. Setting `host_security_enabled: false` or removing
the role prevents further apply runs; it does not uninstall policy already applied.
Deliberate retirement restores reviewed SSH/time/firewall policy and removes only
the profile's audit fragment, followed by native validation and acceptance tests.

Do not disable the firewall broadly to regain access. If firewalld is stopped, validate
its on-disk configuration with `firewall-offline-cmd --check-config` before restoring
normal operation; that client is intended for an offline daemon. [2]

<a id="audit-and-logging"></a>

## How is audit delivery checked?

**Work on:** the managed host, then the authorized Tier 0 evidence-reading path.

1. Run the audit inspection commands above and review local capacity/lost-record counts.
2. Generate one approved benign audited event and confirm it reaches protected Tier 0 intake.
3. Investigate missing events without clearing rules, queues, records or loss counters.

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

## References

1. [firewall-cmd configuration validation and reload](https://firewalld.org/documentation/man-pages/firewall-cmd.html).
2. [firewall-offline-cmd scope and validation](https://firewalld.org/documentation/man-pages/firewall-offline-cmd.html).
3. [Ansible playbook target selection and list-only inspection](https://docs.ansible.com/projects/ansible/latest/cli/ansible-playbook.html).
