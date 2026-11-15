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
      10)
        test "${BACKUP_ALLOW_INITIALIZE:-true}" = true || {
          echo 'The accepted independent repository is missing; lifecycle backup cannot initialize it' >&2
          exit 10
        }
        restic "$@" init --repository-version 2
        ;;
      *) exit "$status" ;;
    esac
    ;;
  filesystem)
    sh "$(dirname "$0")/filesystem-repository.sh" verify
    set --
    ;;
  *) echo 'Unsupported backup backend' >&2; exit 1 ;;
esac
mkdir -p "${RESTIC_CACHE_DIR:-/tmp}"
summary="${RESTIC_CACHE_DIR:-/tmp}/spinnaker-backup-$BACKUP_RUN.json"
restic "$@" backup --json --host "$RESTIC_HOST" --tag spinnaker \
  --tag "$BACKUP_RUN" "$directory" > "$summary"
snapshot="$(sed -n 's/.*"snapshot_id":"\([a-f0-9]*\)".*/\1/p' "$summary" | tail -n 1)"
test "${#snapshot}" = 64
case "$snapshot" in *[!a-f0-9]*) echo 'Invalid retained snapshot identity' >&2; exit 1 ;; esac
restic "$@" check --read-data
verification="${RESTIC_CACHE_DIR:-/tmp}/spinnaker-readback-$BACKUP_RUN"
mkdir -p "$verification"
restic "$@" restore "$snapshot" --target "$verification" --verify
# Restore the exact snapshot and compare both native-validated exports before permitting an upgrade.
for export in mysql.sql.gz redis.rdb; do
  retained="$(find "$verification" -type f -path "*/$BACKUP_RUN/$export")"
  test -n "$retained"
  test "$(printf '%s\n' "$retained" | wc -l | tr -d ' ')" = 1
  test "$(sha256sum "$directory/$export" | cut -d ' ' -f 1)" = \
    "$(sha256sum "$retained" | cut -d ' ' -f 1)"
done
if [ -n "${BACKUP_RECEIPT_FILE:-}" ]; then
  printf '%s\n' "$snapshot" > "$BACKUP_RECEIPT_FILE"
fi
# Remove staging only after a complete independently stored, verified snapshot.
rm -f "$directory/mysql.sql.gz" "$directory/redis.rdb"
rmdir "$directory"
find "$staging" -name mysql.sql.gz -mtime +"${BACKUP_KEEP_DAYS:-7}" -delete
find "$staging" -name redis.rdb -mtime +"${BACKUP_KEEP_DAYS:-7}" -delete
find "$staging" -mindepth 1 -type d -empty -delete
