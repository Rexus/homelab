# Restore a control PostgreSQL database

**Selected method:** object/WAL backups. For scheduled NAS file sets, use
[NAS-file recovery](cnpg-files.md) instead; the two procedures have different recovery limits.

Bootstrap a new CNPG cluster from the existing Barman object-store base backup and WAL archive.
Use this shared procedure for `netbox-db` or `keycloak-db`; the product guides own application
cutover. No second backup scheduler or `pg_dump` path is introduced. [1]

**Prerequisites:** isolated Kubernetes recovery context with compatible CNPG/Barman plugin versions,
the original PostgreSQL image/major version and extensions, new storage capacity, independently held
object-store CA and read-only recovery credentials, original application DB credential, TLS secrets
and a known-good recovery time covered by base backup plus WAL. Preserve the original bucket/prefix.

## Contents

- [Prepare the recovery resources](#prepare-the-recovery-resources)
- [Guard and create](#guard-and-create)
- [Validate and adopt](#validate-and-adopt)
- [References](#references)

## Prepare the recovery resources

Prepare the original product namespace (`netbox` or `keycloak`) in an isolated cluster. Keep application
deployments, jobs, GitOps/Helm reconciliation and public ingress absent. Recreate DB credential and
certificate Secrets from independent custody, or deliberately reissue compromised TLS credentials.
Do not allow secret engines/SSO in the failed cluster to become prerequisites.

Create a private reviewed YAML file with these two documents. Replace example values and choose
`netbox` or `keycloak` consistently. Keep the original `*-db` name so application `*-db-rw` DNS remains
valid. The source ObjectStore has read-only storage credentials and no retention policy/WAL writer.
Use the original backup server name even when recovering to a differently named target. [1]

```yaml
apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata: {name: netbox-db-recovery-source, namespace: netbox}
spec:
  configuration:
    destinationPath: s3://REPLACE-ORIGINAL-BUCKET/PREFIX
    endpointURL: https://REPLACE-OBJECT-STORE
    endpointCA: {name: netbox-db-recovery-source, key: ca.crt}
    s3Credentials:
      accessKeyId: {name: netbox-db-recovery-source, key: ACCESS_KEY_ID}
      secretAccessKey: {name: netbox-db-recovery-source, key: ACCESS_SECRET_KEY}
---
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata: {name: netbox-db, namespace: netbox}
spec:
  instances: 1
  imageName: REPLACE-WITH-ORIGINAL-PINNED-POSTGRES-IMAGE
  enableSuperuserAccess: false
  bootstrap:
    recovery:
      source: original
      recoveryTarget:
        targetTime: 'REPLACE-WITH-APPROVED-RFC3339-RECOVERY-TIME'
  externalClusters:
    - name: original
      plugin:
        name: barman-cloud.cloudnative-pg.io
        parameters:
          barmanObjectName: netbox-db-recovery-source
          serverName: netbox-db
  certificates:
    serverCASecret: netbox-db-ca
    clientCASecret: netbox-db-ca
    serverTLSSecret: netbox-db-server
    replicationTLSSecret: netbox-db-replication
  storage: {storageClass: REPLACE-RECOVERY-CLASS, size: 10Gi}
```

Size storage from original inputs and backup size. `instances: 1` is an isolated validation target,
not an availability claim. A missing WAL segment or unreachable recovery target must be investigated;
do not silently fall back to a more recent/older database or run `initdb`.

## Guard and create

Run from the independent workstation with PyYAML and `kubectl`. Review the context, manifest, source
prefix and incident time first. Set `RECOVERY_APPROVAL` to the exact `context/product` being approved:

```bash
set -euo pipefail
: "${RECOVERY_CONTEXT:?Set the isolated Kubernetes context}"
: "${PRODUCT:?Set netbox or keycloak}"
: "${RECOVERY_MANIFEST:?Set the reviewed two-document YAML path}"
case "$PRODUCT" in netbox|keycloak) ;; *) exit 1 ;; esac
test "${RECOVERY_APPROVAL:-}" = "$RECOVERY_CONTEXT/$PRODUCT"
test "${RECOVERY_ISOLATED:-}" = yes
kubectl --context "$RECOVERY_CONTEXT" get namespace "$PRODUCT"
existing=$(kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT" \
  get clusters.postgresql.cnpg.io,pvc,deployments,statefulsets,jobs,cronjobs,objectstores.barmancloud.cnpg.io -o name)
test -z "$existing"
python3 - "$RECOVERY_MANIFEST" "$PRODUCT" <<'PY'
import sys, yaml
docs = list(yaml.safe_load_all(open(sys.argv[1])))
product = sys.argv[2]
assert len(docs) == 2
store, cluster = docs
assert store['kind'] == 'ObjectStore' and cluster['kind'] == 'Cluster'
assert store['metadata'] == {'name': product+'-db-recovery-source', 'namespace': product}
assert cluster['metadata'] == {'name': product+'-db', 'namespace': product}
assert set(cluster['spec']['bootstrap']) == {'recovery'}
assert cluster['spec']['bootstrap']['recovery']['recoveryTarget']['targetTime']
assert not cluster['spec'].get('plugins') and 'retentionPolicy' not in store['spec']
assert 'REPLACE' not in open(sys.argv[1]).read()
PY
kubectl --context "$RECOVERY_CONTEXT" create --dry-run=server -f "$RECOVERY_MANIFEST"
kubectl --context "$RECOVERY_CONTEXT" create -f "$RECOVERY_MANIFEST"
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT" wait \
  --for=condition=Ready "cluster/$PRODUCT-db" --timeout=30m
```

`create` rejects existing resources; it never patches a live cluster's bootstrap mode or overwrites
claims. A partially failed attempt is not permission to delete or reapply resources: preserve logs,
fence the target and start a new isolated target after diagnosis.

## Validate and adopt

Check recovery logs, actual replay endpoint and DB contents against the incident record. Test the
restored application credential and verified TLS connection before starting the application.
Follow [NetBox](netbox.md) or [Keycloak](keycloak.md) for product checks. Reconcile externally managed
secrets with restored DB credentials; regenerated application passwords do not automatically match
the users in a physical restore.

After acceptance, configure a **new writable backup destination** for the recovered cluster, then
resume WAL/base-backup scheduling through reviewed normal configuration. Never enable retention or
archiving into the recovery source prefix. Restore the original topology and placement from inputs;
validate replication and a fresh backup. Explicitly reconcile Helm/GitOps resources with the recovery
Cluster before resuming automation so the normal `bootstrap.initdb` manifest cannot overwrite it.

## References

1. [Barman plugin recovery through external clusters](https://cloudnative-pg.io/plugin-barman-cloud/docs/concepts/#recovery-of-a-postgres-cluster)
