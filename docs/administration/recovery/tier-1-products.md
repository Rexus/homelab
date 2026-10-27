# Recover Tier 1 product data

Recover shared services after independent Tier 0 access, trust, identity and storage are usable.
**Prerequisites:** original Tier 1 inputs/state, pinned product/tool versions, independent decryption
and object-store credentials, complete product backups, an isolated clean recovery cluster/volumes,
and a known-good recovery point. Follow [tier sequencing](../recovery.md) and
[original state recovery](original-state-etcd.md) first.

## Contents

- [Select the authoritative product procedure](#select-the-authoritative-product-procedure)
- [Guard the target and validate](#guard-the-target-and-validate)
- [References](#references)

## Select the authoritative product procedure

The control backup role does not back up arbitrary Tier 1 PVCs. Product-supported datasets and
operator procedures remain authoritative; use the selected installed variant, not another product's
backup format. The table identifies data that must be present before a restore can be accepted.

| Product / owner | Required recovery material | Native procedure and checks |
| --- | --- | --- |
| Harbor / `delivery_platform` | Registry blobs, database, secrets/configuration, jobservice and selected scanner data; matched point | [Harbor Velero restore][1] for the installed Helm variant; account for Redis/session/task limitations and external DB/object storage separately |
| GitLab / `development_platform` | Toolbox backup, Rails encryption secrets, configuration, Gitaly repositories, external DB/Redis and all configured object buckets | [GitLab Helm recovery][2]; exact original release/type, isolated Toolbox, independent storage access, then repositories/uploads/artifacts and encrypted-variable checks |
| Legacy container GitLab / `gitlab_container` | Native backup, `gitlab-secrets.json`, configuration and selected external storage | [GitLab Linux/container recovery][3]; match exact release/type, stop writers, verify restore and secrets before enabling runners |
| Grafana / `observability_platform` | Existing `grafana-db` CNPG base backup/WAL, Grafana configuration/plugins and encryption secret | Native [Barman recovery][4] with the original `observability` namespace/database contract, then [Grafana recovery set][5]; preserve datasource-secret decryption |
| VictoriaMetrics / `observability_platform` | Independent `vmbackup` data for each actual `metrics-*` instance and configuration/auth | [vmrestore][6] into an empty data volume while VictoriaMetrics is stopped; do not use raw live filesystem copies or conflate independent ingestion replicas with backups |
| OpenSearch / `observability_platform` | Native index snapshots, mappings/templates and independently held security configuration | [Snapshot restore][7] into a compatible isolated cluster, source repository read-only; restrict index scope/global-state restore and restore security through its own procedure |
| Argo CD, if selected / `delivery_platform` | Native export, encrypted repository/cluster credentials and declarative application definitions | [Argo CD recovery][8]; keep application reconciliation/destinations blocked until reviewed |
| Spinnaker, if selected / `delivery_platform` | Native five-schema SQL dump and Redis RDB in independently stored restic snapshots, retained service/keystore/OIDC credentials and declarative pipeline/target inputs | [Native recovery](../../deployment/stage-7-delivery/step-2b-spinnaker.md#maintenance-and-recovery); fence triggers, restore matching SQL/Redis and identities on an isolated target before permitting executions; custom overlays retain their own runbook |
| Netdata / `observability_platform` | Selected historical-data volumes and streaming/claim credentials | Restore qualified volume backups to the same product version or explicitly record history loss; verify streaming and access scopes |

The Grafana CNPG cluster is not `netbox-db` or `keycloak-db`: reuse the native recovery mechanism,
with its actual namespace, database credentials and original serverName. The guarded
[control DB recipe](cnpg.md) intentionally accepts only its two control products.
Search projections may be rebuilt from approved Tier 0 copies instead of snapshot restoration;
follow [security logging access boundaries](../security-logging.md) and record the available range.

## Guard the target and validate

1. Record the exact product backup IDs, dependencies and known-good point. Fence the old writers,
   delivery controllers, runners, webhooks and external integrations. Preserve original evidence.
2. Select a new isolated target, fresh empty volumes and private endpoints. Verify source backups
   read-only, credentials independent, release/schema compatibility and decryption before restoring.
3. Execute the authoritative procedure above. Native tools can overwrite/delete data: never point
   `vmrestore`, GitLab restore, Velero restore or OpenSearch APIs at live resources. Use explicit backup
   IDs and a new target; preserve partial failures and retry on another clean target after diagnosis.

For a native VictoriaMetrics restore, on the new isolated volume host with the product stopped:

```bash
set -euo pipefail
: "${VM_BACKUP_SOURCE:?Set the approved vmbackup source URI}"
: "${VM_NEW_DATA:?Set the NEW empty absolute data directory}"
test "${RECOVERY_ISOLATED:-}" = yes
test "${RECOVERY_APPROVE_VMRESTORE:-}" = "$VM_NEW_DATA"
test -d "$VM_NEW_DATA"
test "$(realpath "$VM_NEW_DATA")" = "$VM_NEW_DATA"
existing=$(find "$VM_NEW_DATA" -mindepth 1 -maxdepth 1 -print -quit)
test -z "$existing"
test "${RECOVERY_VM_STOPPED:-}" = yes
vmrestore -src="$VM_BACKUP_SOURCE" -storageDataPath="$VM_NEW_DATA"
```

Then restore configuration/auth, start only that instance, and verify known series/time ranges.
The stopped-process acknowledgement follows actual runtime inspection. Repeat for each required
instance's own backup; do not infer missing replica data from a successful restore elsewhere. [6]

For every product, test known content and a denied access path: pull an artifact by digest, read a
   repository/upload, decrypt a known protected setting, query a known metric range, or compare
   projected security events against the protected source. Record gaps and observed RPO/RTO.
Reconnect approved clients/controllers individually, validate TLS/SSO and authorization, then
   enable new backups and independent health detection. Never give Tier 1 recovery identities Tier 0
   archive deletion, infrastructure provisioning or root custody privileges.

A product without its complete dataset and an executed acceptance record remains unqualified;
reinstalling Helm releases restores software/configuration, not product data.

## References

1. [Harbor Helm/Velero backup and restore](https://goharbor.io/docs/main/administration/backup-restore/)
2. [GitLab Helm restore](https://docs.gitlab.com/charts/backup-restore/restore/)
3. [GitLab backup restore prerequisites](https://docs.gitlab.com/administration/backup_restore/restore_gitlab/)
4. [Barman CNPG recovery](https://cloudnative-pg.io/plugin-barman-cloud/docs/concepts/#recovery-of-a-postgres-cluster)
5. [Grafana configuration, plugins and database backup](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/)
6. [VictoriaMetrics native restore](https://docs.victoriametrics.com/victoriametrics/vmrestore/)
7. [OpenSearch native snapshot restoration](https://docs.opensearch.org/latest/opensearch/snapshot-restore/)
8. [Argo CD disaster recovery](https://argo-cd.readthedocs.io/en/stable/operator-manual/disaster_recovery/)

[1]: https://goharbor.io/docs/main/administration/backup-restore/
[2]: https://docs.gitlab.com/charts/backup-restore/restore/
[3]: https://docs.gitlab.com/administration/backup_restore/restore_gitlab/
[4]: https://cloudnative-pg.io/plugin-barman-cloud/docs/concepts/#recovery-of-a-postgres-cluster
[5]: https://grafana.com/docs/grafana/latest/administration/back-up-grafana/
[6]: https://docs.victoriametrics.com/victoriametrics/vmrestore/
[7]: https://docs.opensearch.org/latest/opensearch/snapshot-restore/
[8]: https://argo-cd.readthedocs.io/en/stable/operator-manual/disaster_recovery/
