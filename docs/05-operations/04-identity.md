# Identity and access operations

Use existing client networks, identity groups and application permissions. Tier ownership is
not a user role, a Wi-Fi network or an automatic authorization grant. The
[network design](../01-architecture/05-networking/README.md),
[identity design](../01-architecture/09-identity/README.md) and
[service SSO gate](../03-deployment/stage-5-identity/procedures/service-sso.md) own those contracts.

**Install:** [Stage 5: Identity](../03-deployment/stage-5-identity/README.md).
**Configuration:** retain the owning tier's accepted directory/federation inputs from that
procedure; application roles and gateway policy remain with their respective owners.
For service loss, use [directory recovery](06-resilience/recovery/freeipa-ca.md) or
[Keycloak recovery](06-resilience/recovery/keycloak.md).

In **`<prefix>-tier-0/`**, the principal configuration locations are:

| Scope | Configuration and workflow |
| --- | --- |
| FreeIPA hosts and directory | `ansible/group_vars/foundation.yml`, inventory and original foundation state; [directory procedure](../03-deployment/stage-5-identity/procedures/freeipa.md) |
| Keycloak federation and service clients | `ansible/group_vars/control_applications.yml` and its protected credential inputs; [identity-provider procedure](../03-deployment/stage-5-identity/procedures/keycloak.md) |
| Human Kubernetes CLI and namespace access | `ansible/group_vars/kubernetes_human_access.yml`; [client/RBAC reconciliation](../03-deployment/stage-5-identity/procedures/kubernetes-cli-access.md) |

<a id="contents"></a>

## Find a task

- [How is a family, guest or IoT device connected?](#household-devices)
- [Which permissions belong to each role?](#team-roles)
- [How is a person granted application access?](#join-and-leave)
- [How is a departing person's access revoked?](#revoke-access)
- [How is remote administration enabled?](#remote-administration)

<a id="household-devices"></a>

## How is a family, guest or IoT device connected?

**Work on:** the UniFi Network administration interface, then an ordinary test client.
**Prerequisites:** approved VLAN/zone plan and independent router/DHCP/DNS/time services.

1. Place ordinary workstations, family devices, guests and IoT equipment in explicitly selected
   Tier 2 client networks. Map the actual VLANs/ports/SSIDs to zones through the
   [UniFi procedure](../03-deployment/foundation/network/unifi.md).
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

**Expected:** selected applications and ordinary Internet use work; management APIs remain denied.
**Stop/rollback:** if a client reaches Control or loses required basic connectivity, undo the
last reviewed port/SSID/network assignment or rule through the gateway's independent admin path.

<a id="team-roles"></a>

## Which permissions belong to each role?

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
[trust decision](../03-deployment/stage-9-development/procedures/infrastructure-runner.md#step-1-accept-direct-ci-trust)
instead of describing that project as ordinary Tier 1 application automation.

<a id="join-and-leave"></a>

## How is a person granted application access?

**Work on:** the authorized directory, IdP and each application's administration interface.
**Prerequisites:** an approved role/scope, accepted SSO and independently retained recovery access.

1. Enroll the account in the directory using its native administration interface. Assign only
   reviewed groups. Configure each application's group/role mapping; a successful OIDC login
   alone grants no permission. Verify one permitted action and an unrelated denied action.
2. For developers, bind only the intended source project, namespace, runner and
   [approved log scope](../03-deployment/stage-8-observability/step-4b-protected-log-search.md).
   Keep shared administrative accounts and credentials out of routine work.
3. Test a new login, the intended operation and another team's denied operation; record exact
   group/role mappings and the service-specific revocation procedure in project administration.

**Expected:** only the approved application/project/log view is available. An OIDC login
does not grant cluster, CI or infrastructure administration.
**Stop/rollback:** remove the newly granted memberships/roles if scope tests fail; preserve audit records.

<a id="revoke-access"></a>

## How is a departing person's access revoked?

**Work on:** an authorized FreeIPA administrative session and each affected product.
**Prerequisites:** verified account identity, a revocation record and another working recovery administrator.

1. Identify the directory account before changing it:

   Run on **the authorized directory administration host with the approved operator identity**.

   ```bash
   read -r -p "Approved account to disable: " IPA_ACCOUNT
   ipa user-show "$IPA_ACCOUNT"
   ```

2. After verifying the person/scope, disable the account without deleting its identity history: [1]

   Run on **the authorized directory administration host with the approved operator identity**.

   ```bash
   ipa user-disable "$IPA_ACCOUNT"
   ipa user-show "$IPA_ACCOUNT"
   ```

3. Remove retired memberships and product permissions. Revoke IdP/application sessions,
   refresh tokens, personal/service tokens, SSH keys and VPN/device access at their owners.
   Rotate shared secrets if exposure is possible.
   For Kubernetes, review existing namespace RoleBindings explicitly: removing a namespace from
   the human-access inputs does not prune its old binding. Follow the
   [CLI/RBAC ownership contract](../03-deployment/stage-5-identity/procedures/kubernetes-cli-access.md#3-register-the-client-and-namespace-access).
4. Test an existing session, an existing API token and a fresh login. Record any accepted
   revocation delay; preserve identity and audit records under the retention policy.

Directory disablement does not itself revoke every application session, API token, cached group
mapping or SSH key. Record the product-specific revocation path and accepted delay in the
service's local runbook. Preserve identity/audit records according to retention policy.

**Stop:** do not disable the only working recovery administrator. If the wrong identity was
changed, use independently authorized recovery to correct it; restoring directory access does
not recreate revoked product tokens. No cross-product revocation playbook is supplied.

<a id="remote-administration"></a>

## How is remote administration enabled?

**Work on:** the selected VPN/access gateway and an authorized administration workstation.
**Prerequisites:** independently tested console recovery, device enrollment and a supported gateway runbook.

1. Select and qualify the supported VPN/access gateway; no universal VPN installer is supplied.
2. Limit remote entry to the approved workstation/jump path, then separately authorize destinations/actions.
   Do not publish Proxmox, BMC, Vault or Kubernetes admin APIs directly to the Internet.
3. Record device enrollment and lost-device revocation. Test ordinary-user, guest, other-subnet
   and IPv6 denials, then VPN loss and independent console recovery.

Test denied access from ordinary users, guests, another client subnet and IPv6, plus VPN loss
and independent console recovery. Preserve host/gateway/security audit records for these actions;
query privileges must not allow original-log deletion. Remote entry is not required for a first
local-only deployment; mark it not selected until its actual implementation and checks exist.

**Stop/rollback:** revoke the new remote entry if isolation or recovery checks fail; retain local access.

## References

1. [FreeIPA user lifecycle and account disablement](https://www.freeipa.org/page/V4/User_Life-Cycle_Management).
