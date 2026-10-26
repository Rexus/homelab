# Install Tier 0 control applications

Render or install Keycloak, Vault, NetBox and Headlamp with tier-owned product
configuration and Shared's native Helm/Kubernetes execution. Select products by
stage; an install does not grant operational acceptance or transfer directory authority.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted Stage 4 networking/storage/ingress, CNPG, external TLS
and bootstrap custody, protected stdout log delivery, and independent object storage.
Keycloak additionally needs FreeIPA. Consumers need the accepted existing IdP.

## Table of contents

- [Dependencies and ownership](#dependencies-and-ownership)
- [Configure inputs](#configure-inputs)
- [Secrets and certificates](#secrets-and-certificates)
- [Render and apply](#render-and-apply)
- [Persistence and recovery](#persistence-and-recovery)
- [Service access and logging](#service-access-and-logging)
- [References](#references)

## Dependencies and ownership

| Dependency | Required capability |
| --- | --- |
| Control node | Native Helm, `kubernetes.core`, `community.general` with Keycloak action group support, `community.hashi_vault` and Python `kubernetes`, `jsonpatch`, `PyYAML`, `hvac` |
| CNPG and Barman Cloud plugin | Existing controllers and `Cluster`, `Backup`, `ScheduledBackup`, `ObjectStore` CRDs; plugin installed alongside CNPG [1] |
| Ingress and TLS | Existing Traefik ingress and CRD providers with `ServersTransport` CRD; external certificates/keys |
| Backup destination | Existing HTTPS S3-compatible service outside these databases, with separate database prefixes and scoped credentials |
| NetBox media | RWX-capable storage class shared by web, worker and housekeeping pods; separate media backup/restore |
| Protected logs | Shared `cluster_security_logging` captures pod stdout and forwards it to protected Tier 0 mTLS intake |
| Headlamp | Accepted [native Talos API OIDC integration](../../stage-5-identity/procedures/kubernetes-sso.md), with independent X509 recovery and matching `headlamp` audience/group bindings [4] |

The [product role](../../../../tier-0/ansible/roles/control_applications/) owns
values, native supporting resources, database readiness, federation and health.
Shared owns execution. The role reuses Shared's `tasks_from: secrets` gate during
database preparation, then calls its normal release interface. Database CRs in
the release's `before` list are reapplied idempotently from the same definition.

Vault's first installation sets the Shared release's `wait: false`; later phases
use normal readiness. There is no second installer in the empty Flux application starters;
retain one reconciliation owner per resource.

## Configure inputs

From Tier 0, prepare local inputs:

```bash
cp -n ansible/group_vars/control_applications.yml.example ansible/group_vars/control_applications.yml
```

Replace example hosts, ingress class, storage class, directory bases, endpoint,
archive prefixes and approved image/chart pins. Keycloak and Vault use native
Traefik `ServersTransport` resources with explicit server names and CA Secrets.
Enable the Stage 4 Traefik CRD provider before accepting this integration. NetBox and Headlamp
terminate TLS at ingress and use cluster-internal HTTP; qualify network isolation.

| Input | Default / effect |
| --- | --- |
| `control_applications_action` | `render`; `apply` requires explicit kubeconfig, context if selected, and accepted prerequisite flags |
| `control_applications_components` | `[keycloak]`; Stage 6 selects `[vault, netbox, headlamp]` or a subset |
| `control_applications_versions` | Exact chart pins in the example; image versions are chart-derived except explicit PostgreSQL/cache images |
| `control_applications_output` | Private `secrets/control-applications/`; contains values, rendered resources and before/after resources |
| `control_applications_manage_secrets` | `false`; use pre-existing Secrets, or explicitly permit Shared to create them from private `stringData` |
| `control_applications_register_clients` | `false`; enable to converge selected clients on the existing Keycloak realm |
| `control_applications_vault_phase` | `install`, `configure`, then `accept`; see the [Vault ceremony](vault-kubernetes.md) |
| `control_applications_backup_schedule` | Six-field daily schedule; example runs at 02:00 according to the controller's timezone [2] |
| `control_applications_cluster_logging_accepted` | `false`; apply requires evidence of protected stdout delivery for the selected namespaces |
| `control_applications_traefik_crd_accepted` | `false`; Keycloak/Vault require the existing CRD provider and verified upstream transport |

## Secrets and certificates

The [private input example](../../../../tier-0/ansible/group_vars/control_applications_secrets.yml.example)
lists every required namespace/name and key. Populate only selected products in
an encrypted private file and pass it explicitly with `-e @path`. Render never
contacts Kubernetes or applies Secrets. Output files are private even when values
only contain Secret references.

| Secret | Certificate/data contract |
| --- | --- |
| `<product>-tls` | Approved HTTPS leaf/key and issuer `ca.crt`; Keycloak/Vault use the same leaf for their HTTPS backend |
| `<product>-db` | `username` exactly equals `keycloak` or `netbox`; matching private password |
| `<product>-db-ca` | Public CA bundle for server and client authentication; no CA private key |
| `<product>-db-server` | Issued server TLS leaf/key; SAN includes `<product>-db-rw` and its namespace/service FQDN |
| `<product>-db-replication` | Issued client TLS leaf/key with CN `streaming_replica` and client-auth usage [3] |
| `<product>-db-backup` | Scoped object credentials and backup endpoint CA |
| `netbox-config` | Operator-held 50+ character `secret_key` and JSON `api_token_peppers`; retain old peppers during rotation |
| `netbox-superuser` | Independent `username`, `password`, `email`, `api_token` recovery account |
| `netbox-oidc` | `oidc.yaml` containing `SOCIAL_AUTH_OIDC_SECRET`, identical to the existing `netbox` client |
| `netbox-cache` | Private `valkey.conf` with TLS-only listener, AOF, and `requirepass` matching `password` |
| `netbox-cache-tls` | Server leaf/key for `netbox-cache` plus CA; clients verify TLS |
| `service-ca` | Existing IdP trust bundle in NetBox and Headlamp namespaces |
| `headlamp-oidc` | Exact `OIDC_CLIENT_ID=headlamp`, existing issuer, matching client secret and scopes |

Certificates, bootstrap secrets and backup credentials must be provisioned through
independent custody/SOPS or an already accepted secret controller. This path does
not generate a CA/key, request a certificate through future Vault, or initialize Vault.

## Render and apply

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/control-applications.yml
```

Review native workloads, CNPG/backup resources, ingress, required Secret names,
storage and RBAC. Then explicitly apply reviewed inputs:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/control-applications.yml \
  -e @secrets/control-applications.yml --ask-vault-pass \
  -e control_applications_action=apply
```

Apply creates/gates database Secrets, ObjectStores and Clusters, waits for each
database and authenticated TLS cache before installing application Helm releases. The role checks the
first post-install physical backup. A manifest render proves neither controllers
nor live services work. Do not apply these inputs against another tier's cluster.

## Persistence and recovery

CNPG archives WAL through Barman and schedules physical backups to the configured
store. The first `Backup` must reach `completed`; test a fresh post-configuration
backup and clean-target restore before accepting service recovery. [1][2]

For a recovery rehearsal, use the plugin's native recovery recipe with a **new**
Cluster name and fresh PVCs: `bootstrap.recovery.source` references an
`externalClusters[].plugin` entry with `barmanObjectName` and the original database
`serverName`. Restore read credentials and TLS independently. Never replace the
running Cluster's `initdb` bootstrap or share archive prefixes between writers. [1]

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
export the complete `ObjectChange` history. Before acceptance, provide a protected
exporter for `/api/core/object-changes/` in the pinned NetBox release, or reviewed
native event rules/webhooks. Confirm the endpoint against the installed API. [6]
The export contract requires authenticated TLS delivery, actor/object/action/time,
request ID and before/after change data, durable cursor/retry state, replay-safe
record identity, and tests for loss/restart and denied destination access. The
exporter's credentials must permit only the required reads/delivery. This role
does not install that exporter; record it as an outstanding integration until
complete. Its backup is also separate from live protected event delivery.

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
