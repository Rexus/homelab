"""Install the project's checksum-pinned native parser into the CI tool directory."""

import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

root = Path(__file__).resolve().parents[2]
tools = root / '.tmp/architecture-tools'
tools.mkdir(parents=True, exist_ok=True)
record = next(x for x in json.loads((root / 'scripts/architecture/config/toolchain.json').read_text())['downloads']
              if x['name'] == 'pilot.zip')
archive = tools / 'pilot.zip'
if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != record['sha256']:
    with urllib.request.urlopen(record['url'], timeout=120) as response:
        archive.write_bytes(response.read())
if hashlib.sha256(archive.read_bytes()).hexdigest() != record['sha256']:
    raise SystemExit('Native parser checksum differs from the reviewed toolchain')
with zipfile.ZipFile(archive) as package:
    destination = (tools / 'pilot').resolve()
    for name in package.namelist():
        if not (destination / name).resolve().is_relative_to(destination):
            raise SystemExit('Unsafe native parser archive member')
    package.extractall(destination)
print('Prepared checksum-verified SysML native parser')
