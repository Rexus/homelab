#!/usr/bin/env bash
set -euo pipefail
# Dedicated CI container only. Do not install a Squid service on a development host.
export DEBIAN_FRONTEND=noninteractive
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod +x /usr/sbin/policy-rc.d
apt-get update
apt-get install -y --no-install-recommends ca-certificates python3 python3-venv openjdk-21-jdk-headless squid gnupg dpkg-dev graphviz git
python3 -m venv .tmp/architecture-tools/venv
.tmp/architecture-tools/venv/bin/pip install -r tests/requirements.txt ansible-core==2.16.14
.tmp/architecture-tools/venv/bin/ansible-galaxy collection install community.general:10.7.9 -p .tmp/architecture-tools/collections
.tmp/architecture-tools/venv/bin/python scripts/architecture/prepare_architecture_ci.py
if ! id model-check >/dev/null 2>&1; then useradd --create-home --uid 10001 model-check; fi
chown -R model-check:model-check .tmp
