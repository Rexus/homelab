# Restore Keycloak federation

Recover Keycloak's CNPG database and matching configuration before restoring federation endpoints.
**Prerequisites:** isolated clean cluster, the selected database recovery material, original Keycloak/chart
and provider/theme versions, DB credential/TLS, hostname/realm configuration, client secrets and
independent recovery-admin access. Directory login also requires recovered FreeIPA/DNS/time.

<a id="contents"></a>

## Operator tasks

- [How to restore Keycloak without replacing its realms?](#restore-and-start)
- [How to verify federation before reconnecting clients?](#validate-federation)
- [References](#references)

<a id="restore-and-start"></a>

## How to restore Keycloak without replacing its realms?

1. Fence the old Keycloak endpoint and preserve evidence. Keep all Keycloak replicas absent in the
   recovery namespace, block outbound production clients and disable ingress/GitOps/Helm reconciliation.
2. Restore `keycloak-db` using the **recorded backup mode**, with source storage read-only:

   | Recorded backup | Procedure | Recovery point |
   | --- | --- | --- |
   | Completed NAS physical set | [NAS-file CNPG recovery](cnpg-files.md), Keycloak inputs | Selected completed set only |
   | Object base backup plus WAL | [Guarded object/WAL recovery](cnpg.md), `PRODUCT=keycloak` | Approved time covered by base backup/WAL |
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

<a id="validate-federation"></a>

## How to verify federation before reconnecting clients?

1. Open the **recovery-only Keycloak administration endpoint** with independent local
   recovery-admin access. Do not rely on directory/SSO login as the only recovery path.
2. Compare these with independently recorded expected results:

   | Check | Acceptance |
   | --- | --- |
   | Realm/issuer/signing keys | Original issuer URL and intended signing-key identity |
   | Clients | IDs, redirect allowlists, secrets, scopes and roles match the selected point |
   | Directory | Bind TLS, mappings, known user/group login and denied-user rejection work |
   | OIDC | Recovery-only authorization-code flow; signature/issuer/audience and group claims validate |
   | Denials | Unauthorized redirects and forbidden roles are rejected |

3. Reconcile sessions/client secrets with the incident timeline; rotate compromised credentials
   deliberately. Restored DB credentials may differ from external consumers.
4. Restore the selected replica topology. Fence the old identity before endpoint/DNS cutover;
   reconnect clients individually and preserve independent break-glass access.
5. Resume backups to a new accepted destination through the selected DB procedure. Record set/time,
   backup IDs and measured RPO/RTO; pod readiness alone is not federation acceptance.

**Stop/rollback:** failed DB/realm/key/authorization checks keep ingress and client routes blocked.
Preserve the recovery target and original backups; use a new isolated target after diagnosis.
A realm import, fresh realm or normal installer convergence is not rollback over restored data.

## References

1. [Keycloak import/export backup limitations](https://www.keycloak.org/server/importExport)
