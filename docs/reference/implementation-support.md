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

**This is a staged installation, not a zero-touch appliance.** Native installers
and explicit commissioning contracts cover the selected capability paths below.
Offline tests do not accept a live installation, failover or full restore. Satisfy
each prerequisite before proceeding; empty manifests do not meet a stage gate.

| Stage | Supplied path | Commissioning, qualification and optional gaps |
| --- | --- | --- |
| [1: Software intake](../deployment/stage-1-software-intake/README.md) | Tier 2 Squid/keepalived pair and shared Linux consumer settings | Retained repository management and automatic patch rollout remain integration; live policy/failover acceptance required |
| [2: Logging](../deployment/stage-2-logging/README.md) | Receiver VM/disks, Linux senders, independent producer trust, NAS checkpoints and backup recipes | NAS/accounts/snapshots and source certificates require commissioning; device-native forwarding and live fault/restore evidence remain operator work |
| [3: Trust](../deployment/stage-3-trust/README.md) | Software issuer, policy/key preparation, offline ceremony examples and recovery recipes | Software mechanisms supplied; approved packages, manual ceremonies/token activation and live acceptance still required; HSM/ACME variants need integration |
| [4: Kubernetes](../deployment/stage-4-kubernetes/README.md) | Node bootstrap, reusable native CNI/CSI/TLS/ingress/database/Flux recipes, SOPS gates and protected cluster-source collection | Independent private API endpoint, qualified storage, approved Git/images and imported leaf certificates or qualified external enrollment; live audit/persistence/recovery tests |
| [5: Identity](../deployment/stage-5-identity/README.md) | FreeIPA pair, Keycloak/database installation, LDAP federation, clients and guarded Kubernetes OIDC rollout | Offline identity-CA signing, trusted leaf/replication credentials and permitted/denied SSO and replica recovery tests |
| [6: Secrets](../deployment/stage-6-secrets/README.md) | Cluster Vault, NetBox/database/cache, Headlamp and native SSO/RBAC; independent monitoring role; Vault VM alternative | Manual Vault initialization/unseal and independent recovery custody, qualified backups and monitoring host; live audit/restore/access tests |
| [7: Delivery](../deployment/stage-7-delivery/README.md) | Tier 1 cluster/platform, native Harbor, Argo CD or complete native Spinnaker with SQL/cache, optional Tier 2 edge | Explicit controller choice, scoped sources/targets, storage, TLS/SSO and independent backups; live migration, rollback and restore qualification |
| [8: Observability](../deployment/stage-8-observability/README.md) | Native Netdata, OTel gateways, VictoriaMetrics, Data Prepper, OpenSearch and UIs; Tier 0 infrastructure polling/export | Real failure-domain labels, capacity/CSI/kernel settings, scoped certificates and search roles, approved projections and live outage/denial/restore tests |
| [9: Development platform](../deployment/stage-9-development/README.md) | Native GitLab/runner charts, dedicated native data-service VMs and backups, Tier 0 runner VM/role, Vault JWT policies and saved-plan CI | Approved packages/images, scoped object-storage handoff, server-side runner protection and live SSO/CI/restore acceptance required |
| [10: Lab environments](../deployment/stage-10-lab-environments/README.md) | Tier 2 VM/cluster/platform lifecycle, bounded application/RBAC/quota/policy recipe, scoped OTel collection and opt-in public HTTPS | Approved application image/SDK, DNS/TLS and live boundary/restore tests; automatic tenant allocation, expiry and a portal remain separate integrations |

The independent cluster API endpoint and prepared storage are explicit prerequisites,
not resources silently created by the cluster root. Tier 0 supplies an optional separate
[API gateway](../deployment/stage-4-kubernetes/procedures/api-endpoint.md) setup;
existing qualified services remain valid. [Storage prerequisites](../deployment/foundation/storage/README.md)
use existing native interfaces, not an added gateway. Product installers live in
the owning tier's Ansible recipes; Shared supplies reusable execution. Owned
`clusters/` directories remain optional GitOps adoption points, not duplicate installers.
Retain one values/resource owner when transferring a release to a delivery controller.

## Detailed coverage

| Stage | Capability | Repository support |
| --- | --- | --- |
| Foundation | Proxmox, physical network, optional HA/SDN, firewall | Operator procedures; no complete host/network installer |
| Foundation | Approved VM templates | Tier 0 publication root and local/CD commands; shared consumer references |
| Foundation | Linux host controls | Shared native SSH/chrony/firewalld/audit role with tier-local guarded recipes and site-owned allowlists; no universal egress or appliance installer |
| Foundation | Storage interfaces | Commissioned NAS/file storage and existing S3-compatible endpoints where required by consumers; qualification and handoff contracts only. No storage gateway/NAS/RGW installer or inferred HA/WORM |
| 1 | Controlled proxy/cache | Tier 2 ordinary cache VMs, Squid/keepalived automation; independent bootstrap supply required; repository/registry and patch-rollout extensions remain separate integrations |
| 2 | Protected security logging | Tier 0 VM/disk root and isolated receiver; independent reviewed-CSR authority; Shared native Linux forwarding; Tier 0 NAS checkpoints, audited file views and independent restic backup recipes. Approved field-copy publication and scoped mTLS push feed later search without original-archive access. Prepared storage, NAS-owned snapshots/access audit and live fault qualification remain prerequisites; replicated intake and locked-storage enforcement remain separate variants |
| 3 | Root/issuer trust and custody A/B | Tier 0 native runtime, pinned software policy builder, explicit encrypted-key/CSR recipe, offline clca examples, CLI/CRL scheduling and encrypted backup/clean-target restore recipes; package/runtime qualification, ceremonies, token activation, audit forwarding and live acceptance remain required; HSM and internal ACME are separate integrations |
| 3 | C: Replicated USB services | Capacity-sized Tier 0 VM pool/baseline; two-host starter and opt-in backend scaffold. Application HA, devices, keys, readiness and VIP runtime remain operator integration |
| 3 | D: Network HSM | Vendor appliance/client integration guide; no appliance installer or generic HA role |
| 5 | Directory authority | Tier 0 foundation VM pair and FreeIPA CSR/pause/completion recipe with explicit CA replica; offline signing, chain checks and live replica/failure acceptance remain operator work |
| 5 | Identity federation / OIDC | Tier 0 native Keycloak/database release, FreeIPA LDAP integration, consumer clients and serial Talos 1.13 API OIDC rollout from tier-owned plans; secret/certificate custody and live acceptance remain operational work |
| 4/7/10 | Independent cluster nodes/bootstrap | Each tier owns a Kubernetes Terraform root, currently Talos; compact three-control-plane examples, explicit UEFI/network-only static NoCloud, native proxy/DNS/time/mirror patches and optional pool labels; no autoscaler |
| 4/7/10 | Private API gateways | Tier 0 separate `cluster-endpoint` VM pair with native HAProxy/Keepalived and per-cluster VIP/backend inputs; no public edge dependency, TLS termination, quorum or fencing claim |
| 4/5/6 | Cluster add-ons and control services | Tier-owned platform/application recipes and inputs; Shared native chart execution and product gates. Empty GitOps starters are not the executing path |
| 6 | Dedicated secret-service VM | Tier 0 Vault root/role; Shamir reference; no automatic Transit/PKCS#11 migration |
| 6 | Independent monitoring | Tier 0 native Netdata, scoped Proxmox/Redfish polling and independent alerts on an explicitly prepared host outside observed clusters |
| 6 | Audit and recovery transport | Tier 0 GET-only retained NetBox change collection plus native Vault snapshot authentication, encrypted original-input/media copies and product-specific clean-target recovery procedures; independently commissioned source shares, destinations and keys required |
| 7 | Delivery controller | Tier 0 Flux/SOPS bootstrap; Tier 1 explicitly selects native Argo CD or native Spinnaker with eight services, SQL/Redis, certificates, scoped targets, SSO and backup jobs. Custom reviewed Spinnaker overlays remain an alternative; neither controller receives Tier 0 credentials |
| 9 | Source control and general runners | Tier 1 native Helm role renders/applies pinned official charts; separate `development-data` VMs install matching GitLab package roles for PostgreSQL/Redis/Gitaly with tenant object-storage handoff and backups. Protected Secrets and qualified hosting remain required; `development` retains the standalone VM alternative and its original state |
| 7/10 | Public edge | Tier 2 HAProxy/keepalived plus opt-in native HTTP-01, staging/production separation, verified origin TLS and controller renewal timer; real domain, SELinux/network behavior, failover/renewal and independent alert acceptance remain operator work |
| 9 option | Image lifecycle | Tier 0 image builders/publication; Tier 1 general build runner where selected |
| 9 | Trusted infrastructure CI | Tier 0 runner installation, native Vault JWT/policy root and manual saved-plan pipeline; explicitly trusts GitLab/hosting administrators. Live denial, state continuity and recovery qualification required |
| 10 | Bounded workload requests | [Design contract](../architecture/compute/provisioning.md) and profile examples; no allocator, portal or complete request controller |
| 8 | Observability | Tier 1 native Kubernetes releases include Netdata and OpenSearch initially; Tier 0 owns infrastructure collectors, private credentials and approved metric projections. Native values and policy bootstrap accompany the installer |
| 8 alternative | Dedicated observability VM alternative | Separate Tier 1 gateway, metrics and search hosts/baseline; no product installer |
| 10 | Workload collection | Tier 2 native scoped Collector with queue PVCs and distinct metrics/application client credentials; application-owned SDK instrumentation; security evidence follows the separate Tier 0 path |

Existing services can satisfy the same interface contract. A successful Terraform
apply proves resource provisioning, not the acceptance of every service drawn in
the architecture. Ansible maintenance reuses only supported operations.

<a id="purpose"></a>
<a id="recommended-order"></a>
<a id="path-guides"></a>
<a id="related-docs"></a>
