# Security logging acceptance record

Status: **Not tested**. Populate this project-owned record from an authorized drill;
never infer service acceptance from provisioning, fixture tests or matching record counts alone.
Procedure: [logging fault and restore drill](${docs}/administration/logging-drill.md).

## Scope and prerequisites

| Item | Recorded value |
| --- | --- |
| Date, owner and independent reviewer | TBD |
| Deployment revision and receiver/queue/archive versions | TBD |
| Collector hosts, storage and independent failure domains | TBD |
| Source identities, forwarding transports and bootstrap trust | TBD |
| Exact acceptance boundary and evidence of durable copies before source release | TBD |
| Peak rate, outage duration, queue limits and exhaustion policy | TBD |
| Retention policy and separate writer/reader/retention custody | TBD |
| Independent backup ID, data-disk inclusion and separately held keys | TBD |
| RPO / RTO targets and measurement method | TBD |
| Approved disposable targets, fault/undo commands and abort conditions | TBD |

## Scenario results

Use Passed, Failed, Not tested or Out of scope with an explicit reason.
An unmet required scenario blocks acceptance; scope exclusions must not become implicit passes.

| Scenario | Result | UTC start/end | Evidence location / digest | Reviewer |
| --- | --- | --- | --- | --- |
| Healthy collection and authenticated source attribution | Not tested | TBD | TBD | TBD |
| Abrupt receiver-process loss and queued replay | Not tested | TBD | TBD | TBD |
| Physical host/storage failure within the declared envelope | Not tested | TBD | TBD | TBD |
| Network/archive outage and bounded queue exhaustion | Not tested | TBD | TBD | TBD |
| Independent notifications while Tier 1/SSO/cluster are unavailable | Not tested | TBD | TBD | TBD |
| Producer/read-only-role deletion and retention-shortening denials | Not tested | TBD | TBD | TBD |
| Offline inspection of a preserved data-volume copy | Not tested | TBD | TBD | TBD |
| Clean-target restore from the independently protected backup | Not tested | TBD | TBD | TBD |

## Record reconciliation

| Phase / scenario | Manifest digest | Expected unique | Observed unique | Missing / changed / unexpected | Duplicate copies | Report location |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Keep original exports, manifests and tool reports outside the collector's destruction
boundary. Synthetic `source` labels are not authenticated identities. Record actual
transport identities and authorization results separately. Hashes need independently
preserved references; matching hashes alone do not establish custody or prevent deletion.

## Restore and decision

| Item | Recorded value |
| --- | --- |
| Surviving input, backup age and recovery key custodian | TBD |
| Restored target and proof it cannot rejoin live intake | TBD |
| Offline tools, source catalogue, timestamp interpretation and intact event range | TBD |
| RPO observed; RTO to useful inspection and service restoration | TBD |
| Original evidence unchanged; restored-copy reconciliation and access denials | TBD |
| Unaccepted source gaps, accepted-record loss and residual threats | TBD |
| Accepted capability / failure envelope, or rejection and follow-up owner | Not accepted |

Do not place credentials, key material or raw security logs in this document or Git.
Record protected evidence locations and approved summaries only. Repeat after changes
to transport, queue/flush behavior, retention, storage, backup, credentials or failure domains.
