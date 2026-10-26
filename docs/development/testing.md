# Repository testing

Run from the upstream kit root, not a generated tier repository. Tests cover
source/generated ownership, preserved local edits, deployment links, native
configuration and selected product refusal gates. No test suite accepts live
deployment, physical failover, protected retention or disaster recovery.

## Contents

- [Basic suite](#basic-suite)
- [Native checks](#native-checks)
- [Evidence boundary](#evidence-boundary)

## Basic suite

Use the accepted [deployment environment](local-setup.md#deployment-machine),
with Python test dependencies installed in its virtual environment:

```bash
python3 -m pip install -r tests/requirements.txt
python3 -B -m unittest discover -s tests -p 'test_tier*.py' -v
```

The generator needs PyYAML. Native checks need Linux/WSL, the common and selected
tier's collection/Python requirements, and the named product tools. Windows or
missing tools cause explicit skips; inspect the final skip list before reporting
coverage. Tests create disposable files and local test services, not remote resources.

## Native checks

Approve exact packages, checksums and tools before enabling native tests. Keep
them outside tracked source. Some tests fetch pinned charts/CRD schemas over
HTTPS; cached-only product validators use the following explicit paths.

| Check | Environment or tool contract |
| --- | --- |
| Terraform configuration | `terraform` on `PATH`; roots use pinned lock files, mocked resources and no remote backend |
| Platform/control charts | `HOMELAB_NATIVE_CHART_TESTS=1`, native Ansible/Helm and approved repository access |
| Delivery alternatives | Native `kustomize` on `PATH`, in addition to Ansible/Helm |
| Observability charts | `HELM_BINARY`, `OBSERVABILITY_CHART_CACHE` containing the exact `.tgz` packages |
| Collector configuration | `OTELCOL_BINARY`, matching the selected native Collector distribution/version |
| Data Prepper models | `DATA_PREPPER_HOME`, the extracted distribution including its native JDK |
| Database/backup schemas | `CNPG_CRD_CACHE`, pinned CNPG/Barman CRDs for Observability; control-application checks fetch their pinned schemas |
| Cluster security collection | `HOMELAB_NATIVE_SECURITY_LOGGING_TESTS=1`, Ansible/Helm and approved repository access |
| Fluent Bit config, local mTLS and replay | `FLUENT_BIT_TEST_BINARY` with its native library search path where required |
| Native logging patches | `TALOSCTL_TEST_BINARY` (1.13), optional `TALOSCTL14_TEST_BINARY` (1.14) |
| Kubernetes SSO/config preservation | `HOMELAB_TALOSCTL`, the selected Talos 1.13 CLI |

The test modules document additional optional native tools for PKI, receiver,
backup and evidence checks. No real credentials belong in test fixtures. Local
test certificates are disposable and must never become deployment trust anchors.

See [Observability verification](../deployment/stage-8-observability/configuration.md#verification)
for its cached package contract and [diagram verification](diagrams.md#verification)
for visual acceptance. Rendering configuration is not testing network reachability.

## Evidence boundary

Report the revision, command, test count, failures and skips. Distinguish a native
parser/chart/schema test from an actual process/TLS/replay test; neither proves
the site deployment or a complete physical failure envelope.

Live checks belong in the project's deployment/administration records. Accept
each stage's source identities, denied access, storage/queue failures and
clean-target restoration before relying on the resulting capability.
