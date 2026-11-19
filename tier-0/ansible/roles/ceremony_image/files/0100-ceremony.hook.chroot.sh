#!/bin/sh
# Native live-build chroot hook: public tools only; nothing unlocks or signs at boot.
set -eu
# Bookworm ships cryptenroll, cryptsetup and the FIDO2 plugin in systemd itself.
# These probes need no attached token and perform no enrollment or unlock.
dpkg-query --show --showformat='${binary:Package}=${Version}\n' systemd cryptsetup-bin fido2-tools libfido2-1
cryptsetup --version
systemd-cryptenroll --version | grep -E '^systemd 252( |$)'
systemd-cryptenroll --version | grep -F '+FIDO2'
for option in --fido2-device --fido2-with-client-pin --fido2-with-user-presence; do
  systemd-cryptenroll --help | grep -q -- "$option"
done
test -r /usr/lib/x86_64-linux-gnu/cryptsetup/libcryptsetup-token-systemd-fido2.so
/lib/systemd/systemd-cryptsetup --help
fido2-token -V
python3 - <<'PY'
from pathlib import Path
import plistlib

path = Path('/usr/lib/pcsc/drivers/ifd-ccid.bundle/Contents/Info.plist')
data = plistlib.loads(path.read_bytes())
keys = ['ifdVendorID', 'ifdProductID', 'ifdFriendlyName']
rows = [data[key] for key in keys]
if len({len(row) for row in rows}) != 1:
    raise SystemExit('Malformed CCID reader arrays; refuse publishing an unusable PicoHSM image.')
if not any(v.strip().lower() == '0x2e8a' and p.strip().lower() == '0x10fd'
           for v, p in zip(rows[0], rows[1])):
    for key, value in zip(keys, ['0x2e8a', '0x10fd', 'PicoHSM']):
        data[key].append(value)
    path.write_bytes(plistlib.dumps(data, sort_keys=False))
# live-build's build proxy is a build input, not a runtime ceremony connection.
for path in Path('/etc/apt/apt.conf.d').glob('*'):
    if path.is_file() and '::Proxy' in path.read_text(errors='replace'):
        path.unlink()
PY
for unit in networking.service systemd-networkd.service systemd-networkd.socket \
  NetworkManager.service apt-daily.timer apt-daily-upgrade.timer ssh.service ssh.socket; do
  systemctl mask "$unit"
done
systemctl enable pcscd.socket
truncate -s 0 /etc/machine-id
install -d -m 0755 /mnt/orca-work /mnt/orca-transfer /mnt/orca-backup
# Offline ceremony shells leave no persistent history on later attached custody media.
printf '%s\n' 'export HISTFILE=/dev/null' 'umask 077' > /etc/profile.d/ceremony.sh
if [ -f /usr/share/ceremony/yubihsm-selected ]; then
  command -v yubihsm-shell
  command -v yubihsm-connector
  find /usr/lib -name 'yubihsm_pkcs11.so' -print -quit | grep -q .
  systemctl mask yubihsm-connector.service
fi
