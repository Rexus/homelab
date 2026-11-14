# Implementation support

Design options describe valid arrangements, not automatic installer coverage.
[Software intake](../03-deployment/stage-01-software-intake/README.md) is a separate early
capability; it grows into retained repositories and OCI supply without becoming
a foundation prerequisite installer or a dependency on later Harbor deployment.
[Foundation prerequisites](../03-deployment/foundation/README.md) precede the
[numbered capability stages](../03-deployment/README.md).
The [repository map](../03-deployment/README.md#repository-locations) identifies the
working checkouts; Shared helpers do not own the tier deployments they execute.

## Contents

- [Stage coverage](#stage-coverage)
- [Detailed coverage](#detailed-coverage)
- [Tier 1 Flux evidence](#tier-1-flux-evidence)

<a id="first-six-stages"></a>

## Stage coverage

**This is a staged installation, not a zero-touch appliance.** Native installers
and explicit commissioning contracts cover the selected capability paths below.
Offline tests do not accept a live installation, failover or full restore. Satisfy
each prerequisite before proceeding; empty manifests do not meet a stage gate.

| Stage | Supplied path | Commissioning, qualification and optional gaps |
| --- | --- | --- |
| [1: Software intake](../03-deployment/stage-01-software-intake/README.md) | Tier 2 Squid/keepalived and bootstrap/host consumers | Independent initial supply, approved client/source policy and live proxy/takeover acceptance; Windows client configuration and acceptance are manual; verified publication is Stage 3 option 15b, OCI supply is Stage 7 |
| [2: Protected logging](../03-deployment/stage-02-logging/README.md) | Receiver VM/disks, Linux senders, independent producer trust, NAS checkpoints and backup recipes | NAS/accounts/snapshots and source certificates require commissioning; device-native forwarding and live fault/restore evidence remain operator work |
| [3: Cryptographic trust](../03-deployment/stage-03-trust/README.md) | Software issuer, native USB/provider profiles for YubiHSM 2 and PicoHSM, original-key issuer operations and optional restricted PKCS#11 remoting; option 15b installs verified publication | Physical/offline custody, approved middleware and original keys, matching recovery domains and live checks; application signing API is a separate Stage 6 option, ACME adapter qualification remains separate |
| [4: Kubernetes](../03-deployment/stage-04-kubernetes/README.md) | Node bootstrap, reusable native CNI/CSI/TLS/ingress/database/Flux recipes, SOPS gates and protected cluster-source collection | Independent private API endpoint, qualified storage, approved Git/images and imported leaf certificates or qualified external enrollment; live audit/persistence/recovery tests |
| [5: Identity](../03-deployment/stage-05-identity/README.md) | FreeIPA pair, Keycloak/database installation, LDAP federation, guarded API OIDC rollout, public PKCE CLI client and bounded namespace RBAC before Headlamp | Offline identity-CA signing, approved login executable, trusted leaf/replication credentials and real human login/denial, group removal and replica recovery tests |
| [6: Secrets](../03-deployment/stage-06-secrets/README.md) | Cluster or VM HashiCorp Vault, audit/OIDC, configurable seals, control tools/monitoring and independent backups; optional separate OpenBao external-key signing API | Protected initialization/unseal, independent key/state custody and live access/restore tests; native Vault PKCS#11 requires a qualified licensed artifact. OpenBao never migrates Vault; hardware/session failover needs separate qualification |
| [7: Delivery](../03-deployment/stage-07-delivery/README.md) | Independent Tier 1 Cilium/Flux bootstrap, native pinned service exports, Spinnaker/SQL/Redis lifecycle, Harbor, promotion pipeline/worker and external source maintenance; explicit Argo CD/direct alternatives | Separate sources/identities, real encrypted payloads and custody; live fresh install, adoption, approval bypass, migration, drift, upgrade and full recovery remain required |
| [8: Observability](../03-deployment/stage-08-observability/README.md) | Kubernetes or seven-VM native signal/query services and Netdata parents/agents; Tier 0 infrastructure polling/export remains separately owned | Qualified placement, capacity, storage/kernel settings, scoped certificates/search roles, private Netdata stream keys and administrator access; approved projections and live outage/denial/restore tests |
| [9: Development platform](../03-deployment/stage-09-development/README.md) | Native GitLab/runner charts and data-service VMs; standalone VM option with OIDC, encrypted scheduled backups and controller-driven initial access/recovery; Tier 0 runner/Vault CI | Qualified matching packages/images, scoped storage, approved identity clients and runner protection; live SSO, CI, state continuity and isolated restore acceptance |
| [10: Lab environments](../03-deployment/stage-10-lab-environments/README.md) | Tier 2 VM/cluster/platform lifecycle, bounded application/RBAC/quota/policy recipe, scoped OTel collection and opt-in public HTTPS | Approved application image/SDK, DNS/TLS and live boundary/restore tests; automatic tenant allocation, expiry and a portal remain separate integrations |

The independent cluster API endpoint and prepared storage are explicit prerequisites,
not resources silently created by the cluster root. Tier 0 supplies an optional separate
[API gateway](../03-deployment/stage-04-kubernetes/procedures/api-endpoint.md) setup;
existing qualified services remain valid. [Storage prerequisites](../03-deployment/foundation/storage/README.md)
use existing native interfaces, not an added gateway. Product configuration/renderers live in
the owning tier's Ansible recipes; Shared supplies reusable execution and Flux payload rendering.
Selected fresh Tier 1 Kubernetes services are installed by Flux from real exported payloads.
Other tiers' owned `clusters/` directories retain their stated integration scope; empty starters
are not installers.
For the VM deployments, Terraform attaches disks and Ansible prepares the guest filesystems/mounts;
intake, logging and the issuer reuse Shared's guarded data-volume role. NAS client mounts belong to
the consuming recipe; NAS-side exports, permissions, snapshots and independent backup custody
remain external storage prerequisites.
Retain one values/resource owner when transferring a release to a delivery controller.

## Detailed coverage

| Stage | Capability | Repository support |
| --- | --- | --- |
| Foundation | Proxmox, physical network, optional HA/SDN, firewall | Operator procedures; no complete host/network installer. Selected existing-guest HA resources and affinity rules have a [Tier 0 Ansible recipe](../05-operations/01-hosting/proxmox-ha.md); cluster membership, storage and fencing remain prerequisites |
| Foundation | Approved VM templates | Tier 0 publication root and local/CD commands; shared consumer references |
| 1 option 8b; reused later | Linux host controls | Shared native SSH/chrony/firewalld/audit role with tier-local guarded recipes and site-owned allowlists after the target service VMs exist; no universal egress or appliance installer |
| Foundation | Storage interfaces | Commissioned NAS/file storage and existing S3-compatible endpoints where required by consumers; qualification and handoff contracts only. No storage gateway/NAS/RGW installer or inferred HA/WORM |
| 1 | Controlled proxy/cache | Tier 2 ordinary cache VMs, Squid/keepalived with scoped ACLs, source-respecting cache policy, structured access events and native consumer verification defaults; independent bootstrap supply required |
| 3 option 15b | Verified repository/artifact supply | Tier 1 `intake` VM/disks after logging/issuer acceptance, managed blank-disk XFS/ext4 initialization, UUID mount and filesystem growth; native reposync/debmirror acquisition, copied-content verification, bounded ClamAV assessment, private quarantine/holds, read-only Nginx publication and serialized scheduling. Existing data is preserved; missing declared volumes fail. Supplied for EL10 and Debian-family hosts; current feature-compatible tools, definitions, TLS/keys and live acceptance required. No VM guest-filesystem scanner, OCI/Trivy installer, HA or patch rollout |
| 2 | Protected security logging | Tier 0 VM/disk root and isolated receiver; independent reviewed-CSR authority; Shared native Linux forwarding; Tier 0 NAS checkpoints, audited file views and independent restic backup recipes. Approved field-copy publication and scoped mTLS push feed later search without original-archive access. Guarded guest filesystem/UUID-mount preparation is supplied; NAS-owned snapshots/access audit and live fault qualification remain prerequisites. Replicated intake and locked-storage enforcement remain separate variants |
| 3 | Root/issuer trust and custody A/B | Tier 0 native runtime, pinned software policy builder, explicit encrypted-key/CSR recipe, offline clca examples, CLI/CRL scheduling and encrypted backup/clean-target restore recipes; package/runtime qualification, ceremonies, token activation, audit forwarding and live acceptance remain required; native HSM options are listed below, while internal ACME adapter qualification remains separate |
| 3 | C: USB provider pool | Tier 0 VMs/native USB attachment, YubiHSM 2 or PicoHSM middleware, original-key issuer binding; optional native p11-kit/SSH listeners and client modules, scoped source/key access, serial/SSH/SPKI pins and sign/verify checks. Device backup/replication and session failover are custody/application contracts, not automatic token clustering |
| 3 | D: Network HSM | Vendor appliance is an existing interface; selected client packages/configuration and provider inspection use the native provider role. Authenticated appliance commissioning and application HA remain product-specific |
| 5 | Directory authority | Tier 0 foundation VM pair and FreeIPA CSR/pause/completion recipe with explicit CA replica; offline signing, chain checks and live replica/failure acceptance remain operator work |
| 5 | Identity federation / OIDC | Tier 0 native Keycloak/database release, FreeIPA LDAP integration, consumer clients and serial Talos 1.13 API OIDC rollout from tier-owned plans; secret/certificate custody and live acceptance remain operational work |
| 4/7/10 | Independent cluster nodes/bootstrap | Each tier owns a Kubernetes Terraform root, currently Talos; compact three-control-plane examples, explicit UEFI/network-only static NoCloud, native proxy/DNS/time/mirror patches and optional pool labels; no autoscaler |
| 4/7/10 | Private API gateways | Tier 0 separate `cluster-endpoint` VM pair with native HAProxy/Keepalived and per-cluster VIP/backend inputs; no public edge dependency, TLS termination, quorum or fencing claim |
| 4/5/6 | Cluster add-ons and control services | Tier-owned platform/application recipes and inputs; Shared native chart execution and product gates. Empty GitOps starters are not the executing path |
| 6 | Dedicated secret-service VM | Tier 0 Vault root/role; controller API audit/OIDC; Shamir, configured Transit or qualified Enterprise PKCS#11; no automatic seal migration |
| 6 option 11b | Independent signing API | Separate named environment/state through the existing VM root; approved OpenBao/plugin artifacts, native HSM clients, Raft/TLS, audit/OIDC, original external-key mappings, exact certificate-auth signing policies and independent snapshots. Native RSA-PSS/P-256 software-token integration tested; actual Yubi/Pico mechanisms, three-member/device failover and recovery remain target acceptance |
| 6 | Independent monitoring | Optional Tier 0 VM provisioned through the original foundation root, or accepted existing host; native Netdata, scoped Proxmox/Redfish polling and independent alerts outside observed clusters |
| 6 | Audit and recovery transport | Tier 0 GET-only retained NetBox change collection plus native Vault snapshot authentication, encrypted original-input/media copies and product-specific clean-target recovery procedures; independently commissioned source shares, destinations and keys required |
| 7 | Delivery controller | Independent Tier 1 Flux owns selected Kubernetes services, including Flux and native Spinnaker; Spinnaker promotes separate application Git and observes read-only. Native TLS, SQL/Redis, schema, repository/backup and ingress phases remain required. Legacy Argo CD/direct Spinnaker and custom overlays retain explicit scope; no Tier 0 credentials |
| 9 | Source control and general runners | Tier 1 native Helm role renders/applies pinned official charts; separate `development-data` VMs install matching GitLab package roles for PostgreSQL/Redis/Gitaly with tenant object-storage handoff and backups. Protected Secrets and qualified hosting remain required; `development` retains the standalone VM alternative and its original state |
| 7/10 | Public edge | Tier 2 HAProxy/keepalived plus opt-in native HTTP-01, staging/production separation, verified origin TLS and controller renewal timer; real domain, SELinux/network behavior, failover/renewal and independent alert acceptance remain operator work |
| 9 option | Image lifecycle | Tier 0 native digest-pinned bootc-image-builder on a mutable builder, qcow2 verification/fetch and existing publisher catalog handoff; alternative existing bootc-native host switch/finalization. Approved source/product images, registry trust and live boot/rollback qualification remain required; general builds and registry commissioning are separate |
| 9 | Trusted infrastructure CI | Tier 0 runner installation, native Vault JWT/policy root and manual saved-plan pipeline; explicitly trusts GitLab/hosting administrators. Live denial, state continuity and recovery qualification required |
| 10 | Bounded workload requests | [Design contract](../01-architecture/04-hosting/02-provisioning.md) and profile examples; no allocator, portal or complete request controller |
| 8 | Observability | Tier 1 native Kubernetes releases include Netdata and OpenSearch initially; Tier 0 owns infrastructure collectors, private credentials and approved metric projections. Native values and policy bootstrap accompany the installer |
| 8 alternative | Dedicated observability VMs | Seven hosts with stable data disks and native Podman/systemd signal/query services and UIs. Netdata parents run on existing `otel-1/2`; the five metrics/search guests run children. Verified TLS, private child/peer stream keys, administrator-only diagnostics and one allowlisted native metric bridge are installed. Single Grafana SQLite instance; volatile Data Prepper buffers and live streaming/catch-up, backup and failure acceptance remain explicit |
| 10 | Workload collection | Tier 2 native scoped Collector with queue PVCs and distinct metrics/application client credentials; application-owned SDK instrumentation; security evidence follows the separate Tier 0 path |

Existing services can satisfy the same interface contract. A successful Terraform
apply proves resource provisioning, not the acceptance of every service drawn in
the architecture. Ansible maintenance reuses only supported operations.

## Tier 1 Flux evidence

[D-041](../07-decisions/README.md#d-041) accepts the ownership design. It does not establish a
working site. The [installation/adoption path](../03-deployment/stage-07-delivery/procedures/flux-platform.md)
and [live acceptance matrix](../03-deployment/stage-07-delivery/procedures/flux-platform.md#promotion-and-acceptance)
are the required operational handoff.

| Scope | Implementing owner / evidence boundary |
| --- | --- |
| Minimum bootstrap and self-management | Shared `cluster_platform`; exact bootstrap RBAC/canary, separately pinned platform source and matching `flux2` HelmRelease in platform-base; normal Ansible stops applying adopted releases |
| Service definitions | Existing delivery/observability/development native renderers plus Shared `flux_payload`; actual pinned HelmRelease/manifests, staged health and SOPS exports; later stages are opt-in |
| Node security collection | Shared `cluster_security_logging` retains Talos preparation and leaf validation; Tier 1 publishes retained per-node Helm identities through Flux with exact single-node readiness. Tier 0/2 keep their existing installer owners |
| Release orchestration | Tier 1 `delivery_promotion`, versioned pipeline and worker; stable API import, exact approved app change and relevant Flux/workload health; direct executor/API/Git/admin bypass limits are explicit |
| Platform change/recovery configuration | Shared `flux_maintenance` and Tier 1 recovery package tool; external accepted-revision inspection, candidate Git bundles/artifact checksums, guarded advancement and suspended application recovery |
| Data restoration | Native product procedures; maintenance/Flux do not restore PVC contents, reverse schema migrations or fence every restored external trigger automatically |
| Existing installations | Explicit stopped-writer adoption; preserve Helm identities, storage, Secrets and authored cluster/CI inputs; refresh does not migrate live owners |

Fresh bootstrap, adoption, denial attempts, drift correction, product/Flux upgrades, compatible rollback,
Spinnaker/GitLab/registry outages and complete independent recovery require live recorded evidence.
Rendering and source/generated tests establish only their tested contracts. Any service still using
Ansible in a selected Flux site must be recorded as a named transition exception with reason,
migration work and acceptance criteria. No transition exception is implicitly accepted as target completion.

<a id="purpose"></a>
<a id="recommended-order"></a>
<a id="path-guides"></a>
<a id="related-docs"></a>
