# Verified software intake operations

Operate the optional Tier 1 `intake-1` service. The proxy/cache remains a separate transport service.
First installation belongs to the [deployment guide](../deployment/stage-3-trust/step-3b-verified-intake.md);
the [design](../architecture/software/artifact-verification.md) explains authority and trust.

## Contents

- [How is intake run or scheduled?](#how-is-intake-run-or-scheduled)
- [How is the data volume managed or expanded?](#how-is-the-data-volume-managed-or-expanded)
- [Why was a candidate rejected?](#why-was-a-candidate-rejected)
- [How is an incident retained or cleared?](#how-is-an-incident-retained-or-cleared)
- [How is a consumer rolled back?](#how-is-a-consumer-rolled-back)
- [What must be backed up and restored?](#what-must-be-backed-up-and-restored)
- [How is the publication gate tested?](#how-is-the-publication-gate-tested)

## How is intake run or scheduled?

1. Edit sources, trusted public-key fingerprints and limits in **Tier 1 `ansible/group_vars/intake.yml`**.
   Reinstall policy with the deployment recipe; do not edit generated `/etc/software-intake/policy.yml`.
2. Run from **`<prefix>-tier-1/`**:

   ```bash
   bash scripts/deploy.sh intake --ansible-only
   bash scripts/deploy.sh intake --recipe maintenance
   ```

3. Inspect `latest.json` and its versioned receipt using the [deployment checks](../deployment/stage-3-trust/step-3b-verified-intake.md#7-run-and-inspect-the-first-intake).
   To schedule accepted policy, set `software_intake_timer_enabled: true`, select
   `software_intake_schedule` and repeat the first command. There is one serialized service,
   not overlapping workers. To pause new intake, set that value to `false` and reapply.

On **`intake-1`**, inspect execution and scheduling:

```bash
sudo systemctl status intake.service intake.timer --no-pager
sudo journalctl -u intake.service -n 60 --no-pager
```

## How is the data volume managed or expanded?

Terraform owns `scsi1`; the deployment recipe uses Shared's data-volume role to manage its XFS/ext4
filesystem and UUID mount at `/srv/intake`. Only a verified new blank disk is formatted. Recognized
existing data is preserved; a missing declared volume, conflicting mount or mismatched identity fails.
Keep `software_intake_data_device`, `software_intake_data_fstype` and any `software_intake_data_uuid`
pin in **Tier 1 `ansible/group_vars/intake.yml`** aligned with the retained disk. Never clear a mount
record or UUID pin to make an unexpected replacement pass.

To expand capacity:

1. Increase `extra_disks[].size_gb` for `scsi1` in **Tier 1 `terraform/deployments/intake/terraform.tfvars`**.
   Retain its interface and storage mapping; this path grows the filesystem, not shrinks it.
2. Run from **`<prefix>-tier-1/`**:

   ```bash
   bash scripts/deploy.sh intake
   ```

3. On **`intake-1`**, verify the retained UUID, mount restrictions and added space:

   ```bash
   findmnt --mountpoint /srv/intake -o TARGET,SOURCE,UUID,FSTYPE,OPTIONS
   df -h /srv/intake
   ```

**Expected:** the same filesystem identity and data, with increased capacity. Filesystem type changes
and partition/LVM resizing need a separate migration plan; replace lost data through recovery.

## Why was a candidate rejected?

1. Inspect the service journal and `/srv/intake/quarantine/` on **`intake-1`** using administrator access.
2. Read the incident's `intake-quarantine.json`; scanner details, when available, are in its private
   `scanner.log`. Do not copy suspected content into the served tree or execute it.
3. Fix the cause below, then rerun intake. Prior accepted content remains available.

| Cause | Action |
| --- | --- |
| Publisher/hash/metadata failure | Check the independently trusted key, expected digest, repository selection and vendor metadata; do not bypass the gate |
| Detection, encrypted/broken archive or scan limit | Retain for review; narrow the selection or qualify content support before changing policy |
| Missing/stale database or scanner error | Restore current approved definitions/engine; an engine error is not a clean result |
| Low disk space or lost mount | Recover the original data volume or grow it through the deployment inputs; inspect retained incident/history usage before retrying |
| Worker timeout/interruption | Confirm the service is stopped; private staging/publishing remnants were never served. Preserve evidence, then remove only the abandoned job directories |
| Reporting/discovery failure | Inspect the actual version and `latest.json`; a committed publication can exist even if later reporting failed |

Structured local syslog events use ident `software-intake`, facility `local6`, and sanitized
source/verdict/reason/policy fields. Commission [protected forwarding](../deployment/stage-2-logging/sources.md)
and verify delivery to Tier 0. Nginx's local access records omit request paths/queries.
Neither a successful job nor a local journal proves independent archive delivery.
An unchanged content/policy version reuses its immutable first-acceptance receipt; subsequent
assessment times and scanner/database versions belong to the decision events.
Native logrotate retains 14 rotated Nginx logs, checking daily and at a 20 MB size threshold.
That threshold is evaluated when logrotate runs, not a hard disk quota; monitor OS capacity and
protect required records through Tier 0 forwarding before local rotation removes them.

## How is an incident retained or cleared?

1. On **`intake-1`**, identify the incident directory under `/srv/intake/quarantine/` and read its receipt.
2. To hold it beyond automatic expiry, create an administrator-owned `.hold` file inside that incident:

   ```bash
   read -r -p 'Incident directory name: ' INCIDENT
   sudo touch -- "/srv/intake/quarantine/$INCIDENT/.hold"
   ```

3. Archive required evidence independently before clearing a hold. Remove only that `.hold` when
   the incident can expire; ordinary incidents expire after `software_intake_quarantine_days`
   (default 14). Cleanup runs before the next intake's capacity check.

Automatic cleanup requires a recognized quarantine receipt and never deletes approved versions.
Set a smaller repository selection or expand storage when retention exhausts capacity. A hold is
an operator convention, not WORM protection against the administrator. Consult the
[protected evidence design](../architecture/operations/security-logging.md) for that boundary.

## How is a consumer rolled back?

1. Select the previous accepted version from its retained receipt and verify it remains valid under
   vendor signature, revocation and expiry rules.
2. Edit the **consumer's owning repository inputs**, replacing its immutable repository/artifact URL
   with that version. Keep native verification enabled; do not edit publication files or rewrite history.
3. Apply the consumer configuration, inspect its native repository refresh and verify the intended
   package/artifact selection. Package downgrades and database rollback require the product's own plan.

`latest.json` is discovery, not automatic rollout. Retaining bytes does not make expired APT metadata
or a revoked signing key acceptable. Approved history has no automatic deletion; remove a version
only after checking every consumer pin and the independent recovery copy.

## What must be backed up and restored?

1. Include the **OS and data disk** of `intake-1` in the [VM backup routine](backups/virtual-machines.md).
   Retain Tier 1 policy, source keys/fingerprints, trusted TLS identity, receipts and selected publications
   in the [independent recovery set](backups/recovery-set.md). Consumer recovery must also retain its
   own approved packages/tools without depending on this VM.
2. For a consistent backup, stop new intake and wait for `intake.service` to be inactive before capturing
   both disks. Protect private quarantine and the TLS key; ordinary readers receive only public content.
3. Restore to an isolated target using the [VM recovery runbook](recovery/virtual-machines.md), verify
   the data-disk UUID and restore policy/trust. Select that device/filesystem and pin its UUID in
   `software_intake_data_uuid` before rerunning `deploy.sh intake` from **`<prefix>-tier-1/`**.
   Keep the timer off, verify retained hashes and HTTPS reads,
   refresh definitions, then pass a clean and rejected test source before reconnecting consumers.

A single worker/publication VM has no service-level redundancy. Its recovery point is the last
qualified independent backup; supplier failures stop new publication. An existing native repository
service can satisfy the same interface with its own availability contract.

## How is the publication gate tested?

Use an isolated test source and test clients; never put malware test files into a production repository.
Record source/policy/receipt identities, command results and Tier 0 event IDs.

| Test | Required result |
| --- | --- |
| Clean trusted artifact and small signed RPM/APT fixtures | Same verified/scanned bytes served through a versioned URL; native consumer verification succeeds |
| Wrong trusted hash, bad/untrusted signature, tampered metadata/package | No new selection; private incident and sanitized rejection event |
| Harmless EICAR test, encrypted/oversized/unsupported input | No publication; explicit detection/limit/unsupported verdict |
| Definitions missing/expired, scanner crash or interrupted acquisition | Failure, no clean verdict and no partial public version |
| Lose mount, fill reserve or fail publication | Previous selected URL/bytes unchanged; clear failure |
| Fetch/scanner/web account tries to modify approved content | Denied; private/quarantine content cannot be read over HTTPS |
| Denied reader, PUT/DELETE, HTTP or direct WAN bypass | Denied by the appropriate HTTPS/network control |
| Reboot with the real systemd sandbox and EL SELinux enforcing | HTTPS and scheduled clean/rejected jobs work without weakening isolation |
| Restore both disks to a clean target without search/SSO services | Valid retained versions, current definitions and independent evidence forwarding |

Repository tests exercise local components; they do not commission Proxmox, firewall, vendor
repositories, SELinux or the site's backup target. Keep those live results in the project's
administration records before relying on the path for Tier 0 updates.
