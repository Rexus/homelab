# Connect logging sources

Forward Linux journal, audit and selected application files with isolated native
rsyslog instances. Each stream has its own certificate, cursor and bounded disk
queue. The existing OS logger remains in place; no extra input listener is opened.

The source-to-intake relationship is shown in
[Stage 2 Figure 3](../README.md#figure-3-authenticated-source-collection).
This procedure adds approved streams to an existing receiver after initial installation.
For the first receiver and its OS stream, stay on the [continuous Stage 2 guide](../README.md#step-5-configure-the-first-producer).

**Working repository:** the producer's `<prefix>-tier-0`, `-tier-1` or `-tier-2`.
**Implementation:** Shared `ansible/roles/log_forwarder`; all inputs, hosts, keys and
state remain in the owning tier. Debian/systemd and Red Hat/systemd are supported
branches; qualify the actual OS, SELinux/AppArmor and package build before acceptance.
**Prerequisites:** authenticated host access, approved rsyslog 8.2308+ and GnuTLS
packages, cryptography and local storage capacity. **Preparation** generates host keys/CSRs without
a running receiver. **Installation** additionally requires reachable intake and its exact DNS SAN
certificate identity; its connection target may be a fixed IP. No later-tier directory, cluster or registry is required.

## Contents

- [1. Prepare tier-owned streams](#1-prepare-tier-owned-streams)
- [2. Install and test forwarding](#2-install-and-test-forwarding)
- [3. Extend coverage](#3-extend-coverage)
- [Durability limits](#durability-limits)
- [References](#references)

## 1. Prepare tier-owned streams

1. Select existing hosts in `logging_producers` in this tier's ignored inventory. Use
   `children` to reuse an existing group, or `hosts` with empty `{}` entries to select
   individual inventory names. The same hosts keep their existing address/login. [5]
   Tier 0 already includes `foundation_logging` in the current template; older local
   inventories can add the [group membership](../README.md#step-5-configure-the-first-producer).
   Copy the supplied input template:

   Run from the producer owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

   ```bash
   cp -n ansible/group_vars/logging_producers.yml.example ansible/group_vars/logging_producers.yml
   mkdir -p ansible/inventory/host_vars
   read -r -e -p 'Protected public request directory for this tier: ' LOGGING_REQUEST_DIR
   export LOGGING_REQUEST_DIR
   ```

   Edit in the producer owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

   - `ansible/group_vars/logging_producers.yml`: Producer streams, receiver identity and host-local TLS/queue
     inputs.

2. Set the receiver's stable service DNS name in `log_forwarder_peer`. The template's
   `log_forwarder_target` reuses it; override the target with an accepted IP if DNS is
   unavailable. Keep the peer as the exact certificate DNS SAN.
   Add `log_forwarder_streams` to each ignored `ansible/inventory/host_vars/<host>.yml`,
   creating the file if missing. Preserve its existing UUID, address and SSH settings.
   Start with one uniquely named security journal stream per host, including Proxmox
   and the receiver. Set a distinct `log_forwarder_watchdog_url` per host to an
   independently observed dead-man endpoint, never one shared by multiple hosts.
   Add explicit file streams for `/var/log/audit/audit.log` and actual
   CA audit files once those exist. Example shapes are in each tier's template.
   Applications use separate `kind: application`, `input: files` identities and
   explicit paths, never a filtered shared security journal.

   For example, the common endpoint in **`ansible/group_vars/logging_producers.yml`** is:

   ```yaml
   log_forwarder_target: "{{ log_forwarder_peer }}"
   log_forwarder_peer: logs.internal.example.com
   ```

   Use the [first producer's host settings](../README.md#step-5-configure-the-first-producer)
   as the shape for a distinct stream name and health endpoint per host. Do not copy its connection settings.
3. Select one exact inventory host and its existing setup map, then prepare the
   ordered Ansible inputs. Run once per producer; the inventory stays shared with
   Terraform. The setup file is `syslog.yml` for the receiver, `foundation.yml` for
   the issuer/directory, or the owning setup in another tier. For an existing
   hypervisor without a setup map, leave that path empty and set `ansible_host`
   and any SSH overrides in its host file.

   Run from the producer owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

   ```bash
   read -r -p 'Producer inventory host (for example log-1): ' LOGGING_HOST
   read -r -e -p 'Existing setup vars path (empty for unmanaged hosts): ' LOGGING_SETUP_VARS
   logging_inputs=(-i ansible/inventory/hosts.yml --limit "${LOGGING_HOST:?Select one host}"
     -e @ansible/group_vars/all.yml)
   if [[ -n "$LOGGING_SETUP_VARS" ]]; then
     logging_inputs+=(-e "@$LOGGING_SETUP_VARS")
   fi
   logging_inputs+=(-e @ansible/group_vars/logging_producers.yml
     -e "@ansible/inventory/host_vars/$LOGGING_HOST.yml")
   ```

   The host file is last and `--limit` restricts those extra vars to that producer.
   The inventory-adjacent host-vars directory is also natively discoverable.
   Existing `ansible/host_vars/` files remain valid when their actual path is explicitly
   supplied as the final host input; refresh does not move local records. Keep `platform_host_ips`
   in its setup map; per-host overrides can set `ansible_host` directly.
   For a named environment, add its `all.<env>.yml` and `<setup>.<env>.yml` after the
   base setup and before the producer/host inputs. Use the same order for both runs.
4. Prepare host-local keys and fetch only public CSRs:

   Run from the producer owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook "${logging_inputs[@]}" \
     ansible/playbooks/deployment/logging-producers.yml -e log_forwarder_mode=prepare
   ```

   Complete [Tier 0 signing](producer-trust.md#3-approve-producer-requests). Before
   signing an application identity, verify its actual file scope and intended readers.

   After signing, continue directly with installation below. The initial receiver
   was already installed by Stage 2; no disk or authority initialization is repeated.

## 2. Install and test forwarding

1. On Tier 0, register each exact source name/CN, observed IPv4, tier and optional
   `kind: application` in `syslog_ng_sources`; deploy the receiver with the current
   CRL. Multiple identities from one host may share its observed address.
2. In the producer's tier, select the protected directory containing `ca.pem`,
   `revoked.pem` and the approved `<stream>.pem` public leaves. Reuse the selected
   `logging_inputs` from Step 1, rebuilding that array first if this is a new shell,
   then install:

   Run from the producer owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

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

   Run from **the producer's owning tier**, retaining `logging_inputs`:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible "$LOGGING_HOST" --playbook-dir ansible \
     "${logging_inputs[@]}" --become -m ansible.builtin.command \
     -a 'logger -t logging-acceptance logging-acceptance-event-001'
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

For cache hosts, include the [proxy decision stream](../../../08-reference/proxy-cache.md#security-events)
alongside the OS journal when enrolling each host.

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

For a source added after installation, preserve existing archive custody. On the NAS path, append each
new required OS heartbeat to `logging_archive_required_sources` and reconcile the existing
[archive health configuration](../step-15a-nas-archive.md#step-2-connect-collection-to-retained-copies),
retaining its marker, mounts and credentials. Then return to the stage that requested enrollment;
do not repeat first-time archive or backup initialization.

## References

Logging sources checked 2026-10-19; Ansible inventory checked 2026-11-13.

1. [rsyslog queue durability controls](https://docs.rsyslog.com/doc/concepts/queues.html)
2. [rsyslog full-queue timeout and discard behavior](https://docs.rsyslog.com/doc/rainerscript/queue_parameters.html#queue-timeoutenqueue)
3. [rsyslog native TLS forwarding](https://docs.rsyslog.com/doc/configuration/modules/omfwd.html)
4. [UniFi native system log export](https://help.ui.com/hc/en-us/articles/33349041044119-UniFi-System-Logs-SIEM-Integration)
5. [Ansible inventory: parent/child groups and shared host identities](https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html#grouping-groups-parent-child-group-relationships)
