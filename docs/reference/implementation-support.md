# Implementation support

Design options describe valid arrangements, not automatic installer coverage.
[Software intake](../deployment/stage-1-software-intake/README.md) is a separate early
capability; it grows into retained repositories and OCI supply without becoming
a foundation prerequisite installer or a dependency on later Harbor deployment.
[Foundation prerequisites](../deployment/foundation/README.md) precede the
[numbered capability stages](../deployment/README.md).
The [repository map](../deployment/README.md#repository-locations) identifies the
working checkouts; Shared helpers do not own the tier deployments they execute.

## Contents

- [Stage coverage](#stage-coverage)
- [Detailed coverage](#detailed-coverage)

<a id="first-six-stages"></a>

## Stage coverage

**The reference platform is not yet an end-to-end installer.** Supplied mechanisms
can be exercised offline, but no live installation, failover or full restore is
accepted by those tests. Stop at an unimplemented integration or satisfy its
contract with a verified existing service; empty manifests do not meet a stage gate.

| Stage | Supplied path | Remaining main-path implementation |
| --- | --- | --- |
| [1: Software intake](../deployment/stage-1-software-intake/README.md) | Tier 2 Squid/keepalived pair and shared Linux consumer settings | Retained repository management and automatic patch rollout remain integration; live policy/failover acceptance required |
| [2: Logging](../deployment/stage-2-logging/README.md) | Receiver VM/disks, Linux senders, independent producer trust, NAS checkpoints and backup recipes | Selected Linux/NAS mechanisms supplied; appliance/Kubernetes source adapters, NAS commissioning and live fault/restore evidence are separate |
| [3: Trust](../deployment/stage-3-trust/README.md) | Software issuer, policy/key preparation, offline ceremony examples and recovery recipes | Software mechanisms supplied; approved packages, manual ceremonies/token activation and live acceptance still required; HSM/ACME variants need integration |
| [4: Kubernetes](../deployment/stage-4-kubernetes/README.md) | Tier 0 node provisioning, native image-access inputs and Kubernetes bootstrap | Independent API endpoint must exist; add-ons and node/API audit forwarding are not supplied |
| [5: Identity](../deployment/stage-5-identity/README.md) | FreeIPA pair and phased directory recipe | Keycloak manifests, database/TLS/federation integration and live acceptance remain project work |
| [6: Secrets](../deployment/stage-6-secrets/README.md) | Cluster application directories; working Vault VM alternative | Cluster Vault, NetBox, Headlamp and independent monitoring need product configuration/installers |
| [7: Delivery](../deployment/stage-7-delivery/README.md) | Tier 1 cluster lifecycle, source-control/runner VM options and Tier 2 edge | Cluster delivery products, registry and protected Tier 0 runner/authorization remain integration |
| [8: Observability](../deployment/stage-8-observability/README.md) | Cluster integration directory; VM alternative supplies OS baseline | Netdata, Collector, VictoriaMetrics, Data Prepper, OpenSearch, UIs, infrastructure collectors and access/export policies need installers/configuration |
| [9: Workloads](../deployment/stage-9-workloads/README.md) | Tier 2 VM/cluster lifecycle and opt-in public HTTPS | Application manifests, policies, instrumentation and live acceptance remain project work |

The first missing main-path application installation is in **Stage 4, Step 2**.
The independent API endpoint is an earlier explicit prerequisite, not something
the cluster root creates. VM creation or a successful empty Kustomize build does
not install the service drawn inside a project-integration boundary.

## Detailed coverage

| Stage | Capability | Repository support |
| --- | --- | --- |
| Foundation | Proxmox, physical network, optional HA/SDN, firewall | Operator procedures; no complete host/network installer |
| Foundation | Approved VM templates | Tier 0 publication root and local/CD commands; shared consumer references |
| 1 | Controlled proxy/cache | Tier 2 ordinary cache VMs, Squid/keepalived automation; independent bootstrap supply required; repository/registry and patch-rollout extensions remain separate integrations |
| 2 | Protected security logging | Tier 0 VM/disk root and isolated receiver; independent reviewed-CSR authority; Shared native Linux forwarding; Tier 0 NAS checkpoints, audited file views and independent restic backup recipes. Prepared storage, NAS-owned snapshots/access audit and live fault qualification remain prerequisites. Replicated intake, locked-storage enforcement and later search are separate integrations |
| 3 | Root/issuer trust and custody A/B | Tier 0 native runtime, pinned software policy builder, explicit encrypted-key/CSR recipe, offline clca examples, CLI/CRL scheduling and encrypted backup/clean-target restore recipes; package/runtime qualification, ceremonies, token activation, audit forwarding and live acceptance remain required; HSM and internal ACME are separate integrations |
| 3 | C: Replicated USB services | Capacity-sized Tier 0 VM pool/baseline; two-host starter and opt-in backend scaffold. Application HA, devices, keys, readiness and VIP runtime remain operator integration |
| 3 | D: Network HSM | Vendor appliance/client integration guide; no appliance installer or generic HA role |
| 5 | Directory authority | Tier 0 foundation VM pair and FreeIPA CSR/pause/completion recipe with explicit CA replica; offline signing, chain checks and live replica/failure acceptance remain operator work |
| 5 | Identity federation / OIDC | Tier 0 Keycloak application starter; manifests, database/TLS integration, roles and live acceptance remain project work |
| 4/7/9 | Independent cluster nodes/bootstrap | Each tier owns a Kubernetes Terraform root, currently Talos; compact three-control-plane examples, native proxy/DNS/time/mirror patches and optional pool labels; no autoscaler |
| 4/5/6 | Cluster add-ons and control services | Tier-owned cluster starters; application manifests and service integration remain project work |
| 6 | Dedicated secret-service VM | Tier 0 Vault root/role; Shamir reference; no automatic Transit/PKCS#11 migration |
| 6 | Independent monitoring | Tier 0 critical health and external alerts remain project integration outside the observed cluster |
| 7 | Delivery controller | Tier 0 uses Flux; Tier 1 Argo CD/Spinnaker are unselected design options, not supplied installers |
| 7 | Source control and general runners | Tier 1 setups and deployment recipes; registry/mirror variants need project integration |
| 7/9 | Public edge | Tier 2 HAProxy/keepalived plus opt-in native HTTP-01, staging/production separation, verified origin TLS and controller renewal timer; real domain, SELinux/network behavior, failover/renewal and independent alert acceptance remain operator work |
| 7 | Image lifecycle | Tier 0 image builders/publication; Tier 1 general build runner where selected |
| 7/9 | Protected infrastructure runner and bounded request controller | [Design contract](../architecture/compute/provisioning.md), not supplied as a complete controller |
| 8 | Observability | Tier 1 Kubernetes design includes Netdata and OpenSearch initially; Proxmox/BMC collection stays Tier 0. Product manifests, infrastructure collectors and access/export policy remain project integration |
| 8 alternative | Dedicated observability VM alternative | Separate Tier 1 gateway, metrics and search hosts/baseline; no product installer |
| 9 | Workload collection | Tier-local instrumentation and collection integrate with the existing Tier 0 evidence and Tier 1 Observability interfaces |

Existing services can satisfy the same interface contract. A successful Terraform
apply proves resource provisioning, not the acceptance of every service drawn in
the architecture. Ansible maintenance reuses only supported operations.

<a id="purpose"></a>
<a id="recommended-order"></a>
<a id="path-guides"></a>
<a id="related-docs"></a>
