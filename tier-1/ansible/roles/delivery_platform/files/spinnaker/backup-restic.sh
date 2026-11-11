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
    sh "$(dirname "$0")/filesystem-repository.sh" verify
    set --
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
