# Install the Tier 0 basic platform

Tier-local Ansible installs pinned Cilium, optional NFS CSI, cert-manager, Traefik,
CloudNativePG and Flux charts, with the Barman Cloud plugin as an object/WAL backup
option. Shared's reusable platform role executes the native
charts and health gates; Tier 0 owns selections, values and cluster resources. Rendering contacts chart
repositories but never the Kubernetes API. It is not an air-gapped chart cache.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** independent execution host and API access; completed Stage 1-3
or accepted equivalents; approved charts/images and bootstrap DNS/time. Apply
requires explicit cluster-admin kubeconfig/context. No directory, IdP, Vault,
Tier 1 GitLab/registry or other later-stage service is a bootstrap prerequisite.
The [Shared role](../../../../shared/ansible/roles/cluster_platform/tasks/main.yml)
is execution code, not another inventory, state owner or set of deployed services.
Traefik enables its namespace-scoped CRD provider for the verified upstream TLS
transports consumed by control applications; cross-namespace references stay disabled.
Tier 1 and Tier 2 supply the same `ansible/playbooks/deployment/cluster-platform.yml`
entry point and small tier-local examples. Run from that tier's repository root,
with its own kubeconfig and inventory. Their examples omit
Flux; Tier 1 selects its delivery controller in Stage 7. Existing CSI is valid in
every tier; select the documented NFS inputs when commissioning that driver instead.

## Table of contents

- [Step 1: Prepare Talos before bootstrap](#prepare-talos)
- [Step 2: Configure local platform inputs](#configure)
- [Step 3: Render, install CNI and complete the platform](#render-and-apply)
- [Persistence](#persistence)
- [Certificates and ingress](#certificates-and-ingress)
- [Database](#database)
- [Acceptance and recovery](#acceptance-and-recovery)
- [References](#references)

<a id="prepare-talos"></a>

## Step 1: Prepare Talos before bootstrap

The [Kubernetes root](../../../../tier-0/terraform/deployments/kubernetes/machines.tf)
merges the ordered `machine_config_patches` after its native base configuration.
For a **new Talos cluster using the v1.13 configuration schema**, add this entry
to that list in `terraform/deployments/kubernetes/terraform.tfvars`, preserving
existing proxy/mirror patches:

```hcl
machine_config_patches = [<<-YAML
  machine:
    features:
      kubePrism:
        enabled: true
        port: 7445
  cluster:
    network:
      cni:
        name: none
    proxy:
      disabled: true
  YAML
]
```

Use the selected Talos release's schema; v1.14 introduces separate configuration
documents. Do not assume this patch applies unchanged to that schema. [1]
The supplied installer uses Kubernetes IPAM and KubePrism `localhost:7445`,
disables Cilium cgroup/BPF auto-mounting and excludes `SYS_MODULE`. [1]
Set `cluster_platform_talos_cilium_ready: true` only after checking every node's
configuration. The existing Terraform pod CIDR remains authoritative.

Bootstrap and export credentials using the [Talos procedure](talos-terraform.md).
The API must be reachable; nodes and CoreDNS can remain unready until Cilium is
installed. The role checks for known conflicting CNI/proxy DaemonSets, but this
is not exhaustive detection or a supported live-CNI migration procedure.

<a id="configure"></a>

## Step 2: Configure local platform inputs

From the Tier 0 repository root, initialize local input files without overwriting:

```bash
# Run from <prefix>-tier-0/
cp -n ansible/group_vars/cluster_platform.yml.example ansible/group_vars/cluster_platform.yml
export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
```

Edit these files using the fields below:

```text
# Edit in <prefix>-tier-0/
ansible/group_vars/cluster_platform.yml
# Edit: Cluster context, selected components, chart/image pins, storage, network and DNS inputs.
```

Install the coordinated tier-local collection/Python requirements and Helm on
the execution host. The role needs `kubernetes.core` with native `k8s_info`, `k8s`,
`helm` and `helm_template`, plus `kubernetes`, `PyYAML` and `jsonpatch` for apply. [2]

Edit **`ansible/group_vars/cluster_platform.yml`**, using the
[example](../../../../tier-0/ansible/group_vars/cluster_platform.yml.example) as the field reference.
Examples fail closed until pins,
source approvals and prerequisites are supplied. Pass the local file explicitly
with `-e @...`; a `cluster_platform` inventory group is not needed for localhost.

| Input | Contract |
| --- | --- |
| `cluster_platform_components` | Subset of `cilium, storage, cert_manager, ingress, cloudnative_pg, barman_cloud, flux`; fixed dependency order |
| `cluster_platform_versions` | Exact selected chart versions without a leading `v`; no ranges or latest |
| `cluster_platform_repositories` | Optional per-component HTTPS repository overrides, including qualified private mirrors |
| `cluster_platform_approved_repositories` | Explicit list of accepted repository URLs; empty by default |
| `cluster_platform_values` | Per-component native chart value overrides; retain product names, CRDs and health-gate contracts |
| `cluster_platform_expected_nodes` | Actual inventory node names to gate after Cilium |
| `cluster_platform_kubeconfig`, `cluster_platform_context` | Explicit apply target; empty context uses the kubeconfig's selected context |
| `cluster_platform_output` | Private values/manifests directory, default `secrets/cluster-platform/` from the tier root |
| `cluster_platform_manage_secrets` | Default false; supplied Secrets must already exist when applying |

For the first Cilium run, set its exact chart pin/repository approval,
`cluster_platform_expected_nodes` and `cluster_platform_talos_cilium_ready: true`
after verifying Step 1. Complete the other selections before the full-platform run:

| Selection in the same local file | Required edit |
| --- | --- |
| Live storage | Keep `cluster_platform_storage_provider: existing`; set the commissioned block `cluster_platform_storage_class` and accept it only after the persistence tests below |
| Private ingress | Confirm `cluster_platform_ingress_class` and NodePorts against the private routing/firewall configuration |
| Flux/SOPS | Complete [Flux Steps 1-2](flux-sops.md#prepare-the-source): approved URL/commit/path, canary digest, read-only Git and age Secrets |
| Certificate enrollment | Keep issuer/probe inputs empty until a qualified external enrollment path exists; imported application leafs are an explicit alternative |
| Probe database | Leave `cluster_platform_database_enabled: false` unless intentionally creating the optional probe; application databases are created in later stages |

Approve both chart contents and their container image sources for the selected
Kubernetes/Talos versions. A chart pin fixes default image tags but does not
provide image signature verification or digest qualification. Supply reviewed
image/mirror overrides through native values and retain artifacts for recovery.

<a id="render-and-apply"></a>

## Step 3: Render, install CNI and complete the platform

1. From the Tier 0 root, render **Cilium only** before any ordinary cluster pods
   are expected to work:

   ```bash
   # Run from <prefix>-tier-0/
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["cilium"]}' -e cluster_platform_action=render
   ```

   Review private `*-values.yml`, `*-manifests.yml` (including CRDs), and
   `*-before.yml` / `*-after.yml` support resources where present. Files are mode
   `0600`, directories `0700`; verify Windows ACLs when using WSL. Render output can
   contain chart-generated keys. Bootstrap credentials are not exported as plaintext
   manifests. Repository access is required even though cluster access is not. [2]

2. After inspecting the rendered Cilium resources, install it and check readiness:

   ```bash
   # Run from <prefix>-tier-0/
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["cilium"]}' -e cluster_platform_action=apply
   kubectl get nodes -o wide
   kubectl get pods -n kube-system
   ```

3. Complete [Flux Steps 1-3](flux-sops.md), including the remaining platform render
   and apply commands. The main-path private Secrets file is passed explicitly on
   both runs; no directory change is required. If pre-existing Secrets already have
   a qualified owner, retain `cluster_platform_manage_secrets: false` and use:

   ```bash
   # Run from <prefix>-tier-0/
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=render
   ```

   Inspect all selected resources, then:

   ```bash
   # Run from <prefix>-tier-0/
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=apply
   ```

4. Complete the persistence, certificate/ingress and database checks below, then
   return to [Stage 4, Step 3](../README.md#step-3-verify-operation-and-recovery)
   for protected collection and recovery acceptance.

For another selected subset, change `cluster_platform_components` explicitly.
Prerequisites for omitted products must already be accepted.
The role delegates each release to `kubernetes_applications`, then waits for
that product before the next chart. Reruns converge selected releases; removing
a component from the list does not uninstall it. CRD upgrade/adoption and
transferring existing Helm releases need product-specific review.

## Persistence

| Selection | Required inputs and behavior |
| --- | --- |
| `existing` | Named CSI class and `cluster_platform_existing_storage_accepted: true`; no driver/class mutation |
| `nfs` | Existing NAS address/export and `cluster_platform_nfs_prerequisites_accepted: true`; installs native NFS CSI and a non-default class |

NFS CSI creates subdirectories in an existing export. It does not provision a
NAS, format disks, or establish backups. [3] Prepare node-to-NAS access,
NFSv4.1 support, export ownership/root-squash behavior and capacity. The CSI
namespace allows privileged workloads for native mounts; no Talos SSH tasks run.
The class and driver deletion policy retain data. No snapshot controller is
installed. A single NAS and one CSI controller are not an HA storage design.

The automated gate checks the class and registered CSI driver; NFS also gates
controller/node rollout. Before consumers, test a disposable claim, write/read
across pod recreation and node movement, and restore to an isolated claim.
Retained volumes need a separate reviewed reclamation procedure.

## Certificates and ingress

cert-manager installs its CRDs, controller, webhook and CA injector. Optional
`cluster_platform_issuer_spec` creates a native ClusterIssuer against an already
qualified issuer. List existing required Secrets as `{name, keys}` entries in
`cluster_platform_issuer_required_secrets`; these live in `cert-manager`.
Never place signing-root keys in this input. [4]

For certificate bootstrap before Vault, an **imported trusted leaf certificate**
and its matching leaf key are a valid explicit prerequisite. An independent
operator obtains the leaf from the accepted Stage 3 issuance procedure and
imports a native `kubernetes.io/tls` Secret (`tls.crt`, `tls.key`, and the required
chain) in the consuming application's namespace before enabling its TLS listener.
Record renewal and recovery ownership there. No CA private key enters the
cluster; this role rejects CA and self-signed ClusterIssuer specifications.
The installer does not issue/import Vault's leaf or install an OpenXPKI ACME
adapter. Keep those prerequisites explicit in the consumer's installation inputs.

The commented ACME example in the inputs uses the existing qualified Stage 3
adapter; installing cert-manager does not implement or approve that adapter.
Enable `cluster_platform_certificate_dns_names` for a retained issuance probe.
HTTP-01 requires reachable port 80 and matching DNS: install ingress first in
a selected-component run before enabling that probe. [5]

Traefik supplies an explicitly named, non-default ingress class and NodePorts
30080/30443 by default. Dashboard routes and the Gateway provider are disabled;
the Kubernetes CRD provider supports verified backend TLS through ServersTransport,
with cross-namespace references disabled.
Routing, private DNS and firewall admission remain external prerequisites; no
load balancer, address pool or public exposure is created. [6]
Verify a real application Ingress, intended client reachability and certificate
chain/renewal separately; deployment readiness alone cannot establish those.

## Database

CloudNativePG installs the operator/CRDs. Optional
`cluster_platform_database_enabled: true` creates a **new** `platform-db` Cluster
in `databases`, using the selected class and an explicitly approved PostgreSQL
image tag plus digest (for example `postgresql:17.6@sha256:<approved digest>`).
Retain the PostgreSQL major-version tag so the operator can detect its version. [9]
One instance is the example default; it carries no failover claim.
The operator initializes database/owner `app` and generates its credential
Secret; superuser access is disabled. [7]

Choose Proxmox/Ceph-backed block CSI storage qualified for live PostgreSQL durability,
permissions and latency. NAS backup/shared-file claims are separate; accepting NFS
for those claims does not select it for database data. [8]
The selected `barman_cloud` component installs the native Barman Cloud plugin
after cert-manager and CloudNativePG, including its service identity and ObjectStore
CRD. Application recipes own ObjectStore credentials, WAL schedules and destinations;
the optional probe database alone configures no backup. Leave this component
unselected for the scheduled file-backup path. [10]
The role waits for `Cluster` Ready; it does not restore existing database data.
Qualify a client connection, the selected backup/retention method and a clean-target restore
before placing control-service data here.

## Acceptance and recovery

Complete the [Flux/SOPS procedure](flux-sops.md), then all selected
[foundation gates](kubernetes.md#cluster-foundation). Record actual test results
in the project's deployment records. This installer and offline chart rendering
are not evidence of live deployment, HA, decryption or successful recovery.

Retain independent kubeconfig/context, Talos state/secrets, approved charts/images,
native values/resources, Git revision/credentials and age recovery keys outside
the cluster. Preserve etcd and persistent-data backups separately. Use the separate
[protected collection recipe](security-logging.md) for native node/API patches,
per-node collector identities and TLS forwarding. Accept actual source-to-intake
delivery before closing the Stage 4 security-event gate.

## References

Official APIs and values checked 2026-10-26; qualify against selected release pins.

1. [Talos Cilium requirements and configuration schemas](https://docs.siderolabs.com/kubernetes-guides/cni/deploying-cilium).
2. [Ansible Kubernetes collection](https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/).
3. [NFS CSI driver parameters](https://github.com/kubernetes-csi/csi-driver-nfs/blob/master/docs/driver-parameters.md).
4. [cert-manager Helm installation](https://cert-manager.io/docs/installation/helm/).
5. [cert-manager HTTP-01 solver](https://cert-manager.io/docs/configuration/acme/http01/).
6. [Traefik chart values](https://github.com/traefik/traefik-helm-chart/blob/master/traefik/values.yaml).
7. [CloudNativePG bootstrap](https://github.com/cloudnative-pg/cloudnative-pg/blob/main/docs/src/bootstrap.md).
8. [CloudNativePG storage qualification](https://github.com/cloudnative-pg/cloudnative-pg/blob/main/docs/src/storage.md).
9. [CloudNativePG image tag requirements](https://github.com/cloudnative-pg/cloudnative-pg/blob/main/docs/src/container_images.md).
10. [Barman Cloud plugin installation](https://cloudnative-pg.io/plugin-barman-cloud/docs/installation/).
