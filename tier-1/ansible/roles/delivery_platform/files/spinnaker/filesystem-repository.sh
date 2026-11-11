#!/bin/sh
set -eu
action="${1:-verify}"
case "$action" in verify|commission) ;; *) exit 1 ;; esac
: "${RESTIC_REPOSITORY:?Missing independent repository}"
: "${RESTIC_PASSWORD:?Missing recovery password}"
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
case "$BACKUP_FILESYSTEM_MARKER" in ''|*[!A-Za-z0-9_-]*) exit 1 ;; esac
test ! -L "$RESTIC_REPOSITORY"
marker="$RESTIC_REPOSITORY/.spinnaker-backup-repository"
if test ! -e "$RESTIC_REPOSITORY"; then
  test "$action" = commission && test "${BACKUP_FILESYSTEM_INITIALIZE:-false}" = true || {
    echo 'Repository absent; explicitly enable filesystem initialization for a new destination' >&2; exit 1
  }
  # Atomic mkdir refuses races, existing empty directories and partial initialization.
  umask 077
  mkdir "$RESTIC_REPOSITORY"
  restic init --repository-version 2
  (set -C; printf '%s\n' "$BACKUP_FILESYSTEM_MARKER" > "$marker")
fi
test -d "$RESTIC_REPOSITORY"
test -f "$marker"
test ! -L "$marker"
test "$(cat "$marker")" = "$BACKUP_FILESYSTEM_MARKER"
test -s "$RESTIC_REPOSITORY/config"
test ! -L "$RESTIC_REPOSITORY/config"
restic cat config >/dev/null
