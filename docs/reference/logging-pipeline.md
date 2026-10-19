# Logging integration contract

The NAS main path supplies host forwarding, independent producer trust, create-only
checkpoints, audited filesystem views and an independently executed encrypted backup.
It does not supply replicated intake, NAS firmware administration or a search service.
Start with [Stage 1](../deployment/stage-1-logging/README.md), not these implementation details.

## Contents

- [Ownership and entry points](#ownership-and-entry-points)
- [Commit and failure boundaries](#commit-and-failure-boundaries)
- [Storage and access](#storage-and-access)
- [Inputs](#inputs)
- [Tests](#tests)
- [References](#references)

## Ownership and entry points

| Repository | Location inside repository | Responsibility |
| --- | --- | --- |
| Each tier | `ansible/playbooks/deployment/logging-producers.yml`, local inventory/group/host vars | Select host streams and run Shared's role |
| Shared | `ansible/roles/log_forwarder/` | Stateless native rsyslog/journal/file configuration; no inventory or signing key |
| Tier 0 | `ansible/playbooks/deployment/logging-authority.yml`, `ansible/roles/logging_authority/` | Protected controller signing/renewal, cumulative CRL; public CSR approval, no producer key export |
| Tier 0 | `ansible/playbooks/deployment/logging-archive.yml`, `ansible/roles/logging_archive/` | NAS mount, create-only publication, source/copy health, application copies, read-audit rules |
| Tier 0 | `ansible/playbooks/deployment/logging-backup.yml`, `ansible/roles/logging_backup/` | Separate `logging_recovery` host, read-only NAS identity, encrypted restic backup and repository check |

Recipes are Ansible-only integration over existing hosts. They do not add another
Terraform resource/state owner. [Receiver resources](syslog-receiver.md) stay in Tier 0.

## Commit and failure boundaries

| Boundary | What survives / limit |
| --- | --- |
| Native sender disk queue | Process restart within local storage guarantees; item releases on transport submission, not protected commit |
| Receiver local record | Per-record fsync plus reliable local delivery queue; collector/storage/hypervisor can still destroy it |
| NAS checkpoint | Complete JSONL prefixes, chunk hashes, exact byte offsets, source catalogue, previous manifest and UTC creation time; local cursor advances only after NAS file/directory fsync |
| NAS snapshot | Recovery from collector/transfer-account corruption only after a NAS-owned snapshot completes; live SMB files remain writable by its transfer identity |
| Independent restic snapshot | Encrypted recovery copy made by another host with credentials absent from collector; only verified manifest/chunk files included; no automatic forget/prune |

NAS fsync behavior must be qualified on the actual SMB server and stable storage;
a successful client call does not prove protected NAS cache/power behavior. TCP,
checkpoint, snapshot and backup are different boundaries. Define accepted evidence
as the checkpoint covered by the required independently protected copy. Do not
describe all received events as accepted/lossless under this asynchronous profile.

Publication never deletes or overwrites an existing chunk/manifest. Identical chunks
are retries; a partial write or collision fails closed. Preserve/quarantine a damaged
file under custodian approval and restore the known checkpoint before resuming.
Local prefix rewrites fail rather than silently accepting changed history. Hashes
detect changes against retained manifests, not malicious rewriting of every copy.

Producer, checkpoint and backup dead-man URLs ping only after success. Sender probes
check service state, spool headroom and leaf/CRL validity. Missing intake from
required OS streams, stale uncheckpointed records and low receiver/NAS free space
fail the checkpoint health gate. The external monitor must alert on missing pings,
including stopped timers, network loss or a whole-host outage. Configure its allowed
silence from the selected intervals; do not host the only monitor in the platform.

## Storage and access

| Path | Authority |
| --- | --- |
| `/etc/log-forwarder/<stream>/` | Producer root only: private key, public trust/CRL/leaf and native configuration |
| `/var/lib/rsyslog/forwarder/<stream>/` | Producer root only: durable queue and journal/file cursors |
| `/srv/security-logging/` | Tier 0 local staging and receiver source catalogue; existing receiver reader group |
| NAS `<collector>/chunks/<source>/` and `checkpoints/` | Restricted transfer writer; security readers through independently controlled NAS grants; no producer/query credentials |
| `/var/lib/security-logging/checkpoint.json` | Collector root-only cursor; not an end-to-end sender receipt |
| `/srv/application-log-views/<source>/` | Root-owned complete chunk copies; only the approved source's reader group, read-only `0640`/`0750` |
| Independent recovery mount/repository | Recovery custodian only; restic encryption password separately protected |

Only `kind: application` in the **Tier 0 catalogue** may map to an application view.
Journals/audit/CA streams remain security scope. No user is enrolled automatically.
Grant read-only SFTP/export via an approved access path or later Tier 1 projection;
do not grant developers a privileged Tier 0 shell. These files are not an installed
OpenSearch/OIDC query service. Revoke old view access explicitly when changing scope;
historic copies are deliberately not deleted by refresh or role reruns.

Collector audit rules cover raw-record and local-view reads/exports/write attempts.
Forward the actual audit file and test successful/denied reads. NAS reads/snapshot
changes need NAS-side auditing: Linux collector audit does not cover remote NAS clients.
Admin/root/NAS-owner authority is trusted under this profile. OS audit is not invulnerable
to those administrators. Locked-storage custody is the stronger optional boundary.

No automatic local evidence expiry or queue pruning is supplied. Before capacity
exhaustion, approve a retention operation only after snapshot/backup coverage and a
restore are verified; preserve manifests/cursor history and document any retired input.
This deliberate no-delete policy still needs a capacity/retention owner.

## Inputs

Exact defaults live with the named role; local overrides are ignored tier vars.

| Prefix | Required selection |
| --- | --- |
| `log_forwarder_` | Per-host stream name/kind/input/files, receiver address/exact peer, public/request directories, queue and journal budgets |
| `logging_authority_` | Protected directory/passphrase, reviewed CSR fingerprints/profile/SAN, revocation serials; explicit first initialization |
| `logging_archive_` | Encrypted SMB source, independent marker, restricted credential file, snapshot contract, required source identities, free-space/lag/batch budgets, external dead-man URL; optional application source/group map |
| `logging_backup_` | Independent host and prepared mounted repository, read-only NAS source/marker/credential, separately held password file, schedule/dead-man URL; explicit repository initialization |

SMB main-path mounts require 3.1.1 encryption and no executable/suid/device content;
they do not format storage or commission NAS accounts/snapshots. Credential files
contain only the selected service account, never NAS administration credentials.
Secrets and marker/health URLs remain local, not upstream examples or CI output.

## Tests

`test_tier_logging_archive.py`, `test_tier_logging_trust.py` and
`test_tier_syslog_receiver.py` cover generated ownership, native crypto policy,
native TLS forwarding/restart, partial JSONL prefixes, create-only retries,
collisions, forged application classification, offline verification and clean restic restore.
Native tests use temporary files/loopback ports, not installed services.

EL 10 deployment, SELinux/AppArmor, real SMB fsync/snapshots, physical faults, device
buffers, denied reads and alert delivery still require the
[live drill](../administration/logging-drill.md). Source tests do not accept the installation.

## References

Sources checked 2026-10-19.

1. [Native rsyslog TLS and queue controls](https://docs.rsyslog.com/doc/configuration/modules/omfwd.html)
2. [restic backup completion and errors](https://restic.readthedocs.io/en/stable/040_backup.html)
3. [restic restore](https://restic.readthedocs.io/en/stable/050_restore.html)
