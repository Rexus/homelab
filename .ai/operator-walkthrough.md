# Operator walkthrough checklist

Reviewed 2026-10-16 from the perspective of a software engineer with newly installed
servers and UniFi switches. This is the maintainer's working checklist, not generated
project documentation or a claim of production readiness.

**Scope:** clone, generation, foundation, all six stages and adjacent options,
ordinary users, applications, maintenance, expansion and total-loss recovery.
**Evidence boundary:** source/generator review and offline tests; no live gateway,
Proxmox, HSM, service deployment, failover or disaster restore was performed.

## Corrected reading and execution gaps

- [x] Make the front door distinguish runnable workflows from integration starters.
- [x] Keep foundation prerequisites outside numbered capability stages; logging remains Stage 1.
- [x] Prevent the Proxmox preparation guide from skipping logging and jumping to identity/clusters.
- [x] Add gateway/controller adoption and VLAN/port preparation before the UniFi policy matrix.
- [x] Distinguish ordinary client access ports from server trunks and supported multi-switch aggregation.
- [x] Put the existing Linux-provider TLS exception in the API setup gate, not only the HA guide.
- [x] Explain that `--env` does not allocate unique VMIDs, addresses, VIPs or security boundaries.
- [x] Keep directory deployment in the trust stage's existing context/state instead of silently switching to test.
- [x] Add initialization and plan/review/deploy commands to cache, edge and Vault paths.
- [x] Initialize test inputs before VM source-control, runner and image-builder commands.
- [x] Separate plan and apply blocks; retain a human input/allocation review between them.
- [x] Add Vault CLI endpoint/trust selection and authentication before audit configuration.
- [x] Remove repeated identity-authentication and Vault-shape explanations in favor of their authoritative homes.
- [x] Align generated setup ownership and template references with logging and unnumbered foundation.
- [x] Use an ignored Python virtual environment for the generator dependency instructions.

## Blocking work before claiming an end-to-end installation

- [ ] **P1: Secure provider defaults.** Linux roots still hard-code `insecure = true`.
  Implement and test trusted-TLS defaults across all consuming roots; document deliberate
  bootstrap trust and upgrades for existing projects. The current [TLS gate](../docs/deployment/foundation/procedures/api-access.md#tls-gate)
  makes the exception visible but does not change runtime behavior.
- [ ] **P1: Logging integration.** Implement the selected receiver, durable queue/commit
  path, portable evidence, source identities, protected retention and independent copies.
  The `syslog` root currently supplies only VMs/disks and baseline. Complete
  [Stage 1 acceptance](../docs/deployment/stage-1-logging/README.md#step-3-protect-and-verify-retained-evidence)
  with real fault and restore evidence.
- [ ] **P1: Initial trust.** Select one supported CA implementation and write/test the
  actual root/intermediate procedure and recovery. Decide FreeIPA CA relationship explicitly;
  a CA VM or software/USB/network provider selection does not install issuance.
- [ ] **P1: Cluster API endpoint.** Supply a tested private endpoint recipe or a clearly
  verified existing prerequisite before cluster bootstrap. It must not require the public
  Tier 2 edge or the cluster it serves. Include DHCP/MAC reservations and bootstrap DNS/time.
- [ ] **P1: Cluster services.** Add release-pinned delivery, decryption, persistence,
  certificate/ingress and database manifests with health/dependency gates. Empty Kustomize
  directories do not implement the [cluster foundation](../docs/deployment/stage-3-identity-runtime/procedures/kubernetes.md#cluster-foundation).
- [ ] **P1: Control applications.** Implement and verify the selected IdP, inventory
  application, cluster interface and cluster-based secret service, including scoped roles,
  data dependencies, audit forwarding and backups. The Vault VM alternative is a different runtime.
- [ ] **P1: Monitoring and analytics.** Supply the selected product recipes, critical
  external alerts and read-only application views. Test missing signals, blocked deletion,
  forged ownership and Tier 1 outages; reference diagrams are not configured controls.
- [ ] **P1: Protected execution.** Implement the approved Tier 0 runner/controller path
  before delegated provisioning. General runner registration and source-control branch
  protection must not be treated as that authorization boundary.
- [ ] **P1: Destructive-change protection.** Rehearse allocation collisions, state
  ownership, complete-map overlays and accidentally removed definitions. Consider a focused
  preflight for concurrent environments; current naming/state separation is not an allocation service.
- [ ] **P1: Clean-room recovery.** Write and execute product-specific restores for
  directory/CA data, original cluster secrets/state plus etcd, persistent application data,
  secret-service data/keys and protected logs. Restore is not another fresh-cluster bootstrap.
- [ ] **P1: Exposure acceptance.** Verify gateway, host and workload enforcement, actual
  TLS/listeners, IPv4/IPv6, VPN and same-subnet isolation before opening any service externally.
  A firewall design or Ansible baseline is not an attack-resistance certification.

## Paths reviewed

"Reviewed" below means the entry, owner, branch/return and automation boundary were
inspected. Every selected path still needs its own live acceptance evidence.

| Path | Entry | Review outcome / remaining proof |
| --- | --- | --- |
| Foundation | [Preparation](../docs/deployment/foundation/README.md) | Network, access, templates and recovery precede capability deployment; live commissioning required |
| Logging | [Stage 1](../docs/deployment/stage-1-logging/README.md) | Runnable host foundation; receiver/retention integration blocks full service acceptance |
| Trust | [Stage 2](../docs/deployment/stage-2-trust/README.md) | Software and hardware choices explicit; actual CA procedure remains integration |
| Identity/runtime | [Stage 3](../docs/deployment/stage-3-identity-runtime/README.md) | Directory recipe and new-cluster lifecycle supplied; endpoint/add-ons still required |
| Control services | [Stage 4](../docs/deployment/stage-4-control-services/README.md) | Cluster services are starters; independent monitoring has its own path |
| Delivery | [Stage 5](../docs/deployment/stage-5-delivery/README.md) | VM alternatives supplied; controller, registry and protected execution require selected integrations |
| Workloads | [Stage 6](../docs/deployment/stage-6-workloads/README.md) | VM/cluster resources supplied; application manifests, publication and policies remain project work |
| Proxmox HA | [Foundation 1b](../docs/deployment/foundation/step-1b-cluster-ha.md) | Quorum/storage/fencing separate from VM creation; physical failure tests outstanding |
| Guest SDN | [Foundation 1c](../docs/deployment/foundation/step-1c-sdn.md) | Manual VNet setup; verify every eligible node and one tagging owner |
| Outbound cache | [Foundation 3b](../docs/deployment/foundation/step-3b-outbound-cache.md) | Supplied Squid/VIP recipe; independent bootstrap egress and declared transport limits |
| Redundant logging | [Logging 3b](../docs/deployment/stage-1-logging/step-3b-redundant-intake.md) | Added hosts do not establish replicated commitment or retention |
| Replicated USB HSM | [Trust 1b](../docs/deployment/stage-2-trust/step-1b-usb-hsm.md) | Host pool and optional snippet only; provider/application/key readiness and endpoint require implementation |
| Network HSM | [Trust 1c](../docs/deployment/stage-2-trust/step-1c-network-hsm.md) | Vendor commissioning/client/HA procedure required |
| Single USB device | [Trust 1d](../docs/deployment/stage-2-trust/step-1d-single-usb.md) | Custody/backup procedure required; availability is not inferred from a token |
| Manual cluster | [Runtime 2b](../docs/deployment/stage-3-identity-runtime/step-2b-manual-cluster.md) | Valid alternative lifecycle owner; adoption/restore distinct from fresh bootstrap |
| Vault VM | [Control 2b](../docs/deployment/stage-4-control-services/step-2b-vault-vm.md) | Supplied host/service recipe; initialization, authorization, audit forwarding and restore remain explicit |
| Seal choice | [Control 2c](../docs/deployment/stage-4-control-services/step-2c-seal-integration.md) | Shamir/Transit/PKCS#11 capability and edition checks; no automatic migration |
| Telemetry VMs | [Control 2d](../docs/deployment/stage-4-control-services/step-2d-telemetry-vm.md) | Early Tier 1 runtime alternative; not a substitute for Tier 0 monitoring |
| Operator hardware authentication | [Control 3b](../docs/deployment/stage-4-control-services/step-3b-hardware-authentication.md) | Enrollment and lost-token recovery are manual; retain break-glass access |
| Source-control VM | [Delivery 1b](../docs/deployment/stage-5-delivery/step-1b-source-control-vm.md) | Supplied container recipe; pin image, prepare TLS and verify product backup/restore |
| General build runner | [Delivery 1c](../docs/deployment/stage-5-delivery/step-1c-podman-runner.md) | Supplied host recipe; registration/credentials/trust required; no Tier 0 authority |
| Image-based Linux | [Delivery 1d](../docs/deployment/stage-5-delivery/step-1d-image-based-linux.md) | Conversion is distro/product-specific; retain source image and test rollback |

## User and operating paths still needed

- [ ] **P2: First useful private app.** Provide one small, complete service example from
  owner/allocation through deployment, authentication, TLS, scoped logs and restoration;
  avoid requiring every optional platform service merely to validate an application.
- [ ] **P2: Household access.** Add a short outcome path for family, guest and IoT devices:
  client networks, Wi-Fi/ports, permitted apps, optional discovery/printers and denied Control
  access. Include local Internet/DHCP/DNS behavior during platform outages.
- [ ] **P2: Small-team access.** Add onboarding/offboarding and a tested role matrix for
  administrator, developer, employee and guest. Verify repository/app/log scopes and session,
  token and device removal; a shared identity source does not implement application authorization.
- [ ] **P2: Remote entry and publication.** Document one chosen VPN/admin-entry path and
  private-versus-public app publication, including DNS/NAT, certificate renewal and IPv6 checks.
- [ ] **P2: Upgrade and hardware replacement.** Supply a routine calendar/runbook with
  release compatibility, serial health gates, rollback, node/storage retirement and recovery
  on replacement hardware. Existing worker-pool guidance is not a rolling-upgrade controller.
- [ ] **P2: State and local inputs.** Test OS file permissions, encrypted off-host copies,
  one writer per state and retained ignored inputs. Git history alone excludes live inventory,
  secrets and state, so cloning the private repositories alone is not a disaster recovery.
- [ ] **P2: Secret scanning.** Select a project enforcement mechanism for staged content,
  CI output and artifacts; `.gitignore` does not prevent forced additions or tracked secrets.
- [ ] **P2: Cache hardening variants.** Implement client authentication or TLS/mTLS listener
  only for a selected requirement, with support/acceptance documented; keep the HTTP proxy
  reference's limits visible and avoid implying TLS interception is required.
- [ ] **P3: Reading density.** Split historic generated-repository upgrade detail away from
  first-use contracts; separate advanced direct-mesh storage and large cache-sizing material
  from the main path. Preserve old anchors and generated-project edits when moving content.

## Live acceptance record

Store sensitive evidence in the private project's runbook, not this public checklist.

- [ ] Cold-start gateway/controller, switches and the first server with only the offline kit.
- [ ] Boot a disposable clone; verify SSH, DNS, time, network denials and backup restore.
- [ ] Run test and production concurrently with non-overlapping allocations and separate state.
- [ ] Repeat plans after Proxmox migration and after an approved host-failure exercise.
- [ ] Disable Tier 1/2 and normal SSO; verify Tier 0 logging, administration and critical alerts.
- [ ] Verify app-owner reads and rejected cross-app reads, deletion and archive/backup administration.
- [ ] Restore one service and its data onto replacement hardware inside recorded RPO/RTO.
- [ ] Read protected logs with infrastructure offline using only a preserved volume and reader/key kit.
- [ ] Perform a clean-room total-loss recovery from independent copies; record every missing input.
- [ ] Recheck user-visible functions, credentials, audit continuity and failure alarms after recovery.

## Repeat cadence

Latest offline result: 90 regression tests passed; 61 Mermaid diagrams rendered,
with the new commissioning diagram visually inspected. No live acceptance box above
is satisfied by those results.

From an upstream checkout on Linux/WSL with the documented test tools/collections:

```bash
python3 -B -m unittest discover -s tests -p 'test_tier*.py' -v
```

Review skipped tests explicitly. For permission-sensitive WSL tests, use a checkout
on the Linux filesystem. Render changed diagrams and inspect their labels/flow in
addition to checking Markdown links and command wiring.

Repeat this walkthrough after meaningful documentation, topology, generator, inventory
or execution changes and before a release/operational handover. Reopen checks when their
contracts change. Offline tests validate the repository; only recorded live exercises
validate the selected installation. No scheduled automation is configured by this checklist.
