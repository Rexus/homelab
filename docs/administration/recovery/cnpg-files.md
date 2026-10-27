# Recover CNPG from PostgreSQL backups on NAS

Recover a selected completed physical backup into a temporary standalone PostgreSQL Job on **new
Proxmox/Ceph block storage**, then clone it into a new CNPG cluster through the supported
`bootstrap.pg_basebackup` interface. The NAS copy remains mounted read-only. This restores the backup
endpoint only; there is no continuous WAL archive or PITR. [1][2]

**Prerequisites:** isolated recovery Kubernetes context with compatible CNPG, original PostgreSQL 17
image/extensions/architecture, enough block capacity for staging plus the new cluster, independently
held application/TLS Secrets and the commissioned NAS identity from [backup setup](../backups/postgresql.md).
Use the exact recorded image from the completed set. The source fixture is 17.6 / CNPG 1.27.0;
this is an API compatibility baseline, not a claim that those old pins are currently supported.

## Contents

- [Prepare isolated inputs](#prepare-isolated-inputs)
- [Render the recovery manifests](#render-the-recovery-manifests)
- [Create and validate](#create-and-validate)
- [Limits](#limits)
- [References](#references)

## Prepare isolated inputs

Keep applications, ingress and GitOps/Helm reconciliation absent. Select an independent recovery
context and create the original product namespace **as a new namespace** there. Do not use a production
context or attach a live CNPG claim. Retain the source set and logs after every failed attempt.

```bash
set -euo pipefail
: "${RECOVERY_CONTEXT:?}" "${PRODUCT_NAMESPACE:?}" "${CLUSTER:?}"
test "${RECOVERY_ISOLATED:-}" = yes
test "${RECOVERY_APPROVAL:-}" = "$RECOVERY_CONTEXT/$PRODUCT_NAMESPACE/$CLUSTER"
kubectl --context "$RECOVERY_CONTEXT" create namespace "$PRODUCT_NAMESPACE"
```

The storage custodian now imports the original NAS file area into that namespace using a new,
retained, read-only NFS CSI PV/PVC. Do not invent a blank claim or rebind any live database volume.
Verify its CSI driver/handle and the three-line marker against independent records. Where recovering
from encrypted offsite custody, first extract the complete selected set and marker into an authorized
read-only recovery export. Never start PostgreSQL directly on a completed NAS set.

Supply these Secrets independently; the backup contains no Kubernetes Secrets:

| Secret | Contents and purpose |
| --- | --- |
| Original application DB Secret | `username`/`password`, original owner/database |
| `<cluster>-file-backup` | Original or reissued `clientAuth` certificate CN `<cluster>-file-backup`, `tls.key`, server trust `ca.crt` |
| `files-restore-server` | Temporary server `tls.crt`, `tls.key`, and issuing server CA `ca.crt`; SAN must cover `<cluster>-files-restore` |
| Client CA Secret | Public `ca.crt` validating the backup client certificate |
| Target CNPG certificates | Reviewed native certificate mapping for the new target; preserve/reissue original leaves as appropriate |

Allow recovery-pod DNS and TCP 5432 only between the temporary source and new CNPG pods; retain CNPG
operator/replica access. There is no public Service/ingress. NAS access is a qualified CSI underlay path.

Create a private `secrets/cnpg-files-recovery.yml` in the owning tier repository. Example for Keycloak:

```yaml
postgresql_file_backup_action: render
postgresql_file_backup_output: secrets/cnpg-files-recovery
postgresql_file_backup_target:
  cluster: keycloak-db
  namespace: keycloak
  image: ghcr.io/cloudnative-pg/postgresql:17.6  # Exact image recorded in the selected set.
  claim: keycloak-db-backups-recovery
  volume_handle: REPLACE_WITH_IMPORTED_NFS_HANDLE
  tls_secret: keycloak-db-file-backup
  source_id: tier-0/keycloak/keycloak-db
  system_identifier: 'REPLACE_WITH_ORIGINAL_SYSTEM_ID'
  marker: REPLACE_WITH_ORIGINAL_RANDOM_MARKER
  schedule: '0 2 * * *'  # Required identity contract only; recovery creates no CronJob.
  accepted: false
postgresql_file_backup_recovery:
  set_id: REPLACE_WITH_COMPLETED_POD_UID
  storage_class: REPLACE_WITH_QUALIFIED_PROXMOX_OR_CEPH_RBD_CLASS
  size: 10Gi
  database: keycloak
  secret: keycloak-db
  server_tls_secret: files-restore-server
  client_ca_secret: keycloak-db-ca
  certificates:
    serverCASecret: keycloak-db-ca
    clientCASecret: keycloak-db-ca
    serverTLSSecret: keycloak-db-server
    replicationTLSSecret: keycloak-db-replication
```

For NetBox use its original names and identity. Grafana uses database/owner `grafana`, application
Secret `grafana-database`, namespace from original inputs, source ID `tier-1/<namespace>/grafana-db`,
and its original server/client CA/replication Secret names. Size from actual backup and disk use.
This focused recipe supports one PGDATA/WAL volume and no user tablespaces.

## Render the recovery manifests

From the owning generated tier root, use its Shared role search path:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, /dev/stdin \
  -e @secrets/cnpg-files-recovery.yml <<'YAML'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - ansible.builtin.include_role:
        name: postgresql_file_backup
        tasks_from: recovery
YAML
```

Review `secrets/cnpg-files-recovery/restore-source.yml` and `restore-cluster.yml`. Rendering makes no
API calls and never creates a target. The first file contains fresh staging PVC `<cluster>-files-stage`,
ConfigMap/Service/Job `<cluster>-files-restore`; the second contains only the new CNPG `Cluster`.

## Create and validate

Recheck the exact context/namespace/cluster approval. The only existing PVC must be the commissioned
read-only recovery source; applications and old DB resources must be absent:

```bash
set -euo pipefail
test "${RECOVERY_ISOLATED:-}" = yes
test "${RECOVERY_APPROVAL:-}" = "$RECOVERY_CONTEXT/$PRODUCT_NAMESPACE/$CLUSTER"
: "${RECOVERY_SOURCE_CLAIM:?Set the commissioned read-only NAS source claim}"
: "${DATABASE_CLASS:?Set the commissioned Proxmox/Ceph RBD class}"
driver=$(kubectl --context "$RECOVERY_CONTEXT" get storageclass "$DATABASE_CLASS" -o jsonpath='{.provisioner}')
case "$driver" in csi.proxmox.sinextra.dev|rbd.csi.ceph.com|*.rbd.csi.ceph.com) ;; *) exit 1 ;; esac
python3 - "$PRODUCT_NAMESPACE" "$CLUSTER" "$RECOVERY_SOURCE_CLAIM" "$DATABASE_CLASS" <<'PY'
import sys, yaml
namespace, cluster, claim, storage = sys.argv[1:]
source = list(yaml.safe_load_all(open('secrets/cnpg-files-recovery/restore-source.yml')))
target = yaml.safe_load(open('secrets/cnpg-files-recovery/restore-cluster.yml'))
assert all(item['metadata']['namespace'] == namespace for item in source + [target])
assert target['metadata']['name'] == cluster
assert set(target['spec']['bootstrap']) == {'pg_basebackup'}
assert target['spec']['storage']['storageClass'] == storage
assert source[0]['spec']['storageClassName'] == storage
job = next(item for item in source if item['kind'] == 'Job')
assert job['metadata']['name'] == cluster + '-files-restore'
assert job['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim'] == {'claimName': claim, 'readOnly': True}
PY
test "$(kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" get pvc -o name)" \
  = "persistentvolumeclaim/$RECOVERY_SOURCE_CLAIM"
existing=$(kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" \
  get clusters.postgresql.cnpg.io,pods,deployments,statefulsets,jobs,cronjobs -o name)
test -z "$existing"
kubectl --context "$RECOVERY_CONTEXT" create --dry-run=server -f secrets/cnpg-files-recovery/restore-source.yml
kubectl --context "$RECOVERY_CONTEXT" create -f secrets/cnpg-files-recovery/restore-source.yml
```

The Job checks marker/source/image, verifies the selected backup and refuses nonempty staging storage.
It copies to new block storage, verifies again, and changes only that staging copy. It moves inherited
`postgresql.auto.conf`/recovery signals aside, uses a complete standalone configuration, and disables
production archive commands, upstream connections and synchronous-standby expectations. It replays
included WAL and becomes ready only after standalone recovery. It never uses `initdb` as a fallback.
Wait on the already created Job's ready-pod count, so asynchronous pod creation does
not make an empty label selection fail early. [4]

```bash
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" wait pod \
  -l "backup.homelab/restore=$CLUSTER" --for=create --timeout=5m
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" wait "job/$CLUSTER-files-restore" \
  --for=jsonpath='{.status.ready}'=1 --timeout=30m
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" logs "job/$CLUSTER-files-restore"
kubectl --context "$RECOVERY_CONTEXT" create --dry-run=server -f secrets/cnpg-files-recovery/restore-cluster.yml
kubectl --context "$RECOVERY_CONTEXT" create -f secrets/cnpg-files-recovery/restore-cluster.yml
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" wait "cluster/$CLUSTER" \
  --for=condition=Ready --timeout=30m
```

CNPG connects with certificate authentication to the temporary source, copies its physical state and
starts an independent primary on fresh claims. The restore manifest has one validation instance,
no archiver and no backup scheduler. Confirm original database/roles, application-critical records,
actual recovered time and missing datasets before any application cutover. Then rebuild the intended
replica count and backup policy through reviewed product manifests; do not apply a fresh `initdb`
recipe or production Helm reconciliation over the recovery target. [1][3]

After validation, stop the temporary server cleanly:

```bash
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" exec "job/$CLUSTER-files-restore" \
  -- touch /work/release
kubectl --context "$RECOVERY_CONTEXT" -n "$PRODUCT_NAMESPACE" wait "job/$CLUSTER-files-restore" \
  --for=condition=Complete --timeout=2m
```

The Job also has a four-hour deadline. Preserve staging, logs and source copies until the incident
custodian explicitly retires them; this procedure performs no automatic deletion or production overwrite.

## Limits

These are supported PostgreSQL physical recovery and CNPG streaming-bootstrap primitives with
repository-owned orchestration, not a native CNPG filesystem backup catalog. Same PostgreSQL major,
binary-compatible architecture/extensions and tested image are required. CNPG's physical-bootstrap
requirements apply; the temporary source intentionally comes from the original CNPG image. [1]

Manifest validation and file verification do not prove live CSI, TLS, CNI behavior or product recovery.
Record isolated application restore results and measured RPO/RTO. NAS files are plaintext unless
storage encryption is separately commissioned; independently encrypted offsite custody is separate.
Credential recovery must work without the failed Keycloak/Grafana/NetBox/Vault services.

## References

1. [CNPG 1.27 physical streaming bootstrap and requirements](https://cloudnative-pg.io/docs/1.27/bootstrap/)
2. [PostgreSQL 17 standalone hot backups](https://www.postgresql.org/docs/17/continuous-archiving.html#BACKUP-STANDALONE)
3. [CNPG 1.27.0 Cluster CRD](https://github.com/cloudnative-pg/cloudnative-pg/blob/v1.27.0/config/crd/bases/postgresql.cnpg.io_clusters.yaml)
4. [Kubernetes Job readiness status](https://kubernetes.io/docs/reference/kubernetes-api/batch/job-v1/) and [kubectl JSONPath waits](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_wait/)
