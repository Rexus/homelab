# Requirement results and CI

The requirement report starts with every requirement and verification case in the native homelab model.
It connects those obligations to actual test attempts and retains failed, missing, blocked, uncovered
and stale results. A requirement link or a successful model build is never counted as a test pass.

## Contents

- [Run the checks](#run-the-checks)
- [Read a result](#read-a-result)
- [Maintain bindings and freshness](#maintain-bindings-and-freshness)
- [Run the CI job](#run-the-ci-job)
- [Evidence and limits](#evidence-and-limits)
- [References](#references)

## Run the checks

From **the upstream homelab checkout**, rebuild after authored model changes using the
[native model setup](../01-architecture/07-software-intake/02-connected-model.md#build-and-check).
Use Linux/WSL with the [isolated Squid/APT prerequisites](../01-architecture/07-software-intake/06-implementation-comparison.md#repeat-the-comparison),
Ansible Core and `community.general`. The test runner reports missing tools as unsuccessful evidence.
Set `HOMELAB_SQUID`, `ANSIBLE_PLAYBOOK` and, for an unpacked collection, `ANSIBLE_COLLECTIONS_PATH`.
Run checks as an ordinary user; fixture processes use temporary files and loopback ports.

```bash
python scripts/architecture/software_intake.py build
python scripts/architecture/requirements.py run
python scripts/architecture/requirements.py gate
```

`run` executes six bound test methods (including applying the APT/DNF policy), then reports and gates the entire isolated scope. These
exercise source and generated Squid policy, signed APT retrieval against six native model experiments,
and publisher metadata/expiry/trust exceptions. Tests execute their normal unittest fixtures and
assertions. Subtest failures, setup errors, skips and expected failures cannot count as passing evidence.

Each attempt has its own directory under `.tmp/requirement-evidence/runs/`: source fingerprints,
environment/tool versions, individual test outcomes, captured logs and the measured product comparison.
An attempt is recorded before execution; an interrupted attempt stays blocked. Failed attempts remain
after a correction. `--only policy-source` reruns one bound check; it does not narrow the gate.

Open `.tmp/requirement-evidence/report/requirements.md`. JSON and JUnit XML in the same directory
support automation. `report` refreshes those summaries without executing tests. `gate` returns 0 only
for current passing obligations in the selected scope, 1 for failed acceptance, and 2 for invalid inputs.
An assessment error replaces previous summaries with an explicit failure.

```bash
python scripts/architecture/requirements.py report
python scripts/architecture/requirements.py gate --scope all
```

The `all` gate includes site obligations and currently fails because their evidence is missing.
The isolated gate also remains incomplete while the source-connection-refusal variant lacks an executable
check. Passing HTTP-error checks cannot close that separate acceptance path.

## Read a result

| Result | Meaning |
| --- | --- |
| passed | All bound assertions passed for the stated method and environment |
| failed | A current required check failed or errored; inspect its captured assertions/fixtures |
| incomplete | Executed checks do not cover all declared acceptance variants; open coverage gaps remain |
| missing | No attempt exists, or a declared site demonstration has no recorded evidence |
| blocked | A check skipped, timed out, was interrupted, expected-failed, or did not complete |
| uncovered | A native requirement lacks a verification case, or a case lacks an assessment binding |
| stale | The newest attempt's relevant inputs differ from the current declared inputs |

The report shows all four native requirements and every scoped obligation, including ones outside
the isolated CI gate. `REQ-policy` and `REQ-integrity` can pass isolated checks while remaining missing
overall because deployed TLS/trust evidence is absent. `REQ-custody` and `REQ-egress` require site
demonstrations. No site fulfillment is inferred from parsing, simulation, proxy configuration or APT
fixtures. A failed expected denial scenario means the *assertion* failed; correctly refusing a denied
request is a passing test.

Aggregate status prioritizes failed, blocked, uncovered, stale, incomplete, missing, then passed. Individual rows
remain visible. The newest attempt wins for each check; an older passing run never hides a later failure.
A previous failure against changed code becomes stale and requires a new run, not fallback to an old pass.

## Maintain bindings and freshness

Native requirements, acceptance criteria and `verify` relationships remain in their owning SysML files.
[`assessment.json`](../../artifacts/architecture/evidence/software-intake/assessment.json) owns only executable
selectors, methods, scoped claims and material input patterns. It does not duplicate the requirement
inventory or the model's expected experiment outcomes. Add an adequate binding when a requirement or
verification case arrives from SysON; an unbound addition remains visible and fails the gate.

The fingerprints cover authored model sources, verification definitions, test/helpers, relevant
implementation, the assessment plan and CI environment setup. Expanding a declared file pattern also
invalidates prior evidence. Rebuilding diagrams neither renews evidence nor, by itself, invalidates it.
Changes during execution block the attempt. A stale native model must be rebuilt before reporting.

Recorded tool versions identify the environment that actually ran. Source freshness does not attest
that a different machine has those tools. Rerun on a new environment or after tool/dependency changes;
CI always executes all bound checks in its prepared environment. The versioned setup files are material
inputs. Do not copy a result to another environment and describe it as a new observation.

## Run the CI job

The root [GitLab pipeline](../../.gitlab-ci.yml) calls one reusable
[`architecture_ci.py`](../../scripts/architecture/architecture_ci.py) entry point. It checks:

1. Current generated sources/views and a fresh native parser result against the accepted model index.
2. Regression checks for reporting, generated-artifact integrity and selected native view relationships.
3. All isolated implementation checks and the requirement gate, including declared coverage gaps.

The job does not rebuild accepted outputs to make a stale checkout pass. Model or generated changes
must be rebuilt and reviewed in the normal development workflow. The build records checksums for its generated
deliverables. CI validates those checksums and their complete source fingerprint, and reparses the native
model. It does not require Linux and Windows Graphviz/font versions to reproduce identical SVG geometry.
The local `check` command still compares a full rerender with the accepted outputs. All stages retain logs and run even
if an earlier check fails; any failed stage fails the job.

The Ubuntu 24.04 setup prepares Java 21, the checksum-pinned SysML Pilot archive from
[`toolchain.json`](../../scripts/architecture/config/toolchain.json), Python dependencies, Squid, APT/GnuPG and Ansible.
It prevents service startup during container preparation and runs checks as an ordinary user.
The setup script is for a disposable CI container; it is not a host installation procedure.

```bash
# In a dedicated Ubuntu 24.04 CI container, from the copied checkout:
bash .gitlab/prepare-architecture.sh
bash .gitlab/check-architecture.sh
```

The same Python CI entry works in an already prepared Linux environment with the tool variables set.
GitLab receives requirement JUnit results and retains the reports, attempts and logs for 30 days,
including failed jobs. Obligations outside the selected gate appear as skipped with their actual status
in the message, not as passed tests. Preserve required artifacts before expiry. [1]

## Evidence and limits

See the [end-to-end verification record](../01-architecture/07-software-intake/requirement-reporting-verification.md)
for the actual pass/fail/missing/stale/skip runs and CI rehearsal. The repository job is wired and tested
locally in a clean Linux container. A hosted GitLab pipeline run requires the normal signed commit/push
handoff and an available runner; no hosted execution is claimed here.

Manual site evidence ingestion, automatic discovery of arbitrary untraced code and general SysML
round-trip editing remain outside this implementation. Follow the [model development workflow](model-change-workflow.md)
to reconcile those obligations and the [SysON guide](syson.md) for the selected views.

## References

1. [GitLab unit test reports](https://docs.gitlab.com/ci/testing/unit_test_reports/): JUnit reports and retained artifacts.
2. [Python unittest result hooks](https://docs.python.org/3/library/unittest.html#unittest.TestResult): standard test, subtest and fixture results.
