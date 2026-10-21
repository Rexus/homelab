# Implementation support

Design options describe valid arrangements, not automatic installer coverage.
[Foundation prerequisites](../deployment/foundation/README.md) precede the
[seven capability stages](../deployment/README.md).
The [repository map](../deployment/README.md#repository-locations) identifies the
working checkouts; Shared helpers do not own the tier deployments they execute.

| Stage | Capability | Repository support |
| --- | --- | --- |
| Foundation | Proxmox, physical network, optional HA/SDN, firewall | Operator procedures; no complete host/network installer |
| Foundation | Approved VM templates | Tier 0 publication root and local/CD commands; shared consumer references |
| 1 | Protected security logging | Tier 0 VM/disk root and isolated receiver; independent reviewed-CSR authority; Shared native Linux forwarding; Tier 0 NAS checkpoints, audited file views and independent restic backup recipes. Prepared storage, NAS-owned snapshots/access audit and live fault qualification remain prerequisites. Replicated intake, locked-storage enforcement and later search are separate integrations |
| Foundation option | Optional software-supply cache | Tier 2 ordinary cache VMs, Squid/keepalived automation; independent bootstrap supply required |
| 2 | Root/issuer trust and custody A/B | Tier 0 native runtime, pinned software policy builder, explicit encrypted-key/CSR recipe, offline clca examples, CLI/CRL scheduling and encrypted backup/clean-target restore recipes; package/runtime qualification, ceremonies, token activation, audit forwarding and live acceptance remain required; HSM and internal ACME are separate integrations |
| 2 | C: Replicated USB services | Capacity-sized Tier 0 VM pool/baseline; two-host starter and opt-in backend scaffold. Application HA, devices, keys, readiness and VIP runtime remain operator integration |
| 2 | D: Network HSM | Vendor appliance/client integration guide; no appliance installer or generic HA role |
| 3 | Directory authority | Tier 0 foundation VM pair and FreeIPA CSR/pause/completion recipe with explicit CA replica; offline signing, chain checks and live replica/failure acceptance remain operator work |
| 3 | Identity federation / OIDC | Tier 0 Keycloak application starter; manifests, database/TLS integration, roles and live acceptance remain project work |
| 3/5/7 | Independent cluster nodes/bootstrap | Each tier owns a Kubernetes Terraform root, currently Talos; compact three-control-plane examples and optional pool labels; no autoscaler |
| 3/4 | Cluster add-ons and control services | Tier-owned cluster starters; application manifests and service integration remain project work |
| 4 | Dedicated secret-service VM | Tier 0 Vault root/role; Shamir reference; no automatic Transit/PKCS#11 migration |
| 6 alternative | Dedicated observability VM alternative | Separate Tier 1 gateway, metrics and search hosts/baseline; no product installer |
| 4 | Independent monitoring | Tier 0 critical health and external alerts remain project integration outside the observed cluster |
| 6 | Observability | Separate Tier 1 Kubernetes workloads include OpenSearch initially; product manifests and access policy remain project integration |
| 7 | Workload collection | Tier-local instrumentation and collection integrate with the existing Tier 0 evidence and Tier 1 Observability interfaces |
| 5 | Delivery controller | Tier 0 uses Flux; Tier 1 Argo CD/Spinnaker are unselected design options, not supplied installers |
| 5 | Source control and general runners | Tier 1 setups and deployment recipes; registry/mirror variants need project integration |
| 5/7 | Public edge | Tier 2 HAProxy/keepalived plus opt-in native HTTP-01, staging/production separation, verified origin TLS and controller renewal timer; real domain, SELinux/network behavior, failover/renewal and independent alert acceptance remain operator work |
| 5 | Image lifecycle | Tier 0 image builders/publication; Tier 1 general build runner where selected |
| 5/7 | Protected infrastructure runner and bounded request controller | [Design contract](../architecture/compute/provisioning.md), not supplied as a complete controller |

Existing services can satisfy the same interface contract. A successful Terraform
apply proves resource provisioning, not the acceptance of every service drawn in
the architecture. Ansible maintenance reuses only supported operations.

<a id="purpose"></a>
<a id="recommended-order"></a>
<a id="path-guides"></a>
<a id="related-docs"></a>
