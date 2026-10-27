#!/usr/bin/env python3
"""Restore one explicit restic snapshot into a new directory; never restore in place."""

import argparse
import os
from pathlib import Path, PurePosixPath
import re

from control_backup_io import run


def restore(snapshot, target, subfolder=None):
    if not re.fullmatch(r'[a-f0-9]{64}', snapshot):
        raise ValueError('select a full recorded snapshot ID, never latest')
    target = Path(target)
    if not target.is_absolute() or target.parent.resolve() != target.parent:
        raise ValueError('target requires an existing canonical absolute parent')
    if subfolder:
        folder = PurePosixPath(subfolder)
        if not folder.is_absolute() or '..' in folder.parts or ':' in subfolder:
            raise ValueError('subfolder must be an absolute path within the snapshot tree')
    # mkdir is the no-overwrite guard. A failed attempt is never reused automatically.
    target.mkdir(mode=0o700)
    run(['restic', 'check', '--read-data'], timeout=18000)
    selector = f'{snapshot}:{subfolder}' if subfolder else snapshot
    run(['restic', 'restore', selector, '--target', str(target), '--verify'], timeout=18000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--subfolder', help='Optional exact snapshot-tree path from restic ls')
    parser.add_argument('--approve-clean-target', required=True, action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    restore(args.snapshot, args.target, args.subfolder)
