# Receiver storage and runtime

For a first deployment, follow [Stage 3's complete installation route](../README.md#installation-order).
This reference covers existing-volume adoption, storage records and receiver diagnosis.
Storage prepared by the main guide is reused automatically during receiver installation.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).

## Contents

- [Adopt an existing volume](#adopt-an-existing-volume)
- [Retain the storage binding](#retain-the-storage-binding)
- [Receiver runtime](#receiver-runtime)
- [Diagnose the receiver](#diagnose-the-receiver)
- [References](#references)

<a id="step-1-prepare-the-data-volume"></a>
<a id="1-identify-the-data-disk"></a>
<a id="2-prepare-the-persistent-mount"></a>

## Adopt an existing volume

Use the retained `device`, `fstype` and filesystem `uuid` in **Tier 0 `ansible/group_vars/syslog.yml`**.
The starter's new disk uses `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`.
For a different layout, select the actual dedicated device or its stable by-id link.
An existing partition can be selected directly; it is never repartitioned.

Inspect an existing filesystem from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible foundation_logging --playbook-dir ansible \
  -i ansible/inventory/hosts.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/syslog.yml \
  -m ansible.builtin.command -a 'lsblk --output NAME,SERIAL,SIZE,FSTYPE,UUID,MOUNTPOINTS'
```

Set `syslog_ng_data_device`, `syslog_ng_data_fstype` (`xfs` or `ext4`) and `syslog_ng_data_uuid`
to the accepted volume's actual values before [storage preparation](../README.md#step-4-deploy-and-approve-certificates).
Stop if identity is uncertain. A UUID mismatch, incompatible signature, root/partitioned whole disk,
conflicting mount, populated unmounted target or missing declared volume blocks deployment.
The guarded role never authorizes evidence deletion or automatic replacement. Encrypted storage
also needs its accepted unlock mapping and independently retained keys.

<a id="3-record-the-mounted-volume"></a>

## Retain the storage binding

The storage run prints `path`, `device`, `uuid` and `fstype`, followed by the exact UUID input line
and destination file. Keep that output in the recovery record. Ansible already persists the mount
in `/etc/fstab`; saving an explicit input pin adds a future filesystem identity check.

For one receiver, `syslog_ng_data_uuid` in **Tier 0 `ansible/group_vars/syslog.yml`** remains a valid
optional guard. For several receivers, keep the common scalar empty and put each actual UUID in
`logging_workflow_receiver_options.<inventory-host>.data_uuid` in that same file. No host file is required.
Legacy per-host UUID inputs remain supported by the direct receiver recipe; shared extra vars override them.

**IaC:** the [receiver storage task](../../../../tier-0/ansible/roles/syslog_ng/tasks/storage.yml)
invokes [Shared's guarded volume role](../../../../shared/ansible/roles/data_volume/tasks/main.yml).
Its verified UUID supplies the effective receiver identity when no explicit pin is set.
Free-space checks are deployment gates, not continuous capacity alarms.

<a id="step-2-register-trust-and-producers"></a>

## Receiver runtime

The [main guide's Steps 3-5](../README.md#step-3-select-producers) derive requests,
enroll them with the selected authority, install the source catalog and test collection.
The default uses the active infrastructure PKI's logging client/server profiles;
[other authority modes](producer-trust.md) remain explicit alternatives.

The receiver requires approved EL10 syslog-ng **4.11+** packages and issued, verified TLS material.
The minimum includes the first-read peer-metadata fix used for strict CN routing. Do not weaken
identity filters for older packages. Qualify signed native sources; EPEL availability alone does not
prove the minimum, and Fedora/nightly RPMs or disabled signature checks are not substitutes. [1][2]

The dedicated unprivileged `syslog-ng-receiver.service` accepts registered TLS clients and writes
local records/queues. It does not replace journald/rsyslog, consume `/dev/log` or start the vendor
`syslog-ng.service`. A running/enabled vendor instance blocks this recipe; the unused vendor unit
is masked after installation. Local files remain mutable staging, not independent locked retention.

<a id="step-3-deploy-and-verify"></a>

## Diagnose the receiver

Verify its mount, configured UUID and service from **`<prefix>-tier-0/`**:

```bash
bash scripts/deploy.sh syslog --ansible-only --playbook deployment/logging-verify.yml
```

Read startup errors from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible foundation_logging --playbook-dir ansible \
  -i ansible/inventory/hosts.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/syslog.yml \
  --become -m ansible.builtin.command -a 'journalctl --unit=syslog-ng-receiver.service --since="-10 minutes" --no-pager'
```

Use the [receiver contract](../../../08-reference/syslog-receiver.md) for runtime files, queue limits
and recovery safeguards. Do not change queue paths/capacities or discard a backlog during diagnosis.
For first installation, resume [Step 5](../README.md#step-12-install-forwarding-and-verify-the-first-event).

## References

1. [syslog-ng first-read TLS peer metadata fix](https://github.com/syslog-ng/syslog-ng/pull/5603).
2. [Upstream stable package availability](https://www.syslog-ng.com/community/b/blog/posts/syslog-ng-4-11-0-packaging-status).
