# Transport original provisioning inputs

The recovery host pulls ignored operational inputs and original state **from their actual owners**
over bounded read-only shares, then writes independently encrypted restic copies off those hosts.
It does not assume a Git clone or a manually staged recovery-host directory contains ignored files.

**Prerequisites:** identify each real provisioning workstation/CI runner/backend custodian, its full
original paths and authority; independently administer the recovery host/repository; and authorize
an encrypted read-only SMB export, local reader credential and firewall route per source.
The backup role mounts commissioned shares; it does not install or administer source SMB servers.

## Contents

- [Identify original ownership](#identify-original-ownership)
- [Commission a bounded source view](#commission-a-bounded-source-view)
- [Configure transport and selections](#configure-transport-and-selections)
- [Verify independence and freshness](#verify-independence-and-freshness)
- [References](#references)

## Identify original ownership

| Material | Authoritative source that must be exported or independently protected |
| --- | --- |
| Tier-local ignored inventory/group vars/tfvars/IP maps | The actual provisioning checkout, not tracked examples or a runner clone |
| Local Terraform state | Original `.terraform/state/<setup>/<env>/terraform.tfstate` on its actual provisioning host |
| Remote Terraform state | Backend's qualified version/snapshot recovery plus independent credentials; a local cache is not the authoritative state |
| Talos machine secrets/config, kubeconfig/talosconfig, SOPS keys | Original tier-owned ignored recovery paths, with independent custody of required keys |
| CI-generated inputs/state | Persistent owner-controlled runner data before job cleanup, or the original backend; ephemeral CI artifacts alone are insufficient |
| Source/tool/provider/image versions | Pinned code and independent software-intake artifacts; preserve separately from this ignored-input allowlist |

Name every tier/environment/setup and record the owning host, exact source root, state lineage/serial,
export, recovery selection and freshness objective. Each original must have a real route into
independent custody. Add a separate source entry for each owner; never substitute an empty example
checkout when a source is unavailable. Do not place Tier 0 originals under ordinary Tier 1 runner custody.

For CI, retain the actual state/input root on the authorized provisioning host and gate cleanup on an
accepted independent recovery copy. Configure that persistent host path as the source export. If
the runner deletes its workspace before this pull, the role cannot recover those files: change the
runner lifecycle or qualify backend recovery before calling input backup complete.

## Commission a bounded source view

On each source host, the source owner selects a directory containing the actual owning Git working
trees and their ignored data (example `/srv/homelab-iac`). Use a qualified source snapshot or pause
Terraform/configuration writers during capture; client-side `ro` does not freeze source writes.
Use full working trees, not `.git` worktree links pointing outside the export.

For a Linux Samba source, the authorized source administrator commissions an independent local reader
with filesystem read/traverse access only to the approved scope and no interactive/provisioning
rights. Add this focused service to the existing managed Samba configuration; adapt the actual root,
reader and recovery-host address. Preserve other services and the server's security policy. [1]

```ini
[recovery-inputs]
    path = /srv/homelab-iac
    read only = yes
    guest ok = no
    valid users = recovery-input-reader
    hosts allow = 192.0.2.10
    server smb encrypt = required
    follow symlinks = no
    wide links = no
    browseable = no
```

Use a local Samba credential (`smbpasswd -a recovery-input-reader`) independent of failed SSO/FreeIPA.
Grant only read/traverse through the source's native filesystem ACL tooling; verify new state/input
files inherit readable ACLs without giving this identity write or source administration. Validate the
configuration with `testparm --suppress-prompt`, reload through the source's normal service manager,
and allow SMB 3.1.1 only from the recovery host. For a NAS/Windows source, commission equivalent
read-only share and file ACLs through its native administration path.

The source owner creates `.control-backup-source` at the export root with a unique recorded marker,
readable to this reader but never writable by it. Store the SMB username/password in a controller-side
mode `0600` credential file (`username=...` and `password=...`, optionally `domain=...`). This identity
must be unable to change originals or administer snapshots, even from another client.

## Configure transport and selections

```yaml
control_backup_input_sources:
  - name: provisioner
    source: //provisioner.internal.example.com/recovery-inputs
    mount: /mnt/control-inputs-provisioner
    marker: REPLACE_WITH_SOURCE_OWNER_MARKER
    credentials_file: /private/recovery/provisioner-reader.credentials
control_backup_inputs:
  - {repo: /mnt/control-inputs-provisioner/homelab-tier-0, path: .terraform/state}
  - {repo: /mnt/control-inputs-provisioner/homelab-tier-0, path: ansible/inventory/hosts.yml}
  - {repo: /mnt/control-inputs-provisioner/homelab-tier-0, path: ansible/group_vars/all.yml}
  - {repo: /mnt/control-inputs-provisioner/homelab-tier-0, path: secrets}
```

Add the actual remaining local group vars, tfvars, IP maps and each other tier/environment's original
paths explicitly. `repo` is the source Git root **as mounted on the recovery host**; `path` is bounded
repo-relative and ignored. Directory selections must contain no tracked files. The role mounts every
source with separate root-only credentials, SMB 3.1.1 encryption and `ro,nosuid,nodev,noexec`.
Every run checks the exact mounted target, read-only flag, source marker, Git root/ignore status and
that each selected repository is inside one of those mounts. Arbitrary recovery-host paths fail.

The job reads these original paths directly into independent restic custody; no writable source
credential, deployment of the backup job onto the provisioning host, or Git-only replication is used.
The restic manifest records the source export/mount mapping and selected paths for recovery provenance.

## Verify independence and freshness

Freeze writers or commission a coherent source snapshot, run
[the backup playbook](../backups/control-applications.md#configure-and-schedule), then extract a known
set into a [new clean target](files.md). Compare original and restored state lineage/serial, environment,
inventory and one protected input hash. Repeat with the provisioning host, cluster/SSO and hosted CI
unavailable; only independent repository/key access may be required for extraction.

Prove the share reader cannot write/delete a disposable source canary and cannot administer source
snapshots. Record that denied result without touching operational state. Record source snapshot time
or writer-pause interval, input/state age and observed RPO/RTO. A fresh restic timestamp does not prove
that an exported snapshot or CI workspace was itself current. Monitor source-generation lag separately.
Requalify after moving runners, roots, state backends, credentials or cleanup behavior.

## References

1. [Samba share boundaries, read-only access and encryption](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
