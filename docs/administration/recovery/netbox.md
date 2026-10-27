# Restore NetBox database and media

Recover the existing CNPG database and its paired media dataset before starting NetBox.
**Prerequisites:** [CNPG recovery](cnpg.md), [verified control-copy extraction](files.md), original
NetBox/chart/plugin versions, original configuration and TLS trust.
Retain the original `SECRET_KEY` separately, together with database, cache and OIDC credentials.
NetBox media is a separate dataset from PostgreSQL; match its snapshot to the selected DB time. [1]

## Contents

- [Restore the pair](#restore-the-pair)
- [Start and verify](#start-and-verify)
- [References](#references)

## Restore the pair

1. Fence the original NetBox instance and preserve its disks. In a clean isolated recovery cluster,
   keep web, worker and housekeeping workloads absent; block public ingress and outbound integrations.
2. Restore `netbox-db` through [CNPG](cnpg.md) using the original base backup and WAL archive.
   Record actual recovery time and the selected media/storage snapshot ID. Stop if media is missing
   or the consistency gap exceeds the approved RPO; database readiness does not recover uploaded files.
3. Provision a **new empty media volume**, mounted only on the recovery workstation or authorized
   recovery helper host. Restore the extracted media dataset into it while application writers are
   absent. The backup role intentionally has no Kubernetes exec or writable application-volume access.
   A storage custodian must authorize this separate writable recovery mount.

On the authorized Linux mount host, with native GNU `cp` and `findmnt`:

```bash
set -euo pipefail
umask 077
: "${RESTORED_MEDIA:?Set the extracted media directory}"
: "${NEW_MEDIA_MOUNT:?Set the absolute mountpoint of the NEW volume}"
test "${RECOVERY_APPROVE_MEDIA_COPY:-}" = "$NEW_MEDIA_MOUNT"
test "${RECOVERY_ISOLATED:-}" = yes
test -d "$RESTORED_MEDIA"
test ! -L "$RESTORED_MEDIA"
mountpoint --quiet "$NEW_MEDIA_MOUNT"
test "$(realpath "$NEW_MEDIA_MOUNT")" = "$NEW_MEDIA_MOUNT"
test "$(realpath "$RESTORED_MEDIA")" != "$NEW_MEDIA_MOUNT"
existing=$(find "$NEW_MEDIA_MOUNT" -mindepth 1 -maxdepth 1 -print -quit)
test -z "$existing"
cp --archive --no-clobber "$RESTORED_MEDIA/." "$NEW_MEDIA_MOUNT/"
```

Confirm the source is the actual NetBox media directory, not the complete restic target or its parent.
If the new filesystem contains `lost+found`, use a new empty product subvolume mounted at the selected
target rather than removing existing content. Preserve/check source checksums and file counts, and
set ownership to the pinned chart's actual UID/GID. The CIFS backup view may flatten ownership;
copying it is not proof of original POSIX ownership. Retain the source marker as recovery provenance.

## Start and verify

1. Attach the new media claim to a reviewed release-matched NetBox installation. The
   [owned values template](../../../tier-0/ansible/roles/control_applications/templates/netbox-values.yml.j2)
   identifies database TLS, media persistence, worker and housekeeping settings. Adopt the restored
   DB/claim explicitly; do not run the normal full install playbook against recovery resources.
2. Restore original configuration, SECRET_KEY, plugins and custom scripts/reports separately from
   independently held inputs. Keep plugin versions/schema compatible; perform upgrades only after
   a successful baseline restore. Recreate Valkey with its original verified TLS contract; queued
   tasks require explicit reconciliation instead of blind replay.
3. Start one web replica, then inspect object counts, permission scopes and an actual known uploaded
   image/attachment against its expected hash. Verify relationships, plugin objects, DB TLS, local
   recovery-admin access, OIDC and audit/log delivery. Start workers/housekeeping after reconciliation.
4. Fence the old instance before endpoint cutover, restore the configured topology, create a new
   media/DB recovery pair and record observed RPO/RTO. Missing media must remain an explicit failed
   acceptance item even when the UI and database work.

## References

1. [NetBox replication: database, media and configuration](https://netboxlabs.com/docs/netbox/administration/replicating-netbox/)
