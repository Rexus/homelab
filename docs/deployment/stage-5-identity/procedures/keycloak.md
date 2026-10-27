# Keycloak with external FreeIPA

Install the Tier 0 identity provider after accepting the directory pair and the
Kubernetes platform. FreeIPA remains the directory authority on its dedicated VMs.
Keycloak uses its own CNPG database and verifies LDAP and database certificates.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** working FreeIPA LDAPS, a restricted directory reader, external
certificate/credential custody, CNPG, the selected database backup path, independent
backup storage and protected cluster log delivery. None may depend on later Vault.

## Table of contents

- [Configure and install](#configure-and-install)
- [Federation and authorization](#federation-and-authorization)
- [Accept and recover](#accept-and-recover)
- [References](#references)

## Configure and install

Use the [control-application procedure](../../stage-6-secrets/procedures/control-applications.md)
for dependencies, private inputs, certificates and render/apply commands. Select
`control_applications_components: [keycloak]`; retain `render` until review.
For fresh file-backup inputs, follow [database preparation and NAS commissioning](../../../administration/backups/postgresql.md)
before the final application installation. The `prepare` phase alone does not install Keycloak.

The installer creates `keycloak-db` on qualified Proxmox/Ceph-backed volumes with
externally issued TLS and the selected backup resources, then waits for readiness before
installing the pinned `keycloakx` chart. Two Keycloak replicas use JDBC discovery;
this is a placement configuration, not evidence of failover. The maintained chart
runs the upstream Keycloak image in production mode. [1][2]

Scheduled verified full backups can write to a separate NAS backup PVC. The database
itself does not use that PVC. Select the object/WAL path separately when continuous
point-in-time recovery is required; a file backup recovers only to a completed set.

| Input | Required selection |
| --- | --- |
| `control_applications_hosts.keycloak` | Stable HTTPS name; use the same name in certificate SANs and issuer URLs |
| `control_applications_keycloak_realm` | Existing/selected human federation realm; default `platform` |
| `control_applications_ldap_url` | External FreeIPA `ldaps://` endpoint; trusted through `freeipa-ca` |
| `control_applications_ldap_users_dn` | FreeIPA user search base |
| `control_applications_ldap_groups_dn` | FreeIPA group search base |
| `control_applications_ldap_bind_dn` | Restricted directory reader; created and authorized in FreeIPA separately |
| `control_applications_ldap_bind_password` | Private controller input, used only by the Keycloak API module |
| `control_applications_keycloak_auth` | Private API administration credentials; controller must trust HTTPS |

Keep the `keycloak-bootstrap` Secret under independent custody. The initial
administrator is a bootstrap/recovery account, not routine human SSO. After
acceptance, supply a supported durable API administration identity separately;
the initial bootstrap variables do not recreate a removed account in an existing
database. [2]

## Federation and authorization

Native `community.general` modules configure the realm and LDAP provider. The
provider is read-only, uses `uid` and FreeIPA `ipaUniqueID`, and maps `groupOfNames`
membership through `member` DNs. Unspecified built-in attribute mappers are
preserved. Self-registration and directory writes are disabled. [3]

The selected FreeIPA LDAPS endpoint must itself meet the availability requirement.
Supplying two directory VMs does not configure a resilient LDAP endpoint.
Verify read access, disabled-account behavior, group hierarchy and membership
removal against the real directory before accepting federation.

Later services use the same realm. Set `control_applications_register_clients`
when installing those consumers to register exact callbacks and a `groups` claim
through the native Keycloak API. Supply each confidential-client secret privately
and use the identical value in its consumer. NetBox grants no initial permissions;
Vault roles require explicit groups and policies; Headlamp uses Kubernetes RBAC.
Apply the [service SSO gate](service-sso.md) before routine access.
For Headlamp, follow the native [Kubernetes API integration](kubernetes-sso.md),
including preserved X509 authentication and cold-start issuer-outage acceptance.

## Accept and recover

| Check | Evidence |
| --- | --- |
| Discovery | The HTTPS discovery document reports the exact selected issuer |
| Federation | Allowed user, denied user, disabled user and removed group membership behave as approved |
| Audit | Authentication and administrative changes arrive through protected cluster stdout collection |
| Backup | Completed verified file set, or base backup plus archived WAL for the selected object/PITR path; restore into a separate CNPG cluster and exercise a login |
| Failure | Restart one replica, test the directory endpoint failing, then test the IdP outage |
| Recovery | Independent Kubernetes and Keycloak administration, database restore inputs and TLS material remain available |

The role checks database/endpoint health and initial backup completion. Human
login, event arrival, failover and clean-target restoration remain operator
acceptance checks. Restore the existing realm/database; reinstalling an empty
realm changes identity state and is not recovery.

Return to [Stage 5](../README.md#capability-available), then continue to Stage 6.

## References

Official/maintainer guidance checked 2026-10-26; pins live in the example inputs.

1. [Maintained Keycloak chart](https://github.com/codecentric/helm-charts/tree/master/charts/keycloakx).
2. [Keycloak production containers](https://www.keycloak.org/server/containers).
3. [Native Ansible LDAP federation module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_user_federation_module.html).
