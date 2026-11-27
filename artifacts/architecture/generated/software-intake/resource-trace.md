# Software intake resource relationships

Generated from native model relationships. Platform elements are documented boundary contracts;
host counts, device identities and switch-port placement remain site-owned acceptance inputs.

| Consumer | Relationship | Provider / related element |
| --- | --- | --- |
| storage (`DISK-cache-1`) | Uses local storage: cache-1 | Local guest-disk service (`P-storage`) |
| storage (`DISK-cache-2`) | Uses local storage: cache-2 | Local guest-disk service (`P-storage`) |
| Logical fabric network (`P-fabric`) | Realized over | Physical switches and NICs (`P-switches`) |
| Guest network attachment (`P-network`) | Uses logical transport | Logical fabric network (`P-fabric`) |
| Guest network attachment (`P-network`) | P-network-provider | Proxmox virtualization (`P-virtualization`) |
| Physical servers (`P-servers`) | Physical attachment | Physical switches and NICs (`P-switches`) |
| Local guest-disk service (`P-storage`) | Backed by | Physical storage devices (`P-drives`) |
| Local guest-disk service (`P-storage`) | P-storage-provider | Proxmox virtualization (`P-virtualization`) |
| Logical storage network (`P-storage-network`) | Realized over when selected | Physical switches and NICs (`P-switches`) |
| Proxmox virtualization (`P-virtualization`) | Runs on | Physical servers (`P-servers`) |
| cache-1 (`VM-cache-1`) | Uses guest attachment: cache-1 | Guest network attachment (`P-network`) |
| cache-1 (`VM-cache-1`) | Uses virtual execution: cache-1 | Proxmox virtualization (`P-virtualization`) |
| cache-2 (`VM-cache-2`) | Uses guest attachment: cache-2 | Guest network attachment (`P-network`) |
| cache-2 (`VM-cache-2`) | Uses virtual execution: cache-2 | Proxmox virtualization (`P-virtualization`) |

## Follow the same model in both directions

The provider query follows declared dependencies, allocations and composition. The impact query
walks toward consumers and their scenarios; it is conservative review scope, not a failure simulation.

### Providers supporting the proxy contract

`CONTENT-cache-1`, `CONTENT-cache-2`, `DISK-cache-1`, `DISK-cache-2`, `IO-cache-1`, `IO-cache-2`, `L-Proxy`, `P-drives`, `P-fabric`, `P-network`, `P-servers`, `P-storage`, `P-switches`, `P-virtualization`, `R-Pair`, `RUN-cache-1`, `RUN-cache-2`, `VM-cache-1`, `VM-cache-2`

### Potential impact of changing the physical server contract

`ACT-client`, `ACT-intake`, `AN-admission`, `B-HTTP`, `B-HTTPS`, `DISK-cache-1`, `DISK-cache-2`, `F-admit`, `F-cache`, `F-http`, `F-tunnel`, `F-verify`, `H-accepted`, `H-allow`, `H-cache-choice`, `H-cache-rules`, `H-cached`, `H-check`, `H-client`, `H-delivery-choice`, `H-denied`, `H-deny`, `H-fetch`, `H-has-content`, `H-hit`, `H-integrity-choice`, `H-lookup`, `H-miss`, `H-no-content`, `H-origin`, `H-policy`, `H-proxy`, `H-rejected`, `H-request`, `H-response`, `H-source-choice`, `H-source-down`, `H-source-failure`, `H-source-ok`, `H-stop`, `H-trust-failed`, `H-trust-ok`, `H-unavailable`, `H-verify`, `L-Cache`, `L-Consumers`, `L-Proxy`, `L-context`, `P-context`, `P-network`, `P-servers`, `P-storage`, `P-virtualization`, `R-Consumers`, `R-Pair`, `R-VIP`, `RUN-cache-1`, `RUN-cache-2`, `RUN-cache-untrusted`, `RUN-denied`, `RUN-hit-offline`, `RUN-miss`, `RUN-source-failure`, `RUN-untrusted`, `S-allow`, `S-check`, `S-client`, `S-connect`, `S-denied`, `S-deny`, `S-established`, `S-fetch`, `S-open`, `S-policy`, `S-proxy`, `S-ready`, `S-response`, `S-verify`, `SC-http-cache-untrusted`, `SC-http-denied`, `SC-http-hit`, `SC-http-miss`, `SC-http-source-failure`, `SC-http-untrusted`, `SC-https`, `SC-https-denied`, `SYS-delivery`, `SYS-homelab`, `SYS-intake`, `SYS-intake-cache`, `SYS-intake-proxy`, `SYS-operations`, `SYS-platform`, `UC-clone`, `UC-supply`, `UC-update`, `VC-http-cache-untrusted`, `VC-http-denied`, `VC-http-hit`, `VC-http-miss`, `VC-http-source-failure`, `VC-http-untrusted`, `VC-https`, `VC-https-denied`, `VM-cache-1`, `VM-cache-2`, `X-HTTP`, `X-accepted`, `X-cache-rules`, `X-cached`, `X-check`, `X-denied`, `X-fetch`, `X-lookup`, `X-origin`, `X-rejected`, `X-request`, `X-response`, `X-source-failure`, `X-stop`, `X-unavailable`, `X-verify`

### Potential impact of changing the guest network attachment

`ACT-client`, `ACT-intake`, `AN-admission`, `B-HTTP`, `B-HTTPS`, `DISK-cache-1`, `DISK-cache-2`, `F-admit`, `F-cache`, `F-http`, `F-tunnel`, `F-verify`, `H-accepted`, `H-allow`, `H-cache-choice`, `H-cache-rules`, `H-cached`, `H-check`, `H-client`, `H-delivery-choice`, `H-denied`, `H-deny`, `H-fetch`, `H-has-content`, `H-hit`, `H-integrity-choice`, `H-lookup`, `H-miss`, `H-no-content`, `H-origin`, `H-policy`, `H-proxy`, `H-rejected`, `H-request`, `H-response`, `H-source-choice`, `H-source-down`, `H-source-failure`, `H-source-ok`, `H-stop`, `H-trust-failed`, `H-trust-ok`, `H-unavailable`, `H-verify`, `L-Cache`, `L-Consumers`, `L-Proxy`, `L-context`, `P-context`, `P-network`, `R-Consumers`, `R-Pair`, `R-VIP`, `RUN-cache-1`, `RUN-cache-2`, `RUN-cache-untrusted`, `RUN-denied`, `RUN-hit-offline`, `RUN-miss`, `RUN-source-failure`, `RUN-untrusted`, `S-allow`, `S-check`, `S-client`, `S-connect`, `S-denied`, `S-deny`, `S-established`, `S-fetch`, `S-open`, `S-policy`, `S-proxy`, `S-ready`, `S-response`, `S-verify`, `SC-http-cache-untrusted`, `SC-http-denied`, `SC-http-hit`, `SC-http-miss`, `SC-http-source-failure`, `SC-http-untrusted`, `SC-https`, `SC-https-denied`, `SYS-delivery`, `SYS-homelab`, `SYS-intake`, `SYS-intake-cache`, `SYS-intake-proxy`, `SYS-operations`, `SYS-platform`, `UC-clone`, `UC-supply`, `UC-update`, `VC-http-cache-untrusted`, `VC-http-denied`, `VC-http-hit`, `VC-http-miss`, `VC-http-source-failure`, `VC-http-untrusted`, `VC-https`, `VC-https-denied`, `VM-cache-1`, `VM-cache-2`, `X-HTTP`, `X-accepted`, `X-cache-rules`, `X-cached`, `X-check`, `X-denied`, `X-fetch`, `X-lookup`, `X-origin`, `X-rejected`, `X-request`, `X-response`, `X-source-failure`, `X-stop`, `X-unavailable`, `X-verify`

The optional logical storage network remains outside the selected local-cache dependency path.
A physical connection records attachment, not identical failure behavior in both directions.
