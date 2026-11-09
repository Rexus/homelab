# Security logging fault and restore drill

Prove the selected logging path with numbered synthetic records, controlled faults
and a clean-target restore. This is an acceptance procedure, not a collector installer.
A successful VM apply, open port or matching file alone is not evidence of logging HA.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`). Shared supplies the
stateless record checker; Tier 0 owns the system, test inputs and evidence.
**Prerequisites:** functioning [Stage 2 collection](../deployment/stage-2-logging/README.md),
an independently recoverable backup, reader/key kit, authorized custodian and disposable
fault targets. The supplied receiver alone does not satisfy the independent archive,
retention and HA prerequisites.
Do not run fault commands on the only collector, archive, backup or surviving evidence.

<a id="contents"></a>

## Find a task

- [How is the test prepared?](#step-1-prepare-the-test-and-acceptance-boundary)
- [How are faults injected and records compared?](#step-2-inject-faults-and-reconcile-records)
- [How is independent restoration tested?](#step-3-restore-and-investigate-independently)
- [When can the result be accepted?](#acceptance-decision)

<a id="step-1-prepare-the-test-and-acceptance-boundary"></a>

## How is the test prepared?

**Work from:** the Tier 0 repository root on the execution host.

1. Open the project-owned **`docs/administration/logging-evidence.md`** and complete the record below.
   Refresh preserves edits to this record but recreates a missing record from the current starter.
   A recreated blank record is not evidence that an earlier drill passed.
2. Verify independent copies, reader/key access and the approved fault/undo commands.
   Stop if a sole surviving collector, archive or backup would be at risk.
3. Create the synthetic batches with the command below; preserve them outside the collector before the fault.

| Record before testing | Required choice/evidence |
| --- | --- |
| Archive model | [A: NAS-backed or B: retention-locked](../architecture/operations/log-retention.md); named custodians and access denials |
| A: NAS | Independently protected checkpoint, snapshot/backup lag and tested restore; no WORM or zero-RPO claim |
| B: locked storage | Actual version-lock enforcement, including denied shortening/deletion |
| Failure envelope | Versions/configuration, source identities, physical domains, rate, queue budget, outage limit and fault/undo commands |
| Accepted records | Named durable-copy boundary and independent receipts/proof, separate from emitted records |
| Recovery | Data disks, closed segments, catalogue, integrity metadata, keys and approved [RPO/RTO](backups/virtual-machines.md#backup-policy) |

NAS sender queues release on transport submission, not archive commitment. Retain original
source files for replay and measure the unprotected tail. TCP/RELP receipts and orderly shutdown
do not prove arbitrary-crash survival or replicated archive commitment. [1]

On the Tier 0 execution host, create an ignored, protected working directory and
three independent test batches. Keep their manifests/digests outside the collector
before fault injection; do not place raw exports or credentials in Git.

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
umask 077
mkdir -p .logging-evidence
RUN_DIR="$(mktemp -d "$PWD/.logging-evidence/drill.XXXXXX")"
for phase in before during after; do
  bash scripts/log-evidence.sh generate --source lab-producer --count 1000 \
    --output "$RUN_DIR/$phase.jsonl" > "$RUN_DIR/$phase-manifest.json"
done
printf 'Evidence directory: %s\n' "$RUN_DIR"
```

Repeat with a new directory for each scenario/source. These labels and creation
timestamps are test data, not authenticated source attribution or commit times.
The [checker reference](../reference/logging-evidence.md) defines inputs and exit codes.

<a id="step-2-inject-faults-and-reconcile-records"></a>

## How are faults injected and records compared?

**Work on:** the approved disposable producer/receiver for injection; the Tier 0 root for comparison.
**Prerequisites:** Step 1's record, independent manifests, a covered before-batch backup and approved undo steps.

1. Submit `before.jsonl` through the **configured disposable producer's normal path**.
   For a Linux source with local forwarding already configured, run this on that source
   after copying all three batches through an authenticated channel. In that producer session,
   select their actual directory; `$RUN_DIR` on the execution host is not inherited: [2]

   Run on **the approved disposable producer**.

   ```bash
   read -r -e -p "Producer directory containing the copied drill batches: " LOGGING_PRODUCER_BATCHES
   logger --socket-errors=on --size 4096 --tag homelab-logging-drill --file "$LOGGING_PRODUCER_BATCHES/before.jsonl"
   ```

   A repository checkout does not configure forwarding. `logger` success is not a
   durable archive acknowledgement. Confirm the before-batch acceptance boundary,
   preserve its proof independently, and verify authenticated source metadata.
   Close an approved archive checkpoint and take an independent backup containing
   this whole batch. Record that backup ID and its covered manifest before the fault.
2. Apply one approved fault using the recorded command. While it is active, run on the producer:

   Run on **the approved disposable producer**.

   ```bash
   logger --socket-errors=on --size 4096 --tag homelab-logging-drill --file "$LOGGING_PRODUCER_BATCHES/during.jsonl"
   ```

   Observe durable spooling, alarms and the declared rejection/backpressure behavior.
3. Recover using the approved undo command, then run on the producer:

   Run on **the approved disposable producer**.

   ```bash
   logger --socket-errors=on --size 4096 --tag homelab-logging-drill --file "$LOGGING_PRODUCER_BATCHES/after.jsonl"
   ```

   Preserve UTC injection/recovery times and queue/storage counters.
4. On the Tier 0 execution host, wait only until the recorded drain deadline. Obtain a read-only export of these
   original drill messages from the retained archive, not a dashboard or sender spool.
   Reconcile all three batches against `received.jsonl`:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   read -r -e -p "Existing checker-side drill directory: " RUN_DIR
   bash scripts/log-evidence.sh verify \
     --expected "$RUN_DIR/before.jsonl" "$RUN_DIR/during.jsonl" "$RUN_DIR/after.jsonl" \
     --observed "$RUN_DIR/received.jsonl" > "$RUN_DIR/received-report.json"
   ```

The checker accepts direct original JSON messages or the explicitly selected JSON
export message field. See the [format contract](../reference/logging-evidence.md#input-format).
Never construct observed data by copying an expected manifest. Preserve raw segments
and authenticated-source metadata alongside the filtered export; counts alone cannot
prove attribution, commit order, retention enforcement or that a fault actually occurred.
Missing, altered or unexpected records fail reconciliation. Identical retries are counted,
not silently removed or treated as exactly-once delivery.

| Scenario | Controlled fault and required observation |
| --- | --- |
| Healthy control | All expected records arrive with valid source identity; establish the normal latency and count baseline |
| Abrupt receiver process loss | Kill the approved disposable receiver process without a graceful flush; observe restart/replay and reconcile accepted records |
| Physical host/power loss | Remove one approved failure domain under the [redundant-intake contract](../deployment/stage-2-logging/step-3b-redundant-intake.md); a guest reboot is not this test |
| Network or archive outage | Isolate only the approved test path; measure spool/replay and NAS/backup lag. Main path retains within its configured buffers, not until application-level archive acknowledgement; reconcile and report the exposed tail |
| Bounded queue/storage exhaustion | Use a capped test volume/quota, never fill a live filesystem; observe independent alerts and the declared reject/backpressure policy |
| Tier 1, cluster and SSO unavailable | Intake, authorized evidence reads and independent notifications continue within the selected failure envelope |
| Unprivileged access | As producer/query roles, attempt forged ownership, raw reads, overwrite and deletion; deny snapshot/backup administration to the transfer identity; for B also prove retained-version deletion/shortening denial |

For a systemd-managed disposable receiver, an example **process** fault is: [5]

Run on **the approved disposable receiver**.

```bash
read -r -p "Approved disposable receiver service unit: " RECEIVER_UNIT
sudo systemctl status "$RECEIVER_UNIT" --no-pager
```

Verify the unit and recorded fault authorization, then inject abrupt process loss:

Run on **the approved disposable receiver**.

```bash
sudo systemctl kill --kill-whom=main --signal=SIGKILL "$RECEIVER_UNIT"
```

For this service, recover with the recorded systemd operation if automatic restart has not recovered it:

Run on **the approved disposable receiver**.

```bash
sudo systemctl start "$RECEIVER_UNIT"
sudo systemctl status "$RECEIVER_UNIT" --no-pager
```

For other scenarios use the approved product-specific undo command. Automatic restart can shorten
the outage; record what actually happened. This test is not sudden power loss,
storage-controller failure or site-loss evidence. Do not alter production units
or flush queues first to make a crash test pass.

**Expected:** all records inside the declared durability envelope reconcile; duplicates are reported.
**Stop:** on missing/altered data, a failed undo or an exceeded buffer/drain deadline.
Preserve originals and record the failure; do not delete queues or rewrite data to pass.

<a id="step-3-restore-and-investigate-independently"></a>

## How is independent restoration tested?

**Work on:** an isolated recovery host with independently held tools, keys and backups.
Use [NAS backup restoration](security-logging.md#nas-backup-restoration) for the restic commands,
then return to the Tier 0 checker with an authenticated export from the restored copy.

1. Preserve originals using [offline investigation](security-logging.md#offline-investigation).
   Test a surviving-volume **copy** first, then repeat from the independently protected
   backup on a clean target. Keep restored VMs/NICs isolated so duplicate host identities,
   IPs or collector credentials cannot reconnect to live intake.
2. Make the original collector, Tier 1 analytics, normal SSO, cluster and online secret
   service unavailable to the recovery target. Use the independently held tools/keys
   to inspect a read-only, no-journal-replay working copy. Follow the filesystem-specific
   procedure; ext4 `ro` alone can still replay a journal. [3] Any repair uses another copy.
   Verify pre-fault segment digests against independently preserved references, source
   catalogue, timestamps, event ranges and recorded backup ID. Backup-job success or
   verifying a backup without extracting usable records is not a restore test. [4]
3. Export the original drill messages from the **restored records** as `restored.jsonl`.
   The pre-fault backup above must contain the whole before-batch:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   read -r -e -p "Existing checker-side drill directory: " RUN_DIR
   bash scripts/log-evidence.sh verify --expected "$RUN_DIR/before.jsonl" \
     --observed "$RUN_DIR/restored.jsonl" > "$RUN_DIR/restored-report.json"
   ```

   Filter the export to that checkpoint's drill batch, retaining the raw restored
   segments separately. Do not compare against later events absent from this backup.
   A pre-fault backup proves that checkpoint's recovery, not zero-loss recovery of
   the entire outage; the live archive reconciliation covers all three batches.

Measure time to the first useful investigation separately from time to restored
service. Record backup age/recoverable event range as observed RPO, and both recovery
times against RTO. If backup policy permits a tail gap, quantify it; never relabel
lost accepted records inside the declared durability envelope as an expected source gap.

Readability of a restored file does not prove that all required copies survived the
fault. Restore completion also requires the recorded access-denial and key-custody checks.
Rebuild Tier 1 search copies only after Tier 0 evidence is preserved and verified.

<a id="acceptance-decision"></a>

## When can the result be accepted?

Keep the completed project record, original manifests, fault/undo transcript, counters,
commit proof, backup ID, digests and checker reports in independently protected custody.
Raw evidence and keys do not belong in the public upstream or ordinary private Git history.

Mark each required scenario Passed, Failed or Not tested. Approve only the demonstrated
failure envelope; an untested required case blocks acceptance. The checker's
`records_match` result is deliberately separate from `fault_restore_acceptance`, which
it cannot assess. Offline fixture tests validate the checker, not the logging system.

For A, record privileged NAS/backup deletion as a trusted-administrator residual risk,
not a passed prevention test. For B, a privileged identity that can bypass the selected
retention requirement blocks that claim. A change in role holders or required deletion
protection requires renewed acceptance, not just a renamed record.

Return to [Stage 2 acceptance](../deployment/stage-2-logging/README.md#step-3-protect-and-verify-retained-evidence).
Repeat after material transport, queue/flush, storage, backup, retention or identity changes.

## References

Logger/systemd command references checked 2026-11-08; other references checked 2026-10-17.

1. [rsyslog reliable forwarding and crash limits](https://docs.rsyslog.com/doc/tutorials/reliable_forwarding.html)
2. [util-linux logger inputs and socket errors](https://raw.githubusercontent.com/util-linux/util-linux/master/misc-utils/logger.1.adoc)
3. [Linux ext4 read-only and journal behavior](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options)
4. [PBS verification and restore operations](https://pbs.proxmox.com/docs/backup-client.html)
5. [systemd process signalling and target selection](https://github.com/systemd/systemd/blob/main/man/systemctl.xml)
