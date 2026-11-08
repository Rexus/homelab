# Refresh a staged Linux template

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Supported path:** AlmaLinux/Rocky Linux package refresh, using the existing
[deployment recipe](../../../tier-0/ansible/playbooks/deployment/template-refresh.yml).
**Before starting:** accepted source template, independent artifacts/backup, original
state and SSH access. Talos uses [new image publication](template-lifecycle.md) instead.

## Find the task

- [How is a staged builder prepared?](#how-is-a-staged-builder-prepared)
- [How is the builder cleaned and converted?](#how-is-the-builder-cleaned-and-converted)
- [Can an existing template ID be replaced?](#can-an-existing-template-id-be-replaced)

## How is a staged builder prepared?

1. Initialize local inputs. Keep the existing `--env` context if this setup was
   already deployed; a new environment flag is not a state migration.

   Run from `<prefix>-tier-0/` on the protected execution host.

   ```bash
   bash scripts/init-local-files.sh --setup template-refresh
   ```

2. Edit the local files:

   | Tier 0 file | Set |
   | --- | --- |
   | `terraform/deployments/template-refresh/terraform.tfvars` | Approved source image, unused staged `vm_id` such as `9190`, disk/storage; initially `template = false`, `started = true` |
   | `ansible/inventory/hosts.yml` | Matching `template_refresh_builders` host key |
   | `ansible/group_vars/template_refresh.yml` | Matching IP, `template_refresh_prepare_builders: true`, `template_refresh_prepare_for_template: false`, `template_refresh_replace_enabled: false` |
   | Same file | Review `template_refresh_apply_updates` and `template_refresh_reboot_after_update`; both default to `true` |
   | `ansible/group_vars/all.yml`, `.env.local` | Approved package intake, SSH access and verified provider credentials |

3. Prepare the disposable staged clone; review the displayed plan and enter `yes`:

   Run from `<prefix>-tier-0/` on the protected execution host.

   ```bash
   bash scripts/deploy.sh template-refresh
   ```

   The default recipe updates all staged-guest packages and reboots after a changed
   update. It also installs/enables `acpid` and the QEMU guest agent.
4. Check the builder's packages, cloud-init and guest behavior. Stop if the clone
   fails health checks; do not publish a failed builder.

**Expected:** a running staged Linux VM, separate from the selected production template.
Optional preview uses `--plan-only`; approved provisioning jobs can use `--auto-approve`.

## How is the builder cleaned and converted?

1. Set `template_refresh_prepare_for_template: true` in
   `ansible/group_vars/template_refresh.yml`. Keep replacement disabled.
2. Run the cleanup recipe:

   Run from `<prefix>-tier-0/` on the protected execution host.

   ```bash
   bash scripts/deploy.sh template-refresh --ansible-only
   ```

   This cleans cloud-init state, SSH host keys and caches. The staged VM is no longer
   a normal reusable running guest; proceed to conversion.
3. In its Terraform guest entry, set `template = true` and `started = false`, then run:

   Run from `<prefix>-tier-0/` on the protected execution host.

   ```bash
   bash scripts/deploy.sh template-refresh --terraform-only
   ```

4. Test disposable full clones, then record approval and align the
   [Shared consumer catalog](../../reference/template-catalog.md) with the accepted
   template ID and metadata. This builder path does not run the publisher's automatic
   reference synchronization. Keep the old approved image for rollback.

**Expected:** a stopped, qualified staged template. A failed clone test means keeping
the previous approved selection and investigating or rebuilding the candidate.
Image approval and retained recovery artifacts follow the
[artifact-supply design](../../architecture/software/artifact-supply.md).

## Can an existing template ID be replaced?

This is an explicit destructive alternative, not routine promotion. The replacement
role **deletes the old target template** before cloning the staged replacement.

1. Quiesce new clones. Check linked-clone/snapshot dependencies and independent recovery
   copies. Establish one authoritative owner; do not let a separate publisher state
   and this replacement workflow compete for the same VMID.
2. Review `template_refresh_replacements`: actual Proxmox host, distinct staged/target
   IDs and destination storage. The starter maps `9190` to `9100`; replace those with
   the selected owned resources, not another root's active template.
3. Only in the approved replacement window, set `template_refresh_replace_enabled: true`
   and `template_refresh_prepare_builders: false`, then run the Ansible-only recipe above.
4. Verify replacement clones and reconcile the authoritative state/catalog before
   resuming consumption. Return `template_refresh_replace_enabled` to `false`.

**Rollback:** retain the staged image and independent backup before deletion. A failed
replacement may leave the target missing; stop new clones and restore under the same
reviewed ownership contract. No automatic rollback or dependency migration is supplied.
