#!/usr/bin/env bash
set -euo pipefail
export PATH="$PWD/.tmp/architecture-tools/venv/bin:$PATH"
export HOMELAB_SQUID="$(command -v squid)"
export ANSIBLE_PLAYBOOK="$(command -v ansible-playbook)"
export ANSIBLE_COLLECTIONS_PATH="$PWD/.tmp/architecture-tools/collections"
export SYSML_JAVA="$(command -v java)"
export SYSML_KERNEL="$PWD/.tmp/architecture-tools/pilot/sysml/jupyter-sysml-kernel-0.63.1-all.jar"
export SYSML_LIBRARY="$PWD/.tmp/architecture-tools/pilot/sysml/sysml.library"
export PYTHONPATH="$PWD/tests${PYTHONPATH:+:$PYTHONPATH}"
if [ "$(id -u)" -eq 0 ]; then
  export HOME=/home/model-check
  exec runuser -u model-check --preserve-environment -- python -B scripts/architecture/architecture_ci.py
fi
exec python -B scripts/architecture/architecture_ci.py
