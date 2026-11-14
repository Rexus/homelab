# Kubernetes Vault ceremony and acceptance contract

<a id="vault-on-kubernetes"></a>
<a id="table-of-contents"></a>
<a id="step-1-install-the-sealed-service"></a>
<a id="1-select-vault-and-the-target-cluster"></a>
<a id="2-prepare-tls-and-bootstrap-secrets"></a>
<a id="3-render-inspect-and-install-the-sealed-service"></a>
<a id="step-2-operator-ceremony"></a>
<a id="4-verify-the-administrative-tls-path"></a>
<a id="5-initialize-once-under-custodian-control"></a>
<a id="6-unseal-the-three-servers"></a>
<a id="7-check-membership-and-prepare-configuration-access"></a>
<a id="step-3-enable-audit-and-human-access"></a>
<a id="8-supply-the-scoped-configuration-inputs"></a>
<a id="9-configure-audit-and-oidc"></a>
<a id="10-verify-audit-delivery-before-accepting-it"></a>
<a id="step-4-accept-recovery"></a>
<a id="11-test-backup-restore-and-failure-behavior"></a>
<a id="12-run-the-acceptance-pass"></a>

The first-install edit/render/apply sequence is [Stage 6, actions 2-10](../README.md#step-2-reuse-the-control-application-inputs).
This procedure owns the protected initialization/unseal handoff at **action 6**. It does not install
another service or repeat the sealed Helm installation. The VM alternative retains its own ceremony.

**Working repository:** `<prefix>-tier-0` retains installation and audit/SSO inputs.
**Working location:** authorized operator workstation with accepted private TLS and recovery custody.
**Prerequisites:** the already installed sealed service, verified cluster/identity/logging, independently
issued TLS and selected Shamir or separately qualified seal. Never run initialization against restored state.

<a id="install-the-sealed-service"></a>

## Before the ceremony

Confirm the [sealed installation](../README.md#step-5-install-the-reviewed-sealed-service) has completed.
The official chart supplies three Raft processes with separate data/audit claims and verified TLS retry-join.
Normal readiness rejects sealed/uninitialized members; the initial installer checks only running processes.
Its active ingress may have no endpoint yet. Preserve the chart's `OnDelete` behavior for health-gated
one-member maintenance; no lifecycle hook initializes or unseals members. [1][2]

<a id="operator-ceremony"></a>

## Authorized operator ceremony

### 1. Verify the administrative TLS path

On **the authorized operator workstation**, establish verified TLS to `vault-0` through an approved
private route or authenticated port-forward. With a loopback route,
set `VAULT_TLS_SERVER_NAME` to the selected certificate DNS name and configure
`VAULT_CACERT`; do not disable verification.

### 2. Initialize once under custodian control

On **the authorized operator workstation**, follow the native `vault operator init` ceremony with the
approved share/quorum counts and recipient PGP keys. Store encrypted shares and initial root-token
output under independent operator custody, outside Git, this controller's
render directory, Kubernetes Secrets and Vault itself. [3]

### 3. Unseal the three servers

The following share ceremony applies to the supplied Shamir realization. If a project-owned
[seal integration](../step-1c-seal-integration.md) replaced it, use that qualified provider's startup
and recovery ceremony instead; its recovery shares are not Shamir unseal shares. [3]

Unseal `vault-0` with the authorized share quorum through the interactive CLI.
Retry-join enrolls the other servers; unseal each with the same cluster shares.
Never run initialization on each pod. [1][2]

### 4. Check membership and prepare configuration access

Inspect Raft membership and TLS endpoints. Establish a short-lived scoped API
administration credential for the configuration pass. Revoke/restrict the
initial root token after independently tested recovery and admin access.

The role never receives unseal shares, recovery shares, recipient private keys,
or permission to run initialization/unseal. Do not put shares on command lines,
in Ansible inputs or shell history.

After membership and protected access are verified, continue at
[Stage 6, action 7](../README.md#step-7-set-and-render-scoped-auditsso-configuration).

<a id="enable-audit-and-human-access"></a>

## Audit and access contract

| Setting | Result |
| --- | --- |
| Audit `file/` | Native audit device writes `/vault/audit/audit.json` with mode `0600`; incompatible existing configuration fails |
| Audit `stdout/` | Second native file device uses `file_path: stdout`; Shared's pod-log adapter captures this stream |
| Human backend `oidc/` | Existing IdP discovery URL; no default role |
| Named roles | Stable `sub`, required group claims, exact audiences and redirects, bounded token lifetimes and explicit policies |
| Policy map | Native ACL documents supplied by the operator; no generated broad admin policy or engine mount |
| Workload identity | Separate responsibility; these human OIDC roles do not enroll CI or workloads |

Configuration enables both audit devices before policy/SSO writes. The existing audit
and auth mounts are read before creation; ACL policies are compared before updates.
The explicit configure pass writes OIDC credentials/roles because Vault does not
return the confidential client secret. The accept pass reads and verifies them. [4]

The native file audit backend supports `stdout` as a destination. [5] Shared
`cluster_security_logging` collects that container stream and sends it to protected
Tier 0 intake over mTLS. The persistent audit PVC is local custody; it does not
reach intake through the pod collector. There is no PVC-reading sidecar in Vault.

<a id="accept-recovery"></a>

## Recovery acceptance contract

| Check | Required evidence |
| --- | --- |
| Health | Initialized and unsealed active HTTPS endpoint; all intended voters present |
| Human access | Allowed/denied user, group removal, expiry, sign-out and IdP outage tests |
| Audit | Protected intake receives the requests and configuration events with approved source identity |
| Snapshot | Authorized `vault operator raft snapshot save` into protected external custody; snapshots contain sensitive encrypted state |
| Restore | Separate isolated Vault restored with `vault operator raft snapshot restore`, original unseal custody and a verified client path [6] |
| Failure | One-server loss and recovery, storage failure assumptions and seal/unseal behavior meet the selected contract |
| Independence | Recovery credentials, shares, snapshots and certificates remain usable without Keycloak, this Vault or Tier 1 delivery |

Record the snapshot cadence, destination, encryption, retention and authorized
custodians in project administration. Before acceptance, commission the separate
[control recovery-copy recipe](../../../05-operations/06-resilience/backups/control-applications.md#configure-and-schedule)
on an independent `control_recovery` host. It supplies scheduled native snapshots and encrypted restic copies;
the application installer itself does not install that timer. Qualify snapshot authentication and the
first completed backup, then use the [isolated restore procedure](../../../05-operations/06-resilience/recovery/vault.md).
Raft replication and audit PVCs are not backup copies.

Set `control_applications_backup_restore_accepted: true` only after recording that
restore evidence. The accept pass validates health, audit configuration, policy
content, OIDC role bounds and voter count. It does not perform destructive failure
or restore testing on the live service.

The stage owns the final [accept pass at action 10](../README.md#step-10-accept-the-selected-vault-service).
After acceptance continue at its optional signing decision, then the prepared monitoring/tools path.

## References

Guidance checked 2026-10-26.

1. [Vault Helm Raft installation](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/examples/ha-with-raft).
2. [Vault Raft with verified TLS](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/examples/ha-tls).
3. [Vault operator initialization](https://developer.hashicorp.com/vault/docs/commands/operator/init).
4. [Vault OIDC authentication](https://developer.hashicorp.com/vault/docs/auth/jwt).
5. [Vault file audit backend and stdout](https://developer.hashicorp.com/vault/docs/audit/file).
6. [Vault Raft snapshots](https://developer.hashicorp.com/vault/docs/commands/operator/raft#snapshot).
