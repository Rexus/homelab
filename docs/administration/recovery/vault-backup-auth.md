# Authenticate scheduled Vault snapshots

Use a dedicated client certificate to mint a fresh short-lived snapshot-only token for every run.
**Prerequisites:** existing independent approved client CA, a `clientAuth` certificate/key dedicated
to the recovery host, verified Vault server TLS and an authorized Vault provisioning operator.
The certificate/profile issuance and renewal procedure belongs to that existing CA's custodian.
The reference OpenXPKI server-only profile is not a client certificate enrollment implementation.

## Contents

- [Configure the certificate role](#configure-the-certificate-role)
- [Rotate and verify](#rotate-and-verify)
- [AppRole alternative](#approle-alternative)
- [Break-glass local token](#break-glass-local-token)
- [References](#references)

## Configure the certificate role

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
   vault policy write control-raft-snapshot ansible/roles/control_backup/files/vault-snapshot.hcl
   vault auth enable -path=control-backup-cert cert
   ```

   Inspect `vault auth list` first; an existing mount is reviewed and reused, never disabled to force
   initialization. No provisioning/root token is copied to the backup host.
4. Pin the dedicated leaf certificate in its own role. Set the exact approved DNS SAN and CIDR;
   do not authorize a general CA without identity constraints. Native cert auth supports trusted
   certificate/CA entries; renewal of this pinned leaf requires an explicit role update. [1][2]

   ```bash
   set -euo pipefail
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

## Rotate and verify

Record certificate fingerprint, issuer, expiry, renewal owner, role pin and approved monthly/yearly
rotation interval. Keep CA credentials and key recovery independent of the target Vault/SSO cluster.
Monitor expiry externally; the job's default seven-day `openssl x509 -checkend` margin causes missed
health pings if rotation is overdue. An expired certificate never triggers a token/auth downgrade.

Provision the replacement key/certificate, update the dedicated Vault pin and host files during an
approved maintenance window, then run a verified backup. Retain a rollback plan until the new login
and independent copy succeed; remove/revoke the previous identity through the CA/Vault custody process.
Requalify after CA, endpoint/ingress, source-NAT, auth policy or certificate profile changes.

## AppRole alternative

Select `control_backup_vault_auth: approle` explicitly when the site operates SecretID rotation.
Use an existing reviewed `approle` mount and the same policy. Define the approved SecretID lifetime
and use limit with its owner; these are not hidden permanent credentials or a daily-rotation default:

```bash
: "${RECOVERY_CIDR:?Set the approved source CIDR}"
: "${BACKUP_SECRET_ID_TTL:?Set an explicitly maintained SecretID lifetime}"
: "${BACKUP_SECRET_ID_USES:?Set an explicitly maintained login use limit}"
vault write auth/approle/role/control-raft-snapshot \
  token_policies=control-raft-snapshot token_no_default_policy=true token_type=service \
  token_ttl=15m token_max_ttl=15m token_explicit_max_ttl=15m \
  bind_secret_id=true secret_id_ttl="$BACKUP_SECRET_ID_TTL" secret_id_num_uses="$BACKUP_SECRET_ID_USES" \
  token_bound_cidrs="$RECOVERY_CIDR" secret_id_bound_cidrs="$RECOVERY_CIDR"
```

Read the role ID with `vault read -field=role_id auth/approle/role/control-raft-snapshot/role-id` and
generate the SecretID with `vault write -f -field=secret_id auth/approle/role/control-raft-snapshot/secret-id`.
Deliver raw values as protected `control_backup_vault_role_id_file` and
`control_backup_vault_secret_id_file`; rotation/generation authority stays off the backup host.
Replace the host files and prove a new login before retiring the old SecretID accessor. Record expiry
and remaining-use monitoring; missed renewal must raise independent health failure. [3]

## Break-glass local token

`static-token-local` requires explicit acceptance and a protected local token file. It accepts only
the same snapshot-only nonperiodic service token, with remaining TTL and explicit maximum lifetime
at most one hour. It is for one-off manual recovery copies; the role stops/disables the timer in this
mode. The credential custodian supplies a fresh token for another attempt. No renewal is attempted.

## References

Sources checked 2026-10-26.

1. [Vault certificate method, client EKU and listener requirements](https://developer.hashicorp.com/vault/docs/auth/cert)
2. [Vault certificate role, CIDR and token policy parameters](https://developer.hashicorp.com/vault/api-docs/auth/cert)
3. [Vault AppRole role and SecretID lifecycle](https://developer.hashicorp.com/vault/api-docs/auth/approle)
