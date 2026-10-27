# Restore Keycloak federation

Recover Keycloak's CNPG database and matching configuration before restoring federation endpoints.
**Prerequisites:** isolated clean cluster, [CNPG recovery material](cnpg.md), original Keycloak/chart
and provider/theme versions, DB credential/TLS, hostname/realm configuration, client secrets and
independent recovery-admin access. Directory login also requires recovered FreeIPA/DNS/time.

## Contents

- [Restore and start](#restore-and-start)
- [Validate federation](#validate-federation)
- [References](#references)

## Restore and start

1. Fence the old Keycloak endpoint and preserve evidence. Keep all Keycloak replicas absent in the
   recovery namespace, block outbound production clients and disable ingress/GitOps/Helm reconciliation.
2. Execute [guarded CNPG recovery](cnpg.md) with `PRODUCT=keycloak`; use the existing `keycloak-db`
   base backups/WAL and a known-good target time. Keep its source storage credentials read-only.
3. Restore the matching configuration, DB credential, TLS trust, LDAP bind credential, providers,
   themes and extensions from independent custody. The
   [Keycloak values template](../../../tier-0/ansible/roles/control_applications/templates/keycloak-values.yml.j2)
   defines the installed contract. Select the restored `keycloak-db-rw` endpoint with verified TLS.
4. Start one release-matched Keycloak replica with ingress still disabled and no automatic realm
   provisioning. Do not run client-registration/configuration tasks until recovered realm contents
   have been inspected. Do not bootstrap a replacement realm or administrator over recovered data.

The authoritative recovery dataset is the PostgreSQL backup. Realm JSON exports omit some state and
are unsuitable as a substitute for a complete DB restore. Do not run `kc.sh import --override` on the
restored database as a repair step. [1]

## Validate federation

Use independent local recovery-admin access first. Verify the original realm issuer URL, signing-key
identity, client IDs, redirect allowlists, scopes, roles, LDAP mappings, bind TLS and login restrictions.
Compare one known user/group and a denied user to independently recorded expected results.

Test a scoped OIDC client against a recovery-only redirect endpoint: validate discovery/JWKS,
authorization code flow, signature/issuer/audience, group claims and rejection of an unauthorized
redirect. Reconcile restored sessions/client secrets with the incident timeline; revoke/rotate
compromised credentials through a deliberate operation. Restored database contents can include
credentials no longer consistent with external consumers.

Restore the configured replica topology only after baseline validation. Fence the old identity before
DNS/ingress cutover, reconnect dependent Vault/NetBox/Kubernetes clients individually, and verify
independent break-glass access still works. Resume DB backups into a new writable destination as
described in CNPG recovery; record target time, backup IDs and observed RPO/RTO. A Ready pod does not
establish federation or restore acceptance.

## References

1. [Keycloak import/export backup limitations](https://www.keycloak.org/server/importExport)
