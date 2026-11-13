# Install Tier 0 control applications

**Stage route:** [Stage 6, actions 2-10](../README.md#step-2-reuse-the-control-application-inputs) installs Vault;
[actions 13-19](../README.md#step-13-configure-netbox-and-its-private-inputs) install NetBox/Headlamp separately.
**Return:** to the selected step for its ceremony and acceptance checks. Keycloak belongs to
[Stage 5](../../stage-5-identity/README.md#step-2-deploy-identity-federation); do not reinstall it here.

Render or install Keycloak, Vault, NetBox and Headlamp with tier-owned product
configuration and Shared's native Helm/Kubernetes execution. Select products by
stage; an install does not grant operational acceptance or transfer directory authority.

Use the [Stage 6 runtime figure](../README.md#figure-control-applications) for Vault and operator tools,
or the [Stage 5 federation figure](../../stage-5-identity/README.md#figure-identity-federation) for Keycloak.
Select only the products owned by the calling stage step before rendering.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted Stage 4 networking/storage/ingress, CNPG, external TLS
and bootstrap custody, protected stdout log delivery, and a qualified backup destination.
Keycloak additionally needs FreeIPA. Consumers need the accepted existing IdP.

## Table of contents

- [Dependencies and ownership](#dependencies-and-ownership)
- [Step 1: Edit the application inputs](#configure-inputs)
- [Step 2: Prepare Secrets and certificates](#secrets-and-certificates)
- [Step 3: Render and apply](#render-and-apply)
- [Persistence and recovery](#persistence-and-recovery)
- [Service access and logging](#service-access-and-logging)
- [References](#references)

## Dependencies and ownership

| Dependency | Required capability |
| --- | --- |
| Control node | Native Helm, `kubernetes.core`, `community.general` with Keycloak action group support, `community.hashi_vault` and Python `kubernetes`, `jsonpatch`, `PyYAML`, `hvac` |
| CNPG | Existing controller and `Cluster` CRD; the object/WAL option additionally requires Barman Cloud and its backup CRDs [1] |
| Ingress and TLS | Existing Traefik ingress and CRD providers with `ServersTransport` CRD; external certificates/keys |
| Live database storage | Qualified Proxmox/Ceph-backed block volumes; separate from NetBox media and NAS backup claims |
| Database backup destination | [Scheduled verified full copies to NAS](../../../05-operations/06-resilience/backups/postgresql.md), or existing S3-compatible storage for the object/WAL option; no gateway is installed |
| NetBox media | RWX-capable storage class shared by web, worker and housekeeping pods; separate media backup/restore |
| Protected logs | Shared `cluster_security_logging` captures pod stdout and forwards it to protected Tier 0 mTLS intake |
| Headlamp | Accepted [native Talos API OIDC integration](../../stage-5-identity/procedures/kubernetes-sso.md), with independent X509 recovery and matching `headlamp` audience/group bindings [4] |

The [product role](../../../../tier-0/ansible/roles/control_applications) owns
values, native supporting resources, database readiness, federation and health.
Shared owns execution. The role reuses Shared's `tasks_from: secrets` gate during
database preparation, then calls its normal release interface. Database CRs in
the release's `before` list are reapplied idempotently from the same definition.

Vault's first installation sets the Shared release's `wait: false`; later phases
use normal readiness. There is no second installer in the empty Flux application starters;
retain one reconciliation owner per resource.

<a id="configure-inputs"></a>
<a id="step-1-edit-the-application-inputs"></a>

## Product input contract

The continuous first-install commands live in the owning stage. Use the same accepted
`ansible/group_vars/control_applications.yml` and private Secret input throughout; select products
one at a time without removing prior service settings.

| Work | Authoritative installation action |
| --- | --- |
| Keycloak, database and selected backup | [Stage 5, actions 12-20](../../stage-5-identity/README.md#step-12-select-the-existing-cluster-and-identity-provider-inputs) |
| Sealed cluster Vault, then audit/SSO after human ceremony | [Stage 6, actions 2-10](../README.md#step-2-reuse-the-control-application-inputs) |
| NetBox and its own database/backup | [Stage 6, actions 13-17](../README.md#step-13-configure-netbox-and-its-private-inputs) |
| Headlamp after accepted API OIDC | [Stage 6, action 19](../README.md#step-19-install-headlamp-after-api-sso-acceptance) |

| Field to edit | Required value |
| --- | --- |
| `control_applications_components` | `[vault]` for Stage 6 Step 1; then `[netbox]`, and `[headlamp]` after its API OIDC gate |
| `control_applications_kubeconfig`, `control_applications_context` | Private Tier 0 kubeconfig and its exact context |
| `control_applications_hosts` | Actual private service DNS names |
| `control_applications_ingress_class` | Accepted cluster ingress class |
| `control_applications_storage_class`, `control_applications_database_storage_class` | Qualified live block storage; the latter is explicit in files mode |
| `control_applications_netbox_media_storage_class` | Qualified RWX class for NetBox media |
| `control_applications_backup_mode`, `control_applications_backup_files_phase` | NAS database path: `files`, `prepare` for each new database, then `backup`; ignored for Vault/Headlamp-only runs |
| Acceptance flags | Set true only after their named prerequisite has been verified |

Retain approved chart/image pins. Keycloak and Vault use native
Traefik `ServersTransport` resources with explicit server names and CA Secrets.
Enable the Stage 4 Traefik CRD provider before accepting this integration. NetBox and Headlamp
terminate TLS at ingress and use cluster-internal HTTP; qualify network isolation.

| Input | Default / effect |
| --- | --- |
| `control_applications_action` | `render`; `apply` requires explicit kubeconfig, context if selected, and accepted prerequisite flags |
| `control_applications_components` | `[keycloak]` by default; select the Stage 6 components one pass at a time as above |
| `control_applications_versions` | Exact chart pins in the example; image versions are chart-derived except explicit PostgreSQL/cache images |
| `control_applications_output` | Private `secrets/control-applications/`; contains values, rendered resources and before/after resources |
| `control_applications_manage_secrets` | `false`; use pre-existing Secrets, or explicitly permit Shared to create them from private `stringData` |
| `control_applications_register_clients` | `false`; enable to converge selected clients on the existing Keycloak realm |
| `control_applications_vault_phase` | `install`, `configure`, then `accept`; see the [Vault ceremony](vault-kubernetes.md) |
| `control_applications_vault_seal_type` | `shamir` by default; [option 1c](../step-1c-seal-integration.md) configures Transit or a qualified licensed PKCS#11 artifact before initialization |
| `control_applications_backup_mode` | Fresh examples select `files`; omitted values retain the existing `object` behavior |
| `control_applications_backup_files_phase` | With Keycloak/NetBox selected, `prepare` pauses the batch after database setup; `backup` proceeds after NAS commissioning. Ignored for Vault/Headlamp-only runs |
| `control_applications_database_storage_class` | Qualified live Proxmox/Ceph-backed block class, separate from the backup destination |
| `control_applications_netbox_media_storage_class` | Explicit RWX media class; independent of database block disks |
| `control_applications_backup_schedule` | Object/WAL only: six-field schedule. File jobs use each database's five-field UTC schedule |
| `control_applications_cluster_logging_accepted` | `false`; apply requires evidence of protected stdout delivery for the selected namespaces |
| `control_applications_traefik_crd_accepted` | `false`; Keycloak/Vault require the existing CRD provider and verified upstream transport |

<a id="secrets-and-certificates"></a>
<a id="step-2-prepare-secrets-and-certificates"></a>

## Secrets and certificates

The private input example lists all namespace/name/key entries. The first selected product
creates an encrypted private file; later products edit that same file. Only enable
`control_applications_manage_secrets` for its selected installer owner. An accepted existing
Secret controller remains an alternative; it must supply the same nonempty fields before apply.
No unseal share or root key belongs in these inputs. Keep decryption and TLS renewal/recovery
custody independent of the service being installed.

| Secret | Certificate/data contract |
| --- | --- |
| `<product>-tls` | Approved HTTPS leaf/key and issuer `ca.crt`; Keycloak/Vault use the same leaf for their HTTPS backend |
| `<product>-db` | `username` exactly equals `keycloak` or `netbox`; matching private password |
| `<product>-db-ca` | Public CA bundle for server and client authentication; no CA private key |
| `<product>-db-server` | Issued server TLS leaf/key; SAN includes `<product>-db-rw` and its namespace/service FQDN |
| `<product>-db-replication` | Issued client TLS leaf/key with CN `streaming_replica` and client-auth usage [3] |
| `<product>-db-backup` | Object/WAL option only: scoped object credentials and backup endpoint CA |
| `netbox-config` | Operator-held 50+ character `secret_key` and JSON `api_token_peppers`; retain old peppers during rotation |
| `netbox-superuser` | Independent `username`, `password`, `email`; fresh v2 API bootstrap also uses a 12-character alphanumeric `api_key` and private plaintext `api_token`. Retain both; existing accounts are not rotated |
| `netbox-oidc` | `oidc.yaml` containing `SOCIAL_AUTH_OIDC_SECRET`, identical to the existing `netbox` client |
| `netbox-cache` | Private `valkey.conf` with TLS-only listener, AOF, and `requirepass` matching `password` |
| `netbox-cache-tls` | Server leaf/key for `netbox-cache` plus CA; clients verify TLS |
| `service-ca` | Existing IdP trust bundle in NetBox and Headlamp namespaces |
| `headlamp-oidc` | Exact `OIDC_CLIENT_ID=headlamp`, existing issuer, matching client secret and scopes |

Certificates, bootstrap secrets and backup credentials must be provisioned through
independent custody/SOPS or an already accepted secret controller. This path does
not generate a CA/key, request a certificate through future Vault, or initialize Vault.

<a id="render-and-apply"></a>
<a id="step-3-render-and-apply"></a>

## Execution contract

The stage supplies exact `control-applications.yml` render/apply commands. Rendering has no
cluster mutation; inspect private `secrets/control-applications/` before explicit `action=apply`.
Apply has no additional confirmation prompt. Managed Secrets use the same encrypted file and
Vault password/identity for both commands; existing-owner mode omits those arguments.

For a files-mode database, `prepare` creates only that database. After external per-database
NAS commissioning, `backup` enables the file jobs and dependent application. Vault/Headlamp-only
selections do not use that database phase. A mixed batch containing Keycloak/NetBox pauses the
whole batch, so keep installation selections separate. Rendering alone proves neither live
readiness nor first backup/restore success.

## Persistence and recovery

Select one backup method. Scheduled full file backups send verified copies to a
separate NAS backup PVC; live database data remains on Proxmox/Ceph-backed volumes.
These copies include the WAL needed for that backup, not transactions written
after it completes. Recovery is bounded by the last completed verified set.
Follow [prepare, commission and enable](../../../05-operations/06-resilience/backups/postgresql.md)
before treating a fresh files-mode application install as complete.

The object/WAL option archives through Barman and schedules physical backups to
the configured endpoint. Its first `Backup` must reach `completed`. Existing
object/WAL inputs remain compatible; changing methods is a reviewed recovery-policy
decision, not an automatic refresh migration. Test the selected method's fresh
backup and clean-target restore before accepting service recovery. [1][2]

For an object/WAL recovery rehearsal, use the plugin's native recipe with a **new**
Cluster name and fresh PVCs: `bootstrap.recovery.source` references an
`externalClusters[].plugin` entry with `barmanObjectName` and the original database
`serverName`. Restore read credentials and TLS independently. Never replace the
running Cluster's `initdb` bootstrap or share archive prefixes between writers. [1]
Use the separate [NAS-file recovery procedure](../../../05-operations/06-resilience/recovery/cnpg-files.md)
for a completed file set; it does not replay a Barman archive.

NetBox media has a separate RWX persistent volume shared by web, worker and
housekeeping pods; its backup/restore and cache AOF
retention need the accepted storage backup path. Database backups do not include
media. Vault uses Raft and its [separate recovery ceremony](vault-kubernetes.md).

## Service access and logging

NetBox authenticates with native OIDC and creates users without permissions. Assign
reviewed object permissions in NetBox; keep local emergency access. Headlamp uses
per-user OIDC tokens and namespace `view` RoleBindings for the selected group. Its
pod receives no cluster-admin binding and never impersonates all users as its
service account. Existing target namespaces are prerequisites; the separate
[post-identity operation](../../stage-5-identity/procedures/kubernetes-sso.md)
supplies native API configuration and a serial rollout, not an implicit API
rewrite during application installation. [4][5]

NetBox sends application logs to stdout; Headlamp and Keycloak use their normal
container logs. Verify actual login/denial and operator events at protected intake
through Shared `cluster_security_logging`, including the CNPG/cache containers.
Vault's second native audit device writes to stdout after unseal; the persistent
file audit PVC is not visible to the pod-log collector. A local log or running
collector does not prove protected delivery.

NetBox's audited object changes remain in its database; ordinary stdout does not
export the complete `ObjectChange` history. Complete the separate
[NetBox audit installation](netbox-audit.md), Steps 1–3, before acceptance.
That recipe supplies the read-only API collector and retained local ledger;
this application role does not install it. Confirm the API endpoint against the installed release. [6]

Apply the [SSO acceptance gate](../../stage-5-identity/procedures/service-sso.md),
including denied access and IdP outage. Record source enrollment, retention,
loss detection, restore and media recovery evidence before routine use.

## References

Guidance checked 2026-10-26.

1. [Barman Cloud plugin usage and restore](https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/).
2. [CNPG backups and scheduling](https://cloudnative-pg.io/docs/1.28/backup/).
3. [CNPG externally provided certificates](https://cloudnative-pg.io/docs/1.28/certificates/).
4. [Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/).
5. [NetBox chart values](https://github.com/netbox-community/netbox-chart/blob/main/charts/netbox/values.yaml).
6. [Pinned NetBox core API routes](https://github.com/netbox-community/netbox/blob/v4.7.3/netbox/core/api/urls.py).
