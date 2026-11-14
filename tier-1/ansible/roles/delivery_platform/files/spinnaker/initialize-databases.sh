#!/bin/sh
set -eu
case "${SPINNAKER_DATABASE_ACTION:-initialize}" in
  initialize) ;;
  verify)
    # Adoption, upgrade and recovery must never create missing databases or reset users.
    for service in clouddriver echo fiat front50 orca; do
      mysql --host=spinnaker-mysql --user=root --ssl-mode=VERIFY_IDENTITY --ssl-ca=/roots/platform.crt \
        --database="$service" --execute='SELECT 1' >/dev/null
    done
    exit 0
    ;;
  *) echo 'Unsupported database lifecycle action' >&2; exit 1 ;;
esac
for service in clouddriver echo fiat front50 orca; do
  password=$(cat "/credentials/$service-password")
  migration_password=$(cat "/credentials/$service-migration-password")
  case "$password:$migration_password" in
    *[!a-zA-Z0-9:]* | :* | *:) echo 'Invalid database credential format' >&2; exit 1 ;;
  esac
  mysql --host=spinnaker-mysql --user=root --ssl-mode=VERIFY_IDENTITY --ssl-ca=/roots/platform.crt <<SQL
CREATE DATABASE IF NOT EXISTS \`$service\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${service}_service'@'%' IDENTIFIED BY '$password' REQUIRE SSL;
ALTER USER '${service}_service'@'%' IDENTIFIED BY '$password' REQUIRE SSL;
CREATE USER IF NOT EXISTS '${service}_migrate'@'%' IDENTIFIED BY '$migration_password' REQUIRE SSL;
ALTER USER '${service}_migrate'@'%' IDENTIFIED BY '$migration_password' REQUIRE SSL;
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, EXECUTE, SHOW VIEW
  ON \`$service\`.* TO '${service}_service'@'%';
GRANT ALL PRIVILEGES ON \`$service\`.* TO '${service}_migrate'@'%';
SQL
done
