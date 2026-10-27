# Restore Vault Raft state

Restore the same Vault identity on an isolated clean target from an inspected native snapshot.
**Prerequisites:** [verified extraction](files.md), original unseal quorum or functioning original
auto-unseal mechanism, release-matched Vault server/CLI, original configuration and external plugin
binaries, verified TLS, and independent administrative access. A snapshot does not include external
plugin artifacts; recovery shares cannot replace an unavailable auto-unseal key/service. [1][2]

## Contents

- [Prepare a clean target](#prepare-a-clean-target)
- [Restore and unseal](#restore-and-unseal)
- [Validate before cutover](#validate-before-cutover)
- [References](#references)

## Prepare a clean target

Fence the original cluster and preserve its volumes/evidence. Build a replacement with new empty
Raft storage; never point this procedure at retained production claims. Remove production
`retry_join` targets and block both cluster traffic and outbound production secret-engine access.
Keep clients, DNS publication and ingress disabled: restored leases can otherwise revoke live
third-party credentials. Use only the authorized recovery workstation route. [1]

The existing [Vault configuration](../../../tier-0/ansible/roles/control_applications/templates/vault-values.yml.j2)
shows TLS, storage and audit requirements, not a restore installer. On Kubernetes, prepare a separate
isolated cluster/namespace and a single Vault replica with fresh claims and reviewed values. Do not
run ordinary Helm convergence against the failed cluster as a recovery shortcut.

Run on the recovery workstation, with `VAULT_ADDR` naming only that isolated instance:

```bash
set -euo pipefail
set -o noclobber
umask 077
: "${VAULT_ADDR:?Set the isolated HTTPS target}"
: "${VAULT_CACERT:?Set its verified CA file}"
: "${VAULT_TLS_SERVER_NAME:?Set its certificate DNS name}"
: "${RECOVERY_SNAPSHOT_FILE:?Set the extracted vault.snap}"
: "${EXPECTED_VAULT_SHA256:?From independent custody}"
: "${RECOVERY_INIT_FILE:?Set a NEW private absolute init receipt path}"
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

## Restore and unseal

Authenticate with the temporary target's new root token through a hidden prompt, then restore:

```bash
read -r -s -p 'Temporary isolated target root token: ' VAULT_TOKEN
export VAULT_TOKEN
printf '\n'
test "${RECOVERY_APPROVE_FORCE_RESTORE:-}" = yes
vault operator raft snapshot restore -force "$RECOVERY_SNAPSHOT_FILE"
unset VAULT_TOKEN
```

The force operation replaces only this freshly initialized target's Raft state; it is needed when
the target's temporary keys differ. After restoring, unseal using the **original** snapshot quorum.
For auto-unseal, preserve the original seal configuration and accessible original key; do not attempt
a seal migration implicitly. Keep the target isolated during all unseal/lease processing. [1][2]

## Validate before cutover

1. Observe server logs through completed post-unseal setup; command success alone only means the
   restore was accepted. Check `vault status`, expected Raft applied index and active state. [1]
2. With independently recovered, scoped operator access, verify expected secret paths/values without
   logging secrets, policies, auth methods, audit device and external plugin availability.
3. Rebuild additional peers on fresh storage using the native Raft join procedure. Verify membership,
   peer TLS, quorum, restart/unseal and protected audit forwarding before exposing clients.
4. Reconcile restored leases and external credentials with the incident timeline. Rotate compromised
   credentials deliberately; fence the old identity permanently before final endpoint/DNS cutover.
5. Recommission the narrow snapshot AppRole and timer, take a new independent backup, and record
   observed RPO/RTO, original snapshot hash and all acceptance results. Protect temporary init material
   under the custody policy; never include it in normal application automation.

## References

1. [Vault isolated snapshot restore, force semantics and completion](https://developer.hashicorp.com/vault/docs/sysadmin/snapshots/restore)
2. [Vault seal and recovery-key dependency](https://developer.hashicorp.com/vault/docs/concepts/seal)
3. [Vault Kubernetes snapshot recovery](https://support.hashicorp.com/hc/en-us/articles/10773573595923-How-to-restore-a-snapshot-to-a-Vault-cluster-running-on-Kubernetes)
