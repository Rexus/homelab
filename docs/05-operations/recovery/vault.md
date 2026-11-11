# Restore Vault Raft state

Restore the same Vault identity on an isolated clean target from an inspected native snapshot.
**Prerequisites:** [verified extraction](files.md), original unseal quorum or functioning original
auto-unseal mechanism, release-matched Vault server/CLI, original configuration and external plugin
binaries, verified TLS, and independent administrative access. A snapshot does not include external
plugin artifacts; recovery shares cannot replace an unavailable auto-unseal key/service. [1][2]

<a id="contents"></a>

## Operator tasks

- [How to prepare a clean Vault target?](#prepare-a-clean-target)
- [How to restore and unseal the original identity?](#restore-and-unseal)
- [How to verify Vault before endpoint cutover?](#validate-before-cutover)
- [References](#references)

<a id="prepare-a-clean-target"></a>

## How to prepare a clean Vault target?

1. Fence the old cluster and preserve its volumes/evidence.
2. Prepare a replacement with new empty Raft storage; never reuse retained production claims.
3. Remove production `retry_join` targets. Block old cluster routes and outbound production
   secret-engine access; keep clients, ingress and DNS publication disabled.
4. Permit only the recovery workstation. Restored leases can revoke external credentials
   if production integrations become reachable before reconciliation. [1]

The existing [Vault configuration](../../../tier-0/ansible/roles/control_applications/templates/vault-values.yml.j2)
shows TLS, storage and audit requirements, not a restore installer. On Kubernetes, prepare a separate
isolated cluster/namespace and a single Vault replica with fresh claims and reviewed values. Do not
run ordinary Helm convergence against the failed cluster as a recovery shortcut.

Run on the recovery workstation, with **`VAULT_ADDR`** naming only that isolated instance:

Run on **the independent isolated recovery workstation**.

```bash
set -euo pipefail
set -o noclobber
umask 077
read -r -p "Isolated Vault HTTPS target: " VAULT_ADDR
read -r -p "Verified Vault CA file: " VAULT_CACERT
read -r -p "Vault certificate DNS name: " VAULT_TLS_SERVER_NAME
export VAULT_ADDR VAULT_CACERT VAULT_TLS_SERVER_NAME
read -r -p "Extracted vault.snap path: " RECOVERY_SNAPSHOT_FILE
read -r -p "Independently recorded snapshot SHA-256: " EXPECTED_VAULT_SHA256
read -r -p "NEW private absolute init receipt path: " RECOVERY_INIT_FILE
read -r -p "Target isolation verified (yes): " RECOVERY_ISOLATED
test "${RECOVERY_ISOLATED:-}" = yes
test -z "${VAULT_SKIP_VERIFY:-}"
case "$VAULT_ADDR" in https://*) ;; *) exit 1 ;; esac
printf '%s  %s\n' "$EXPECTED_VAULT_SHA256" "$RECOVERY_SNAPSHOT_FILE" | sha256sum -c -
vault operator raft snapshot inspect "$RECOVERY_SNAPSHOT_FILE"
status=$(vault status -format=json) || test "$?" -eq 2
printf '%s' "$status" | python3 -c \
  'import json,sys; s=json.load(sys.stdin); assert not s["initialized"] and s["sealed"]'
vault operator init -format=json > "$RECOVERY_INIT_FILE"
```

The uninitialized-status check rejects an existing Vault identity, and `noclobber` rejects a reused
init receipt. Supply the site's approved init flags if using different shares or auto-unseal. Protect
the temporary root token and temporary key shares in this new receipt; they are restore-only material,
not backup-job credentials. Unseal the temporary target with its new shares using interactive
`vault operator unseal` prompts (or verify the original auto-unseal mechanism works).

<a id="restore-and-unseal"></a>

## How to restore and unseal the original identity?

Complete [clean-target preparation](#prepare-a-clean-target) first; retain its verified
snapshot path and isolated target context for these commands.

Authenticate with the temporary target's new root token through a hidden prompt, then restore:

Run on **the independent isolated recovery workstation**.

```bash
read -r -s -p 'Temporary isolated target root token: ' VAULT_TOKEN
export VAULT_TOKEN
printf '\n'
read -r -p "Approve force-restore on this fresh isolated target (yes): " RECOVERY_APPROVE_FORCE_RESTORE
test "${RECOVERY_APPROVE_FORCE_RESTORE:-}" = yes
vault operator raft snapshot restore -force "$RECOVERY_SNAPSHOT_FILE"
unset VAULT_TOKEN
```

The force operation replaces only this freshly initialized target's Raft state; it is needed when
the target's temporary keys differ. After restoring, unseal using the **original** snapshot quorum.
For auto-unseal, preserve the original seal configuration and accessible original key; do not attempt
a seal migration implicitly. Keep the target isolated during all unseal/lease processing. [1][2]

<a id="validate-before-cutover"></a>

## How to verify Vault before endpoint cutover?

1. Observe server logs through completed post-unseal setup; command success alone only means the
   restore was accepted. Check `vault status`, expected Raft applied index and active state. [1]
2. With independently recovered, scoped operator access, verify expected secret 06-paths/values without
   logging secrets, policies, auth methods, audit device and external plugin availability.
3. Rebuild additional peers on fresh storage using the native Raft join procedure. Verify membership,
   peer TLS, quorum, restart/unseal and protected audit forwarding before exposing clients.
4. Reconcile restored leases and external credentials with the incident timeline. Rotate compromised
   credentials deliberately; fence the old identity permanently before final endpoint/DNS cutover.
5. Recommission the selected narrow certificate/AppRole snapshot identity and timer, take a new independent backup, and record
   observed RPO/RTO, original snapshot hash and all acceptance results. Protect temporary init material
   under the custody policy; never include it in normal application automation.

**Stop/rollback:** on hash, identity, seal, applied-state or product-check failure, keep clients blocked
and preserve the failed target/logs. Retry only on another fresh isolated target. No in-place
rollback, seal migration or automatic product provisioning is supplied by this procedure.

## References

1. [Vault isolated snapshot restore, force semantics and completion](https://developer.hashicorp.com/vault/docs/sysadmin/snapshots/restore)
2. [Vault seal and recovery-key dependency](https://developer.hashicorp.com/vault/docs/concepts/seal)
3. [Vault Kubernetes snapshot recovery](https://support.hashicorp.com/hc/en-us/articles/10773573595923-How-to-restore-a-snapshot-to-a-Vault-cluster-running-on-Kubernetes)
