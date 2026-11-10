# Storage service prerequisites

Use existing storage through its supported interfaces. Mount a NAS share for file
data; use an existing object-storage endpoint only when the consumer requires an
object API. The reference does not deploy a storage gateway or an additional
storage VM to translate one interface into another.

**Working repositories:** `<prefix>-tier-0` for control databases and protected
archives; `<prefix>-tier-1` for shared applications. Shared provides reusable
execution, not storage resources, inventory or credentials.
**Design:** [storage interfaces](../../../architecture/data/README.md#storage-interfaces).
**Prerequisites:** commissioned storage, scoped access, verified transport and an
independent recovery copy. Storage administration remains a Tier 0 authority.

**Live database data remains on Proxmox/Ceph-backed storage.** NAS backup
destinations receive copies; they do not become the live database volume.

## Contents

- [Step 1: Record live storage and select backup interfaces](#choose-the-native-interface)
- [Step 2a: Prepare NAS file storage](#use-nas-file-storage)
- [Step 2b: Qualify an object endpoint when required](#qualify-an-object-endpoint)
- [Step 3: Verify recovery and return](#recovery-and-existing-installations)
- [References](#references)

<a id="choose-the-native-interface"></a>

## Step 1: Record live storage and select backup interfaces

1. Open **Proxmox > Datacenter > Storage** and record each existing datastore's
   **ID**, allowed **Content** types and eligible **Nodes**. Names alone do not imply features.
2. Select a datastore accepting VM disks for live VM/CloudInit disks. The common
   `local` Import/ISO datastore is not automatically suitable; `local-zfs` is a
   separate datastore ID. Check every selected destination node.
3. During [bootstrap Step 4](../bootstrap/README.md#step-4-configure-trust-credentials-and-platform-inputs),
   map those actual IDs into **Shared `config/platform.tfvars` → `proxmox_storage_classes`**.
   Keep Tier 0's **`templates/proxmox.yml` → `all.image_datastore_id`** pointed at Import storage.
4. Select backup interfaces from the table. Follow **2a**, **2b**, or both as required
   by the selected consumers. Commission each target before its first consumer;
   unrelated foundation work need not wait for future application storage.

| Consumer | Interface used by the supplied implementation | Procedure |
| --- | --- | --- |
| VM/CT backup files | Proxmox-managed NAS NFS target; PBS remains a separate alternative | [Native NAS backup path](../../../administration/backups/virtual-machines.md#nas-file-target) |
| Protected log archive | Direct encrypted SMB mount; local intake remains independent of the NAS | [NAS archive](../../stage-2-logging/step-3c-nas-archive.md) |
| Control recovery copies | Commissioned mounted file repository; read-only source views, separately encrypted backup copies | [Control backups](../../../administration/backups/control-applications.md) |
| NetBox shared media | Existing RWX-capable Kubernetes storage, such as qualified NAS-backed CSI | [Application storage](../../stage-6-secrets/procedures/control-applications.md#dependencies-and-ownership) |
| Keycloak, NetBox and Grafana database backups | Scheduled verified full backups to a separate NAS file PVC; existing object/WAL archive remains an explicit PITR option | [Database backup inputs](../../stage-6-secrets/procedures/control-applications.md#dependencies-and-ownership), [Grafana](../../stage-8-observability/configuration.md) |
| GitLab Kubernetes chart | Existing object storage with ten private versioned buckets; S3-compatible API, including live application objects | [GitLab data services](../../stage-9-development/procedures/data-services.md#prepare-object-storage) |
| GitLab data-VM recovery copies | Encrypted file repository on a commissioned NAS mount or existing SFTP destination | [Data-service backup inputs](../../stage-9-development/procedures/data-services.md#backups-and-recovery) |
| Spinnaker recovery | Existing file repository or object endpoint, selected explicitly | [Backup inputs](../../stage-7-delivery/step-2b-spinnaker.md#step-2-prepare-credentials-and-boundaries) |

GitLab's chart requires object storage for its application objects. The Barman
Cloud path uses object storage for continuous WAL/PITR. A NAS file-backup choice
uses a different implementation and recovers to a completed scheduled backup,
not an arbitrary later time. A mounted share is not an API substitution. [1][2]
Use the [PostgreSQL file-backup procedure](../../../administration/backups/postgresql.md)
for the selected NAS path; it leaves live database storage unchanged.
If the required native interface is unavailable, stop at that prerequisite or
select a separately documented application variant. Do not invent an endpoint.

<a id="use-nas-file-storage"></a>

## Step 2a: Prepare NAS file storage

1. Commission a dedicated export/share and capacity budget on the NAS. Assign
   only the producer, transfer or reader permissions needed by that dataset.
   Select NFS or SMB according to the consumer and the NAS's supported security.
2. Mount it using the consuming procedure or a qualified CSI driver. Verify the
   actual export, expected marker and permissions before enabling writes.
   The logging recipe implements encrypted SMB; an NFS alternative needs explicit
   identity, network and mount qualification, not just a changed URI.
3. Test NAS/network loss, full storage, remount and clean-target restore. A failed
   mount must not redirect writes into an empty local directory. Keep log intake
   on local storage; NAS availability affects archive progress, not its listener.

Use the consumer procedure linked in Step 1 for exact share, mount, credential and
backup inputs. Do not mount a generic NAS path and assume every application uses it.
Continue at **Step 3**, or complete **2b** first if a selected consumer needs object storage.

A mounted repository is file storage even when a backup tool encrypts or
deduplicates its contents. It does not become an object API, immutable archive or
HA service. NAS administrators may retain deletion authority; document that trust
and protect a separate recovery copy. Restic supports file repositories without
an object-storage service. [3]

<a id="qualify-an-object-endpoint"></a>

## Step 2b: Qualify an object endpoint when required

The storage owner supplies an existing private HTTPS endpoint, trusted CA, bucket
names and distinct consumer keys. A supported NAS endpoint or Ceph RGW can meet
this contract; Proxmox RBD, CephFS or an NFS/SMB share alone cannot. This repository
does not install RGW or another gateway as a side effect. See the
[Ceph and UNAS interface distinction](../../../architecture/data/README.md#storage-interfaces).

| Check | Required evidence |
| --- | --- |
| Transport | Trusted certificate, correct server name and permitted consumer sources |
| Client operations | Actual client read/write, listing and multipart operations, plus versioning/encryption where required |
| Isolation | Each consumer denied other tenants' buckets and storage administration |
| Retention | Documented deletion/version policy; API compatibility alone is not Object Lock |
| Availability | Known dependencies and measured outage limits; replication is not inferred |
| Recovery | Independent data, key and configuration copies; clean-target restore tested |

Use the owning installer to qualify its contract. GitLab's `preprovisioned` mode
uses tenant keys only and checks its required S3-compatible data operations and
cross-tenant denial. API-specific input names such as `development_data_s3_endpoint`
remain unchanged; they describe the actual protocol, not an AWS dependency.

<a id="recovery-and-existing-installations"></a>

## Step 3: Verify recovery and return

Keep provisioning state, recovery tools and decryption keys usable without the
storage being recovered. Another bucket/share on the same NAS or Ceph cluster
does not provide an independent failure domain.

No refresh or input change should destroy an existing storage service or move
its data. If an earlier local experiment deployed a gateway, retain its original
state and credentials until its consumers and data are explicitly migrated and
verified. Removing a starter from the reference is not permission to destroy it.

Return to [foundation host/network preparation](../README.md#before-starting-hosts-and-networks).
The first disposable guest's [backup/restore test](../../../administration/backups/virtual-machines.md#quick-steps)
is an acceptance gate before relying on this recovery path.

## References

Checked 2026-10-27; qualify the actual product/software and client versions.

1. [GitLab chart requirements](https://docs.gitlab.com/charts/).
2. [CloudNativePG backup interfaces and WAL requirements](https://cloudnative-pg.io/docs/current/backup/).
3. [Restic file and remote repositories](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).
