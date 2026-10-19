# Deploy the network log receiver

Install syslog-ng OSE on the independent Tier 0 log VM without replacing its OS
logger. TLS producers are explicitly registered; legacy UDP is disabled by default.
Local records are mutable staging, **not an immutable archive or HA acceptance**.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** [Stage 1, Step 1](README.md#step-1-provision-the-log-host), EL 10
(AlmaLinux/Rocky/RHEL), approved signed syslog-ng 4.11+ packages and dependencies,
working time/DNS, firewalld, and independently supplied TLS certificates.
Prepare repository access or an approved offline mirror before deployment; the role
does not enable EPEL or depend on a later Tier 1 software-supply service. [1]
The 4.11 minimum includes the upstream first-read TLS metadata fix: older versions
can omit the CN used for strict routing and drop the first read batch. Do not relax
the identity filter to accommodate those packages. Qualify the signed repository
or approved offline package source before the receiver installation. [3]
Do not assume EPEL alone satisfies that gate: distribution versions may lag it.
Qualify the upstream stable EL 10 packages/signing key or a reviewed internal build;
never substitute Fedora RPMs, nightly packages or disabled signature checks. [1][4]

## Contents

- [Step 1: Prepare the data volume](#step-1-prepare-the-data-volume)
- [Step 2: Register trust and producers](#step-2-register-trust-and-producers)
- [Step 3: Deploy and verify](#step-3-deploy-and-verify)
- [References](#references)

## Step 1: Prepare the data volume

1. On the receiver, identify the separate data disk by its actual device/serial:

   ```bash
   lsblk --output NAME,SERIAL,SIZE,FSTYPE,UUID,MOUNTPOINTS
   ```

2. Prepare an approved XFS/ext4 filesystem and persistent UUID-based mount at
   `/srv/security-logging`, including encryption and independently held keys where
   required. This is an explicit operator operation: verify the disk and backup
   before any formatting. An existing prepared volume is valid. Never format the OS
   disk, historical evidence or an unidentified device. Verify it survives a reboot.
3. Inspect the mounted filesystem and set its UUID as `syslog_ng_data_uuid` in Tier 0
   `ansible/group_vars/syslog.yml`. For multiple collectors, put each UUID in its
   inventory host variables instead. Check UUID and free capacity on each host:

   ```bash
   findmnt --mountpoint /srv/security-logging --output TARGET,SOURCE,UUID,FSTYPE,OPTIONS
   df -h /srv/security-logging
   ```

The role requires this exact writable mount on a different filesystem/device from
`/`; it never partitions, formats or mounts disks. The service also refuses startup
without the mount. The preflight free-space threshold is a gate, not a capacity alarm.

## Step 2: Register trust and producers

1. Follow [independent logging trust](producer-trust.md), or supply an existing qualified
   independent CA bundle, current server certificate/full chain with the
   receiver DNS/IP in its SAN and server-auth usage, and matching unencrypted service
   key. Issue client-auth certificates per producer/relay. Protect these files outside
   Git on the execution host; keep CA signing/recovery keys separately. Stage 2 PKI is
   not required. Local validation checks the first CA's validity/CA constraint and server
   validity/key matching before copying files; the live client
   must still verify chain, SAN, purpose and trust. [2]
2. In Tier 0 `ansible/group_vars/syslog.yml`, fill `syslog_ng_sources` using the example
   entry there: a unique safe `name`, observed IPv4 `address`, numeric `tier` and exact
   certificate `tls_dn`. The certificate CN must equal `name`. This binds an authenticated
   connection to a server-owned stream; claimed HOST/app labels never choose its path.
   Use the receiver-observed relay/NAT address, not an unobservable original address.
3. Set the actual firewalld interface zone and narrow upstream network rules. Keep
   `syslog_ng_legacy_sources` empty unless accepting a documented unauthenticated UDP
   exception. Prefer a local authenticated relay; a legacy source IP is not proof of identity.

Set execution-host file paths interactively, without placing private-key contents in
configuration or command history:

```bash
read -r -e -p 'Receiver CA bundle path: ' SYSLOG_NG_TLS_CA_FILE
read -r -e -p 'Receiver certificate chain path: ' SYSLOG_NG_TLS_CERT_FILE
read -r -e -p 'Receiver private key path: ' SYSLOG_NG_TLS_KEY_FILE
read -r -e -p 'Current signed producer CRL path: ' SYSLOG_NG_TLS_CRL_FILE
export SYSLOG_NG_TLS_CA_FILE SYSLOG_NG_TLS_CERT_FILE SYSLOG_NG_TLS_KEY_FILE SYSLOG_NG_TLS_CRL_FILE
```

No generic unauthenticated TCP listener is installed. TLS requires client certificates,
trusted subjects and matching source IP/CN; TLS versions below 1.2 are disabled. [2]
The supplied [software PKI policy](../stage-2-trust/procedures/software-pki.md#decisions-and-recovery-kit)
does not issue client-auth certificates. Its TLS-server profile is not a replacement
for the independent producer authority; qualify that integration before migrating trust.
Configure [producer forwarding and durable queues](sources.md) in the owning tier;
device-specific exceptions remain explicit. Verify the actual source path, including local
receiver events; the OS logger's journal/socket/configuration remain untouched.

## Step 3: Deploy and verify

1. From the Tier 0 repository root, after reviewing local inputs:

   ```bash
   bash scripts/deploy.sh syslog --ansible-only
   ```

   This installs `syslog-ng-receiver.service`, a dedicated unprivileged network-only
   instance. It does not start the vendor `syslog-ng.service`, stop rsyslog, consume
   `/dev/log` or replace journald. A running/enabled vendor syslog-ng instance blocks
   this recipe; adopt an explicit alternative instead of modifying the OS logger.
   The unused vendor unit is disabled/masked after installation to prevent a boot conflict.
2. On the receiver, inspect service state and diagnose failures without deleting queues:

   ```bash
   sudo systemctl status syslog-ng-receiver.service
   sudo journalctl --unit syslog-ng-receiver.service --since '-10 minutes'
   ```

   From a registered producer, submit a uniquely numbered event through its normal
   TLS forwarding path. Verify the corresponding record's `source`, `peer_ip`, `peer_cn`,
   `raw` and `received_at`; an open listener is not this check. Reject unknown/missing
   certificates, mismatched origins and attempts to select another source namespace.
3. Continue [Stage 1, Step 3](README.md#step-3-protect-and-verify-retained-evidence)
   and the [fault/restore drill](../../administration/logging-drill.md). Prepare independent
   [NAS checkpoints, independent copies and audited reader access](step-3c-nas-archive.md),
   or the selected locked-storage alternative.

The [receiver reference](../../reference/syslog-receiver.md) defines files, queue sizing,
runtime safeguards, reconciliation fields and limitations. The maintenance recipe reuses
the role serially; package upgrades, historical cleanup and archive integration are not automatic.
Do not remove sources or change queue paths/capacities with an unreviewed backlog.

## References

Sources checked 2026-10-19.

1. [Fedora package catalogue: syslog-ng and EPEL versions](https://packages.fedoraproject.org/pkgs/syslog-ng/syslog-ng/index.html)
2. [syslog-ng TLS, certificate validation and subject restrictions](https://syslog-ng.github.io/admin-guide/100_TLS-encrypted_message_transfer/004_TLS_options.html)
3. [syslog-ng first-read TLS peer metadata fix](https://github.com/syslog-ng/syslog-ng/pull/5603)
4. [Upstream stable package availability and binary-installation entry](https://www.syslog-ng.com/community/b/blog/posts/syslog-ng-4-11-0-packaging-status)
