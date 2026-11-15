# Select and extend logging producers

For the first installation, use [Stage 3, Steps 3-5](../README.md#step-3-select-producers).
Each producer owner keeps one `ansible/group_vars/logging_producers.yml`; `host_vars` is an optional
legacy/exception mechanism, not a file that must be created per host.

**Working repositories:** `<prefix>-tier-0` owns the receiver and enrollment;
`<prefix>-tier-1` and `<prefix>-tier-2` own their producer catalogs.

## 1. Prepare tier-owned streams

Edit **`ansible/group_vars/logging_producers.yml`** in the owning tier:

```yaml
log_forwarder_peer: logs.internal.example.com
log_forwarder_target: "{{ log_forwarder_peer }}"
logging_producer_hosts:
  pve01: {}
  ca-1:
    setup: foundation
    streams:
      - {name: ca-1-os, kind: security, input: journal}
      - name: ca-1-audit
        kind: security
        input: files
        files: [/var/log/audit/audit.log]
```

A key selects an existing inventory host; `{}` selects its `<host>-os` journal stream.
An explicit `streams` list replaces that default. Preserve issued stream names on existing producers.
Application streams use separate `kind: application`, `input: files` identities and explicit paths;
a shared security journal is not an application-log filter.
The combined Tier 0 workflow reads `setup` to reuse its existing IP map.

For the infrastructure CA, inspect its installed native logging configuration from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible ca-1 --playbook-dir ansible \
  -i ansible/inventory/hosts.yml -e @ansible/group_vars/all.yml \
  -e @ansible/group_vars/foundation.yml --become \
  -m ansible.builtin.command -a 'cat /etc/openxpki/log.conf'
```

Read the configured audit appender's file path and add that actual path to the selected security file
stream above, alongside the OS audit file when present. Retain `ca-1-os` in the explicit list.
The immutable bundle owns `log.conf`; selecting only the OS journal leaves file-based CA audit records
outside forwarding. Generate a real CA approval/issuance event to verify that file capture in Step 2.

## 2. Install and test forwarding

For selected **Tier 0** producers, run in **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh syslog --ansible-only
```

It enrolls new public CSRs, extends the receiver source catalog and installs forwarding after approval.
Rerun the [acceptance command](../README.md#step-5-verify-collection) after a change.
The test covers native journal capture, TLS identity and retained records. Qualify file capture with
an actual application event; the automated file-stream probe tests its TLS ingestion only.

For **another owning tier**, the shared sender recipe selects its local catalog but does not own
Tier 0 receiver enrollment. Its public handoff requires the [authority interface](producer-trust.md#existing-external-issuer)
and a reviewed Tier 0 source binding before installation. Producer keys stay in their owning hosts.
Do not claim enrollment is complete from a prepared CSR or a running sender alone.

## 3. Extend coverage

| Source | Owner action |
| --- | --- |
| Another Linux/systemd host in Tier 0 | Add its existing inventory key to the catalog and rerun the combined deployment |
| Independent heartbeat | Add a unique private HTTPS `watchdog_url` from the independent monitoring service; omit until available |
| Required independent alerting | Set `log_forwarder_watchdog_required: true`; missing endpoints then block installation |
| Device-native syslog | Configure its native sender through its owning IaC integration; admit only the declared source identity/address |
| Legacy UDP | Explicitly declare `syslog_ng_legacy_sources`; record that the first hop is unauthenticated |
| Application logs | Declare exact files and a separate certificate identity; do not mix application control with security evidence |

## Durability limits

The sender retains a bounded disk queue and journal cursor, without replacing the OS logger.
TCP/TLS queue release is not a committed archive acknowledgement. Rotation, an exhausted queue,
receiver failure and the uncheckpointed tail can lose or duplicate records. Acceptance needs the
[retention choice](../README.md#step-7-protect-retained-records) and measured fault/restore drills.

[Return to deployment](../README.md#step-6-select-receiver-topology).

## References

Logging sources checked 2026-10-19; Ansible inventory checked 2026-11-13.

1. [rsyslog queue durability controls](https://docs.rsyslog.com/doc/concepts/queues.html)
2. [rsyslog full-queue timeout and discard behavior](https://docs.rsyslog.com/doc/rainerscript/queue_parameters.html#queue-timeoutenqueue)
3. [rsyslog native TLS forwarding](https://docs.rsyslog.com/doc/configuration/modules/omfwd.html)
4. [UniFi native system log export](https://help.ui.com/hc/en-us/articles/33349041044119-UniFi-System-Logs-SIEM-Integration)
5. [Ansible inventory: parent/child groups and shared host identities](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html#grouping-groups-parent-child-group-relationships)
