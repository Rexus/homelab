# Platform installation acceptance

All rows are **Not tested**. Native rendering and schema checks do not establish
service operation. Use disposable targets, a change window, independent backups
and the record format in [manual verification](operational-verification.md#use-this-list).
Record deployed revision, result, UTC time, evidence and reviewer privately.

## Prerequisites

- [ ] Independent cluster API endpoints, DHCP/DNS/time and accepted image intake work without later tiers.
- [ ] CSI behavior, node mounts, storage failure/recovery and backup target credentials are qualified.
- [ ] Private certificate SANs, chains, expiry/renewal and negative TLS cases pass for every caller.
- [ ] Local credentials, original state, cluster secrets and restore tools exist outside hosted services.

## Capability Gates

| ID | Stage | Pass condition |
| --- | --- | --- |
| K8S-1 | 4 | Expected nodes, cross-node CNI/DNS, selected NodePorts and retained PVCs survive the selected restart/failure cases |
| K8S-2 | 4 | Flux fetches only the approved commit; SOPS canary decrypts; source/key failure does not prune or bootstrap replacement resources |
| K8S-3 | 4 | Numbered Talos, Kubernetes API and container events reach the catalogued Tier 0 identity; receiver outage/replay stays within measured limits |
| K8S-4 | 4 | Original state/secrets plus etcd and data restore a clean target without reinitializing the old cluster identity |
| ID-1 | 5 | FreeIPA replication, Keycloak LDAP federation and allowed/denied groups work; deletion/offboarding removes access as specified |
| ID-2 | 5/6 | Kubernetes OIDC accepts only the configured audience/claims; Headlamp has exactly its namespace permissions, not cluster-admin |
| ID-3 | 5 | With IdP/directory unavailable, certificate-based break-glass API access and control-plane recovery still work |
| DB-1 | 5/6/8 | Each database completes a WAL/base backup and clean-target point-in-time restore from its independent prefix/credentials |
| SEC-1 | 6 | Vault is manually initialized/unsealed, all expected voters join, scoped OIDC policies deny unrelated paths, and file/stdout audit reaches protected intake |
| SEC-2 | 6 | Vault snapshot plus independent unseal/recovery material restore the selected seal identity; NetBox media/database and Headlamp access recover coherently |
| SEC-3 | 6 | NetBox audited-change export is separately commissioned and tested; application stdout alone is not accepted as its full change history |
| MON-1 | 6/8 | Proxmox/BMC collection cannot mutate/power-cycle targets; missing sensors remain unknown and stale sources alert |
| MON-2 | 6/8 | Tier 1/SSO outage does not stop Tier 0 history, local administration, critical alerts or external dead-man notification |
| DEL-1 | 7 | Only accepted sources/destinations deploy; Tier 0 targets are denied; rollback, source outage and controller recovery are tested |
| DEL-2 | 7 | Registry SSO, push/pull scopes, signed/approved image policy and restore pass; bootstrap sources remain independently usable |
| OBS-1 | 8 | Gateways persist/replay queues, metrics receive both writes, and promotion selects a caught-up readable copy rather than merely a live process |
| OBS-2 | 8 | OpenSearch retains expected shard copies/quorum through a complete selected host loss; index recovery is measured |
| OBS-3 | 8 | Signed reader groups see only approved indices/views; forged scope, direct API writes and Tier 0 archive mutation are denied |
| OBS-4 | 8 | Independently backed-up state/configuration restores metrics, search and UIs; queue/storage exhaustion and certificate failures alert |
| CI-REF | 9 | Complete the [CI handover checks](operational-verification.md#4-development-platform-and-ci-handover), including changed-input rejection and configuration-only retry |
| LAB-1 | 10 | Private application HTTPS, quota, restricted pods, namespace reads and default-deny traffic work; other namespace Secrets/mutations are denied |
| LAB-2 | 10 | Application logs/metrics/traces reach their authenticated scope; collector restart/gateway outage meets measured replay/loss limits |
| LAB-3 | 10 | Approved update/rollback and first-app recovery work; lab destruction cannot select shared/Tier 0 resources |

## Integration Boundaries

Spinnaker requires a complete reviewed product overlay. External GitLab data
services, NAS commissioning, application SDK instrumentation, security-projection
export transport and hardware-specific custody retain explicit contracts.
Automatic tenant allocation/expiry and a portal are not supplied by the operator
lab recipe. Record these as Not applicable only when the selected path does not use them.

Return to the [operator checklist](operator-walkthrough.md).
