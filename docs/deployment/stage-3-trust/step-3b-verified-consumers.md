# Step 3b: Connect a consumer to verified publication

**Branch from:** [Step 3](README.md#step-3-enable-and-verify-routine-issuance), within option **3b**,
after the worker's [first accepted intake](step-3b-verified-intake.md#5-run-and-inspect-the-first-intake).
**Change:** connect a selected native package consumer to the accepted publication.
**Return:** [Stage 3 completion](README.md#capability-available) after the selected consumer passes
and [worker scheduling](step-3b-verified-intake.md#6-connect-consumers-and-schedule-intake) is complete.

It changes the consumer's native repository definitions; the worker never installs packages into consumers.
Complete one disposable consumer before changing bootstrap or Proxmox.

**Working repositories:** `<prefix>-tier-0`, `<prefix>-tier-1` or `<prefix>-tier-2` owns the consumer
selection; commands below run on that selected guest/host. Tier 1 owns only the publication service.

## Contents

- [1. Record the selected version](#1-record-the-selected-version)
- [2a. EL10 repository](#2a-el10-repository)
- [2b. Debian, Ubuntu or Proxmox repository](#2b-debian-ubuntu-or-proxmox-repository)
- [3. Accept the cutover](#3-accept-the-cutover)

## 1. Record the selected version

From an allowed management client, read `https://<intake-host>/approved/<source>/latest.json` and
its versioned receipt. Record the selected `content_path` and expected publisher in the consumer's
own project configuration. Use the full HTTPS hostname plus **immutable content path**, not `latest.json`.

Keep a copy of the current repository configuration and trusted vendor keys before editing.
The publication CA must already be trusted on the consumer; never add `insecure`, `trusted=yes`
or a signature bypass to make the mirror work. An RPM feed and an APT feed are separate sources.

## 2a. EL10 repository

On the **EL10 consumer**, edit the selected existing file under `/etc/yum.repos.d/`.
Retain its repository ID, vendor `gpgkey` and other distro-specific settings. Set `baseurl`
to the selected RPM content URL and remove that entry's external `mirrorlist`/`metalink`.
The relevant fields look like this; replace placeholders and retain the selected metadata policy:

```ini
[<existing-repository-id>]
baseurl=https://<intake-host>/approved/<source>/<version>/content/
enabled=1
gpgcheck=1
sslverify=1
skip_if_unavailable=0
proxy=_none_
```

Keep `repo_gpgcheck=1` when that vendor supplies signed metadata; do not enable it blindly for
an unsigned-metadata feed. Native package signatures remain required. Leave the existing independently
trusted `gpgkey` in place. Each enabled repository needs its own accepted internal endpoint or must
be explicitly disabled; changing BaseOS alone does not redirect AppStream, EPEL or other sources.

Refresh only the edited repository on the **consumer**:

```bash
read -r -p 'Existing repository ID: ' REPO_ID
sudo dnf --disablerepo='*' --enablerepo="$REPO_ID" --refresh makecache
```

**Expected:** native metadata refresh and signature checks succeed using the pinned publication.
This command installs no updates.

## 2b. Debian, Ubuntu or Proxmox repository

On the **APT consumer**, edit the matching `.sources` or `.list` file under `/etc/apt/sources.list.d/`
(or its existing `/etc/apt/sources.list` entry). Preserve the vendor suite, components, architectures
and `Signed-By` keyring. Replace only its URI with the selected APT content URL.
A deb822 entry has this shape:

```deb822
Types: deb
URIs: https://<intake-host>/approved/<source>/<version>/content/
Suites: <existing-suite>
Components: <existing-components>
Signed-By: <existing-vendor-keyring-path>
```

Use separate published sources for separate suites/pockets; match their signed Codenames as configured
on the worker. Keep `Check-Valid-Until` enabled. A frozen release that expires requires a newly verified
publication, not disabling expiry. Avoid duplicate external entries for the same repository.

If a global APT proxy remains enabled, add a host-specific direct route in
**`/etc/apt/apt.conf.d/91intake-direct`**. Replace the hostname:

```text
Acquire::https::Proxy::<intake-host> "DIRECT";
```

On the **consumer**, refresh metadata:

```bash
sudo apt-get -o APT::Update::Error-Mode=any update
```

**Expected:** every required source refreshes successfully; no package is upgraded. Proxmox's
Debian, Proxmox and Ceph feeds remain separate native repository entries. This reference acquires
public HTTPS feeds; authenticated subscription sources require a separately qualified integration.

## 3. Accept the cutover

1. Confirm every enabled source uses accepted supply and native verification remains enabled.
2. Deny direct WAN bypass independently. Stop the mirror in a disposable test and require a clear
   refresh failure, not fallback to an external source.
3. For **boot-1**, select the existing [mirror-mode recipe](../stage-1-software-intake/bootstrap-consumer.md#2b-native-mirrors-or-disconnected-supply)
   after repository/tool supply is commissioned. Other tools still need their own accepted supply.
4. Record the previous and selected URLs. Follow the [rollback and recovery runbook](../../administration/software-intake.md)
   for another selection; patch rollout/reboots remain separate maintenance operations.

These are manual native consumer edits. Keep their selected values in the owning project's
configuration management; the Tier 1 `intake` Terraform state owns only the worker and disks.
