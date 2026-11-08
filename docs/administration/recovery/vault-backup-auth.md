# Authenticate scheduled Vault snapshots

Use a dedicated client certificate to mint a fresh short-lived snapshot-only token for every run.
**Prerequisites:** existing independent approved client CA, a `clientAuth` certificate/key dedicated
to the recovery host, verified Vault server TLS and an authorized Vault provisioning operator.
The certificate/profile issuance and renewal procedure belongs to that existing CA's custodian.
The reference OpenXPKI server-only profile is not a client certificate enrollment implementation.

<a id="contents"></a>

## Operator tasks

- [How to authorize certificate-based snapshots?](#configure-the-certificate-role)
- [How to rotate and verify the client identity?](#rotate-and-verify)
- [How to use an explicitly maintained AppRole instead?](#approle-alternative)
- [How to take a one-off break-glass copy?](#break-glass-local-token)
- [References](#references)

<a id="configure-the-certificate-role"></a>

## How to authorize certificate-based snapshots?

**Run on:** the authorized Vault administration workstation, from generated Tier 0 for
repository policy files. Credential files stay outside Git; the backup host receives no
provisioning/root token.

1. Provide a private route that preserves TLS client authentication all the way to Vault: a direct
   private Vault listener or an independently qualified TCP TLS-passthrough endpoint. The normal
   Traefik HTTP termination/re-encryption path does not carry the backup client's TLS certificate.
   Vault must have TLS enabled and client-certificate handling enabled on that listener. Record the
   certificate server name, actual source CIDR as seen by Vault, and firewall allowance. [1]
2. On the independent administration workstation, verify the client certificate's issuer, public-key
   match, clientAuth EKU and validity using the approved client CA. Use a distinct key/identity from
   Vault's server certificate, application ingress, general operators and backup repository access.
3. With a separately authorized provisioning credential and verified `VAULT_ADDR`, `VAULT_CACERT`
   and `VAULT_TLS_SERVER_NAME`, create the policy and enable a dedicated cert mount **once**:

   ```bash
   # Run from <prefix>-tier-0/ on the authorized Vault administration workstation.
   vault policy write control-raft-snapshot ansible/roles/control_backup/files/vault-snapshot.hcl
   vault auth enable -path=control-backup-cert cert
   ```

   Inspect `vault auth list` first; an existing mount is reviewed and reused, never disabled to force
   initialization. No provisioning/root token is copied to the backup host.
4. Pin the dedicated leaf certificate in its own role. Set the exact approved DNS SAN and CIDR;
   do not authorize a general CA without identity constraints. Native cert auth supports trusted
   certificate/CA entries; renewal of this pinned leaf requires an explicit role update. [1][2]

   ```bash
   # Run from <prefix>-tier-0/ on the authorized Vault administration workstation.
   set -euo pipefail
   read -r -e -p "Approved client certificate PEM path: " BACKUP_CLIENT_CERT
   read -r -p "Exact approved client DNS SAN: " BACKUP_CLIENT_DNS
   read -r -p "Approved recovery-host source CIDR: " RECOVERY_CIDR
   : "${BACKUP_CLIENT_CERT:?Set the approved client leaf certificate PEM}"
   : "${BACKUP_CLIENT_DNS:?Set its exact approved DNS SAN}"
   : "${RECOVERY_CIDR:?Set the actual recovery host source CIDR}"
   vault write auth/control-backup-cert/certs/control-raft-snapshot \
     certificate=@"$BACKUP_CLIENT_CERT" allowed_dns_sans="$BACKUP_CLIENT_DNS" \
     token_policies=control-raft-snapshot token_no_default_policy=true token_type=service \
     token_ttl=15m token_max_ttl=15m token_explicit_max_ttl=15m \
     token_bound_cidrs="$RECOVERY_CIDR"
   ```

5. In the backup vars, set `control_backup_vault_auth: cert`, controller-side
   `control_backup_vault_client_cert_file` (leaf plus required intermediates),
   `control_backup_vault_client_key_file`, `control_backup_vault_bound_cidrs` and
   `control_backup_vault_client_tls_accepted: true` after checking the actual route.
   Keep the dedicated auth mount/role defaults unless the commissioned names differ.

The job sets `VAULT_CLIENT_CERT`/`VAULT_CLIENT_KEY`, then uses native
`vault write auth/control-backup-cert/login name=control-raft-snapshot` without storing a login token.
It validates self-lookup for the exact policy, short lifetime and CIDR binding before saving a snapshot,
then revokes the minted token. Client key, repository password and all credential files remain root-only.
Inherited identity/group policies must not broaden this backup identity.

<a id="rotate-and-verify"></a>

## How to rotate and verify the client identity?

1. Record fingerprint, issuer, expiry, CA renewal owner, role pin and approved rotation interval.
   Keep issuance/recovery independent of Vault/SSO. Monitor before the default seven-day expiry margin.
2. Have the CA custodian issue the replacement client identity. On the administration workstation:

   ```bash
   # Run from <prefix>-tier-0/ on the authorized Vault administration workstation.
   read -r -p "Approved replacement client certificate PEM: " BACKUP_CLIENT_CERT
   openssl x509 -in "$BACKUP_CLIENT_CERT" -noout -sha256 -fingerprint -dates
   openssl x509 -in "$BACKUP_CLIENT_CERT" -noout -checkend 604800
   ```

   Independently verify issuer, clientAuth EKU, key match and exact allowed SAN/CIDR.
3. Update the pinned certificate role using the task above. Edit **Tier 0
   `ansible/group_vars/control_backup.yml`** with the replacement controller-side cert/key paths.
4. Reapply [backup configuration](../backups/control-applications.md#configure-and-schedule),
   then require a new inspected backup, independent restic copy and external health ping.
5. Only after acceptance, retire/revoke the old identity through its CA/Vault custodians.
   Preserve the approved old pin/files for rollback until then.

**Stop/rollback:** if new login or copying fails, restore the approved old role pin/file paths,
reapply and prove a successful backup. Never broaden policy or downgrade authentication to
bypass expiry. Requalify after CA, ingress, NAT, policy or certificate-profile changes.

<a id="approle-alternative"></a>

## How to use an explicitly maintained AppRole instead?

Select `control_backup_vault_auth: approle` explicitly when the site operates SecretID rotation.
Use an existing reviewed `approle` mount and the same policy. Define the approved SecretID lifetime
and use limit with its owner; these are not hidden permanent credentials or a daily-rotation default:

```bash
# Run from <prefix>-tier-0/ on the authorized Vault administration workstation.
read -r -p "Approved recovery-host source CIDR: " RECOVERY_CIDR
read -r -p "Approved SecretID lifetime: " BACKUP_SECRET_ID_TTL
read -r -p "Approved SecretID login-use limit: " BACKUP_SECRET_ID_USES
: "${RECOVERY_CIDR:?Set the approved source CIDR}"
: "${BACKUP_SECRET_ID_TTL:?Set an explicitly maintained SecretID lifetime}"
: "${BACKUP_SECRET_ID_USES:?Set an explicitly maintained login use limit}"
vault write auth/approle/role/control-raft-snapshot \
  token_policies=control-raft-snapshot token_no_default_policy=true token_type=service \
  token_ttl=15m token_max_ttl=15m token_explicit_max_ttl=15m \
  bind_secret_id=true secret_id_ttl="$BACKUP_SECRET_ID_TTL" secret_id_num_uses="$BACKUP_SECRET_ID_USES" \
  token_bound_cidrs="$RECOVERY_CIDR" secret_id_bound_cidrs="$RECOVERY_CIDR"
```

Capture the values directly into a **new private directory outside Git**, rather than printing them:

```bash
# Run from <prefix>-tier-0/ on the authorized Vault administration workstation.
umask 077
read -r -e -p "New absolute credential directory outside Git: " AUTH_DIRECTORY
mkdir -m 0700 "$AUTH_DIRECTORY" &&
vault read -field=role_id auth/approle/role/control-raft-snapshot/role-id > "$AUTH_DIRECTORY/role-id" &&
vault write -f -field=secret_id auth/approle/role/control-raft-snapshot/secret-id > "$AUTH_DIRECTORY/secret-id"
```

Stop on failure; do not reuse partial files. Set `control_backup_vault_role_id_file` and
`control_backup_vault_secret_id_file` to these controller-side paths, then reapply the
[backup recipe](../backups/control-applications.md#configure-and-schedule).
Rotation/generation authority stays off the backup host. Retire the previous SecretID only
after the new identity completes an inspected independent backup.
Replace the host files and prove a new login before retiring the old SecretID accessor. Record expiry
and remaining-use monitoring; missed renewal must raise independent health failure. [3]

<a id="break-glass-local-token"></a>

## How to take a one-off break-glass copy?

1. In **Tier 0 `ansible/group_vars/control_backup.yml`**, explicitly set
   `control_backup_vault_auth: static-token-local`, the protected
   `control_backup_vault_static_token_file` path and
   `control_backup_vault_static_token_local_accepted: true`.
2. Apply [backup configuration](../backups/control-applications.md#configure-and-schedule).
   The first run takes the copy; inspect its recorded result.
3. Confirm `control-backup.timer` is disabled/stopped. Return to certificate auth or
   maintained AppRole and reapply before scheduled operation.

This path accepts only
the same snapshot-only nonperiodic service token, with remaining TTL and explicit maximum lifetime
at most one hour. It is for one-off manual recovery copies; the role stops/disables the timer in this
mode. The credential custodian supplies a fresh token for another attempt. No renewal is attempted.

## References

Sources checked 2026-10-26.

1. [Vault certificate method, client EKU and listener requirements](https://developer.hashicorp.com/vault/docs/auth/cert)
2. [Vault certificate role, CIDR and token policy parameters](https://developer.hashicorp.com/vault/api-docs/auth/cert)
3. [Vault AppRole role and SecretID lifecycle](https://developer.hashicorp.com/vault/api-docs/auth/approle)
