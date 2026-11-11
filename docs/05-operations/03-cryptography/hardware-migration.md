# Change CA key custody

<a id="move-signing-custody-to-hardware"></a>


Use a controlled issuer rollover when moving from software custody to hardware.
The [custody design](../../01-architecture/08-cryptography/03-hsm-selection.md) explains the
options. The supplied software installer does **not** implement HSM migration.

**Run from:** Tier 0 for project records/recovery inputs; hardware and root operations
run only in their authorized provider or offline environments.
**Before starting:** accepted current issuer, verified recovery set, custodians and
an exact vendor/application migration procedure qualified with disposable keys.

<a id="contents"></a>

## Tasks

- [Which migration is required?](#choose-the-migration)
- [What must be recorded before changing custody?](#what-must-be-recorded-before-changing-custody)
- [How is the new provider qualified and activated?](#qualify-and-roll-over)
- [When can the old key be retired?](#retire-and-recover)
- [What is the stop or rollback condition?](#what-is-the-stop-or-rollback-condition)
- [References](#references)

<a id="choose-the-migration"></a>

## Which migration is required?

| Operation | Selected route |
| --- | --- |
| New HSM-generated issuer key | Preferred new-key rollover; approve certificate/chain overlap first |
| Import existing software key | Only when supported/approved; historical software exposure remains |
| Root custody change | Separate offline root/trust-anchor ceremony; not an issuer maintenance task |
| DataVault protection change | Separate encrypted-data migration; an HSM PIN cannot replace its master secret |

Qualify exact device, firmware, middleware/provider and OpenXPKI versions.
Select mechanisms from supported capabilities and [measured capacity](../../08-reference/yubihsm-performance.md),
not product labels. Hardware adoption alone establishes neither PQC nor regulatory compliance. [1]

## What must be recorded before changing custody?

1. Run [issuer health checks](certificate-authority.md#routine-controls) and
   [capture a recovery set](issuer-recovery.md#capture-a-recovery-set).
2. Record the following in the private project migration record, **not as new role inputs**:

   | Record | Required detail |
   | --- | --- |
   | Current identity | Issuer certificate/public-key fingerprint, realm and active token alias |
   | Recovery binding | Current package/configuration/schema combination, latest database and independent DataVault/controller secrets |
   | Selected hardware | Stable device identity, object ID/label, mechanisms, domains/capabilities and supported backup/wrapping attributes |
   | Cutover | Permitted consumers, new chain/profile scope, overlap, publication URLs and operator approval |
   | Recovery/rollback | Qualified spare/provider, original state retention and latest-writer rule |

3. Stop if recovery, provider support or the required key attributes are unproven.
   Do not alter `issuer.yml` to bypass the existing immutable-binding checks.

<a id="qualify-and-roll-over"></a>

## How is the new provider qualified and activated?

1. On an isolated restored application copy, use disposable keys to test CSR,
   certificate/CRL signing, denied operations, PIN/session failure, connector loss,
   restart and independent restore. Keep authentication/wrapping credentials separate.
2. In the authorized hardware ceremony, generate the new key using the selected
   vendor procedure. Record public identity and permitted operations; keep PINs,
   wrapping keys and authentication secrets off command lines and out of Git. [1]
3. Transfer only the approved CSR to the [offline root ceremony](../../03-deployment/stage-3-trust/procedures/offline-root.md).
   Return the signed subordinate certificate/public chain, never the root key.
4. Rehearse the native provider configuration and token lifecycle against the
   restored current database/history. Approve package/schema/configuration migration
   explicitly; routine deployment rejects changed bindings rather than migrating them. [2]
5. During the approved cutover, follow that qualified native token procedure.
   Verify new certificates use the intended issuer, publish both required chains/CRLs,
   test consumers and retain protected audit evidence before admitting traffic.

There is no universal device CLI sequence or shipped hardware activation playbook.
Use the exact vendor/product revision qualified above; do not substitute generic
PKCS#11 object commands, overwrite the active key file or repoint an alias during routine CI.

<a id="retire-and-recover"></a>

## When can the old key be retired?

1. Stop old-key **new issuance** only after consumer and new-issuer acceptance.
2. Retain old issuance/history and the ability to revoke outstanding certificates
   until its complete publication/revocation obligation ends.
3. Test restoration on a separate authorized device and replacement application
   host. Matching model numbers do not establish matching keys or permissions.
4. Archive custody records; destroy obsolete material only through the approved
   retention/ceremony procedure. An offline backup device is not an automatic active peer.

## What is the stop or rollback condition?

Stop on wrong key identity, failed denial/restore tests, unavailable publication or
unqualified consumer trust. Before new issuance, the unchanged old issuer may remain
the selected writer under the approved plan. After new writes, preserve both authorities'
current histories and chain/revocation obligations; never restore an older database blindly.

Suspected compromise requires incident revocation/reissuance, not importing the
suspect key into hardware. Use the [incident path](security-controls.md#detect-and-respond).

## References

Provider interfaces checked 2026-11-08; production steps remain revision-specific.

1. [YubiHSM command and algorithm capabilities](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-cmd-reference.html).
2. [OpenXPKI native crypto/token configuration](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md).
