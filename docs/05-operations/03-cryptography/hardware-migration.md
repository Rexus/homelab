# Change CA key custody

<a id="move-signing-custody-to-hardware"></a>


Use a controlled issuer rollover when moving from software custody to hardware.
The [custody design](../../01-architecture/08-cryptography/03-hsm-selection.md) explains the
options. The normal runtime installer preserves its existing immutable binding; it does **not**
migrate a live issuer to another provider or signing identity.

**Run from:** Tier 0 for project records/recovery inputs; hardware and root operations
run only in their authorized provider or offline environments.
**Before starting:** accepted current issuer, verified recovery set, custodians and
an exact vendor/application migration procedure qualified with disposable keys.

<a id="contents"></a>

## Tasks

- [Which migration is required?](#choose-the-migration)
- [What must be recorded before changing custody?](#what-must-be-recorded-before-changing-custody)
- [How is the same key rebound to another provider?](#same-key-provider-rebind)
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
| Same wrapped issuer key on another device or remote endpoint | Use the [same-key rebind](#same-key-provider-rebind); preserve the issuer certificate/history. The normal restore requires the original provider identity |
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

<a id="same-key-provider-rebind"></a>

## How is the same key rebound to another provider?

Use this branch for a replacement token or [single-device pool upgrade](usb-hsm.md#single-device-to-pool).
It preserves the issuer's key/certificate; the new-key rollover below is a different operation.

The supplied [explicit migration recipe](../../../tier-0/ansible/playbooks/deployment/openxpki-pkcs11-migrate.yml)
supports an existing Debian 12 amd64 PKCS#11 issuer moving to a prepared remote client. It preserves
the application signing PIN, package versions, DataVault/CLI/session secrets, certificate and schema.
It is a **planned outage**, with `prepare`, `apply` and `rollback` operations. Ordinary installation
still rejects a changed binding. No database import, schema initialization or key creation is performed.

1. **Keep the original available.** Restore the original wrapped key to the new same-family device
   and verify the original SPKI and signing permissions. For **two total boards**, keep the original
   attached to `ca-1`; provision only `hsm-1` with the restored replica. Accept its
   [single-backend transition](../../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md#2-declare-the-transport-and-client-inputs)
   with `hsm_remote_single_backend_transition: true`. There is no provider failover at this point.
   Install and check the native remote client for `openxpki` before this migration. Retain the original
   effective provider inputs privately as `ansible/group_vars/hsm.before-pool.yml` for rollback.
   Retain `hsm_provider`, `hsm_provider_mode`, packages, `hsm_provider_library`,
   `hsm_provider_expected_serial`, `hsm_issuer_key`, `hsm_issuer_engine_library`,
   `hsm_provider_environment`, provider user/group and native configuration-file inputs. For YubiHSM,
   also retain its physical serial/connector settings; for PicoHSM, its accepted reader/PCSC inputs.
2. **Create only the provider configuration revision.** Retain the original approved archive and SHA.
   The ordinary bundle builder creates a new CLI identity; use the narrow revision tool below instead.
   It retains every original bundle member/secret and changes only `ca-signer.key` and its native
   engine section. Select one explicit accepted remote serial/object URI, proxy library and engine.

   On the **protected controller, `<prefix>-tier-0/`**, with Python/PyYAML from its accepted Ansible environment:
   Read the old archive path from `issuer.yml`'s `openxpki_configuration_src` and the realm from
   `openxpki_realm`; use the original SPKI fingerprint from independent key-commissioning custody.

   ```bash
   read -r -e -p 'Original openxpki_configuration_src from issuer.yml: ' OLD_ISSUER_BUNDLE
   read -r -e -p 'New private custody directory: ' PKI_POOL_CUSTODY
   install -d -m 0700 "$PKI_POOL_CUSTODY"
   read -r -p 'Original openxpki_realm from issuer.yml (for example infrastructure): ' ISSUER_REALM
   read -r -p 'Accepted remote private-key URI: ' NEW_HSM_KEY_URI
   read -r -p 'Installed issuer proxy library path: ' NEW_HSM_LIBRARY
   read -r -p 'Installed issuer OpenSSL engine path: ' NEW_HSM_ENGINE
   python3 ansible/roles/openxpki/files/pkcs11-migration-bundle.py \
     --old "$OLD_ISSUER_BUNDLE" --output "$PKI_POOL_CUSTODY/configuration.tar.gz" \
     --realm "$ISSUER_REALM" --key "$NEW_HSM_KEY_URI" \
     --library "$NEW_HSM_LIBRARY" --engine "$NEW_HSM_ENGINE"
   ```

   Example URI: `pkcs11:serial=NEW_DEVICE_SERIAL;id=%01;type=private`; use the actual ID bytes.
   Use the [remote issuer profile](../../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md#fresh-inactive-issuer)
   in private `ansible/group_vars/hsm.pool-client.yml`. Do not run its fresh-install binding recipe
   against the active issuer. The migration checks the new key and native PIN against the original
   certificate and protected secret; a different key, PIN, policy or schema is refused.
3. **Declare the ceremony.** Keep `issuer.yml` pointing at the **old** archive/SHA until successful
   cutover. Keep `openxpki_initialize_database: false`, `openxpki_create_issuer_key: false`,
   `openxpki_activate_runtime: true`, and the original `openxpki_token_alias`. In protected local
   **`ansible/group_vars/issuer-provider-migration.yml`**, replace these values with independent records:

   ```yaml
   openxpki_pkcs11_migration_approved: true
   openxpki_pkcs11_migration_expected_old_sha256: COPY_THE_OLD_ARCHIVE_SHA256
   openxpki_pkcs11_migration_new_src: /absolute/private/custody/configuration.tar.gz
   openxpki_pkcs11_migration_new_sha256: COPY_THE_REVISION_TOOL_SHA256
   openxpki_pkcs11_migration_spki_sha256: COPY_THE_ORIGINAL_64_HEX_SPKI_SHA256
   openxpki_backup_recipient: age1COPY_THE_INDEPENDENT_RECIPIENT
   openxpki_pkcs11_migration_backup_dest: /absolute/private/custody/before-pool.tar.gz.age
   openxpki_pkcs11_migration_backup_retained: false
   openxpki_pkcs11_migration_resume_accepted: false
   ```

   The backup parent must already be a real private directory, mode `0700`; the destination must not
   exist, including as a dangling symlink. Encrypted capture is published exclusively, without replacing
   a destination created concurrently. Keep the original issuer/root/public certificate source fields
   in `issuer.yml`. Restore the three original database/session secrets and the unchanged application
   PIN into the **same protected controller shell**, unless established encrypted vars already supply
   those exact inputs. Retrieve them from original independent custody; never generate replacements:

   ```bash
   read -r -s -p 'Original database password from custody: ' OPENXPKI_DATABASE_PASSWORD; printf '\n'
   read -r -s -p 'Original session password from custody: ' OPENXPKI_SESSION_PASSWORD; printf '\n'
   read -r -s -p 'Original session secret from custody: ' OPENXPKI_SESSION_SECRET; printf '\n'
   read -r -s -p 'Original unchanged HSM application PIN from custody: ' HSM_ISSUER_PIN; printf '\n'
   export OPENXPKI_DATABASE_PASSWORD OPENXPKI_SESSION_PASSWORD OPENXPKI_SESSION_SECRET HSM_ISSUER_PIN
   ```
4. **Prepare and pause.** Quiesce other deployment jobs and approve the outage. From
   **`<prefix>-tier-0/`** on the controller:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
     -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
     -e @ansible/group_vars/foundation.yml -e @ansible/group_vars/issuer.yml \
     -e @ansible/group_vars/hsm.pool-client.yml \
     -e @ansible/group_vars/issuer-provider-migration.yml \
     -e openxpki_pkcs11_migration_operation=prepare \
     ansible/playbooks/deployment/openxpki-pkcs11-migrate.yml
   ```

   This validates the new provider, stops issuer/portal/CRL writers, installs durable startup inhibits,
   captures a frozen logical database plus original recovery state, encrypts it and transfers it to
   the private controller destination. **The issuer remains paused after prepare.** Retain and verify
   that archive under custody independent of the issuer/controller before proceeding. Do not rerun
   `prepare` over its existing transaction or resume services by removing inhibit files manually.
5. **Accept the backup and commit/resume boundary.** Set `openxpki_pkcs11_migration_backup_retained: true`
   and `openxpki_pkcs11_migration_backup_sha256` to the independently checked encrypted archive SHA.
   Set `openxpki_pkcs11_migration_resume_accepted: true` only when ready to commit and resume the backend.
   Run from **`<prefix>-tier-0/`**, in the same protected shell:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
     -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
     -e @ansible/group_vars/foundation.yml -e @ansible/group_vars/issuer.yml \
     -e @ansible/group_vars/hsm.pool-client.yml \
     -e @ansible/group_vars/issuer-provider-migration.yml \
     -e openxpki_pkcs11_migration_operation=apply \
     ansible/playbooks/deployment/openxpki-pkcs11-migrate.yml
   ```

   Apply rechecks frozen history/custody and the same key, then changes only the configuration links,
   provider environment, immutable artifact and recorded configuration SHA. **Backend resume is the
   accepted commit boundary:** queued/background workflows may write immediately. Native backend
   connectivity and the active token's sign/verify test gate portal/CRL-timer admission; those checks
   do not promise a write-free interval after backend start. Failure leaves durable inhibition and
   the transaction record, preserving the latest database for recovery or guarded rollback.
6. **Record the accepted configuration and finish the second endpoint.** After success, update normal
   `issuer.yml` to the new artifact/SHA and retained remote-provider inputs; normal reconciliation must
   pass with that binding and must reject the old one. Accept issuance, revocation/CRL publication,
   denial and restart checks. Now remove the original device's **foundation** USB attachment and attach
   it to new provider `hsm-2` through HSM Terraform state. Qualify its original key/own serial, expand
   `hsm_remote_backends`, set `hsm_remote_single_backend_transition: false`, and reconcile/check all
   server/client endpoints. Exactly two boards are sufficient. The issuer stays pinned to its selected
   serial; endpoint visibility alone does not implement consumer switching.
7. **Rollback when required.** Restore the original physical attachment/access first. Keep the migration
   record, original configuration directory and latest database. The old URI, module,
   engine and PIN must match the retained old configuration/environment; pool locators are refused.
   Retain the accepted resume flag and backup SHA. From **`<prefix>-tier-0/`** in the protected shell,
   enter the original SHA from the migration record, even if normal issuer inputs now select the new SHA:

   ```bash
   read -r -p 'Original expected_old_sha256 from issuer-provider-migration.yml: ' OLD_CONFIG_SHA256
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
     -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
     -e @ansible/group_vars/foundation.yml -e @ansible/group_vars/issuer.yml \
     -e @ansible/group_vars/hsm.pool-client.yml \
     -e @ansible/group_vars/issuer-provider-migration.yml \
     -e @ansible/group_vars/hsm.before-pool.yml \
     -e "openxpki_configuration_sha256=$OLD_CONFIG_SHA256" \
     -e openxpki_pkcs11_migration_operation=rollback \
     ansible/playbooks/deployment/openxpki-pkcs11-migrate.yml
   ```

   Rollback verifies the immutable old subset, including rendered connections and the saved environment,
   and restores the digest-verified **remote** original archive. It does not depend on an unchanged
   controller copy of that old archive. It restores configuration/binding and signs through the old
   provider before resuming. It never restores an old database over post-cutover writes. On failure,
   preserve both inhibits and the journal; recover the recorded original state explicitly.

No root signing is needed solely to relocate an unchanged issuer key/certificate. Keep the offline
root separate; a new key, changed authority or compromise instead requires its approved CA ceremony.

<a id="qualify-and-roll-over"></a>

## How is the new provider qualified and activated?

1. On an isolated restored application copy, use disposable keys to test CSR,
   certificate/CRL signing, denied operations, PIN/session failure, connector loss,
   restart and independent restore. Keep authentication/wrapping credentials separate.
2. In the authorized hardware ceremony, generate the new key using the selected
   vendor procedure. Record public identity and permitted operations; keep PINs,
   wrapping keys and authentication secrets off command lines and out of Git. [1]
3. Transfer only the approved CSR to the [offline root ceremony](../../03-deployment/stage-02-trust/procedures/offline-root.md).
   Return the signed subordinate certificate/public chain, never the root key.
4. Rehearse the native provider configuration and token lifecycle against the
   restored current database/history. Approve package/schema/configuration migration
   explicitly; routine deployment rejects changed bindings rather than migrating them. [2]
5. During the approved cutover, follow that qualified native token procedure.
   Verify new certificates use the intended issuer, publish both required chains/CRLs,
   test consumers and retain protected audit evidence before admitting traffic.

The [hardware issuer recipes](../../03-deployment/stage-02-trust/step-1d-single-usb.md#3-bind-the-inactive-issuer-to-its-original-key)
supply binding, CSR and token activation for a prepared inactive runtime. They are not a live
configuration/database migration or a universal device CLI sequence. Use the exact vendor/product
revision qualified above; do not overwrite the active key file or repoint an alias during routine CI.

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
