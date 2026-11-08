# Deploy a fresh software-backed PKI

Build an offline root and an OpenXPKI infrastructure issuer in Stage 3.
Stage 5 adds the sibling FreeIPA CA using that root; it is not installed by this procedure.
Public websites use [Let's Encrypt at the edge](../../stage-10-lab-environments/public-https.md),
not this private root. Root keys never enter a connected hypervisor.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted logging, independent DNS/time/SSH, encrypted persistent
CA storage and an isolated rehearsal environment. Run tier commands from the
owning generated repository. Existing authorities need migration, not this procedure.

## Contents

- [Step 1: Approve policy and custody](#decisions-and-recovery-kit)
- [Step 2: Build the private policy bundle](#build-the-private-policy-bundle)
- [Step 3: Install and prepare the issuing key](#install-and-prepare-the-issuing-key)
- [Step 4: Sign and activate](#sign-and-activate)
- [Step 5: Accept the issuer and continue](#accept-the-issuer-and-continue)
- [References](#references)

<a id="decisions-and-recovery-kit"></a>

## Step 1: Approve policy and custody

Approve names, trust scope and [algorithms](../../../architecture/cryptography/algorithm-selection.md)
before generating keys. The supplied policy has one TLS-server leaf profile,
client-held keys, explicit DNS suffixes, a 30-day default lifetime and a separate
requester/approver. It has no internal ACME, OCSP, client-auth or code-signing endpoint.
Manual renewal uses a new CSR through the same approval workflow.

| Material | Custody |
| --- | --- |
| Root instance, encrypted root key and unlock secret | Offline, separately authorized copies |
| Signer passphrase and DataVault master secret | Independently backed-up recovery kit |
| Database/session credentials and session secret | Stable protected controller inputs |
| Configuration archive and local CLI key | Secret-bearing artifacts; encrypt backups, never commit |
| CA certificates and fingerprints | Public records, independently verified |
| Recovery recipient private key | Offline, separate from the issuer and backup destination |

Software encryption does not prevent a compromised running CA host from signing.
Restrict host administration and qualify the
[hardware migration path](../../../administration/cryptography/hardware-migration.md).

<a id="build-the-private-policy-bundle"></a>

## Step 2: Build the private policy bundle

1. On the Linux Tier 0 controller, create the private policy input outside Git:

   ```bash
   read -r -e -p 'Absolute private issuer policy file path: ' ISSUER_POLICY_FILE
   cp -n ansible/group_vars/issuer-policy.yml.example "$ISSUER_POLICY_FILE"
   ```

   Its parent directory must already be protected. Edit that file:

   | Field | Set |
   | --- | --- |
   | `openxpki_bundle_directory` | New absolute protected build directory; retain each completed immutable bundle |
   | `openxpki_bundle_portal_fqdn` | Actual `ca-1` portal DNS name |
   | `openxpki_bundle_publication_url` | Reachable CA public-object URL ending in `/download/` |
   | `openxpki_bundle_dns_suffixes` | Approved internal certificate scope, no example suffixes |
   | `openxpki_bundle_users` | Separate named requester/approver accounts and their independent Argon2id hashes |

2. Generate Argon2id password hashes with the native `argon2` CLI on the trusted
   controller (install the OS's `argon2` package first), independently for each
   account. The password travels on stdin, not the process command line: [2]

   ```bash
   read -rsp 'New account password: ' account_password; echo
   printf '%s' "$account_password" | argon2 "$(openssl rand -hex 16)" -id -e -t 3 -m 16 -p 4
   unset account_password
   ```

   Record the encoded hash in the private input and keep the password separately.
   These costs use 64 MiB and three passes; measure login load on the actual issuer.
   The product's native Argon2 hash facility is an alternative once installed.

3. Prepare independent secrets in a private shell:

   ```bash
   read -rsp 'Issuer key passphrase (32+ characters): ' OPENXPKI_SIGNER_PASSWORD; echo
   export OPENXPKI_SIGNER_PASSWORD
   export OPENXPKI_DATAVAULT_SECRET="$(openssl rand -hex 32)"
   ```

   Back up these exact values securely **before** building. The signer passphrase is
   also required for key preparation. DataVault loss cannot be repaired by generating
   another random value. [1]

4. Build from the Tier 0 repository root:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/openxpki-bundle.yml -e "@$ISSUER_POLICY_FILE"
   ```

   Retain the printed artifact path/SHA256. Set them as
   `openxpki_configuration_src` / `openxpki_configuration_sha256` in
   `ansible/group_vars/issuer.yml` after initialization in Step 3.

The builder pins an upstream commit, copies native schemas/workflows and applies
site policy with Ansible modules. It refuses an existing final archive.
The explicit configuration selects the tier's roles when running from its root.
Review the private output and checksum; qualify it with the exact signed package
versions. A successful build is not a live OpenXPKI acceptance test.

The seven-day self-signed portal certificate is bootstrap-only. Verify its printed
fingerprint out of band and configure explicit trust on the isolated admin client.
Never bypass TLS warnings or install it as a general-purpose CA. Replace it with
an approved portal certificate before normal operations.

<a id="install-and-prepare-the-issuing-key"></a>

## Step 3: Install and prepare the issuing key

1. Complete [issuer Steps 1-2](issuer.md#step-1-provision-the-host), including data
   mount, archive/checksum, TLS files, audit forwarding and approved native packages.
   Set `openxpki_managed_cli: true` for this bundle. Initialize the empty database
   only once and keep runtime activation disabled. Return initialization to false
   after success; do not create a second state or repeat initialization.
2. Edit **`ansible/group_vars/issuer.yml`**:

   ```yaml
   openxpki_managed_cli: true
   openxpki_issuer_common_name: REPLACE_WITH_APPROVED_INFRASTRUCTURE_CA_NAME
   openxpki_ceremony_directory: /REPLACE_WITH_ABSOLUTE_PRIVATE_HANDOFF_DIRECTORY
   openxpki_create_issuer_key: true
   ```

   Keep `openxpki_activate_runtime: false`. The explicit fresh-key recipe creates
   an encrypted P-384 key on the issuer and fetches only its CSR:

   ```bash
   bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki-key.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

3. Return `openxpki_create_issuer_key` to `false` immediately. Never delete an existing
   key to make preparation pass; recover a partial CSR operation with that same key.

<a id="sign-and-activate"></a>

## Step 4: Sign and activate

1. Verify the CSR signature, identity and public-key fingerprint independently.
   Follow the [offline software ceremony](offline-software-root.md) to sign only
   the approved subordinate profile. Keep root and issuer keys in their own custody.
2. Copy the public issuer certificate to `/srv/openxpki/identity/issuer.pem`
   (root:openxpki, 0640), and the public root to `identity/root.pem`.
   Record the issuer SHA-256 fingerprint in the protected inputs.
3. Required state paths are `keys/issuer.pem`, `keys/cli.pem` and the
   immutable bundle's `config.d/system/crypto.yaml`, all beneath the data mount.
   The latter contains the DataVault secret; preserve its exact path and contents.
4. Enable runtime activation and rerun the
   [issuer recipe](issuer.md#step-3-activate-and-accept-issuance), then complete
   [native token activation](issuer-token.md). Starting services is not token import.

<a id="complete-identity-and-acceptance"></a>

<a id="accept-the-issuer-and-continue"></a>

## Step 5: Accept the issuer and continue

Before accepting Stage 3, pass the selected
[CA acceptance tests](../../../administration/cryptography/certificate-authority.md#acceptance-evidence),
including [independent restoration](../../../administration/cryptography/issuer-recovery.md).
Record the issuer's readiness before continuing to
[Stage 4: Kubernetes](../../stage-4-kubernetes/README.md).

In Stage 5, use the [two-phase FreeIPA installation](../../stage-5-identity/procedures/freeipa.md).
Sign its CSR in a separate root ceremony using the same subordinate constraints.
Complete the primary before installing the CA-enabled replica. This is a sibling
issuer, not a leaf issued through the TLS-server portal.

Public edge deployment is separate later work, not a Stage 3 acceptance dependency.
When publishing public services, follow the
[HTTPS deployment](../../stage-10-lab-environments/public-https.md) for origin trust, renewal
and failover, and retain [independent security alerts](../../../administration/cryptography/security-controls.md).

## References

Sources checked 2026-10-18.

1. [OpenXPKI native CLI, token setup and DataVault custody](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
2. [Argon2 reference CLI and encoded password hashes](https://github.com/P-H-C/phc-winner-argon2#command-line-utility)
