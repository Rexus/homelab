# Deploy the network log receiver

Install syslog-ng OSE on the independent Tier 0 log VM without replacing its OS
logger. TLS producers are explicitly registered; legacy UDP is disabled by default.
Local records are mutable staging, **not an immutable archive or HA acceptance**.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** [Stage 2, Step 1](README.md#step-1-provision-the-log-host), EL 10
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

### 1. Identify the data disk

On **`log-1`**, identify the separate data disk by its actual device/serial:

```bash
lsblk --output NAME,SERIAL,SIZE,FSTYPE,UUID,MOUNTPOINTS
```

**Expected:** the OS disk and separate data disk are distinguishable. Stop if the data disk is unidentified.

### 2. Prepare the persistent mount

On **`log-1`**, prepare an approved XFS/ext4 filesystem and persistent UUID-based mount at
`/srv/security-logging`, including encryption and independently held keys where required.
An existing prepared volume is valid. This is manual storage preparation, not a playbook action.
Verify the disk and backup before any formatting; never format the OS disk or historical evidence.

Reboot the receiver and reconnect. Inspect its mount and free capacity:

```bash
findmnt --mountpoint /srv/security-logging --output TARGET,SOURCE,UUID,FSTYPE,OPTIONS
df -h /srv/security-logging
```

**Expected:** the intended data filesystem remains mounted after reboot, with the required capacity.
Stop if the persistent mount is not ready; deployment cannot create it safely from an assumed device name.

### 3. Record the mounted volume

On the execution host, edit **`<prefix>-tier-0/ansible/group_vars/syslog.yml`**.
Use the UUID reported above, not a device name:

```yaml
syslog_ng_data_mount: /srv/security-logging
syslog_ng_data_uuid: REPLACE_WITH_VERIFIED_FILESYSTEM_UUID
```

For multiple collectors, put each UUID in its inventory host variables instead and repeat these checks per host.

The role requires this exact writable mount on a different filesystem/device from
`/`; it never partitions, formats or mounts disks. The service also refuses startup
without the mount. The preflight free-space threshold is a gate, not a capacity alarm.

## Step 2: Register trust and producers

### 4. Issue the receiver certificate

From the protected **Tier 0 signing controller**, complete [logging trust Steps 1-2](producer-trust.md),
then return here. An existing qualified independent authority is an alternative.

**Expected:** public CA bundle, current server certificate/full chain with the receiver identity in its
SAN and server-auth usage, matching unencrypted service key, and current signed CRL. Protect service files
outside Git on the execution host; hold CA signing/recovery keys separately. Stage 3 PKI is not required.
Local validation checks the first CA's validity/CA constraint and server validity/key matching;
the live client must still verify chain, SAN, purpose and trust. [2]

### 5. Prepare the receiver's own producer identity

From **`<prefix>-tier-0/`**, complete [source Step 1](sources.md#1-prepare-tier-owned-streams)
for `log-1`'s OS journal, including CSR approval/signing. Return here before source Step 2.
Issue client-auth certificates per producer/relay; do not share one certificate across sources.

**Expected:** the approved `log-1-os` identity is ready. A nonempty approved catalogue is required to install intake.

### 6. Register the approved source and intake rules

Edit **`<prefix>-tier-0/ansible/group_vars/syslog.yml`**. Replace `syslog_ng_sources: []`
with the approved identities. Replace the address below with the receiver-observed address;
retain the exact approved certificate subject:

```yaml
syslog_ng_sources:
  - name: log-1-os
    address: 10.10.10.30
    tier: 0
    tls_dn: CN=log-1-os
```

The certificate CN must equal `name`. This selects a server-owned stream; claimed HOST/app labels
never choose its path. A relay/NAT address is valid only when intake actually observes it.

In the **same Tier 0 file**, set `syslog_ng_firewall_zone` to the intake interface's zone.
At the **network firewall**, allow only registered sources to TCP 6514.
Keep `syslog_ng_legacy_sources` empty unless accepting a documented unauthenticated UDP exception.
Prefer an authenticated local relay; a legacy source IP is not proof of identity.

### 7. Select the certificate files

On the execution host, run from **`<prefix>-tier-0/`** in the shell used for installation.
Enter file paths, never private-key contents:

```bash
read -r -e -p 'Receiver CA bundle path: ' SYSLOG_NG_TLS_CA_FILE
read -r -e -p 'Receiver certificate chain path: ' SYSLOG_NG_TLS_CERT_FILE
read -r -e -p 'Receiver private key path: ' SYSLOG_NG_TLS_KEY_FILE
read -r -e -p 'Current signed producer CRL path: ' SYSLOG_NG_TLS_CRL_FILE
export SYSLOG_NG_TLS_CA_FILE SYSLOG_NG_TLS_CERT_FILE SYSLOG_NG_TLS_KEY_FILE SYSLOG_NG_TLS_CRL_FILE
```

No generic unauthenticated TCP listener is installed. TLS requires client certificates,
trusted subjects and matching source IP/CN; TLS versions below 1.2 are disabled. [2]
The supplied [software PKI policy](../stage-3-trust/procedures/software-pki.md#decisions-and-recovery-kit)
does not issue client-auth certificates. Its TLS-server profile is not a replacement
for the independent producer authority; qualify that integration before migrating trust.
Configure [producer forwarding and durable queues](sources.md) in the owning tier;
device-specific exceptions remain explicit. Verify the actual source path, including local
receiver events; the OS logger's journal/socket/configuration remain untouched.

## Step 3: Deploy and verify

### 8. Install the receiver

Run from **`<prefix>-tier-0/`**, retaining the certificate environment from action 7:

```bash
bash scripts/deploy.sh syslog --ansible-only
```

**Expected:** `syslog-ng-receiver.service` is installed as a dedicated unprivileged network-only instance.
It does not start the vendor `syslog-ng.service`, stop rsyslog, consume `/dev/log` or replace journald.
A running/enabled vendor syslog-ng instance blocks this recipe; select an explicit alternative instead.
The unused vendor unit is disabled/masked after installation to prevent a boot conflict.

### 9. Check the service

On **`log-1`**, inspect startup errors without deleting queues:

```bash
sudo systemctl status syslog-ng-receiver.service
sudo journalctl --unit syslog-ng-receiver.service --since '-10 minutes'
```

### 10. Enable the first producer and verify its event

From **`<prefix>-tier-0/`**, complete [source Step 2](sources.md#2-install-and-test-forwarding)
for the prepared `log-1-os` identity. Submit its uniquely numbered test event through normal TLS forwarding.
At **protected intake**, verify `source`, `peer_ip`, `peer_cn`, `raw` and `received_at` in the matching record.
An open listener is insufficient. Reject unknown/missing certificates, mismatched origins and cross-source writes.

Add the supported Proxmox hosts and appliance exports through that same source guide.

### 11. Continue with retained evidence

Return to [Stage 2, Step 3](README.md#step-3-protect-and-verify-retained-evidence).
Prepare [NAS checkpoints, independent copies and audited reader access](step-3c-nas-archive.md),
or the selected locked-storage alternative, then run the [fault/restore drill](../../administration/logging-drill.md).

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
