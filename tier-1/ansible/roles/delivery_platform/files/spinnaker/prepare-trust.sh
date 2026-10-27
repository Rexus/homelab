#!/bin/sh
set -eu
java_bin=$(readlink -f "$(command -v java)")
java_home=${java_bin%/bin/java}
cp "$java_home/lib/security/cacerts" /trust/cacerts
for authority in identity platform; do
  keytool -importcert -noprompt -trustcacerts -storepass changeit \
    -alias "homelab-$authority" -file "/roots/$authority.crt" -keystore /trust/cacerts
done
