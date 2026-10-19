# Security logging fault and restore drill

Prove the selected logging path with numbered synthetic records, controlled faults
and a clean-target restore. This is an acceptance procedure, not a collector installer.
A successful VM apply, open port or matching file alone is not evidence of logging HA.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`). Shared supplies the
stateless record checker; Tier 0 owns the system, test inputs and evidence.
**Prerequisites:** functioning [Stage 1 collection](../deployment/stage-1-logging/README.md),
an independently recoverable backup, reader/key kit, authorized custodian and disposable
fault targets. The supplied receiver alone does not satisfy the independent archive,
retention and HA prerequisites.
Do not run fault commands on the only collector, archive, backup or surviving evidence.

## Contents

- [Step 1: Prepare the test and acceptance boundary](#step-1-prepare-the-test-and-acceptance-boundary)
- [Step 2: Inject faults and reconcile records](#step-2-inject-faults-and-reconcile-records)
- [Step 3: Restore and investigate independently](#step-3-restore-and-investigate-independently)
- [Acceptance decision](#acceptance-decision)
- [References](#references)

## Step 1: Prepare the test and acceptance boundary

1. Complete the Tier 0 project-owned `docs/administration/logging-evidence.md` record.
   It is seeded for new/generated collections, including after refresh, but never
   overwritten. Existing locally deleted project records remain deleted.
   Select [A: NAS-backed or B: retention-locked](../architecture/operations/log-retention.md).
   Record trusted administrators and the selected copy/checkpoint boundary. For A,
   measure snapshot/backup lag and test restoration from a checkpoint the share writer
   cannot administer; do not label that result WORM or zero RPO. For B, require actual
   version-lock enforcement. Neither choice waives producer/query access denials.
2. Record exact product versions/configuration, source identities, failure domains,
   expected rate, tolerated outage, buffer capacity and fault/undo commands. Separate
   the **emitted** set from the **accepted** set: name the durable commit/replication
   boundary and capture its receipts or equivalent proof before releasing source copies.
   TCP/RELP receipts and orderly-shutdown queue persistence do not prove survival
   of arbitrary crashes or replicated archive commitment. [1]
   Under the bounded-loss NAS main path, native queue release is transport-based:
   record that limitation, retain original source files for replay, and measure the
   unprotected tail rather than claiming sender-to-archive acknowledgements.
3. Verify the independent backup includes data disks, closed segments, source catalogue,
   integrity metadata and required keys. Record approved RPO/RTO and abort thresholds
   from the [backup policy](compute/backup-restore.md#backup-policy). Stop if access,
   storage, rollback or an independent recovery copy is missing.

On the Tier 0 execution host, create an ignored, protected working directory and
three independent test batches. Keep their manifests/digests outside the collector
before fault injection; do not place raw exports or credentials in Git.

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

## Step 2: Inject faults and reconcile records

1. Submit `before.jsonl` through the **configured disposable producer's normal path**.
   For a Linux source with local forwarding already configured, run this on that source
   after copying the batch through an authenticated channel if needed: [2]

   ```bash
   logger --socket-errors=on --size 4096 --tag homelab-logging-drill --file "$RUN_DIR/before.jsonl"
   ```

   A repository checkout does not configure forwarding. `logger` success is not a
   durable archive acknowledgement. Confirm the before-batch acceptance boundary,
   preserve its proof independently, and verify authenticated source metadata.
   Close an approved archive checkpoint and take an independent backup containing
   this whole batch. Record that backup ID and its covered manifest before the fault.
2. Apply one approved fault. While it is active, submit `during.jsonl` with the same
   local logger command. Observe durable spooling, alarms and the declared rejection
   or backpressure behavior. Recover using the approved undo command, then submit
   `after.jsonl`. Preserve UTC injection/recovery times and queue/storage counters.
3. Wait only until the recorded drain deadline. Obtain a read-only export of these
   original drill messages from the retained archive, not a dashboard or sender spool.
   Reconcile all three batches against `received.jsonl`:

   ```bash
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
| Physical host/power loss | Remove one approved failure domain under the [redundant-intake contract](../deployment/stage-1-logging/step-3b-redundant-intake.md); a guest reboot is not this test |
| Network or archive outage | Isolate only the approved test path; measure spool/replay and NAS/backup lag. Main path retains within its configured buffers, not until application-level archive acknowledgement; reconcile and report the exposed tail |
| Bounded queue/storage exhaustion | Use a capped test volume/quota, never fill a live filesystem; observe independent alerts and the declared reject/backpressure policy |
| Tier 1, cluster and SSO unavailable | Intake, authorized evidence reads and independent notifications continue within the selected failure envelope |
| Unprivileged access | As producer/query roles, attempt forged ownership, raw reads, overwrite and deletion; deny snapshot/backup administration to the transfer identity; for B also prove retained-version deletion/shortening denial |

For a systemd-managed disposable receiver, an example **process** fault is: [5]

```bash
read -r -p "Approved disposable receiver service unit: " RECEIVER_UNIT
sudo systemctl kill --kill-whom=main --signal=SIGKILL "$RECEIVER_UNIT"
```

Use the recorded product-specific recovery command. Automatic restart can shorten
the outage; record what actually happened. This test is not sudden power loss,
storage-controller failure or site-loss evidence. Do not alter production units
or flush queues first to make a crash test pass.

## Step 3: Restore and investigate independently

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

   ```bash
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

## Acceptance decision

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

Return to [Stage 1 acceptance](../deployment/stage-1-logging/README.md#step-3-protect-and-verify-retained-evidence).
Repeat after material transport, queue/flush, storage, backup, retention or identity changes.

## References

Sources checked 2026-10-17.

1. [rsyslog reliable forwarding and crash limits](https://docs.rsyslog.com/doc/tutorials/reliable_forwarding.html)
2. [util-linux logger inputs and socket errors](https://man7.org/linux/man-pages/man1/logger.1.html)
3. [Linux ext4 read-only and journal behavior](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options)
4. [PBS verification and restore operations](https://pbs.proxmox.com/docs/backup-client.html)
5. [systemd process signalling and target selection](https://github.com/systemd/systemd/blob/main/man/systemctl.xml)
