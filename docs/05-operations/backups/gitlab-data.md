# GitLab data-VM backups

Back up PostgreSQL, Redis and Gitaly from live Proxmox/Ceph VM disks to encrypted restic repositories.
These cold component copies are separate from GitLab Toolbox backups and application object storage.

**Working repository:** generated Tier 1.
**Run configuration on:** the deployment host. **Run checks on:** each existing data VM.
**Prerequisites:** commissioned NAS shares/identities or SFTP service, independent encryption passwords,
approved restic 0.17+ and [accepted data services](../../03-deployment/stage-9-development/procedures/data-services.md#render-and-apply).
**Design:** [backup and recovery](../../01-architecture/24-operations/04-backup-recovery.md).

<a id="contents"></a>

## Operator tasks

- [How to select a destination and schedule?](#select-the-file-destination)
- [How to commission a NAS mount?](#commission-a-nas-mount)
- [How to run, inspect and restore a component copy?](#run-and-restore)
- [When to stop, roll back or prune?](#failure-limits)
- [References](#references)

<a id="select-the-file-destination"></a>

## How to select a destination and schedule?

1. Edit **Tier 1 `ansible/group_vars/development_data.yml`**, using the
   [existing example](../../../tier-1/ansible/group_vars/development_data.yml.example).
   Keep private passwords/keys in the referenced protected files.

   | Field | Set to |
   | --- | --- |
   | `development_data_backup_transport` | `filesystem` for NAS mount, or `sftp` for a qualified SSH file service |
   | `development_data_backup_repository` | A distinct repository per data VM, matching the selected transport |
   | `development_data_backup_filesystem` | NAS mode: exact mount/source/type, marker and effective write UID/GID per VM |
   | Per-host `manage_mount`, `options` | `true` for normal IaC setup; optional safe protocol/tuning list, such as `[vers=4.1, proto=tcp]` |
   | Per-host `credentials_src` | CIFS only: absolute private controller credentials-file path; copied root-only to the VM |
   | `development_data_backup_password_src` | Independently retained encryption-password file |
   | `development_data_backup_ssh_key_src`, `development_data_backup_known_hosts_src` | SFTP mode: scoped private key and independently verified host keys |
   | `development_data_backup_calendar` | Native systemd expression; default `"*-*-* 02:00:00"`, plus up to 15 minutes random delay |
   | `development_data_backup_initialize` | `true` only for explicit one-time initialization of a genuinely empty repository; return to `false` afterwards |
   | `development_data_backup_custody_accepted` | `true` only after independent copy/access/retention responsibilities are accepted |
   | `development_data_backup_timeout_seconds` | Failure deadline; not a guarantee that blocked NFS I/O terminates |

2. For NAS, complete the next task before applying. For SFTP, qualify scoped credentials and
   repository access through the existing service; retain the selected transport on existing projects.
3. Apply via the [data-service installer](../../03-deployment/stage-9-development/procedures/data-services.md#render-and-apply).
   It mounts the client, verifies the independent marker/repository, persists the mount and probes access before scheduling.
   It installs no NAS server or export and never creates/replaces the marker.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":18,"padding":10,"wrappingWidth":350,"subGraphTitleMargin":{"top":8,"bottom":16}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1[" "]
    T1Title["Tier 1 / GitLab data"]
    subgraph VMs["Three existing data VMs / per-host recipe"]
      direction RL
      Disks[("Live Proxmox/Ceph-backed disks<br/>db-1 / PostgreSQL<br/>kv-1 / Redis<br/>repo-1 / Gitaly")]
      Jobs["On each VM<br/>development-data-backup.timer<br/>development-data-backup.service"]
      Disks -->|Cold component copy| Jobs
    end
    T1Title ~~~ VMs
  end
  subgraph T0["Tier 0 / existing storage administration"]
    direction LR
    NAS[("Existing NAS / dedicated exports<br/>Encrypted restic repositories")]
    PVE["Existing Proxmox/Ceph<br/>Live VM disk hosting"]
  end
  VMs -->|Encrypted backup files| NAS
  VMs -. Live disk hosting .-> PVE
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef servicesHeading fill:#e7f0fc,stroke:#e7f0fc,color:#203a5b
  class T1,Jobs services
  class T1Title servicesHeading
  class VMs runtime
  class T0,PVE control
  class Disks,NAS data
```

**IaC + commissioned storage:** Tier 1 [backup tasks](../../../tier-1/ansible/roles/development_data/tasks/backup.yml),
[job](../../../tier-1/ansible/roles/development_data/templates/backup.sh.j2) and
[inputs](../../../tier-1/ansible/group_vars/development_data.yml.example) install one
timer/service per existing data VM. Scope: selected `filesystem` recovery copies,
not GitLab application objects or the SFTP alternative. Proxmox disks, NAS exports,
share identities and independent retention remain existing prerequisites. Client mounts are installed by
[native mount tasks](../../../tier-1/ansible/roles/development_data/tasks/backup-mount.yml).

<a id="commission-a-nas-mount"></a>

## How to commission a NAS mount?

**NAS custodian, then deployment operator:**

1. Prepare a private export/share and capacity budget per host; retain snapshot/pruning
   administration separately. Keep NFS root-squash and qualify UID/GID mapping, or use scoped SMB.
2. On the **NAS**, have the custodian create the private repository directory and
   `.development-data-backup-target` at the mount root with the recorded unique host marker.
   The client validates existing contents; it never establishes its own target identity.
3. Edit **Tier 1 `ansible/group_vars/development_data.yml`**. Supply each host's export/share,
   target path, type, marker and UID/GID. Set `manage_mount: true`. For CIFS, also set
   `credentials_src` to a private controller file with `username=`, `password=` and optional
   `domain=` lines. Keep credentials outside Git; Ansible copies them as root-only files. [4][6]
4. Apply through [the data-service installer](../../03-deployment/stage-9-development/procedures/data-services.md#render-and-apply).
   IaC installs the NAS client, rejects conflicting mount/fstab declarations and nonempty or unreadable
   local targets, mounts, checks the independent marker and repository, then persists the accepted mount.
   Require capacity and create/read/sync/rename/delete probes to pass before any component stops.
5. Verify on the **selected data VM**:

   ```bash
   read -r -p "Configured backup mount: " BACKUP_MOUNT
   findmnt -rn -M "$BACKUP_MOUNT" -o TARGET,SOURCE,FSTYPE,OPTIONS
   sudo systemctl cat development-data-backup.service
   ```

Managed NFS defaults to hard I/O; managed SMB requires encryption and private UID/GID mapping.
Managed mounts are `noexec,nosuid,nodev`.
`nofail` keeps unavailable backup storage from preventing VM boot; the backup service and script still require
the exact NAS mount and marker. Live PostgreSQL/Redis/Gitaly data stays on Proxmox-backed VM disks. [4][5][6]

**Existing commissioned mounts:** `manage_mount: false` retains external mount management and still verifies
the full identity. Legacy CIFS without `credentials_src` follows that verify-only path; a missing mount fails.
Verify-only mode does not upgrade existing mount options.
To adopt CIFS into IaC, provide `credentials_src` and set `manage_mount: true` in an approved maintenance window.

**Stop on mismatch.** Do not enable `no_root_squash`, replace a marker or redirect the job into
a local directory to force success. The role does not change export permissions. A new mount that fails
marker verification remains temporary: correct the approved contract or have the operator unmount it;
the role does not persist that unverified mount or initialize its repository.

<a id="run-and-restore"></a>

## How to run, inspect and restore a component copy?

### 1: Start and check a backup

**On each data VM**, during the approved service-interruption window:

Run on **the selected GitLab data VM during the approved maintenance window**.

```bash
sudo systemctl list-timers --all development-data-backup.timer
sudo systemctl cat development-data-backup.timer
sudo systemctl start development-data-backup.service
sudo systemctl status development-data-backup.service --no-pager
sudo journalctl -u development-data-backup.service -n 80 --no-pager
sudo /opt/gitlab/bin/gitlab-ctl status
```

The job stops its single component, copies it cold, requests restart and runs a repository check.
Verify actual source readiness; a logged restart request is not proof. Three successful component
copies are not an atomic GitLab recovery point. Coordinate them with Toolbox, Secrets and object
buckets in the [product recovery plan](../recovery/tier-1-products.md). [2]

### 2: List and verify retained points

On the selected VM, enter an authorized root shell. Load only the installed root-owned profile:

Run on **the selected GitLab data VM during the approved maintenance window**.

```bash
sudo -i
```

Run on **the selected GitLab data VM as root, using its installed backup profile**.

```bash
set -a
source /etc/development-data/backup.env
set +a
```

For **NAS/filesystem** repositories:

Run on **the selected GitLab data VM as root, retaining the installed profile exports**.

```bash
restic snapshots --json
restic check --read-data
```

For **SFTP**, use the same qualified key/host-key options as the installed job:

Run on **the selected GitLab data VM as root, retaining the installed profile exports**.

```bash
RESTIC_SFTP_ARGS='-i /etc/development-data/backup.key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/development-data/known_hosts'
restic -o "sftp.args=$RESTIC_SFTP_ARGS" snapshots --json
restic -o "sftp.args=$RESTIC_SFTP_ARGS" check --read-data
```

### 3: Extract onto a new isolated target

On an independent recovery host, configure the same repository/password from independent custody;
for SFTP also supply its authorized key and verified host keys. Preserve incident/source data.
That host does not inherit the data VM's root shell, profile exports or `RESTIC_SFTP_ARGS`.

Run on **the independent isolated recovery workstation**.

```bash
set -euo pipefail
read -r -p "Independently recorded restic repository path or URI: " RESTIC_REPOSITORY
read -r -e -p "Independent repository password-file path: " RESTIC_PASSWORD_FILE
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
read -r -p "Full recorded component snapshot ID: " RECOVERY_SNAPSHOT
read -r -p "NEW absolute extraction directory on encrypted recovery storage: " RECOVERY_TARGET
read -r -p "Target isolation verified (yes): " RECOVERY_ISOLATED
test "$RECOVERY_ISOLATED" = yes
[[ "$RECOVERY_SNAPSHOT" =~ ^[a-f0-9]{64}$ ]]
case "$RECOVERY_TARGET" in /*) ;; *) exit 1 ;; esac
umask 077
mkdir -m 0700 "$RECOVERY_TARGET"
```

Choose the configured transport. For NAS/filesystem:

Run on **the independent isolated recovery workstation**.

```bash
restic restore "$RECOVERY_SNAPSHOT" --target "$RECOVERY_TARGET" --verify
```

For SFTP, after configuring that recovery host's credential paths:

Run on **the independent isolated recovery workstation**.

```bash
read -r -e -p "Authorized recovery-host SSH key path (no whitespace): " RECOVERY_SFTP_KEY
read -r -e -p "Verified recovery-host known_hosts path (no whitespace): " RECOVERY_SFTP_KNOWN_HOSTS
test -f "$RECOVERY_SFTP_KEY" && test -f "$RECOVERY_SFTP_KNOWN_HOSTS"
[[ "$RECOVERY_SFTP_KEY$RECOVERY_SFTP_KNOWN_HOSTS" != *[[:space:]]* ]]
RESTIC_SFTP_ARGS="-i $RECOVERY_SFTP_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$RECOVERY_SFTP_KNOWN_HOSTS"
restic -o "sftp.args=$RESTIC_SFTP_ARGS" restore "$RECOVERY_SNAPSHOT" --target "$RECOVERY_TARGET" --verify
```

`mkdir` must succeed on a new path. Never overwrite running PostgreSQL files.
Inspect/decrypt the extracted set before the matching-version
[GitLab native recovery](../recovery/tier-1-products.md). [1][2]

<a id="failure-limits"></a>

## When to stop, roll back or prune?

| Condition | Required action |
| --- | --- |
| NAS/SFTP loss, full storage, wrong mount or marker | Fail closed; no local fallback or automatic deletion |
| Cold backup blocks past its deadline | Investigate actual source readiness; hard NFS I/O can remain blocked despite termination |
| Schedule must pause | `sudo systemctl stop development-data-backup.timer`; an active service is separate |
| Invalid changed schedule or credentials | Restore accepted input values, reapply the installer and prove repository access before resuming |
| Restore/consistency check fails | Preserve failed target and retry on another clean isolated target after diagnosis |
| History or credentials require retirement | Separate backup/storage custodian reviews independent copies and holds first |

Use the [custodian retention review](control-applications.md#custodian-retention) with this
repository's environment and explicit snapshot ID. The installed job performs **no forget/prune**.
A repository password protects confidentiality, not retention: writable backup credentials,
host root or NAS administrators may still alter/delete history despite the job's lack of pruning.
Record actual schedule/outage behavior, accepted RPO/RTO and independently retained copies.

## References

1. [Restic mounted-file and SFTP repositories](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html).
2. [GitLab backup/restore requirements](https://docs.gitlab.com/administration/backup_restore/).
3. [Restic native restore verification](https://restic.readthedocs.io/en/stable/050_restore.html).
4. [Native Ansible mount lifecycle](https://docs.ansible.com/ansible/latest/collections/ansible/posix/mount_module.html).
5. [NFS hard-mount behavior](https://man7.org/linux/man-pages/man5/nfs.5.html).
6. [SMB credentials and encryption](https://manpages.debian.org/trixie/cifs-utils/mount.cifs.8.en.html).
