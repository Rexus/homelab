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

- [Decisions and recovery kit](#decisions-and-recovery-kit)
- [Build the private policy bundle](#build-the-private-policy-bundle)
- [Install and prepare the issuing key](#install-and-prepare-the-issuing-key)
- [Sign and activate](#sign-and-activate)
- [Accept the issuer and continue](#accept-the-issuer-and-continue)
- [References](#references)

## Decisions and recovery kit

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

## Build the private policy bundle

On the Linux Tier 0 controller, copy the
[policy example](../../../../tier-0/ansible/group_vars/issuer-policy.yml.example)
to a private inputs file outside Git. Set real suffixes, publication URL, portal name,
absolute private build directory and two named accounts with different custodians.
Generate Argon2id password hashes with the native `argon2` CLI on the trusted
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

Prepare independent secrets in a private shell:

```bash
read -rsp 'Issuer key passphrase (32+ characters): ' OPENXPKI_SIGNER_PASSWORD; echo
export OPENXPKI_SIGNER_PASSWORD
export OPENXPKI_DATAVAULT_SECRET="$(openssl rand -hex 32)"
```

Back up these exact values securely **before** building. The signer passphrase is
also required for key preparation. DataVault loss cannot be repaired by generating
another random value. [1]

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook -i localhost, ansible/playbooks/deployment/openxpki-bundle.yml \
  -e @/absolute/private/issuer-policy.yml
```

The builder pins an upstream commit, copies native schemas/workflows and applies
site policy with Ansible modules. It refuses an existing final archive.
The explicit configuration selects the tier's roles when running from its root.
Review the private output and checksum; qualify it with the exact signed package
versions. A successful build is not a live OpenXPKI acceptance test.

The seven-day self-signed portal certificate is bootstrap-only. Verify its printed
fingerprint out of band and configure explicit trust on the isolated admin client.
Never bypass TLS warnings or install it as a general-purpose CA. Replace it with
an approved portal certificate before normal operations.

## Install and prepare the issuing key

Follow [issuer host/runtime installation](issuer.md#step-1-provision-the-host).
Set archive path/checksum, bootstrap TLS files, prepared mount UUID and package pins
in protected issuer inputs. For this bundle set `openxpki_managed_cli: true`.
Install with database initialization enabled once and runtime activation disabled;
return initialization to false after success.

Set `openxpki_issuer_common_name`, an absolute private
`openxpki_ceremony_directory` and `openxpki_create_issuer_key: true`
in the protected inputs. The explicit fresh-key recipe creates an encrypted
P-384 key on the issuer and fetches only its CSR:

```bash
bash scripts/deploy.sh foundation --ansible-only \
  --playbook deployment/openxpki-key.yml --ansible-vars ansible/group_vars/issuer.yml
```

Return the approval flag to false immediately. Never delete an existing key to
make preparation pass; recover a partial CSR operation with that same key.

## Sign and activate

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

## Accept the issuer and continue

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
