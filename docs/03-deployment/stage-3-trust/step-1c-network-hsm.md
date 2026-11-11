# Step 1c: Network HSM

**Working repository:** `<prefix>-tier-0/` on the protected controller (source: `tier-0/`).

<a id="network-hsm-integration"></a>

**Branch from:** [Step 1](README.md#step-1-prepare-issuer-and-key-custody), before production keys.
**Change:** use an accepted network appliance and an explicitly selected native client on the issuer.
**Return:** [Step 1, action 2](README.md#step-1-prepare-issuer-and-key-custody) for runtime and original-key
CSR preparation, then Step 2 signing.
**Design:** [network HSM boundaries](../../01-architecture/08-cryptography/05-network-hsm.md).

## Contents

- [1. Select and commission the appliance](#1-select-and-commission-the-appliance)
- [2. Configure the issuer client inputs](#2-configure-the-issuer-client-inputs)
- [3. Install and inspect the native client](#3-install-and-inspect-the-native-client)
- [4. Qualify issuance and recovery](#4-qualify-issuance-and-recovery)
- [References](#references)

## 1. Select and commission the appliance

Select the product, firmware/client release, supported issuer mechanisms, partition policy,
management network and entitlement. Physical commissioning, partition creation, appliance-side
client enrollment and recovery custody use that product's procedures. No appliance installer,
universal enrollment API or generic HSM cluster role is supplied.

Record accepted client identities, authenticated transport, partition/token serial and independent
backup material. An existing enterprise appliance is valid; no USB gateway pool is required.
Root custody remains offline and separately administered.

For existing USB devices, the supported local profiles are `yubihsm2` and `picohsm`, not a
generic network appliance. Keep the [local issuer path](step-1d-single-usb.md) first. Optional
[native remote PKCS#11](procedures/pkcs11-remoting.md) is a separate advanced extension with
explicit endpoints; it does not imply vendor-native cluster replication or application HA.

## 2. Configure the issuer client inputs

Provision `ca-1` and install its inactive runtime through the
[issuer procedure](procedures/issuer.md). Keep `openxpki_create_issuer_key` and
`openxpki_activate_runtime` false. Continue with hardware binding before its software key step.

Prepare `ansible/group_vars/hsm.yml` using the
[provider inputs](../../../tier-0/ansible/group_vars/hsm.yml.example):

| Input | Selected value |
| --- | --- |
| `hsm_provider`, `hsm_provider_mode` | `pkcs11`, `client` for a vendor appliance client |
| `hsm_provider_packages` | Approved native client and OpenSSL PKCS#11 engine packages, available from configured baseline sources |
| `hsm_provider_library` | Exact installed vendor library on this OS/CPU |
| `hsm_provider_config_files` | Controller source and installed destination for vendor-native configuration, trust and enrolled client files; destination directories come from the package |
| `hsm_provider_environment` | Required nonsecret native configuration paths |
| `hsm_provider_expected_serial` | Independently recorded partition/token serial; put per-host values in host vars |
| Issuer binding inputs | `openxpki` user/group, engine path and original `hsm_issuer_key`, as described in [single-device binding](step-1d-single-usb.md#3-bind-the-inactive-issuer-to-its-original-key) |

No vendor package names, ports, HA configuration or client enrollment are inferred. Licensed SDKs
requiring interactive installers or product-specific enrollment outside these package/configuration
interfaces need a dedicated integration; that work remains **unimplemented** until a product is selected.
Do not call it a routine prerequisite completed by this role.

## 3. Install and inspect the native client

Run from **`<prefix>-tier-0/`** after preparing both input files:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/issuer.yml ansible/playbooks/deployment/hsm-issuer.yml
```

Expected result: the controller installs selected client packages, copies the supplied native client
configuration, lists the expected partition without login, and validates the inactive issuer's
approved PKCS#11 binding. No appliance partition or new key is created. The final `issuer.yml`
argument preserves its complete IP map; provider host values belong in host vars when shared.

Repeat read-only inspection from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/issuer.yml -e hsm_inspect_group=issuing_ca \
  ansible/playbooks/deployment/hsm-inspect.yml
```

## 4. Qualify issuance and recovery

Use the [existing-key CSR operation](step-1d-single-usb.md#4-create-a-csr-from-the-existing-key)
before Step 2. After certificate installation, use the supplied
[hardware-token activation](step-1d-single-usb.md#5-complete-activation-and-acceptance)
and original public-key check; the software token recipe checks a filesystem key.

Test disposable sign/verify, rejected operations, client loss, selected member loss and independent
restore. Appliance/client listing alone proves neither signing authorization nor HA. If vendor HA
is selected, configure and test that exact product feature; Luna client groups, for example, have
their own setup and synchronization contract. [1] Record evidence before accepting the option.

## References

1. [Thales Luna HA group setup](https://thalesdocs.com/gphsm/luna/7/docs/network/Content/admin_partition/ha/setup.htm)
2. [OpenXPKI native PKCS#11 engine contract](https://github.com/openxpki/openxpki/blob/master/core/server/OpenXPKI/Crypto/Backend/OpenSSL/Engine/PKCS11.pm)
