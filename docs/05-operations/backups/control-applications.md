# Control application recovery copies

Schedule Vault Raft snapshots and encrypted restic copies of selected original inputs/media
on an independent recovery host. Database backups retain their [separate scheduler](postgresql.md).

**Working repository:** generated Tier 0.
**Run installation on:** the deployment host; run operational checks on the `control_recovery` host.
**Design:** [backup/recovery boundaries](../../01-architecture/24-operations/04-backup-recovery.md).
**Prerequisites:** independent Linux/systemd host, Python 3.9+, verified matching Vault CLI,
commissioned read-only input exports, initialized independent restic repository and retained password/ID,
verified private Vault TLS and an independent HTTPS dead-man monitor.
The role supports Debian and RedHat families; install the declared Ansible collections first.

<a id="contents"></a>

## Operator tasks

- [How to select protected datasets?](#custody-and-scope)
- [How to authorize scheduled Vault snapshots?](#commission-snapshot-authentication)
- [How to install or change the schedule?](#configure-and-schedule)
- [How to run a backup and check success?](#operate-and-verify)
- [How to list, inspect and restore a recovery point?](#list-and-restore)
- [How to rotate credentials or retire old copies?](#custodian-retention)
- [When to stop or roll back?](#stop-and-rollback)
- [References](#references)

<a id="custody-and-scope"></a>

## How to select protected datasets?

| Dataset | Required selection |
| --- | --- |
| Vault | Native `vault operator raft snapshot save` and `inspect`; not a live Raft-volume copy [1] |
| Original inputs/state | Bounded marked read-only exports from actual provisioning owners; explicit ignored paths |
| NetBox media, optional | Authorized read-only view of the actual media volume/snapshot, separate reader identity and source marker |
| NetBox/Keycloak databases | [Scheduled NAS sets](postgresql.md) or existing object/WAL path; no duplicate DB scheduler here |
| Logs, FreeIPA, issuer, etcd, Tier 1 | Their own [product procedures](../recovery/README.md) |

1. Commission [input transport](../recovery/input-custody.md) from the actual owner;
   a Git clone and arbitrary recovery-host directories are insufficient.
2. Keep console, DNS/time, passwords, CA trust and keys independent of the failed platform.
   Use encrypted root-only staging. Repository write credentials and host root can still alter/delete
   file-backed history; this job's lack of pruning does not prevent that.
3. If selecting NetBox media, have the storage owner supply `.control-backup-source` and a
   consistent snapshot, or hold application writes while capturing the paired DB/media point.
   A client-side `ro` mount does not freeze server writes. Record both IDs and their time gap.
4. Leave media disabled without that authorized view. Accepting transport alone does not
   establish complete NetBox recovery.

<a id="commission-snapshot-authentication"></a>

## How to authorize scheduled Vault snapshots?

1. Follow [certificate snapshot authentication](../recovery/vault-backup-auth.md).
   Use an independently approved client CA/profile; OpenXPKI's server-only profile is insufficient.
2. Qualify end-to-end client TLS to the private Vault listener. Ordinary HTTP-terminating
   ingress does not carry the backup client's certificate. [2]
3. Select certificate auth or a maintained AppRole. The job requires exactly the snapshot policy,
   a nonperiodic service token with remaining TTL and explicit maximum lifetime of 60–3600 seconds,
   and the certificate token's configured CIDRs. Broad/default/root/identity policies are rejected.
4. Keep issuance, renewal and SecretID rotation with their custodians. Minted tokens are revoked
   after capture, including inspection failure; no renewal or root-token fallback exists.

`static-token-local` is a separately accepted one-off path. It requires a protected token file,
accepts the same narrow short-lived token and leaves the timer stopped/disabled. It neither renews
nor revokes that externally supplied token. Return to managed auth for scheduled operation.

<a id="configure-and-schedule"></a>

## How to install or change the schedule?

1. Have the repository custodian initialize only an approved empty target and independently record
   `restic cat config` → full `id` and password. This role never initializes repositories.
2. Add the existing host to **Tier 0 `ansible/inventory/hosts.yml` → `control_recovery`**.
   No VM is provisioned by this recipe.
3. From the Tier 0 root, create the local configuration if absent:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   cp -n ansible/group_vars/control_backup.yml.example ansible/group_vars/control_backup.yml
   chmod 600 ansible/group_vars/control_backup.yml
   ```

4. Edit **`ansible/group_vars/control_backup.yml`**:

   | Field | Set to |
   | --- | --- |
   | `control_backup_independent_host_accepted` | `true` only after independent access/recovery checks |
   | `control_backup_repository`, `control_backup_repository_id` | Exact existing mounted path and full recorded repository ID |
   | `control_backup_password_file`, `control_backup_vault_ca_file` | Protected absolute controller-side files |
   | `control_backup_vault_binary` | Verified release-matched host CLI; default `/usr/local/bin/vault` |
   | `control_backup_vault_*` | Auth role, end-to-end TLS, client files and actual permitted source CIDRs |
   | `control_backup_input_sources`, `control_backup_inputs` | Marked read-only exports and explicit ignored selections below those mounts |
   | `control_backup_media_*` | Enable only for a qualified authorized media view |
   | `control_backup_calendar` | Native systemd expression; default `hourly` |
   | `control_backup_watchdog_url` | Independent HTTPS dead-man capability URL |

5. Install, or reapply after a schedule/credential edit:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/control-backup.yml -e @ansible/group_vars/control_backup.yml
   ```

The [role](../../../tier-0/ansible/roles/control_backup/tasks/main.yml) installs native tools,
root-only credential/config files, read-only input/media mounts, service and persistent timer.
It requires a successful first backup before enabling the schedule. The timer adds up to 60 seconds
of random delay. Wrong/missing repositories fail closed. [3][4]

<a id="operate-and-verify"></a>

## How to run a backup and check success?

Run these steps on **the independent `control_recovery` host**.
The receipt examples use the default `control_backup_directory`. If overridden, read the installed
`/etc/control-backup/config.json` and substitute its `directory` value.

### 1. Check the installed schedule

```bash
sudo systemctl list-timers --all control-backup.timer
sudo systemctl cat control-backup.timer
```

Expect the approved calendar and an upcoming run for managed certificate/AppRole authentication.
`static-token-local` deliberately leaves the timer stopped/disabled.

### 2. Run one backup

```bash
sudo systemctl start control-backup.service
```

Wait for completion. On failure, inspect Step 3 and [stop conditions](#stop-and-rollback) before retrying.

### 3. Read the service result

```bash
sudo systemctl status control-backup.service --no-pager
sudo journalctl -u control-backup.service -n 80 --no-pager
```

This is a oneshot service; `inactive (dead)` after successful completion is normal.
Require successful completion in the service/journal, then check its receipts.

### 4. Check the success receipts

```bash
sudo cat /var/lib/control-backup/health.json
sudo cat /var/lib/control-backup/last-success.json
```

Require fresh `ok: true`, the full restic snapshot ID in `restic_snapshot` and Vault/manifest hashes.
Retain the repository ID separately from the snapshot receipt; it is pinned by
`control_backup_repository_id`, not included in `last-success.json`.
The job inspects the native snapshot, verifies digests and runs `restic check` before publishing success.
Nonzero/partial restic exit 3 fails. [5]

A kernel lock serializes systemd and direct CLI runs. Failed ordinary runs preserve last success
but write `ok: false`; crashes or failures before Python starts can leave stale status.
Monitor timestamp age and missed external pings, not file presence.

### 5. Confirm independent monitoring and source age

In **the independent dead-man monitor**, require a current health ping.
Record set age, input-source age, media/DB pairing and observed RPO/RTO.
A fresh restic timestamp does not prove its source export is current.

### 6. Prove the retained copy can be read and restored

Use [repository checks and selection](#list-and-restore) below for periodic read-data checks,
then run [isolated product restores](../recovery/README.md).
A successful file check does not prove application consistency.

<a id="list-and-restore"></a>

## How to list, inspect and restore a recovery point?

### 1. Open an authorized root shell

Run on the independent **`control_recovery`** host.

```bash
sudo -i
```

### 2. Select and verify the repository

Run on **the independent `control_recovery` host as root**:

```bash
export RESTIC_REPOSITORY="$(python3 -c 'import json; print(json.load(open("/etc/control-backup/config.json"))["repository"])')"
export RESTIC_PASSWORD_FILE=/etc/control-backup/restic.password
restic cat config
```

Compare its full repository ID with independently retained records. Stop on a mismatch.

### 3. List recovery points

In **the same root shell**, retain the repository exports above:

```bash
restic snapshots --tag control-recovery --json
```

Select the full snapshot ID from independently retained records.

### 4. Check stored data

In **the same root shell**:

```bash
restic check --read-data
```

Require success before extraction. Diagnose corruption against independent copies; do not overwrite history.

### 5. Inspect the selected snapshot

In **the same root shell**:

```bash
read -r -p "Full recorded snapshot ID: " RECOVERY_SNAPSHOT
restic ls "$RECOVERY_SNAPSHOT"
```

### 6. Extract to a clean target and restore the product

Follow [clean extraction](../recovery/files.md), then the product-specific restore.
During a total outage, supply repository/password from independent custody rather than fetching
them from Vault or relying on this host's installed files.

<a id="custodian-retention"></a>

## How to rotate credentials or retire old copies?

**Credential rotation:**

1. Have the CA/Vault custodian provision the replacement identity and update the pinned role;
   follow [rotation checks](../recovery/vault-backup-auth.md#rotate-and-verify).
2. Edit controller-side credential paths in `control_backup.yml` and reapply the installation command.
3. Require a new inspected backup, independent copy and health ping before retiring the old identity.
   Keep the approved old files/role selection for rollback until acceptance.

**Retention — separately authorized repository custodian only:**

1. Verify the exact repository, independent copy, expiry policy and absence of incident/legal holds.
   Ordinary backup/query identities are not authorized to perform retention operations.
   Writable file credentials may nevertheless permit deletion; enforce independent protection
   on storage/copies rather than inferring it from the job's command list.
2. With that custodian's repository access configured, preview one explicit full snapshot ID:

   Run on **the independently authorized retention-custodian host**.

   ```bash
   read -r -p "Full snapshot ID approved for retirement: " RETIRE_SNAPSHOT
   restic snapshots --json
   restic forget "$RETIRE_SNAPSHOT" --dry-run
   restic prune --dry-run
   ```

3. Review the selected ID before any real `forget`; review another `prune --dry-run` after
   forgetting to see newly unreferenced data. Only the custodian executes approved deletion
   through native restic, then `restic check`. Pruning locks the repository and needs a
   nonoverlapping maintenance window. [6]

The role deletes **no source files, pending sets, local snapshots or repository history**.
Retention/pruning is not scheduled by this installer. Local staging cleanup is a separate explicit
custodian decision; retain required receipts and independently accepted copies.

<a id="stop-and-rollback"></a>

## When to stop or roll back?

| Condition | Action |
| --- | --- |
| Wrong repository/mount/marker or unavailable source | Stop; correct custody/transport, never initialize or replace a marker to force success |
| Auth, expiry or CIDR check fails | Repair/rotate the narrow identity; no downgrade to broader credentials |
| NAS full or source/backup age exceeds the objective | Alert independently; preserve failed sets and arrange authorized capacity/retention action |
| Schedule must pause | `sudo systemctl stop control-backup.timer`; this does not terminate a running service |
| Failed rotation | Restore the approved prior credential 06-paths/role pin and reapply; prove a fresh backup before resuming normal operation |
| Extraction/product restore fails | Preserve the failed target and use another clean target after diagnosis |

Resume a deliberately paused managed-auth timer with `sudo systemctl start control-backup.timer`
only after the cause is corrected. Never enable it in static-token break-glass mode.

## References

1. [Vault native Raft snapshot commands](https://developer.hashicorp.com/vault/docs/commands/operator/raft).
2. [Vault certificate authentication](https://developer.hashicorp.com/vault/docs/auth/cert).
3. [Ansible native mount module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/mount_module.html).
4. [Ansible native systemd service module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/systemd_service_module.html).
5. [Restic backup file selection and exit status](https://restic.readthedocs.io/en/stable/040_backup.html).
6. [Restic retention, preview and pruning](https://restic.readthedocs.io/en/stable/060_forget.html).
