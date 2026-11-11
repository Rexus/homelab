# Transport original provisioning inputs

The recovery host pulls ignored operational inputs and original state **from their actual owners**
over bounded read-only shares, then writes independently encrypted restic copies off those hosts.
It does not assume a Git clone or a manually staged recovery-host directory contains ignored files.

**Prerequisites:** identify each real provisioning workstation/CI runner/backend custodian, its full
original paths and authority; independently administer the recovery host/repository; and authorize
an encrypted read-only SMB export, local reader credential and firewall route per source.
The backup role mounts commissioned shares; it does not install or administer source SMB servers.

<a id="contents"></a>

## Operator tasks

- [How to identify the actual input/state owners?](#identify-original-ownership)
- [How to expose a bounded read-only source view?](#commission-a-bounded-source-view)
- [How to configure the input transport?](#configure-transport-and-selections)
- [How to verify copy freshness and independence?](#verify-independence-and-freshness)
- [References](#references)

<a id="identify-original-ownership"></a>

## How to identify the actual input/state owners?

| Material | Authoritative source that must be exported or independently protected |
| --- | --- |
| Tier-local ignored inventory/group vars/tfvars/IP maps | The actual provisioning checkout, not tracked examples or a runner clone |
| Local Linux setup state | Original `.terraform/state/<setup>/<env>/terraform.tfstate` on its actual provisioning host |
| Kubernetes/template state | Original `.terraform/state/talos/terraform.tfstate` or `.terraform/state/proxmox-templates/terraform.tfstate`; preserve configured overrides from the [state-path record](../../01-hosting/terraform-state.md#inspect-the-original-state) |
| Remote Terraform state | Backend's qualified version/snapshot recovery plus independent credentials; a local cache is not the authoritative state |
| Talos machine secrets/config, kubeconfig/talosconfig, SOPS keys | Original tier-owned ignored recovery paths, with independent custody of required keys |
| CI-generated inputs/state | Persistent owner-controlled runner data before job cleanup, or the original backend; ephemeral CI artifacts alone are insufficient |
| Source/tool/provider/image versions | Pinned code and independent software-intake artifacts; preserve separately from this ignored-input allowlist |

1. Record each tier/environment/setup, owner, exact root, state lineage/serial and freshness objective.
2. Add one source export/selection per actual owner; an unavailable source is a failed backup prerequisite.
3. Keep Tier 0 originals outside ordinary Tier 1 runner custody. Never substitute an empty example checkout.

For CI, retain the actual state/input root on the authorized provisioning host and gate cleanup on an
accepted independent recovery copy. Configure that persistent host path as the source export. If
the runner deletes its workspace before this pull, the role cannot recover those files: change the
runner lifecycle or qualify backend recovery before calling input backup complete.

<a id="commission-a-bounded-source-view"></a>

## How to expose a bounded read-only source view?

On each source host, the source owner selects a directory containing the actual owning Git working
trees and their ignored data (example `/srv/<prefix>-iac`). Use a qualified source snapshot or pause
Terraform/configuration writers during capture; client-side `ro` does not freeze source writes.
Use full working trees, not `.git` worktree links pointing outside the export.

**Linux source administrator:** edit the existing managed `/etc/samba/smb.conf` or its selected include.
Commission an independent local reader
with filesystem read/traverse access only to the approved scope and no interactive/provisioning
rights. Add this focused service to the existing managed Samba configuration; adapt the actual root,
reader and recovery-host address. Preserve other services and the server's security policy. [1]

```ini
[recovery-inputs]
    path = /srv/<prefix>-iac
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

<a id="configure-transport-and-selections"></a>

## How to configure the input transport?

1. Edit **Tier 0 `ansible/group_vars/control_backup.yml`**. Preserve its other selections;
   replace the source/selection entries with actual owner values:

```yaml
control_backup_input_sources:
  - name: provisioner
    source: //provisioner.internal.example.com/recovery-inputs
    mount: /mnt/control-inputs-provisioner
    marker: REPLACE_WITH_SOURCE_OWNER_MARKER
    credentials_file: /private/recovery/provisioner-reader.credentials
control_backup_inputs:
  - {repo: /mnt/control-inputs-provisioner/<prefix>-tier-0, path: .terraform/state}
  - {repo: /mnt/control-inputs-provisioner/<prefix>-tier-0, path: ansible/inventory/hosts.yml}
  - {repo: /mnt/control-inputs-provisioner/<prefix>-tier-0, path: ansible/group_vars/all.yml}
  - {repo: /mnt/control-inputs-provisioner/<prefix>-tier-0, path: secrets}
```

2. Add remaining local group vars, tfvars, IP maps and every required original tier/environment path explicitly.
3. Apply [control backup configuration](../backups/control-applications.md#configure-and-schedule).
 `repo` is the source Git root **as mounted on the recovery host**; `path` is bounded
repo-relative and ignored. Directory selections must contain no tracked files. The role mounts every
source with separate root-only credentials, SMB 3.1.1 encryption and `ro,nosuid,nodev,noexec`.
Every run checks the exact mounted target, read-only flag, source marker, Git root/ignore status and
that each selected repository is inside one of those mounts. Arbitrary recovery-host paths fail.

The job reads these original paths directly into independent restic custody; no writable source
credential, deployment of the backup job onto the provisioning host, or Git-only replication is used.
The restic manifest records the source export/mount mapping and selected paths for recovery provenance.

<a id="verify-independence-and-freshness"></a>

## How to verify copy freshness and independence?

1. Freeze source writers or select a coherent source snapshot, then run the
   [control backup](../backups/control-applications.md#operate-and-verify).
2. On the recovery host, inspect the configured source mount:

   Run on **the independent recovery host**.

   ```bash
   read -r -p "Configured input-source mount (for example /mnt/control-inputs-provisioner): " INPUT_MOUNT
   findmnt -rn -M "$INPUT_MOUNT" -o TARGET,SOURCE,FSTYPE,OPTIONS
   ```

   Require the exact source and read-only mount; compare its marker with the owner's record.
3. Extract the known set into a [new clean target](files.md). Compare state lineage/serial,
   environment, inventory and a protected input hash with the original records.
4. Repeat extraction with the provisioning host, cluster/SSO and hosted CI unavailable.
   Independent repository/key access must suffice.

Prove the share reader cannot write/delete a disposable source canary and cannot administer source
snapshots. Record that denied result without touching operational state. Record source snapshot time
or writer-pause interval, input/state age and observed RPO/RTO. A fresh restic timestamp does not prove
that an exported snapshot or CI workspace was itself current. Monitor source-generation lag separately.
Requalify after moving runners, roots, state backends, credentials or cleanup behavior.

**Stop/rollback:** if roots, markers, ACLs or freshness differ, stop accepting copies.
Restore the approved source/configuration selection through its custodian, rerun a verified copy
and retain earlier good sets. The role does not create source servers or repair runner cleanup.

## References

1. [Samba share boundaries, read-only access and encryption](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
