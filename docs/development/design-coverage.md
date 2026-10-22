# Design coverage and historical alternatives

The documentation review used the May 2026 tree at `5801e46`, the May documentation
changes, and the earlier HSM design carried into that tree. All 45 documentation
paths in that snapshot have a current home or an explicit relocation mapping.
The checks below concern design coverage, not equivalence of every historical sentence.

## Table of contents

- [Preserved option families](#preserved-option-families)
- [Support boundaries](#support-boundaries)
- [Change checklist](#change-checklist)
- [References](#references)

## Preserved option families

| Historical concept | Current design home | Deployment realization |
| --- | --- | --- |
| Per-capability levels 0/1/2; new, existing or isolated services [1] | [Service boundaries](../architecture/service-boundaries.md) | [Deployment readiness](../deployment/readiness.md); progress is not part of the static design |
| Software token, single USB, replicated USB, enterprise network HSM [2] | [Custody A-D](../architecture/cryptography/hsm-selection.md) | [Trust-stage branches](../deployment/stage-2-trust/README.md#step-1-prepare-issuer-and-key-custody) |
| Shamir, independent Transit, Vault Enterprise PKCS#11, OpenBao evaluation [2] | [Seal patterns](../architecture/cryptography/vault-seal.md) | [Seal integration](../deployment/stage-4-secrets/step-1c-seal-integration.md) |
| Existing identity; dedicated authority; optional hardware authentication and Windows integration [3] | [Identity](../architecture/identity/README.md) | Identity and Secrets stages; no new mandatory AD deployment |
| Bridges or SDN; host/storage-fabric choices [4] | [Compute](../architecture/compute/README.md), [network](../architecture/networking/README.md) | Unnumbered [foundation](../deployment/foundation/README.md), including optional HA/SDN |
| Direct software access, cache, mirrors or offline sources; shared/isolated egress [5] | [Traffic and delivery](../architecture/delivery/README.md) | Foundation software supply and optional cache |
| VM source control, registry alternatives, runner and image-based Linux [6] | [Delivery](../architecture/delivery/README.md), [artifact supply](../architecture/delivery/artifact-supply.md) | Stage 5 options; image publication remains Tier 0 |
| Shared or isolated telemetry, multiple signal backends [1] | [Telemetry](../architecture/operations/telemetry.md) | Stage 4 independent Tier 0 monitoring; Stage 6 Observability; Stage 7 workload collection |
| Private, hybrid and tenant-platform comparisons [7] | [Private-cloud model](../architecture/private-cloud.md), [service boundaries](../architecture/service-boundaries.md) | Proxmox remains the implemented hypervisor; external services need explicit contracts |

## Support boundaries

The May HSM material contained comparisons, a USB host/gateway blueprint and seal
designs. It did not contain a complete enterprise-appliance installer. Restoring
those alternatives therefore means preserving design and adding clear vendor
integration paths, not claiming previously working automation was recovered.

Historical pricing, team-size estimates and broad product rankings are not promoted
to current design guarantees. Product capability claims require current primary
documentation and verification against the selected release. The
[support map](../reference/implementation-support.md) distinguishes runnable code
from host-only automation and operator integration.

## Change checklist

1. Identify the domain's purpose and affected interface before changing code or docs.
2. Preserve valid alternatives; record an explicit decision when retiring one.
3. Put topology, trade-offs and constraints in architecture; stages, readiness and evidence in deployment; recurring
   tasks in administration and implementation work in development.
4. Link the design option, stage procedure and acceptance record in both upstream
   and generated project templates. Avoid a second deployment sequence.
5. Run documentation, generator and preservation tests; retain project-owned records.

## References

1. [May capability paths](https://github.com/Rexus/homelab/commit/49f1ea1)
2. [May HSM design tree](https://github.com/Rexus/homelab/tree/5801e46/docs/security)
3. [Identity and hardware-authentication changes](https://github.com/Rexus/homelab/commit/cfeb784)
4. [Optional Proxmox SDN](https://github.com/Rexus/homelab/commit/32b2c8b)
5. [Cache and edge HA changes](https://github.com/Rexus/homelab/commit/9d98b32)
6. [Application platform and image lifecycle](https://github.com/Rexus/homelab/commit/acaee6c)
7. [Private/public cloud design](https://github.com/Rexus/homelab/commit/1d35c71)
