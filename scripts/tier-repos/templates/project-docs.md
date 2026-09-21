# ${prefix} Documentation

Project records describe this environment; auto-docs explain the reusable
design and tooling. Populate the project records before provisioning.

## Project records

| Start here | Purpose |
| --- | --- |
| [Naming conventions](naming-conventions.md) | VM names, Proxmox tags, VMID ranges, and VLAN conventions |
| [Project overview](owned/design/overview.md) | actual topology, owners, services, and design decisions |
| [Recovery runbook](owned/runbooks/recovery.md) | local recovery inputs, steps, and verification |

Add detailed decisions, services, tier records, and network policy under
`owned/`. Keep this index current as the project grows.

## Upstream reference

`auto-docs/` is refreshed from the upstream kit. Do not put local decisions
there; refresh preserves local edits but cannot update those edited files.

- [Guide index](auto-docs/README.md)
- [Architecture and zone view](auto-docs/architecture/overview.md)
- [Network placement](auto-docs/architecture/network.md)
- [Firewall policy](auto-docs/security/firewall-policy.md)
- [Deployment commands](auto-docs/reference/repository-scripts.md)
- [Refresh and ownership](auto-docs/reference/generated-repository-model.md#refresh-and-local-ownership)
