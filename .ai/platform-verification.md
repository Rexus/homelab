# Platform installation acceptance

All rows are **Not tested**. Native rendering and schema checks do not establish
service operation. Use disposable targets, a change window, independent backups
and the record format in [manual verification](operational-verification.md#use-this-list).
Record deployed revision, result, UTC time, evidence and reviewer privately.

## Prerequisites

- [ ] Independent cluster API endpoints, DHCP/DNS/time and accepted image intake work without later tiers.
- [ ] CSI behavior, node mounts, storage failure/recovery and backup target credentials are qualified.
- [ ] Selected release requests fit actual node allocatable resources, storage and the required
  failure headroom. The bootstrap-sized Tier 1 starter is expanded before the complete service stack.
- [ ] Private certificate SANs, chains, expiry/renewal and negative TLS cases pass for every caller.
- [ ] A qualified client-auth issuance profile/authority supplies logging and CNPG replication/backup
  identities; the default Stage 3 TLS-server profile is not used for these identities.
- [ ] The selected Kubernetes SSO path matches qualified Talos 1.13 configuration; initial OIDC
  test-client/token and RBAC access work before Headlamp. Talos 1.14 needs separate qualification.
- [ ] Observability has an independently qualified private authenticated gateway and failover path;
  NodePort listeners alone do not supply authentication, balancing or HA.
- [ ] Local credentials, original state, cluster secrets and restore tools exist outside hosted services.

## Capability Gates

| ID | Stage | Pass condition |
| --- | --- | --- |
| HOST-1 | Foundation | Key-only SSH, time, source-scoped host rules and audit survive reboot; required VRRP/ICMP/service traffic passes and unrelated sources are denied; console recovery works |
| BOOT-1 | Foundation Step 3 | A manual Linux clone or accepted workstation can generate/restore the collection, verify Proxmox TLS, stage approved artifacts and recover original local inputs/state without GitLab, Vault, FreeIPA or Kubernetes; independent recovery survives loss of the bootstrap VM and its host |
| BOOT-2 | Offline new-install test | With public egress denied, a matching verified bundle installs a fresh boot-1; empty tier state adopts the recreated manual template, publishes and boots qualified candidates, then installs cache guests from prepared local package sources. Retain old state separately and record exact revision, paths, failures and limits; this does not establish all-stage offline support or original-identity recovery |
| HA-1 | Foundation HA option | Native 9.2+ HA recovers the same VMID after tested host death/fencing, preserves affinity and data, and accepts a clean Terraform plan; constrained/no-quorum cases wait safely; rebalancing and returned-host behavior are measured separately |
| IMAGE-1 | Foundation | Approved UEFI raw/qcow2 imports boot disposable clones with correct EFI/storage/CPU and fixed Talos RAM; schematic agent, NoCloud static networking (or selected DHCP), native configuration and recovery are qualified; legacy BIOS inputs are not migrated implicitly |
| IMAGE-2 | Foundation adoption | Existing manual template/file IDs import into the original Tier 0 state without replacement/re-upload; reviewed hardware and optional DHCP CloudInit media match, post-adoption plan is clean, and a disposable clone boots; remote artifact SHA256 is independently verified |
| IMAGE-3 | Explicit boot-disk maintenance | Preview performs no writes; execution replaces only scsi0 at the same VMID, retains the old base volume and linked-clone access, records receipts and refreshes original state; a fresh clone boots and old-disk rollback is tested |
| API-1 | Before 4/7/10 | One private API VIP owner at a time, correct isolated backends, client denial and gateway/peer/link failure cases pass without public-edge or cluster dependencies |
| STORE-1 | Before storage consumers | Actual native file/object interface, transport, scoped access, capacity and required operations are qualified; no unsupported NAS feature is inferred |
| STORE-2 | Before backup acceptance | NAS/path/host loss and wrong/missing mounts fail closed; independent encrypted copies restore with retained keys, without silently writing to local fallback paths |
| STORE-3 | Guest data-volume deployments | Normal IaC creates the selected blank data filesystem and UUID mount; reboot/rerun preserves records, expanded disks grow without UUID changes, and a missing/wrong declared volume stops without formatting or OS-disk fallback; CA binds remain on the selected volume |
| K8S-1 | 4 | Expected nodes, cross-node CNI/DNS, selected NodePorts and retained PVCs survive the selected restart/failure cases |
| K8S-2 | 4 | Flux fetches only the approved commit; SOPS canary decrypts; source/key failure does not prune or bootstrap replacement resources |
| K8S-3 | 4 | Numbered Talos, Kubernetes API and container events reach the catalogued Tier 0 identity; receiver outage/replay stays within measured limits |
| K8S-4 | 4 | Original state/secrets plus etcd and data restore a clean target without reinitializing the old cluster identity |
| ID-1 | 5 | FreeIPA replication, Keycloak LDAP federation and allowed/denied groups work; deletion/offboarding removes access as specified |
| ID-2 | 5/6 | Kubernetes OIDC accepts only the configured audience/claims; Headlamp has exactly its namespace permissions, not cluster-admin |
| ID-3 | 5 | With IdP/directory unavailable, certificate-based break-glass API access and control-plane recovery still work |
| DB-1 | 5/6/8 | Live database stays on Proxmox/Ceph-backed storage; selected NAS full-copy or object/WAL backup restores a clean target within its declared RPO/RTO; file mode makes no PITR claim |
| DB-2 | 5/6/8 files option | NAS loss/full storage and wrong source/marker never publish a valid set; finite WAL sender timeout and source capacity are qualified; isolated recovery keeps NAS read-only and stages on new block storage |
| SEC-1 | 6 | Vault is manually initialized/unsealed, all expected voters join, scoped OIDC policies deny unrelated paths, and file/stdout audit reaches protected intake |
| SEC-2 | 6 | Vault snapshot plus independent unseal/recovery material restore the selected seal identity; NetBox media/database and Headlamp access recover coherently |
| SEC-3 | 6 | NetBox audited-change export is separately commissioned and tested; application stdout alone is not accepted as its full change history |
| MON-1 | 6/8 | Proxmox/BMC collection cannot mutate/power-cycle targets; missing sensors remain unknown and stale sources alert |
| MON-2 | 6/8 | Tier 1/SSO outage does not stop Tier 0 history, local administration, critical alerts or external dead-man notification |
| DEL-1 | 7 | Only accepted sources/destinations deploy; Tier 0 targets are denied; rollback, source outage and controller recovery are tested |
| DEL-2 | 7 | Registry SSO, push/pull scopes, signed/approved image policy and restore pass; bootstrap sources remain independently usable |
| DEL-3 | 7 option | Spinnaker preissued/issuer certificates, SQL migrations, Redis sessions, Fiat denial, restricted targets and independent backup restore pass; changed credentials never reinitialize existing data |
| OBS-1 | 8 | Gateways persist/replay queues, metrics receive both writes, and promotion selects a caught-up readable copy rather than merely a live process |
| OBS-2 | 8 | OpenSearch retains expected shard copies/quorum through a complete selected host loss; index recovery is measured |
| OBS-3 | 8 | Signed reader groups see only approved indices/views; forged scope, direct API writes and Tier 0 archive mutation are denied |
| OBS-4 | 8 | Independently backed-up state/configuration restores metrics, search and UIs; queue/storage exhaustion and certificate failures alert |
| CI-REF | 9 | Complete the [CI handover checks](operational-verification.md#4-development-platform-and-ci-handover), including changed-input rejection and configuration-only retry |
| LAB-1 | 10 | Private application HTTPS, quota, restricted pods, namespace reads and default-deny traffic work; other namespace Secrets/mutations are denied |
| LAB-2 | 10 | Application logs/metrics/traces reach their authenticated scope; collector restart/gateway outage meets measured replay/loss limits |
| LAB-3 | 10 | Approved update/rollback and first-app recovery work; lab destruction cannot select shared/Tier 0 resources |
| REL-1 | All | Changed/removed definitions, duplicate allocations and concurrent state writers are rejected or stopped by the reviewed plan/locking process; no example map is applied over a live deployment |
| REL-2 | All | Actual host, gateway and workload rules enforce allowed/denied IPv4/IPv6 paths; no administrative listener is exposed accidentally; independent console recovery works |
| REC-1 | Backup/recovery | Restore both bootstrap disks from independent backup without original hosts/SSO/CI; verify mounts, tools, current original state/inputs and newly accepted API trust before enabling one writer |
| REC-2 | VM/host recovery | Restore a failed VM and a non-HA host's guests; fence originals, validate selected data age/disks and reconcile same/new VMID mappings before apply; record measured RPO/RTO |
| REC-3 | Platform recovery | Recreate minimum Proxmox/network/live storage, reconnect independent backups, restore bootstrap and original service identities/data in dependency order; prove new backups without silently provisioning empty replacements |

## Integration Boundaries

The native Spinnaker path includes its product/dependency installation; custom
overlays remain optional. GitLab data-service recipes, native storage contracts, approved
security projections, NetBox audit and recovery transports are supplied mechanisms,
not live acceptance. NAS commissioning, application SDK instrumentation and
hardware-specific custody retain explicit contracts.
Automatic tenant allocation/expiry and a portal are not supplied by the operator
lab recipe. Record these as Not applicable only when the selected path does not use them.

Return to the [operator checklist](operator-walkthrough.md).
