# Step 3b: Connect a consumer to verified publication

**Branch from:** [Step 3](README.md#step-3-enable-and-verify-routine-issuance), within option **3b**,
after [first accepted intake](step-3b-verified-intake.md#5-run-and-inspect-the-first-intake).
**Change:** configure a selected existing consumer through its owning tier's Ansible.
**Return:** [Stage 3 completion](README.md#capability-available) after acceptance and
[worker scheduling](step-3b-verified-intake.md#6-connect-consumers-and-schedule-intake).

**Working repository:** the consumer's `<prefix>-tier-0`, `<prefix>-tier-1` or `<prefix>-tier-2`.
Run all commands from that repository on the deployment controller. Tier 1 owns publication,
not another tier's package installations. Test a disposable consumer before bootstrap or Proxmox.

## Contents

1. [Record the selected version](#1-record-the-selected-version)
2. [Select native repositories](#2-select-native-repositories)
3. [Apply from the controller](#3-apply-from-the-controller)
4. [Accept the cutover](#3-accept-the-cutover)

## 1. Record the selected version

Read the publication's `latest.json` and versioned receipt from an approved management client.
Select its immutable `content_path` and expected publisher; retain those values in local consumer inputs.
Use the full HTTPS content URL, never `latest.json` as a repository URL.

From the **consumer-owning repository**, initialize its additional inputs:

```bash
cp -n ansible/group_vars/software_consumer.yml.example ansible/group_vars/software_consumer.yml
```

Edit `software_consumer.yml`: set `software_consumer_group` to a populated existing inventory
group, and `baseline_trust_anchors` to approved public CA files on the controller when needed.
Load the existing target/IP vars with this file; do not create a second inventory or assign the worker's address.

## 2. Select native repositories

<a id="2a-el10-repository"></a>

### 2a. EL10 repositories

In **`ansible/group_vars/software_consumer.yml`**, add a `repository_proxy_dnf_sources` entry
for each selected existing repository: `file`, `section`, immutable HTTPS `baseurl` and `direct: true`.
Use the commented example as the shape. The role retains vendor `gpgkey`/metadata policy,
removes `mirrorlist`/`metalink` for those stanzas and bypasses the proxy only for selected feeds.
Keep `repo_gpgcheck` enabled where the vendor signs metadata; every enabled feed needs an accepted source.

<a id="2b-debian-ubuntu-or-proxmox-repository"></a>

### 2b. Debian, Ubuntu or Proxmox repositories

In the **same file**, add `baseline_apt_repositories` entries with `name`, immutable HTTPS
`uri`, original `suites`, `components`, optional `architectures` and existing vendor `signed_by` keyring.
Keep Debian, security, Proxmox and Ceph feeds separate. Add the intake hostname to
`baseline_apt_direct_hosts` if it bypasses a global proxy.

List whole old files under `baseline_apt_retired_files` only after every required feed in
each file has a managed replacement. The role retains `.save` copies before retiring those files.
Unlisted sources and trusted keyrings remain in place. It never enables `trusted=yes`,
disables expiry/signature checks or substitutes a new publisher key.

## 3. Apply from the controller

Run from the **consumer-owning repository**, loading its existing IP/setup vars before the
consumer file. Enter that existing setup vars path when prompted:

```bash
read -r -p 'Existing consumer IP/setup vars file (example: ansible/group_vars/syslog.yml): ' CONSUMER_VARS
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e "@$CONSUMER_VARS" \
  -e @ansible/group_vars/software_consumer.yml ansible/playbooks/deployment/software-consumer.yml
```

**Expected:** approved CA trust and selected repository definitions are applied, then strict
metadata refresh succeeds on every selected consumer. No package upgrade or reboot is run.
The existing global proxy is preserved; exact selected internal sources bypass it.

<a id="3-accept-the-cutover"></a>

## 4. Accept the cutover

1. Verify every enabled feed has accepted supply and native publisher verification remains enabled.
2. Independently deny direct WAN bypass. In a disposable test, loss of publication must fail clearly.
3. For bootstrap, select the existing [mirror-mode recipe](../stage-1-software-intake/step-6-bootstrap-consumer.md#2b-native-mirrors-or-disconnected-supply)
   after native repository and tool supply is commissioned.
4. Record old and new selections. Restore a previous accepted input and reapply using the
   [rollback guidance](../../05-operations/02-software-intake/verified-publication.md).

Patch rollout/reboots remain separate maintenance. The worker's Terraform state owns only its own
guest and disks; each consuming tier owns its input selections and Ansible changes.
