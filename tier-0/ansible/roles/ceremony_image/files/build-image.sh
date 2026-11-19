#!/usr/bin/env bash
# Product CLI boundary: Ansible owns inputs/packages; native live-build owns the OS image.
set -euo pipefail
work=$1
revision=$2
[[ "$work" == "/var/lib/ceremony-build/$revision" && "$revision" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]{0,47}$ ]] || exit 1
exec 9>"$work/.build-lock"
flock -n 9 || { echo 'This revision is already building.' >&2; exit 1; }
cd -- "$work"
python3 ./public-inputs.py seal "$work"
if [[ -f complete ]]; then
  sha256sum --check --strict "ceremony-$revision.iso.sha256" >/dev/null
  printf '%s\n' unchanged
  exit 0
fi
[[ ! -e started ]] || { echo 'Incomplete build: inspect its log and select a NEW revision; no automatic cleanup.' >&2; exit 1; }
touch started
(
  cd build
  python3 - <<'PY'
import json
import subprocess
from pathlib import Path
recipe = json.loads(Path('../recipe.json').read_text())
subprocess.run(['lb', 'config', *recipe['live_build_arguments']], check=True)
PY
  lb build
) >build.log 2>&1 || { tail -n 50 build.log >&2; exit 1; }
cp -- build/live-image-amd64.hybrid.iso "ceremony-$revision.iso"
dpkg-query --admindir="$work/build/chroot/var/lib/dpkg" --show \
  --showformat='${binary:Package}\t${Version}\n' >"ceremony-$revision.packages.txt"
python3 - "$revision" <<'PY'
import json
from pathlib import Path
import sys
revision = sys.argv[1]
record = json.loads(Path('recipe.json').read_text())
record['inputs_sha256'] = Path('inputs.sha256').read_text().strip()
record['security_scope'] = 'Public read-only live OS; no Secure Boot or TPM attestation qualification.'
Path(f'ceremony-{revision}.build.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
PY
sha256sum "ceremony-$revision.iso" "ceremony-$revision.packages.txt" \
  "ceremony-$revision.build.json" >"ceremony-$revision.iso.sha256"
touch complete
printf '%s\n' built
