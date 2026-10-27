# Control application recovery copies

Schedule native Vault Raft snapshots and independently encrypted restic copies on a separately
administered recovery host. The selected database jobs retain ownership of NetBox and Keycloak
database backups. This procedure installs backup transport; live recovery qualification remains required.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** independent Linux host with Python 3.9+, systemd, verified release-matched Vault
CLI, authorized read-only exports of original provisioning inputs, an already initialized restic repository on
an independent mount, its recorded repository ID/password, verified HTTPS to Vault, and an independent
HTTPS dead-man monitor. Install Shared's `ansible.posix` collection through the normal control-node setup.
The role supports Debian and RedHat families when these package/tool prerequisites are available.

## Contents

- [Custody and scope](#custody-and-scope)
- [Commission snapshot authentication](#commission-snapshot-authentication)
- [Configure and schedule](#configure-and-schedule)
- [Operate and verify](#operate-and-verify)
- [References](#references)

## Custody and scope

| Dataset | Source and contract |
| --- | --- |
| Vault | Recovery host pulls with `vault operator raft snapshot save`, then native `inspect`; no raw Raft volume copy [1] |
| Original IaC inputs/state | Recovery host mounts bounded read-only exports from actual provisioning hosts and copies explicit ignored paths into independent restic custody |
| NetBox media | Optional storage-owner-authorized CIFS view, mounted read-only with a separate reader credential and source marker |
| NetBox/Keycloak PostgreSQL | [Selected scheduled full file backups](postgresql.md) or object/WAL path; this transport installs no duplicate database scheduler |
| Logs, FreeIPA, issuer, etcd, Tier 1 | Separate product procedures in the [recovery directory](../recovery/README.md) |

The recovery host must survive the cluster/SSO/GitLab/Vault loss being planned for. Its console,
DNS/time, repository password, CA trust and recovery credentials must work independently. Keep
plaintext staging and local input copies on encrypted host storage with root-only access.
The target repository is separately encrypted by restic. A writable filesystem repository still
trusts recovery-host root; absence of pruning in this job does not enforce immutability.
Commission offline/offsite or retention-locked custody separately under the
[backup policy](../compute/backup-restore.md#backup-policy).

Commission the [original-input transport](../recovery/input-custody.md) on each actual provisioning
host/runner or backend custodian. A Git clone excludes ignored files. Local paths on the recovery host
alone are rejected: selections must be inside configured, marked, read-only source mounts.

For media, authorize an export of the actual NetBox media volume or a storage snapshot of it, not an
arbitrary NAS directory. The storage custodian places `.control-backup-source` containing the agreed
random marker. The job verifies the exact mount, `ro` option and marker before each run. A read-only
client mount does not freeze server-side writes: use a custodian-created consistent snapshot or hold
NetBox writes while capturing the paired media/DB recovery point. Record both IDs and the time gap.
Without an authorized export, leave media disabled and qualify an alternative product/storage backup;
the role does not claim NetBox recovery completeness in that state.

## Commission snapshot authentication

Use native **certificate authentication** for the scheduled job. Commission the dedicated role, pinned
backup client certificate and CIDR binding through [snapshot authentication](../recovery/vault-backup-auth.md).
The client certificate comes from an existing independently approved client CA/profile; the reference
OpenXPKI server-only profile does not supply it. Vault receives the actual client certificate through
an end-to-end private TLS path, not the normal HTTP TLS-terminating ingress. [2]

The job checks self-lookup for exactly the selected policy, including inherited identity policies;
requires a service token with remaining TTL of 60-3600 seconds and explicit max lifetime of 60-3600
seconds; rejects periodic/root/default/broad tokens; verifies the certificate token's exact configured
CIDRs; and revokes minted tokens after snapshot capture, including inspection failure.
No renewal or root-token fallback exists. The job rejects a client certificate within its configured
expiry margin (default seven days); monitor and rotate certificates on the approved monthly/yearly
CA schedule before that margin. AppRole remains an alternative with explicit SecretID rotation.

`control_backup_vault_auth: static-token-local` is **break-glass only**, requiring
`control_backup_vault_static_token_local_accepted: true` and a controller-side
`control_backup_vault_static_token_file`. It accepts the same narrow short-lived service token,
copied locally mode `0600`. Run a single manual backup with an independently supplied token. The
role leaves the timer disabled/stopped in this mode. The job never renews or revokes this token;
return to certificate auth or explicitly maintained AppRole before enabling scheduled backups.

## Configure and schedule

1. Commission the independent mounted repository separately with the native restic CLI. Initialization
   is a one-time custodian operation on an approved empty target; the role has no initialization flag.
   Retain its password independently and record the full `id` returned by `restic cat config`.
2. Add the existing recovery host to `control_recovery` in Tier 0 inventory. This does not provision a
   VM. Set `control_backup_independent_host_accepted: true` only after verifying the independence above.
3. Copy [control_backup.yml.example](../../../tier-0/ansible/group_vars/control_backup.yml.example) to
   the ignored local `ansible/group_vars/control_backup.yml`; supply absolute controller credential
   files, host-local input selections, repository identity, health URL and optional media view.
   Repo paths must be below configured `/mnt/control-inputs-*` mounts, not controller or home paths.
4. From the Tier 0 root, run:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
     -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/control-backup.yml \
     -e @ansible/group_vars/control_backup.yml
   ```

The [role](../../../tier-0/ansible/roles/control_backup) installs native distro restic and supporting
tools, copies credentials mode `0600`, mounts optional media with `ansible.posix.mount`, runs the first
backup, then enables a persistent systemd timer. An existing/wrong/unavailable repository fails closed;
no target is silently initialized. systemd exposes selected inputs read-only and permits writes only
to the backup repository and `/var/lib/control-backup`. [3][4]

| Input | Default / action |
| --- | --- |
| `control_backup_repository`, `*_repository_id` | Required mounted absolute path and full commissioned ID |
| `control_backup_password_file`, `*_vault_ca_file` | Required controller-side files |
| `control_backup_vault_binary` | `/usr/local/bin/vault`; provision a verified compatible CLI separately |
| `control_backup_vault_*` | Verified end-to-end TLS, cert auth/role, expected CIDRs and private client cert/key; alternate auth is explicit |
| `control_backup_input_sources` | Nonempty marked read-only CIFS exports from actual input custodians |
| `control_backup_inputs` | Nonempty explicit `{repo, path}` list below those mounted sources |
| `control_backup_media_*` | Disabled until an authorized source, marker and credential are supplied |
| `control_backup_calendar` | `hourly`; native systemd calendar expression |
| `control_backup_watchdog_url` | Required HTTPS capability URL stored in a root-only curl configuration |

## Operate and verify

```bash
sudo systemctl list-timers control-backup.timer
sudo systemctl start control-backup.service
sudo systemctl status control-backup.service
sudo cat /var/lib/control-backup/health.json
```

Each attempt uses a unique private directory. Only an inspected nonempty snapshot is renamed from
`.pending-*` to its permanent set; SHA-256 and manifest identify the file. Native restic backs up that
set and the selections using a verbatim file list. Any nonzero exit, including partial backup exit 3,
fails the job. `restic check`, a second source digest check and successful external health notification
precede atomic `last-success.json` and `health.json` publication. [5]

An internal nonblocking Linux `flock` protects the entire job for systemd and direct Python CLI runs.
Concurrent invocations exit without changing the active job's health; the kernel releases the lock
after exit/crash. Do not bypass the entry point by importing the orchestration function manually.

Failed ordinary runs write `ok: false` without replacing the last success. Host loss, forced termination
or failure before Python starts can leave old status: monitor timestamp age and missed dead-man pings,
not merely file existence. A lost health notification can occur after a usable backup; inspect restic
and select its recorded ID manually. Local structural checks do not certify restore or live acceptance.
Use periodic `restic check --read-data` and [clean extraction](../recovery/files.md) to verify data.

No run deletes source files, pending sets, snapshots or repository history. Capacity monitoring and
retention decisions belong to an independent custodian; growth eventually requires explicit action.
Record known-good restic ID, Vault hash, media source/DB recovery time, input set age, observed RPO/RTO,
missing datasets and isolated product restore results before accepting the service.

## References

Sources checked 2026-10-26.

1. [Vault native Raft snapshot commands](https://developer.hashicorp.com/vault/docs/commands/operator/raft)
2. [Vault certificate authentication](https://developer.hashicorp.com/vault/docs/auth/cert)
3. [Ansible native mount module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/mount_module.html)
4. [Ansible native systemd service module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/systemd_service_module.html)
5. [Restic backup file selection and exit status](https://restic.readthedocs.io/en/stable/040_backup.html)
