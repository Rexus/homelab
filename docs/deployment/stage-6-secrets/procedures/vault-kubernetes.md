# Vault on Kubernetes

Install the Tier 0 Vault service with three Raft voters, separate per-pod data and
audit claims, TLS, persistent plus stdout audit and scoped human OIDC. Initialization,
unseal and root-token custody belong to the authorized operators.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted cluster/identity/log intake, external certificate and
credential custody, sufficient independent storage failure domains, and the
[control-application inputs](control-applications.md). The shipped seal is Shamir;
other seals use the [explicit integration branch](../step-1c-seal-integration.md).

## Table of contents

- [Install the sealed service](#install-the-sealed-service)
- [Operator ceremony](#operator-ceremony)
- [Enable audit and human access](#enable-audit-and-human-access)
- [Accept recovery](#accept-recovery)
- [References](#references)

## Install the sealed service

Select `[vault]` and `control_applications_vault_phase: install`. Render and review
the [native installation](control-applications.md#render-and-apply), then apply only
after the independent custody and platform gates are recorded.

The official Helm chart installs Raft servers with one data and one audit PVC per
replica. TLS retry-join uses the internal pod addresses and verifies the selected
public server name against the mounted certificate/CA. Readiness continues to
reject sealed/uninitialized instances. Installation uses `wait: false` and checks
only that server processes run; this is not secret-service acceptance. [1][2]

No lifecycle hook initializes or unseals the servers. The active service and its
ingress may have no endpoint until an operator completes the ceremony. Preserve
the chart's `OnDelete` rolling-restart behavior; plan one-server-at-a-time upgrades
and re-unseal explicitly.

## Operator ceremony

1. Establish a verified administrative TLS connection to `vault-0`, through an
   approved private route or an authenticated port-forward. With a loopback route,
   set `VAULT_TLS_SERVER_NAME` to the selected certificate DNS name and configure
   `VAULT_CACERT`; do not disable verification.
2. Follow the native `vault operator init` ceremony with the approved share/quorum
   counts and recipient PGP keys. Store encrypted shares and initial root-token
   output under independent operator custody, outside Git, this controller's
   render directory, Kubernetes Secrets and Vault itself. [3]
3. Unseal `vault-0` with the authorized share quorum through the interactive CLI.
   Retry-join enrolls the other servers; unseal each with the same cluster shares.
   Never run initialization on each pod. [1][2]
4. Inspect Raft membership and TLS endpoints. Establish a short-lived scoped API
   administration credential for the configuration pass. Revoke/restrict the
   initial root token after independently tested recovery and admin access.

The role never receives unseal shares, recovery shares, recipient private keys,
or permission to run initialization/unseal. Do not put shares on command lines,
in Ansible inputs or shell history.

## Enable audit and human access

Select `control_applications_vault_phase: configure`. Supply the private API token,
existing `vault` client secret, trusted IdP CA PEM, and reviewed role/policy maps.
Use `control_applications_register_clients: true` when Tier 0 should converge the
client in the existing Keycloak realm; otherwise register it there independently.

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

Verify an allowed request and a denied request at intake. Exercise intake loss,
collector restart and replay, audit-volume pressure and certificate expiry before
setting `control_applications_vault_audit_forwarding_accepted: true`.

The stdout collector is asynchronous. It does not make remote delivery
synchronous with Vault API success. Size/monitor audit storage, retain records
under the approved policy and qualify rotation/reopen. No automatic deletion or
rotation of the security record is installed by this role.

## Accept recovery

Use `control_applications_vault_phase: accept` only after the following checks:

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
custodians in project administration. This role supplies the native snapshot/
restore procedure, not a scheduled off-cluster Vault snapshot transport. Raft
replication and the audit PVCs are not backup copies.

Set `control_applications_backup_restore_accepted: true` only after recording that
restore evidence. The accept pass validates health, audit configuration, policy
content, OIDC role bounds and voter count. It does not perform destructive failure
or restore testing on the live service.

Return to [Stage 6](../README.md#step-2-add-operational-tools).

## References

Guidance checked 2026-10-26.

1. [Vault Helm Raft installation](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/examples/ha-with-raft).
2. [Vault Raft with verified TLS](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/helm/examples/ha-tls).
3. [Vault operator initialization](https://developer.hashicorp.com/vault/docs/commands/operator/init).
4. [Vault OIDC authentication](https://developer.hashicorp.com/vault/docs/auth/jwt).
5. [Vault file audit backend and stdout](https://developer.hashicorp.com/vault/docs/audit/file).
6. [Vault Raft snapshots](https://developer.hashicorp.com/vault/docs/commands/operator/raft/snapshot).
