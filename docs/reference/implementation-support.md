# Implementation support

Design options describe valid arrangements, not automatic installer coverage.
[Six capability stages](../deployment/README.md) combine the selected procedures.

| Stage | Capability | Repository support |
| --- | --- | --- |
| 1 | Proxmox, physical network, optional HA/SDN, firewall | Operator procedures; no complete host/network installer |
| 1 | Approved VM templates | Tier 0 publication root and local/CD commands; shared consumer references |
| 1 | Optional software-supply cache | Tier 2 ordinary cache VMs, Squid/keepalived automation; independent bootstrap supply required |
| 2 | Root/issuer trust and custody A/B | Operator integration and product procedures; no complete CA or token installer |
| 2 | C: Replicated USB services | Capacity-sized Tier 0 VM pool/baseline; two-host starter and opt-in backend scaffold. Application HA, devices, keys, readiness and VIP runtime remain operator integration |
| 2 | D: Network HSM | Vendor appliance/client integration guide; no appliance installer or generic HA role |
| 3 | Directory authority | Tier 0 foundation VM pair and FreeIPA deployment recipe |
| 3/5/6 | Independent cluster nodes/bootstrap | Each tier owns a Kubernetes Terraform root, currently Talos; compact three-control-plane examples and optional pool labels; no autoscaler |
| 3/4 | Cluster add-ons and control services | Tier-owned cluster starters; application manifests and service integration remain project work |
| 4 | Dedicated secret-service VM | Tier 0 Vault root/role; Shamir reference; no automatic Transit/PKCS#11 migration |
| 4 | Telemetry VM pattern | Tier 1 observability hosts/baseline; collectors/backends need service automation |
| 5 | Delivery controller | Tier 0 uses Flux; Tier 1 Argo CD/Spinnaker are unselected design options, not supplied installers |
| 5 | Source control and general runners | Tier 1 setups and deployment recipes; registry/mirror variants need project integration |
| 5/6 | Public edge | Tier 2 edge VMs and HAProxy/keepalived recipes; clients are network references only |
| 5 | Image lifecycle | Tier 0 image builders/publication; Tier 1 general build runner where selected |
| 5/6 | Protected infrastructure runner and bounded request controller | [Design contract](../architecture/compute/provisioning.md), not supplied as a complete controller |

Existing services can satisfy the same interface contract. A successful Terraform
apply proves resource provisioning, not the acceptance of every service drawn in
the architecture. Ansible maintenance reuses only supported operations.

<a id="purpose"></a>
<a id="recommended-order"></a>
<a id="path-guides"></a>
<a id="related-docs"></a>
