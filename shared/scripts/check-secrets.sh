#!/usr/bin/env bash
# Guide: docs/development/secret-scanning.md. Run from the owning Git repository.
set -euo pipefail
mode=${1:-history}
command -v gitleaks >/dev/null || { printf 'Install the approved Gitleaks CLI first.\n' >&2; exit 2; }
case "$mode" in
  staged)
    git rev-parse --show-toplevel >/dev/null
    exec gitleaks git --pre-commit --staged --redact --ignore-gitleaks-allow
    ;;
  history)
    git rev-parse --show-toplevel >/dev/null
    exec gitleaks git --redact --ignore-gitleaks-allow --log-opts=--all
    ;;
  artifacts)
    [[ $# == 2 && -d "$2" ]] || { printf 'Usage: check-secrets.sh artifacts DIRECTORY\n' >&2; exit 2; }
    exec gitleaks dir --redact --ignore-gitleaks-allow "$2"
    ;;
  *) printf 'Usage: check-secrets.sh [staged|history|artifacts DIRECTORY]\n' >&2; exit 2 ;;
esac
