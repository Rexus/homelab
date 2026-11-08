# Recovery

Recover Tier 0 independently, preserve evidence before rebuilding, then restore
platform services and workloads. Offline investigation does not require a running platform.
The [service-boundary design](../architecture/service-boundaries.md) explains this recovery independence.

<a id="table-of-contents"></a>

## Find a task

- [What must survive outside the platform?](#recovery-inputs)
- [What is the first action after total loss?](#first-action)
- [In what order are services restored?](#recovery-order)
- [Which restore procedure applies?](#product-procedures)

<a id="recovery-inputs"></a>

## What must survive outside the platform?

Retain these outside the system being restored:

| Material | Purpose |
| --- | --- |
| Tier/shared code, tools, provider artifacts, images | Bootstrap without hosted source control, CI, or registry |
| State, inventory, network/storage records | Recreate resources without an inventory application |
| Machine configuration, credentials, SOPS and recovery keys | Restore without unavailable identity or secret services |
| etcd and application-data backups | Restore data, not merely empty VMs |
| Protected log-data copies, schema/source catalogue and offline reader/key kit | Investigate a total shutdown without the collector, identity services or search indexes |
| Working API, DNS/time, image access, and runbook | Execute recovery independently of the target |

Record owners, backup locations, and restore results in project-owned runbooks.
Offline custody has no routed access from the connected management network.

<a id="first-action"></a>

## What is the first action after total loss?

**Work from:** a trusted isolated recovery host and the independently held recovery kit.
**Prerequisites:** authorized custody, readable backups and original keys/state. Do not depend on hosted SSO or CI.

1. Stop competing workstation/runner writers. Preserve surviving disks and logs before rebuilding.
2. Retrieve the tier/Shared code, inventory, private inputs and **original** state from protected backup.
   Keep their sibling repository layout and recorded revisions.
3. Follow the [original-state restore procedure](recovery/README.md) before any apply.
   In each restored tier root, inspect the checkout and retained state locations:

   ```bash
   git status --short
   ls -ld .terraform/state
   ```

4. Verify backup identifiers, key availability, state lineage and resource addresses using that procedure.
   Then continue in the order below; restore only onto accepted clean targets.

**Expected:** the original deployment identity is recovered before provisioning resumes.
**Stop:** on missing state/keys, unexplained resource differences or evidence of compromise.
Do not replace missing state with an empty `init`, initialize new CA/Vault keys or bootstrap a replacement cluster.

<a id="recovery-order"></a>

## In what order are services restored?

| Order | Action | Acceptance |
| --- | --- | --- |
| 1 | Isolate affected systems and preserve surviving logs/disks before rebuilding | Authorized [offline investigation](security-logging.md#offline-investigation) works from a protected copy; original evidence is unchanged |
| 2 | Recover Tier 0 console/network/storage access and bootstrap tools | Independent local credentials, recovery keys and backup access work without SSO or Tier 1/2 |
| 3 | Restore Tier 0 intake and protected evidence storage | New recovery events are retained; original evidence stays separate; buffered sources replay with gaps accounted for |
| 4 | Restore Tier 0 trust, identity and control services in prerequisite order | Selected PKI, directory and cluster functions verified before dependent consumers |
| 5 | Restore Tier 1 platform and scoped analytics | Search indexes rebuilt from approved copies; no delete authority over Tier 0 evidence |
| 6 | Restore Tier 2 workloads and their integrations | Service data, access scopes and collection verified |

For hardware-only outages, preserve evidence without unnecessarily delaying safe
intake restoration. Suspected compromise requires a clean recovery environment;
reconnecting old disks or credentials must not reintroduce the compromised authority.
Use the [deployment stages](../deployment/README.md) for service-specific prerequisites,
the [backup guide](compute/backup-restore.md) for recovery objectives and restore validation, and
[secret strategy](secret-handling/strategy.md) for protected recovery material.
For the software issuer, follow the [clean-target restore procedure](cryptography/issuer-recovery.md),
not fresh key creation or initial token activation.

<a id="product-procedures"></a>

## Which restore procedure applies?

The [product recovery index](recovery/README.md) provides clean-target procedures for original
inputs/state and etcd, FreeIPA/CA, Vault, CNPG databases, Keycloak, NetBox/media and Tier 1 data.
Install [scheduled control backup transport](backups/control-applications.md) before accepting
the dependent services. Preserve the selected database/media recovery points and independent keys;
a fresh bootstrap or an empty application deployment is not a restore.

1. Select the affected product in that index and match the backup to its original version/configuration.
2. Restore on isolated capacity; keep duplicate guest identities and credentials off live networks.
3. Verify data, permitted/denied access, logs and a measured recovery point/time before reconnecting consumers.

**Stop/rollback:** keep failed restores isolated and preserve their diagnostics. Return to the retained
backup and a fresh clean target; never overwrite the only surviving evidence or recovery set.
