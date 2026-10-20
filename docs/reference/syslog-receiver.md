# Syslog receiver contract

Tier 0 owns `ansible/roles/syslog_ng/`, the `foundation_logging` inventory and
receiver inputs. Shared supplies only baseline/execution code. Deployment is in
[Stage 1 receiver setup](../deployment/stage-1-logging/receiver.md); the
[evidence design](../architecture/operations/security-logging.md) owns retention and trust boundaries.

## Contents

- [Guest identity](#guest-identity)
- [Inputs](#inputs)
- [Files and records](#files-and-records)
- [Runtime boundaries](#runtime-boundaries)
- [Validation](#validation)
- [References](#references)

## Guest identity

The starter uses `log-1`, with optional `log-2`, as stable logical keys in Tier 0's
`vm_instances`, Ansible inventory and `platform_host_ips`. Environment prefixes or
suffixes come from `ansible/group_vars/all.yml`; deployment stages are not guest-name prefixes.
`syslog` remains the deployment/state entry point. The existing `foundation_logging`
Ansible group and recipe paths remain compatible selectors, not a deployed namespace.

Existing installations keep their current keys, including earlier `foundation-log-1`
and `foundation-log-2` selections. Terraform uses map keys to identify module instances;
changing a key is not merely changing a display label. [3] Refresh preserves local
inventory, inputs and state; it does not rename live guests or move state.
Any deliberate rename also requires review of DNS, TLS identities, producer stream
names and collector archive paths. Preserve historical evidence and credentials.

## Inputs

Defaults live in Tier 0 `ansible/roles/syslog_ng/defaults/main.yml`; operational
overrides stay in ignored Tier 0 group/host vars, never Shared.

| Input | Default / contract |
| --- | --- |
| `syslog_ng_data_mount`, `syslog_ng_data_uuid` | `/srv/security-logging`; UUID required, prepared independent writable XFS/ext4 filesystem |
| `syslog_ng_min_free_mb` | 2048; startup/deployment gate, not continuous quota or alarm |
| `syslog_ng_sources` | Empty, blocks deployment; entries: `name`, observed IPv4 `address`, numeric `tier` 0/1/2, exact `tls_dn` with matching CN |
| `syslog_ng_legacy_sources` | Empty, no UDP; explicit accepted entries: `name`, `address`, `tier`; names unique across both lists |
| `syslog_ng_listen_address` | Inventory host address; explicit non-wildcard IPv4 only |
| `syslog_ng_tls_port`, `syslog_ng_udp_port` | 6514 / 514; UDP exists only with legacy sources |
| `syslog_ng_tls_ca_src`, `syslog_ng_tls_cert_src`, `syslog_ng_tls_key_src` | Execution-host files from `SYSLOG_NG_TLS_CA_FILE`, `SYSLOG_NG_TLS_CERT_FILE`, `SYSLOG_NG_TLS_KEY_FILE` |
| `syslog_ng_tls_crl_src` | Optional externally supplied signed CRL from `SYSLOG_NG_TLS_CRL_FILE`; required by the supplied independent-authority main path; native hashed CRL directory, receiver restart on change |
| `syslog_ng_manage_firewall`, `syslog_ng_firewall_zone` | `true`, `public`; firewalld must already run; select the interface's actual zone |
| `syslog_ng_queue_bytes` | 268435456 per destination; budget for every active source/date writer and backlog, not total archive capacity |
| `syslog_ng_max_message_bytes`, `syslog_ng_max_connections` | 65536 / 100; oversize behavior must be tested against the selected producer/framing |
| `syslog_ng_read_group` | `security-log-readers`; membership is separately governed, never automatically granted |

## Files and records

| Location | Purpose and permissions |
| --- | --- |
| `/etc/syslog-ng-receiver/` | Root-owned config/TLS; service group read only; separate from vendor config |
| `/srv/security-logging/records/<source>/<UTC receive date>.jsonl` | Portable local staging, service-owned `0640`, directories `0750`; paths use only catalogued names |
| `/srv/security-logging/source-catalogue.json` | Root-owned source/tier/transport mapping, readable by reader group; prior versions backed up on change |
| `/srv/security-logging/.state/` | Private `0700` reliable queues and persist file; not the readable archive |
| `/run/syslog-ng-receiver/` | Private runtime control socket/PID; no general reader access |

Native JSON encoding preserves framed `raw` messages alongside best-effort parsed
`message`, `reported_at`, `reported_host`, reception time and actual peer metadata.
`source`, `source_tier` and `transport` come from the server catalogue, not submitted labels.
Malformed syslog is retained in `raw`; normalization errors do not authorize its contents.
Transport framing is not included in `raw`; binary packet capture is a separate requirement. [1]

For synthetic drill exports, use `--message-field message` with the
[record checker](logging-evidence.md), retaining raw segments and metadata separately.
`reported_*` values are source assertions; only reception time is receiver-generated.
UDP records have no authenticated peer CN. A relay is the authenticated source; this
does not cryptographically authenticate every device behind it.

## Runtime boundaries

| Control | Supplied behavior / remaining limit |
| --- | --- |
| Host logger | No local socket/journal consumption or OS logger changes; running/enabled vendor daemon blocks adoption; unused vendor unit masked; configure OS forwarding separately |
| Storage safety | Exact mount/UUID/device/free-space preflight; systemd mount requirement; no formatting, retention deletion or queue pruning |
| TLS | Trusted client chain plus exact subject allowlist and observed-IP/CN routing; first CA validity/constraint and server validity/key checks before file copy; no automatic issuance |
| Host isolation | Dedicated non-login service user, read-only system, limited bind capability and native SELinux labels/ports; policy remains enabled |
| Network ACL | Narrow per-source host rules; no automatic removal of stale/pre-existing broader firewall rules; review gateway and host rules on source removal |
| Local delivery | File flush per record, `fsync(yes)`, reliable disk buffer and flow control; storage/controller behavior still matters [2] |
| Archive custody | Local files remain mutable; separate [NAS pipeline recipes](logging-pipeline.md) supply checkpoints, independent encrypted backup and audited file views. NAS snapshot/access administration and optional locks remain outside this receiver role |
| HA / quotas / analytics | No replication, multi-host commit, per-tenant filesystem quotas, external alerts or Tier 1 forwarding installed |

Disk buffers are delivery queues, not replicated commit receipts or protected retention.
TCP/TLS acknowledgement does not prove that required archive copies survived a fault.
Queue mode/path or source removal with undrained data can strand backlog; preserve
persist files and drain under the product procedure before changing them. [2]
File destinations and evidence grow until governed retention/capacity controls intervene.
Do not regard connection/message limits as per-source rate or disk quotas.

## Validation

Upstream `tests/test_tier_syslog_receiver.py` checks generation/ownership and safety
contracts. On Linux, setting `SYSLOG_NG_TEST_BINARY` enables isolated native TLS,
raw/parsed record, wrong-client/origin, explicit UDP and process-crash/restart tests.
Jinja2 (included with Ansible) renders the real receiver template; Ansible with
`community.crypto` also checks certificate/key validation against disposable certificates.
`SYSLOG_NG_TEST_MODULE_PATH` optionally selects extracted matching modules.
These tests use temporary files and loopback ports, never installed system services.
Use a 4.11+ receiver for first-batch interoperability: earlier syslog-ng releases can
omit the TLS identity on an entire first read batch. A passing orderly-closing Python
client test alone does not cover that defect.

Native process checks are not EL host deployment, SELinux enforcement, physical
power-loss, bounded-full-disk, independent backup or WORM acceptance. Record those
separately with the [operator drill](../administration/logging-drill.md).

## References

Sources checked 2026-10-17.

1. [syslog-ng macros, raw messages and TLS peer metadata](https://syslog-ng.github.io/admin-guide/110_Template_and_rewrite/000_Customize_message_format/004_Macros_of_syslog-ng.html)
2. [syslog-ng file flush, disk buffering and persistence constraints](https://syslog-ng.github.io/admin-guide/070_Destinations/040_File/000_File_destination_options.html)
3. [Terraform instance identity with `for_each`](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each)
