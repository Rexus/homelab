# Household and team access

Use existing client networks, identity groups and application permissions. Tier ownership is
not a user role, a Wi-Fi network or an automatic authorization grant. The
[network design](../architecture/networking/README.md),
[identity design](../architecture/identity/README.md) and
[service SSO gate](../deployment/stage-5-identity/procedures/service-sso.md) own those contracts.

## Contents

- [Household devices](#household-devices)
- [Team roles](#team-roles)
- [Join and leave](#join-and-leave)
- [Remote administration](#remote-administration)

## Household devices

1. Place ordinary workstations, family devices, guests and IoT equipment in explicitly selected
   Tier 2 client networks. Map the actual VLANs/ports/SSIDs to zones through the
   [UniFi procedure](../deployment/foundation/procedures/unifi-zones.md).
2. Permit DNS/time and selected application endpoints. Deny hypervisor/BMC, directory
   administration, storage administration, original logs and cluster-control access.
   Scope printer/discovery exceptions to the required client/device groups, not every VLAN.
3. Test the ordinary experience while Kubernetes, FreeIPA, Keycloak and Tier 1 are unavailable.
   Router/DHCP/bootstrap DNS/time and ordinary Internet access must not need those later services.
   Applications requiring SSO can be unavailable during an IdP outage; record this explicitly.

Keep browser/application access separate from infrastructure access. A family account or
developer laptop does not become a privileged workstation by joining the same identity directory.
Existing gateway, DHCP/DNS and Wi-Fi configuration remains operator-owned; this kit does not install
a household router or automatically configure every appliance.

## Team roles

Record exact group names and actual permissions in project administration. The following is a
starting responsibility matrix, not a supplied cross-product role synchronizer:

| Role | Permitted scope | Excluded authority |
| --- | --- | --- |
| Infrastructure administrator | Explicit Tier 0 administration and audited recovery duties | Offline root/key custody unless separately authorized |
| Platform operator | Selected Tier 1 delivery/diagnostics and service administration | Tier 0 credentials and original-log mutation |
| Developer | Selected source projects, job results, lab namespaces and application-log views | Shared infrastructure provisioning, other teams' Secrets or raw security archives |
| Employee/family member | Selected applications through their normal authentication interface | CI, cluster administration and management networks |
| Guest/IoT device | Explicit network/application exceptions | Default east-west, identity administration or Control access |
| Recovery/log custodian | Separately approved restore or evidence-reading duties | Routine developer authority does not imply this role |

The direct infrastructure-CI exception changes this matrix: administrators of the trusted
GitLab project and its control/hosting plane are Tier 0 authorities. Record that accepted
[trust decision](../deployment/stage-9-development/procedures/infrastructure-runner.md#step-1-accept-direct-ci-trust)
instead of describing that project as ordinary Tier 1 application automation.

## Join and leave

1. Enroll the account in the directory using its native administration interface. Assign only
   reviewed groups. Configure each application's group/role mapping; a successful OIDC login
   alone grants no permission. Verify one permitted action and an unrelated denied action.
2. For developers, bind only the intended source project, namespace, runner and
   [approved log scope](../deployment/stage-8-observability/protected-log-search.md).
   Keep shared administrative accounts and credentials out of routine work.
3. On departure or role reduction, remove memberships/disable the account, revoke application
   sessions and refresh tokens, revoke personal/service tokens and SSH/VPN/device access, then
   test an existing session as well as a new login. Rotate shared secrets if they were exposed.

Directory disablement does not itself revoke every application session, API token, cached group
mapping or SSH key. Record the product-specific revocation path and accepted delay in the
service's local runbook. Preserve identity/audit records according to retention policy.

## Remote administration

Select and qualify a supported VPN/access gateway before enabling remote administration; no
universal VPN installer is supplied. Do not publish Proxmox, BMC, Vault or Kubernetes admin APIs
to the Internet as a shortcut. Scope the remote entry to an authorized workstation/jump path,
then separately authorize the destination and action. Keep device enrollment and lost-device
revocation in the local access runbook.

Test denied access from ordinary users, guests, another client subnet and IPv6, plus VPN loss
and independent console recovery. Preserve host/gateway/security audit records for these actions;
query privileges must not allow original-log deletion. Remote entry is not required for a first
local-only deployment; mark it not selected until its actual implementation and checks exist.
