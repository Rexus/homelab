"""Install the pinned official execution CLI into ignored project tooling; verify before extraction."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tarfile
from urllib.request import urlopen
import zipfile


def install(root, selected, archive=None):
    pin = json.loads((root / 'scripts/architecture/config/toolchain.json').read_text())['execution']
    version = pin['version']
    destination = root / '.tmp/tools' / ('opensysml-' + version.removeprefix('v'))
    destination.mkdir(parents=True, exist_ok=True)
    suffix = '.zip' if selected.startswith('windows') else '.tar.gz'
    name = 'opensysml-' + selected + suffix
    if archive is None:
        archive = destination / name
        url = 'https://github.com/Open-MBEE/OpenSysML/releases/download/' + version + '/' + name
        with urlopen(url, timeout=60) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != pin[selected + '-sha256']:
        raise ValueError('Archive checksum does not match the pinned official release')
    executable = 'sysml.exe' if selected.startswith('windows') else 'sysml'
    target = destination / executable
    if suffix == '.zip':
        with zipfile.ZipFile(archive) as bundle:
            matches = [m for m in bundle.infolist() if m.filename == executable and not m.is_dir()]
            if len(matches) != 1:
                raise ValueError('Archive must contain exactly one named runtime')
            with bundle.open(matches[0]) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
    else:
        with tarfile.open(archive) as bundle:
            matches = [m for m in bundle.getmembers() if m.name == executable and m.isfile()]
            if len(matches) != 1:
                raise ValueError('Archive must contain exactly one regular named runtime')
            with bundle.extractfile(matches[0]) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
        target.chmod(0o755)
    print('Installed checksum-verified ' + pin['version'] + ': ' + str(target))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = 'windows-amd64' if platform.system() == 'Windows' else 'linux-amd64'
    parser.add_argument('--platform', choices=('linux-amd64', 'windows-amd64'), default=default)
    parser.add_argument('--archive', type=Path, help='Use an already downloaded official archive; checksum still required')
    args = parser.parse_args()
    try:
        install(Path(__file__).resolve().parents[2], args.platform, args.archive)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
