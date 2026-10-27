#!/bin/sh
set -eu
: "${BACKUP_RUN:?Missing backup run identity}"
case "$BACKUP_RUN" in *[!A-Za-z0-9-]*) echo 'Invalid backup run identity' >&2; exit 1 ;; esac
: "${RESTIC_REPOSITORY:?Missing independent repository}"
: "${RESTIC_PASSWORD:?Missing recovery password}"
: "${RESTIC_HOST:?Missing stable backup host}"
staging="${BACKUP_DIRECTORY:-/backup}"
directory="$staging/$BACKUP_RUN"
test -s "$directory/mysql.sql.gz"
test -s "$directory/redis.rdb"
case "${BACKUP_BACKEND:-s3}" in
  s3)
    : "${RESTIC_CACERT:?Missing verified storage TLS trust}"
    set -- --option s3.bucket-lookup=path
    restic "$@" cat config >/dev/null && status=0 || status=$?
    case "$status" in
      0) ;;
      10) restic "$@" init --repository-version 2 ;;
      *) exit "$status" ;;
    esac
    ;;
  filesystem)
    : "${BACKUP_FILESYSTEM_MARKER:?Missing repository custody marker}"
    mount="${BACKUP_FILESYSTEM_MOUNT:-/repository}"
    case "$mount" in /*) ;; *) exit 1 ;; esac
    test ! -L "$mount"
    test "$(cd "$mount" && pwd -P)" = "$mount"
    # A marker alone must never turn an unmounted local directory into a repository.
    awk -v target="$mount" '$5 == target { found=1 } END { exit !found }' /proc/self/mountinfo || {
      echo 'NAS repository mount is absent' >&2; exit 1
    }
    case "$RESTIC_REPOSITORY" in "$mount"/*) ;; *) exit 1 ;; esac
    repository_name="${RESTIC_REPOSITORY#"$mount"/}"
    case "$repository_name" in ''|*[!a-z0-9_-]*) exit 1 ;; esac
    test ! -L "$RESTIC_REPOSITORY"
    marker="$RESTIC_REPOSITORY/.spinnaker-backup-repository"
    test -f "$marker"
    test ! -L "$marker"
    test "$(cat "$marker")" = "$BACKUP_FILESYSTEM_MARKER"
    test -s "$RESTIC_REPOSITORY/config"
    test ! -L "$RESTIC_REPOSITORY/config"
    set --
    restic cat config >/dev/null
    ;;
  *) echo 'Unsupported backup backend' >&2; exit 1 ;;
esac
restic "$@" backup --host "$RESTIC_HOST" --tag spinnaker \
  --tag "$BACKUP_RUN" "$directory"
restic "$@" check --read-data
# Remove staging only after a complete independently stored, verified snapshot.
rm -f "$directory/mysql.sql.gz" "$directory/redis.rdb"
rmdir "$directory"
find "$staging" -name mysql.sql.gz -mtime +"${BACKUP_KEEP_DAYS:-7}" -delete
find "$staging" -name redis.rdb -mtime +"${BACKUP_KEEP_DAYS:-7}" -delete
find "$staging" -mindepth 1 -type d -empty -delete
