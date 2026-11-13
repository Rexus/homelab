# Keycloak federation contract

<a id="keycloak-with-external-freeipa"></a>
<a id="table-of-contents"></a>
<a id="step-1-configure-the-identity-provider"></a>
<a id="1-create-local-inputs-and-select-the-cluster"></a>
<a id="3-select-the-secret-owner"></a>
<a id="4-create-and-fill-the-encrypted-bootstrap-input"></a>
<a id="5-render-database-preparation"></a>
<a id="6-inspect-and-prepare-the-database"></a>
<a id="7-commission-the-nas-backup-destination"></a>
<a id="8-render-the-completed-selection"></a>
<a id="9-install-the-reviewed-application-and-federation"></a>

Follow [Stage 5, actions 12-23](../README.md#step-12-select-the-existing-cluster-and-identity-provider-inputs)
for the continuous first installation. This page owns the native federation/certificate contract;
it is not a second application or database installer. FreeIPA stays on its original dedicated hosts.

**Working repository:** `<prefix>-tier-0/`.

<a id="configure-and-install"></a>
<a id="step-2-supply-private-certificates-and-credentials"></a>
<a id="step-3-prepare-the-database-and-backup"></a>
<a id="step-3a-scheduled-nas-backups-main-path"></a>
<a id="step-3b-objectwal-backups-alternative"></a>
<a id="step-4-install-keycloak-and-federation"></a>
<a id="2-edit-the-identity-provider-settings"></a>

## First-install locations

| Work | Stage action |
| --- | --- |
| Target, service inputs and backup choice | [12-13](../README.md#step-12-select-the-existing-cluster-and-identity-provider-inputs) |
| Accepted Secret owner, externally issued TLS and bind-only directory reader | [14](../README.md#step-14-supply-private-certificates-and-credentials) |
| NAS-only database preparation and destination commissioning | [15-17a](../README.md#step-15-render-database-preparation) |
| Object/WAL alternative | [17b](../README.md#step-17-commission-the-selected-backup-destination) |
| Completed render, reviewed apply and acceptance | [18-20](../README.md#step-18-render-the-completed-keycloak-selection) |

## Private material

| Required private material | Contract |
| --- | --- |
| `keycloak-bootstrap`, `keycloak-db` | Independent bootstrap administrator and database credentials |
| `freeipa-ca`, `keycloak-tls` | Trusted LDAP CA bundle; approved HTTPS leaf/key/chain for the selected IdP DNS name |
| `keycloak-db-ca`, `keycloak-db-server`, `keycloak-db-replication` | External DB trust, server leaf covering the read/write service name, and client-auth replication identity |
| `keycloak-db-file-backup` | Files mode: client-auth CN `keycloak-db-file-backup`, matching key and server trust |
| `keycloak-db-backup` | Object/WAL alternative only: independently scoped object credentials and endpoint trust |

Use the [exact namespace/key and certificate contract](../../stage-6-secrets/procedures/control-applications.md#secrets-and-certificates).
Obtain all leaves through qualified issuance before apply; the Stage 3 TLS-server
policy does not supply client-auth profiles. No CA private key or later Vault
dependency belongs in these inputs. Keep TLS verification enabled on the controller.

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

### 10. Test identity, audit delivery and restoration

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

Continue at [Stage 5, action 21](../README.md#step-21-roll-out-kubernetes-api-human-sso)
for Kubernetes human SSO and the service-access gates before Stage 6.

## References

Official/maintainer guidance checked 2026-10-26; pins live in the example inputs.

1. [Maintained Keycloak chart](https://github.com/codecentric/helm-charts/tree/master/charts/keycloakx).
2. [Keycloak production containers](https://www.keycloak.org/server/containers).
3. [Native Ansible LDAP federation module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_user_federation_module.html).
