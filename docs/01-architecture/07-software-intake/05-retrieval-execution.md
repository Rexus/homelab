# Execute an HTTP retrieval

Open the [execution view](../../../architecture/views/software-intake/execution.svg), select a run,
then follow an observed message to its function or compare it with the expected sequence. The same
model identities connect both views to the design, IaC and verification owners.

[![Native retrieval execution](../../../architecture/views/software-intake/execution.svg)](../../../architecture/views/software-intake/execution.svg)

This runs the native SysML action refinement with OpenSysML MDK 0.12.1. The official Pilot still validates
the complete connected model. Git owns both the model and the reviewed evidence; diagrams remain views.

## Contents

- [What runs](#what-runs)
- [Prepare the runtime](#prepare-the-runtime)
- [Run and inspect](#run-and-inspect)
- [Change the experiment](#change-the-experiment)
- [Evidence boundaries](#evidence-boundaries)
- [References](#references)

## What runs

The [native action](../../../architecture/functions/software-intake/retrieval-execution.sysml) starts
with admission, then performs cache lookup, source access when needed, and client verification only
when content arrived. It calls the same admission calculation as `F-admit`. Native decisions and
assignments determine the route and observable counters; Python runs the engine and checks its trace.

| Experiment | Expected outcome | Source attempts | Client verification |
| --- | --- | --- | --- |
| Available source, cache miss | Accept verified content | 1 | 1 |
| Fresh eligible cache hit, source offline | Accept verified cached content | 0 | 1 |
| Disallowed request, content cached | Deny before cache lookup | 0 | 0 |
| Cache miss, source unavailable | Return retrieval error; no usable content | 1 | 0 |
| Source content fails verification | Reject before use | 1 | 1 |
| Cached content fails verification | Reject before use | 0 | 1 |

[Experiment usages](../../../architecture/test/software-intake/retrieval-runs.sysml) own the six fixed
input sets and expected outcomes. [Native dependencies](../../../architecture/trace/software-intake-execution.sysml)
connect each execution action to a sequence message and each experiment to its use-case scenario.
The runner rejects missing or reordered message steps, unknown action steps and mismatched inputs or
outcomes. The observed sequence is built from the engine trace, not copied from the expected sequence.

The full model's interaction shorthand currently fails OpenSysML's `then message` validation. The
manifest therefore declares a bounded execution subset: the shared admission calculation, executable
action and experiment usages. These are the same authored files included in the full Pilot-validated
model; nothing is rewritten into a second behavior language. This is an executable refinement linked
to the interaction model, not a claim that the engine directly executes the existing message diagrams.

## Prepare the runtime

First prepare the existing [native build dependencies](02-connected-model.md#build-and-check), including
Java, the Pilot kernel/library and Graphviz. Add the OpenSysML CLI from the
[pinned release](https://github.com/Open-MBEE/OpenSysML/releases/tag/v0.12.1). Its Apache-2.0 license
permits this local use without a subscription. [1]

From **the upstream homelab checkout in Linux or WSL**, the following installs the Linux x64 runtime
under ignored `.tmp/tools/`; it does not change system settings:

```bash
python scripts/architecture/install_execution_runtime.py
```

The installer checks the versioned archive against the SHA-256 recorded in
[toolchain.json](../../../architecture/toolchain.json). Set `SYSML_RUNTIME` to the installed executable:

```bash
export SYSML_RUNTIME="$PWD/.tmp/tools/opensysml-0.12.1/sysml"
```

For **a Windows checkout using WSL**, run the following from the upstream checkout in PowerShell.
Replace `AlmaLinux-10` with the installed distribution name shown by `wsl --list --quiet`:

```powershell
python scripts/architecture/install_execution_runtime.py --platform linux-amd64
$env:SYSML_WSL = 'AlmaLinux-10'
$runtimePath = (Resolve-Path '.tmp/tools/opensysml-0.12.1/sysml').Path
$env:SYSML_RUNTIME = (wsl --distribution $env:SYSML_WSL --exec wslpath -a $runtimePath).Trim()
```

Keep the existing Windows Java/Pilot variables. Use WSL execution only where the host permits it;
do not disable application-control policy. The variables above apply to this PowerShell session.

## Run and inspect

From **the upstream homelab checkout**, with both toolchains configured:

```bash
python scripts/architecture/software_intake.py execute
python scripts/architecture/software_intake.py check
```

`execute` validates and regenerates the connected model, runs all six experiments with the pinned
native engine, and publishes [execution.json](../../../architecture/test/software-intake/execution.json)
only when every run matches its expected outcomes and sequence. The record includes UTC time, tool
version, source fingerprints, inputs, outputs, native engine records, executed actions and decisions.
The [execution SVG](../../../architecture/views/software-intake/execution.svg) shows each run using
the same participants and palette as the expected sequence. Its message labels retain both execution
and interaction identities. Supporting files and raw native output are under ignored
`.tmp/software-intake-execution/`.

Open the source-failure run: it must include the failed source attempt and retrieval error, followed by
stopping without verification. Compare the offline-cache run: it must skip source access but still
verify the content. This difference is a result of executed native branches. [2]

The runtime can also be supplied with `--runtime`; `--wsl` selects a WSL distribution. A missing runtime,
wrong version, native error, unfinished execution or trace mismatch fails the command. Previous recorded
evidence is retained when execution fails. Build/check mark old evidence stale when its source fingerprint
differs; they do not silently present it as a new execution.

## Change the experiment

Discuss a selected box/message and the intended change, then edit its owning SysML source through the
agent. Change environment inputs in `retrieval-runs.sysml`; change behavior in `retrieval-execution.sysml`.
Update the corresponding expected scenario, sequence and acceptance intent when the design changes.
Rebuild and execute to see the new route. Do not edit the generated trace to make an experiment pass.

The meaningful negative check changes the native admission branch to allow all requests in an isolated
copy. Native execution then reaches content for the denied experiment, and the comparison rejects it.
The reviewed evidence remains unchanged. Run the focused suite from the checkout with `PYTHONPATH=tests`:

```bash
python -B -m unittest -v test_tier_intake_execution
```

## Evidence boundaries

- This is one-request HTTP behavior execution, not network performance or packet simulation. There
  are no modeled durations, concurrent clients, queues, retries or cache population between runs.
- `eligibleFreshResponse` is an initial environment observation, not a calculated freshness policy.
  The cache-miss failure experiment has no eligible stale fallback. It does not establish every
  product's stale-if-error behavior or add a new deployed cache setting.
- `contentVerified` supplies the client check's outcome. The model does not calculate hashes, verify
  signatures or authenticate certificates. Actual package-policy tests remain separate evidence.
- HTTPS/CONNECT remains in the connected expected behavior but is outside this execution subset.
  Successful TLS, deployed network controls and independent custody retain their existing acceptance gaps.
- OpenSysML's action execution is a supported subset with self-assessed conformance. The exact model
  was tested here with the pinned version; this does not certify all SysML execution semantics. [3]

The [real Squid/APT comparison](06-implementation-comparison.md) separately checks these expectations
against actual package retrieval and verification. No live infrastructure is changed. Other architecture areas remain mapped. The
[verification record](verification.md) distinguishes these model runs from prior isolated product tests.

## References

1. [OpenSysML MDK 0.12.1 release and license](https://github.com/Open-MBEE/OpenSysML/tree/v0.12.1).
2. [Pinned CLI: action execution, trace output and recorded runs](https://github.com/Open-MBEE/OpenSysML/blob/v0.12.1/docs/reference/cli.md).
3. [Pinned runtime coverage and limits](https://github.com/Open-MBEE/OpenSysML/blob/v0.12.1/README.md).
