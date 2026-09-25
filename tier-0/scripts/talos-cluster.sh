#!/usr/bin/env bash
set -euo pipefail

# Compatibility entry point for existing project READMEs and CI jobs.
exec bash "$(dirname "${BASH_SOURCE[0]}")/kubernetes-cluster.sh" "$@"
