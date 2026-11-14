#!/usr/bin/env python3
"""Read the project-only bot credential without putting it into Git URLs or argv."""

from pathlib import Path
import sys

field = "username" if "username" in sys.argv[1].lower() else "password"
print(Path("/git-credential", field).read_text().strip())
