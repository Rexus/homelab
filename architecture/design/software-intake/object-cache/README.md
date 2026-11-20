# Rebuildable cache storage

[Up: Software intake](../README.md) · Level 2 · `L-Cache` / `DEF-cache`


Provide storage for disposable content reused by the [policy proxy](../policy-proxy/README.md).

## Storage and content

`L-Cache` is the logical **storage component**, allocated to each selected guest disk. It owns an item
feature, `L-cached-content : CachedContent [0..*]`, representing **stored response data and cache metadata**.
The blue cylinder identifies storage; the mauve item inside identifies its content. Each realized disk
has its own content usage (`CONTENT-cache-1`, `CONTENT-cache-2` in the example), of the same item type.
This does not assert shared contents, replication, authoritative retention or publisher trust.

The [logical view](../../../views/software-intake/logical.svg) and
[software deployment](../../../views/software-intake/placement.svg) preserve that distinction.
The [functions view](../../../views/software-intake/functions.svg) allocates responsibilities to the
proxy/storage components; content is the information acted on. Physical disks remain separate in the
[resource view](../../../views/software-intake/resource-dependencies.svg).


[definition.sysml](definition.sysml) owns this contract. Loss of these objects causes refetching;
they are neither authoritative retention nor independent recovery custody.

| Concern | Connected design or evidence |
| --- | --- |
| Logical access | Parent [logical design](../logical.md), native flow `L-cache-io` |
| Selected realization | [Per-VM virtual disks](../deployment.md), allocated from the same `L-Cache` |
| Shared provider and physical backing | [Platform data](../../platform/data/README.md), [resource relationships](../resources.md) |
| Implementation and verification | [Storage guard](../../../../tier-2/ansible/roles/cache_proxy/tasks/storage.yml), [test entry](../../../test/software-intake/README.md) |

The selected local disk class has no dependency on the optional storage network. A different storage
choice must update the provider relationship and acceptance evidence; a virtual disk is not a physical drive.

<!-- BEGIN DESIGN CONTEXT -->
## Connected views

[Owning documentation](../resources.md).

This component selects HTTP reuse scenarios through its cache-function allocation. It does not inherit every intake scenario or external-client obligation.
<!-- END DESIGN CONTEXT -->
