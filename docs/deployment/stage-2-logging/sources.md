# Connect logging sources

Forward Linux journal, audit and selected application files with isolated native
rsyslog instances. Each stream has its own certificate, cursor and bounded disk
queue. The existing OS logger remains in place; no extra input listener is opened.

**Working repository:** the producer's `<prefix>-tier-0`, `-tier-1` or `-tier-2`.
**Implementation:** Shared `ansible/roles/log_forwarder`; all inputs, hosts, keys and
state remain in the owning tier. Debian/systemd and Red Hat/systemd are supported
branches; qualify the actual OS, SELinux/AppArmor and package build before acceptance.
**Prerequisites:** authenticated host access, approved rsyslog 8.2308+ and GnuTLS
packages, cryptography, local storage capacity, a reachable receiver and its exact
DNS SAN certificate identity; its connection target may be a fixed IP. No later-tier
directory, cluster or registry is required.

## Contents

- [1. Prepare tier-owned streams](#1-prepare-tier-owned-streams)
- [2. Install and test forwarding](#2-install-and-test-forwarding)
- [3. Extend coverage](#3-extend-coverage)
- [Durability limits](#durability-limits)
- [References](#references)

## 1. Prepare tier-owned streams

1. Add existing hosts to `logging_producers` in this tier's ignored inventory, retaining
   their existing host/IP definitions. Include the collector itself in Tier 0. Copy
   the supplied input template:

   ```bash
   cp ansible/group_vars/logging_producers.yml.example ansible/group_vars/logging_producers.yml
   read -r -e -p 'Protected public request directory for this tier: ' LOGGING_REQUEST_DIR
   export LOGGING_REQUEST_DIR
   ```

2. Set `log_forwarder_target` and exact `log_forwarder_peer` in the local file.
   Set `log_forwarder_streams` per host in ignored `ansible/host_vars/<host>.yml`.
   Start with one uniquely named security journal stream per host, including Proxmox
   and the receiver. Set a distinct `log_forwarder_watchdog_url` per host to an
   independently observed dead-man endpoint, never one shared by multiple hosts.
   Add explicit file streams for `/var/log/audit/audit.log` and actual
   CA audit files once those exist. Example shapes are in each tier's template.
   Applications use separate `kind: application`, `input: files` identities and
   explicit paths, never a filtered shared security journal.
3. Select one exact inventory host and its existing setup map, then prepare the
   ordered Ansible inputs. Run once per producer; the inventory stays shared with
   Terraform. The setup file is `syslog.yml` for the receiver, `foundation.yml` for
   the issuer/directory, or the owning setup in another tier. For an existing
   hypervisor without a setup map, leave that path empty and set `ansible_host`
   and any SSH overrides in its host file.

   ```bash
   read -r -p 'Producer inventory host (for example log-1): ' LOGGING_HOST
   read -r -e -p 'Existing setup vars path (empty for unmanaged hosts): ' LOGGING_SETUP_VARS
   logging_inputs=(-i ansible/inventory/hosts.yml --limit "${LOGGING_HOST:?Select one host}"
     -e @ansible/group_vars/all.yml)
   if [[ -n "$LOGGING_SETUP_VARS" ]]; then
     logging_inputs+=(-e "@$LOGGING_SETUP_VARS")
   fi
   logging_inputs+=(-e @ansible/group_vars/logging_producers.yml
     -e "@ansible/host_vars/$LOGGING_HOST.yml")
   ```

   These files are explicit inputs: `ansible/host_vars/` is not automatically
   discovered beside the nested playbook/inventory paths. The host file is last
   and `--limit` restricts those extra vars to that producer. Keep `platform_host_ips`
   in its setup map; per-host overrides can set `ansible_host` directly.
   For a named environment, add its `all.<env>.yml` and `<setup>.<env>.yml` after the
   base setup and before the producer/host inputs. Use the same order for both runs.
4. Prepare host-local keys and fetch only public CSRs:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook "${logging_inputs[@]}" \
     ansible/playbooks/deployment/logging-producers.yml -e log_forwarder_mode=prepare
   ```

   Complete [Tier 0 signing](producer-trust.md#3-approve-producer-requests). Before
   signing an application identity, verify its actual file scope and intended readers.

## 2. Install and test forwarding

1. On Tier 0, register each exact source name/CN, observed IPv4, tier and optional
   `kind: application` in `syslog_ng_sources`; deploy the receiver with the current
   CRL. Multiple identities from one host may share its observed address.
2. In the producer's tier, select the protected directory containing `ca.pem`,
   `revoked.pem` and the approved `<stream>.pem` public leaves. Reuse the selected
   `logging_inputs` from Step 1, rebuilding that array first if this is a new shell,
   then install:

   ```bash
   read -r -e -p 'Approved public certificate handoff directory: ' LOGGING_PUBLIC_DIR
   export LOGGING_PUBLIC_DIR
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook "${logging_inputs[@]}" \
     ansible/playbooks/deployment/logging-producers.yml
   ```

   Native validation checks the leaf's identity/key, client purpose, chain and CRL,
   then parses each standalone rsyslog configuration before enabling it. Persistent
   journal retention is bounded; source rate limiting is disabled deliberately and
   must be accompanied by storage limits/alerts. Existing local logging remains enabled.
3. On a journal producer, submit a uniquely numbered test event:

   ```bash
   logger -t logging-acceptance 'logging-acceptance-event-001'
   sudo systemctl status 'log-forwarder-*.service'
   ```

   Inspect the Tier 0 record's real CN/IP, fixed source/tier, original message and
   timestamps. Test file streams through their real application/audit path, not by
   assuming that a successful journal test covers them. Journal streams emit a
   heartbeat every minute; include active critical OS identities in archive health checks.

## 3. Extend coverage

| Source | Main path / exception |
| --- | --- |
| Proxmox and other supported Linux | Tier-local journal stream; add actual audit/service files that are not journalled |
| Collector OS | Tier 0 journal plus audit-file streams; sends to its explicit receiver address, not a new local socket |
| CA / signing operations | Tier 0 host journal and configured product audit files; record privileged signing approvals separately |
| Network appliances | Native TLS/client certificate export if supported; otherwise a constrained local relay and explicit legacy-source exception |
| Kubernetes / Talos | Product-native collector/relay integration remains a selected later runtime integration; this host role does not install a Kubernetes DaemonSet |
| Application files | Separate approved identity and read group; submitted app/owner labels cannot change archive classification |

Keep first-hop device buffers and early host records until their coverage is verified.
UDP and devices with no durable spool retain explicit gaps. Do not run host configuration
management on appliances/Talos or imply that this role controls their firmware logging.

For UniFi, use its native **Integration > System Logging / SIEM** export, select
the required categories and the restricted receiver/relay address and configured
port. The vendor export uses CEF; retain its original message even when normalization
cannot parse it. Do not assume that export provides mTLS or a durable spool. [4]
When only UDP is available, explicitly register that observed address in
`syslog_ng_legacy_sources`, narrow the firewall path and record the unauthenticated
first-hop/loss exception. Keep the receiver's default UDP listener disabled otherwise.
Test an actual device event; controller-internal logging ports are not an external
receiver configuration and must not be copied into these settings automatically.

## Durability limits

The disk queue checkpoints/synchronizes native queue files and retries indefinitely
while capacity exists. At a full queue, a 60-second enqueue timeout can discard data;
journal/file rotation can also overtake a delayed reader. These are bounded stores,
not a promise of infinite backpressure. Size and fault-test them against the approved
outage window. Preserve original journals/files for a separately declared replay window. [1][2]

TCP/TLS success releases a native forwarding queue item, **not an archive acknowledgement**.
A last in-flight event may be lost or duplicated on failure before the NAS checkpoint.
No automation deletes local journal/file history based on archive commitment. Their
native retention can still expire; measure that window and reconcile gaps/replays.
Use an application-acknowledged replicated intake when that residual loss is unacceptable.

Queue/cursor directories are never reset during reruns. Withdrawing a stream does not
delete or stop an old unit automatically: disable its unit deliberately, preserve the
backlog, revoke at the receiver and record the handover before removing configuration.
The health timer checks unit state, spool usage below 80% of its budget, free space,
leaf expiry and chain/CRL validity before pinging. This measures capacity/credentials,
not receiver commitment; required source freshness is checked separately at the archive.

Continue with [NAS checkpoints and independent backup](step-3c-nas-archive.md).

## References

Sources checked 2026-10-19.

1. [rsyslog queue durability controls](https://docs.rsyslog.com/doc/concepts/queues.html)
2. [rsyslog full-queue timeout and discard behavior](https://docs.rsyslog.com/doc/rainerscript/queue_parameters.html#queue-timeoutenqueue)
3. [rsyslog native TLS forwarding](https://docs.rsyslog.com/doc/configuration/modules/omfwd.html)
4. [UniFi native system log export](https://help.ui.com/hc/en-us/articles/33349041044119-UniFi-System-Logs-SIEM-Integration)
