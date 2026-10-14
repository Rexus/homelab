# Step 1c: Network HSM

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for issuer/client integration.
Appliance commissioning uses the vendor procedure; no appliance installer is supplied.

<a id="network-hsm-integration"></a>

**Branch from:** [Step 1](README.md#step-1-prepare-issuer-and-key-custody), before creating production keys.
**Change:** Use a supported network appliance and its client integration.
**Return:** [Step 2](README.md#step-2-establish-the-certificate-hierarchy) for intermediate signing and issuer verification.

**Design:** [option D](../../architecture/cryptography/network-hsm.md).
**Prerequisites:** approved appliance/provider, entitlement, client compatibility,
network policy, custodians and backup method. This repository does not install
appliances or supply a generic HSM-cluster role.

## Procedure

| Step | Action | Acceptance evidence |
| --- | --- | --- |
| 1 | Record partitions, client identities, custody roles and failure domains | Selected architecture and access policy |
| 2 | Commission the appliance and its protected management path using the vendor procedure | Independent administration/recovery works |
| 3 | Install the supported client and establish authenticated partition access on approved issuer hosts | Expected partition visible only to authorized clients |
| 4 | Configure the application's supported algorithms and key policy | Disposable sign/verify and denied-operation tests |
| 5 | Configure vendor HA only when selected; test client/member loss | Measured interruption and verified synchronization behavior |
| 6 | Perform authorized backup/restore with test material | Recovery works without the original active appliance |
| 7 | Integrate production issuance after approval | Trust-stage issuer and custody checks pass |

Luna is one example with a vendor HA procedure. Its client-group setup is not
interchangeable with HTTP load balancing or the repository's USB gateway setup. [1]
Use the documentation matching the purchased hardware, firmware and client release.
No generic network port, export policy or automatic replication behavior is assumed.

The tier-local guest code can provision issuer/client VMs, but not the appliance.
Do not deploy the USB gateway pool solely because the setup is named hsm.
Root custody remains separately offline; online appliance availability does not
justify routing into the ceremony environment.

Record recurring health, client rotation and restore procedures under project
administration. Return to [Step 2](README.md#step-2-establish-the-certificate-hierarchy).

## References

1. [Thales Luna: setting up an HA group](https://thalesdocs.com/gphsm/luna/7/docs/network/Content/admin_partition/ha/setup.htm) (checked 2026-10-08)
