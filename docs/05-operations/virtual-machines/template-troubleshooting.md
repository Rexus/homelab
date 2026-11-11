# Template publication troubleshooting

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Before starting:** pause other publishers and retain the original catalog/state.
This runbook diagnoses failures; it does not authorize deleting images or state.

## Find the symptom

| Question | Task |
| --- | --- |
| Upload failed or reported no space? | [Inspect both machines](#why-did-an-upload-fail) |
| Bootstrap temporary storage is too small? | [Change upload staging](#how-is-upload-staging-moved) |
| A file/template exists after an interrupted apply? | [Recover with the original state](#how-is-partial-publication-recovered) |

## Why did an upload fail?

1. Retain the **first** error, timestamp, full path and publishing node. `broken pipe`,
   `use of closed network connection` and later postcondition errors do not identify
   the original cause.
2. On the **target Proxmox host**, inspect logs, capacity and the image datastore:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   journalctl -u pveproxy -u pvedaemon --since '-30 min' --no-pager | tail -n 80
   df -h / /var/tmp /var/lib/vz
   df -i /var/tmp /var/lib/vz
   pvesm status
   ```

3. On the **bootstrap/execution host**, inspect its own staging filesystem:

   Run on **`boot-1`** as automation.

   ```bash
   df -h / /tmp /var/tmp
   df -i /tmp /var/tmp
   findmnt -T /tmp
   ```

4. Check the selected publishing identity and storage in Proxmox:

   | Check | Required result |
   | --- | --- |
   | Image storage | **Import** content enabled on the configured image datastore |
   | Effective token permissions | `Datastore.AllocateTemplate` on that datastore, including the token ACL when privilege separation is enabled |
   | Actual storage path | Check its configured path if different from `/var/lib/vz` |
   | Connection | No rejecting proxy/firewall, request-body limit or service failure; retain verified TLS |

   Use the [scoped API permission checks](../../03-deployment/foundation/proxmox/api-access.md#validate-access).

5. Resolve the identified limit, then use [partial-publication recovery](#how-is-partial-publication-recovered).

**Interpretation:** a client IP names a connection, not a full filesystem. Free space
after temporary files were removed does not prove space was available during upload.
The bare `problem with client ...; No space left on device` message can also reflect
an AnyEvent connection-buffer limit; check effective upload permissions too. [1][2][3]

## How is upload staging moved?

1. On the execution host, select an existing sufficiently sized filesystem, create a
   private writable directory and record its absolute path.
2. Edit Tier 0 `.env.local`, using that literal path, for example:

   Edit in **`<prefix>-tier-0/.env.local`**; use the prepared absolute staging path.

   ```dotenv
   PROXMOX_VE_TMPDIR=/srv/src/template-upload-tmp
   ```

3. Confirm the selected directory exists, is writable by the execution account and
   has enough space for the approved artifact. The provider documents temporary use
   of roughly twice the image size plus overhead. [4]
4. Prepare a new `import` plan using the original catalog/state. The wrapper loads
   this provider-native setting with `--env-file .env.local`.

This affects execution-host staging, not Proxmox `/var/tmp`. Uploads run sequentially
with `-parallelism=1`; one artifact must still fit. [5] Do not delete `base-*` volumes
or files used by active uploads to make space.

## How is partial publication recovered?

1. Back up the existing `.terraform/state/proxmox-templates/terraform.tfstate` and
   retain its matching inputs. Successful imports/resources may already be recorded.
2. Inspect **Node > storage > Import**. For a complete untracked file, independently
   verify its remote SHA256 and set the exact `image_file_name` in the original catalog.
   Stop on incomplete or unverified bytes.
3. From the **Tier 0 root**, prepare a new adoption plan:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh import --env-file .env.local
   ```

4. Review imports and hardware changes, then return to
   [publication/apply and verification](template-lifecycle.md#how-are-existing-templates-adopted).
   Preserve stable catalog keys and the same state path.

**Expected:** completed prior work is reconciled and only reviewed remaining actions
are applied. A VM import does not mean its planned settings or boot-disk bytes changed.
Never discard state, remove lifecycle guards or force disk deletion to complete adoption.

## References

1. [Proxmox temporary upload handling](https://github.com/proxmox/pve-http-server/blob/master/src/PVE/APIServer/AnyEvent.pm).
2. [AnyEvent connection-buffer limits and ENOSPC](https://metacpan.org/release/MLEHMANN/AnyEvent-7.17/view/lib/AnyEvent/Handle.pm).
3. [Upload connection failures and Datastore.AllocateTemplate](https://github.com/bpg/terraform-provider-proxmox/issues/2047).
4. [Provider upload staging and temporary-directory configuration](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/index.md).
5. [Terraform apply parallelism](https://developer.hashicorp.com/terraform/cli/commands/apply#parallelism-n).
