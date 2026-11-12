# Software intake operations

Operate the Tier 2 Squid/keepalived outbound proxy after [software intake deployment](../../03-deployment/stage-1-software-intake/README.md).
The [software intake architecture](../../01-architecture/07-software-intake/README.md) describes its trust and recovery boundaries;
the [proxy/cache reference](../../08-reference/proxy-cache.md) owns the complete settings and behavior.
For verified publication, use [verified software intake operations](verified-publication.md).

## Find the configuration or task

| Owner | Inputs or procedure |
| --- | --- |
| **`<prefix>-tier-2/`** | `ansible/group_vars/cache.yml` for VIP, client networks, approved sources and storage; `ansible/inventory/hosts.yml` for targets |
| **`<prefix>-tier-1/`** | `ansible/group_vars/intake.yml`: [verified publication](verified-publication.md), installed as the [Stage 3 option](../../03-deployment/stage-3-trust/step-3b-verified-intake.md) |
| Consumer's tier | Proxy/mirror inputs for that consumer; [Proxmox updates](host-updates.md), [APT troubleshooting](apt-refresh.md) |

The cache controls transport; verified intake owns quarantine and publication after
trust is established. The maintenance and troubleshooting steps below operate the cache pair.

**Prerequisites:** an existing cache deployment, Tier 2 inventory and local inputs, working SSH/sudo,
control-node tooling and an approved initial package source. Keep the cache's own repository proxy disabled
or use a separate working upstream proxy. Preserve independent bootstrap and recovery supply.

## Contents

- [How is configuration reconciled?](#how-is-configuration-reconciled)
- [How is the service validated?](#how-is-the-service-validated)
- [What should I check when it fails?](#what-should-i-check-when-it-fails)
- [How is a cache recovered?](#how-is-a-cache-recovered)
- [How is cache storage managed safely?](#how-is-cache-storage-managed-safely)

## How is configuration reconciled?

1. Review **`<prefix>-tier-2/ansible/group_vars/cache.yml`**: host IPs, VIP, client CIDRs,
   approved source and redirect hostnames, storage and validation URLs. Review inventory and
   [role defaults and inputs](../../08-reference/proxy-cache.md#input-locations); retain accepted values.
   Consumer proxy settings belong to each consumer's tier. Review `cache_squid_extra_options` as policy.
2. Reconcile existing hosts serially. This can install packages and restart services.

   Run from **`<prefix>-tier-2/`** on the prepared execution host:

   ```bash
   bash scripts/deploy.sh cache --recipe maintenance
   ```

3. Expect each host to converge and, when enabled, its local approved and denied proxy tests to pass.
   The maintenance recipe does not run the deployment playbook's VIP or failover exercise.
   Check the service and consumer path below. For a kit update, follow
   [existing-cache update adoption](../../03-deployment/stage-1-software-intake/step-2b-adopt-update.md#3-reconcile-the-existing-cache).

For full Ansible deployment validation on existing VMs, run without concurrent package jobs from
**`<prefix>-tier-2/`**:

```bash
bash scripts/deploy.sh cache --ansible-only
```

This can temporarily stop keepalived on the VIP owner when failover validation is enabled. It does
not run Terraform. The [validation reference](../../08-reference/proxy-cache.md#validation) lists the checks
and the `cache_validation_failover_enabled` option; disabling it skips the takeover exercise.

## How is the service validated?

1. On **each cache VM**, inspect the services, VIP and recent errors:

   ```bash
   sudo systemctl status squid keepalived --no-pager
   ip -brief address
   sudo journalctl -u squid -u keepalived -n 60 --no-pager
   ```

   Expect both services active and exactly one cache host to own the configured VIP.
2. Follow [Stage 1 acceptance](../../03-deployment/stage-1-software-intake/README.md#step-5-test-the-selected-intake-path)
   from permitted and forbidden networks: approved retrieval succeeds, an unapproved destination and
   direct WAN bypass fail, and HTTP cache hits are checked where selected. Check DNS for clients using
   the FQDN and retain native signature and digest verification.
3. Deployment validation tests the VIP from the deployment host and failover reachability from cache hosts;
   an FQDN failure is reported as a warning. It does not prove access or bypass denial from every consumer network.

## What should I check when it fails?

| Symptom | Check |
| --- | --- |
| HTTP 403 | Client CIDR, destination hostname and approved redirects; inspect `/var/log/squid/access.log` on the active cache. |
| Timeout or no VIP | Squid and keepalived status, VIP ownership, routing, firewall, VRRP and upstream reachability. |
| VIP works by IP but not name | DNS or the consumer's temporary hosts entry; test from that consumer. |
| HTTPS downloads do not show cache hits | CONNECT tunnels are encrypted and are not cached or scanned; test a cacheable HTTP object when applicable. |
| Repeated HTTP misses | Check source cacheability, refresh policy and object limits; do not override source privacy or expiry. |
| Package verification fails | Stop and investigate keys, metadata and source; do not disable verification or bypass the proxy. |

### Terraform initialization reports registry access forbidden

1. In **`<prefix>-tier-2/ansible/group_vars/cache.yml`**, add this entry to the existing
   `cache_squid_allowed_domains` list, retaining the other approved sources:

   ```yaml
   - registry.terraform.io
   ```

2. Reconcile the cache policy from **`<prefix>-tier-2/`**. Maintenance runs Ansible only;
   it needs no Terraform provider download:

   ```bash
   bash scripts/deploy.sh cache --recipe maintenance
   ```

3. On **`boot-1`**, verify registry discovery through the configured proxy:

   ```bash
   source /etc/profile.d/shell-proxy.sh
   curl --fail --silent --show-error --connect-timeout 5 --max-time 20 \
     https://registry.terraform.io/.well-known/terraform.json
   ```

   **Expected:** JSON containing `providers.v1`. Rerun the interrupted deployment command.
   Preserve its lock file and selected provider versions. Provider download/checksum/signature hosts
   must also be approved; inspect an actual denied destination if the next request fails.

For disconnected operation, select the [prepared filesystem mirror](../../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md#9-select-local-sources-and-verify).
A plugin cache or version lock alone does not replace that mirror's local-only installation policy;
see the [native Terraform configuration](https://developer.hashicorp.com/terraform/cli/config/config-file#provider-installation).

See [consumer failures and policy](../../08-reference/proxy-cache.md#consumer-verification-and-failure-behavior)
and [APT diagnostics](apt-refresh.md). The cache has one active VIP owner, not active-active
load balancing; peers have independent cache data.

## How is a cache recovered?

1. Identify the failed host and confirm the remaining owner and consumer access. Preserve logs and
   inputs; do not silently switch consumers to direct WAN. Use independent recovery supply if needed.
2. Restore or rebuild the failed VM using the [VM recovery runbook](../06-resilience/recovery/virtual-machines.md)
   and the retained Tier 2 inputs and state. Cache objects are rebuildable; peers do not replicate them.
   For an unexpected disk or identity, stop and investigate using the storage checks below.
3. Reconcile the restored configuration, then repeat service and consumer validation. Test failover
   during an appropriate window; record the results. A warm cache or successful proxy request alone
   does not establish retained offline supply or package approval.

## How is cache storage managed safely?

The example uses a separate `scsi1`, normally mounted at `/var/spool/squid`. The volume role checks
device identity and mounts before stopping Squid; it formats only an undeclared, signature-free new
device, preserves recognized filesystems and mounts by UUID. It rejects foreign mounts, hidden target
files, incompatible signatures and mismatched UUIDs. Never remove a UUID pin or mount record merely
to make an unexpected replacement pass. See [cache storage](../../08-reference/proxy-cache.md#cache-storage).

1. On **each cache VM**, inspect the selected stable device and mount before changing storage:

   ```bash
   lsblk -f
   readlink -f /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1
   findmnt --mountpoint /var/spool/squid -o TARGET,SOURCE,UUID,FSTYPE,OPTIONS
   df -h /var/spool/squid
   ```

   Substitute the configured `cache_squid_data_device` and `cache_squid_cache_dir` if different;
   compare UUID, filesystem and mount with the retained inputs and records.
2. To grow a disk, increase the appropriate `vm_instances.<cache>.extra_disks[*].size_gb` in
   **`<prefix>-tier-2/terraform/deployments/cache/terraform.tfvars`**. Keep its interface and
   storage mapping; keep `cache_squid_cache_mb` below available filesystem capacity.
3. Run from **`<prefix>-tier-2/`**, review the Terraform plan and approve only the intended change:

   ```bash
   bash scripts/deploy.sh cache
   ```

4. Repeat the mount and capacity checks on the affected VM. Expect the same UUID and retained data,
   with increased capacity. Shrinking is not automated; use a separate migration or recovery plan
   for a lost disk, changed filesystem or unexpected identity.
