# IaC input names

Reusable instructions select the actual owning repository, deployment and resource.
Names in `<...>` are placeholders, not literal configuration keys or fixed service selections.

## Contents

- [Storage identity inputs](#storage-identity-inputs)
- [Find the actual key](#find-the-actual-key)
- [Preserve existing inputs](#preserve-existing-inputs)

## Storage identity inputs

Use lowercase `snake_case` with a service/role namespace and a volume purpose.
New filesystem UUID pins follow **`<service>_<volume>_uuid`**.

| Part or input | Meaning |
| --- | --- |
| `<service>` | The role's public configuration prefix, independent of VM hostname, VMID or tier |
| `<volume>` | The filesystem's purpose, such as `data` or `repository`; distinguish separate volumes |
| `<service>_<volume>_uuid` | Expected filesystem UUID; a guard against using different storage |
| `<service>_<volume>_device` | Stable guest device selector, matched to the configured controller slot |

Use the exact public keys exposed by the selected role. Existing UUID keys with an additional
`expected` qualifier remain valid; this convention does not rename deployed inputs.
A configuration prefix may contain several words. Do not derive it from the setup filename or hostname.

The filesystem UUID is different from a Proxmox VMID, managed volume ID, disk serial or controller slot.
Preserved or copied filesystems keep their UUID pin. Clear a pin only for an intentionally fresh volume;
the [VMID data-disk procedure](../05-operations/01-hosting/vmid-data-disks.md) explains that choice.

## Find the actual key

1. Open the service configuration file named by its deployment guide.
2. Follow its header to `ansible/roles/<role>/defaults/main.yml` or the stated schema.
3. Use the exact UUID key printed by the service's storage preparation. Its verified UUID is the value
   to retain for that host; runtime facts such as `data_volume_result.uuid` are not configuration keys.
4. Save one pin per host/volume in the owning service inputs or
   `ansible/inventory/host_vars/<host>.yml`, following the
   [input precedence rules](../08-reference/platform-inputs.md#vm-disk-storage).

Ansible already persists the prepared mount by UUID. Saving the optional input pin adds an identity check;
it does not attach, mount, copy or erase storage by itself.

## Preserve existing inputs

Keep established public variable names working when evolving a role. A future rename needs a documented
compatibility path and validation that an existing UUID guard still reaches storage preparation.
Do not silently drop a pin or treat an unrecognized key as permission to initialize new storage.

When adding a storage-backed service, expose its UUID guard in the configuration example and pass it
to Shared's `data_volume_expected_uuid`. Set `data_volume_uuid_input` to that public key so the role prints
the correct line to retain. Service-specific output may instead provide the same exact-key handoff.
See [adding a service](../04-development/adding-service.md#option-b-add-an-independent-linux-setup) and
[supported input definitions](../08-reference/platform-inputs.md#find-supported-settings).
