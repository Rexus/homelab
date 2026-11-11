# Install the Tier 0 basic platform

Tier-local Ansible installs pinned Cilium, optional Ceph RBD or NFS CSI, cert-manager, Traefik,
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
every tier; `ceph_rbd` installs block CSI against the existing Proxmox/Ceph storage cluster.
Select NFS separately for backup/shared-file claims.

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

### 1. Append the Cilium node patch

The [Kubernetes root](../../../../tier-0/terraform/deployments/kubernetes/machines.tf)
merges the ordered `machine_config_patches` after its native base configuration.
For a **new Talos cluster using the v1.13 configuration schema**, add this entry
to **`<prefix>-tier-0/terraform/deployments/kubernetes/terraform.tfvars`**, preserving
existing proxy/mirror patches and the other entries in that list:

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

For an **existing externally managed cluster**, have its owner apply these native settings
through the original node IaC. Retain that lifecycle/state owner rather than adding a second writer.

Use the selected Talos release's schema; v1.14 introduces separate configuration
documents. Do not assume this patch applies unchanged to that schema. [1]
The supplied installer uses Kubernetes IPAM and KubePrism `localhost:7445`,
disables Cilium cgroup/BPF auto-mounting and excludes `SYS_MODULE`. [1]
Set `cluster_platform_talos_cilium_ready: true` only after checking every node's
configuration. The existing Terraform pod CIDR remains authoritative.

### Ceph RBD node preparation (when selected)

Before bootstrap, append this additional native patch to `machine_config_patches` in
**the cluster-owning tier's `terraform/deployments/kubernetes/terraform.tfvars`**.
Preserve the Cilium, logging and image-access patches. For an existing cluster, the original
node IaC owner applies the same settings through its existing lifecycle; the platform role
does not change Talos machine configuration. [11]

```hcl
machine_config_patches = [
  # Preserve the other patch entries here.
  <<-YAML
  machine:
    kernel:
      modules:
        - name: rbd
    kubelet:
      extraMounts:
        - destination: /var/lib/ceph-csi
          type: bind
          source: /var/lib/ceph-csi
          options: [bind, rshared, rw]
  YAML
]
```

Use the selected Talos schema (this example is v1.13); keep its normal kubelet root
`/var/lib/kubelet`. CSI mounts its plugin/pod directories with bidirectional propagation;
the extra bind exposes the writable `/var/lib/ceph-csi` log directory to kubelet. The chart
mounts that host directory at `/var/log/ceph` inside its containers and disables the
`/etc/selinux` host mount. It does not use a host package installer or SSH. [11, 12]

Qualify `rbd` kernel support, Ceph release/CRUSH compatibility and image features on **every
consumer node**. The supplied class uses kernel `rbd`, `ext4` and conservative `layering`;
it does not fall back to `rbd-nbd`. Additional supported features must satisfy their
dependencies and the selected kernel. Keep `provisioner.skipForceFlatten: false` so CSI
retains its flattening compatibility behavior. Set `cluster_platform_talos_ceph_rbd_ready: true`
only after the node owner applies and verifies this configuration. [12, 13]

### 2. Finish cluster bootstrap

Return to the selected lifecycle: [Terraform node preparation](talos-terraform.md#controlled-image-access)
or [existing owner’s node IaC](../step-1b-existing-cluster.md#generate-configuration).
Prepare the logging patches, bootstrap once and export credentials. If bootstrap is already complete,
retain that cluster/state and continue below; do not bootstrap again.
The API must be reachable; nodes and CoreDNS can remain unready until Cilium is
installed. The role checks for known conflicting CNI/proxy DaemonSets, but this
is not exhaustive detection or a supported live-CNI migration procedure.

<a id="configure"></a>

## Step 2: Configure local platform inputs

### 3. Create the local platform input file

Run from **`<prefix>-tier-0/`**, using the exported cluster credentials:

```bash
cp -n ansible/group_vars/cluster_platform.yml.example ansible/group_vars/cluster_platform.yml
export KUBECONFIG="${KUBECONFIG:-$PWD/secrets/talos/kubeconfig}"
```

Retain the kubeconfig exported by the selected cluster lifecycle. For an existing externally managed cluster in a new shell,
set `KUBECONFIG` to its existing `secrets/<cluster-name>/kubeconfig` before this block; the fallback
above is only the Terraform workflow's export path. Set `cluster_platform_kubeconfig` to that same file.

**Expected:** missing inputs copied; existing selections preserved. On **the execution host**, complete
the [control-node tooling](../../../08-reference/control-node-tooling.md) for the coordinated tier-local
collection/Python requirements and Helm. The role needs `kubernetes.core` with native `k8s_info`, `k8s`,
`helm` and `helm_template`, plus `kubernetes`, `PyYAML` and `jsonpatch` for apply. [2]

### 4. Set the cluster target and component inputs

Edit **`<prefix>-tier-0/ansible/group_vars/cluster_platform.yml`**, using the
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
| Live storage | Choose `ceph_rbd` to install native block CSI or `existing` to accept another owner's commissioned driver; complete the selected [persistence branch](#persistence) before consumers |
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

### 5. Render Cilium only

Run from **`<prefix>-tier-0/`**, before expecting ordinary cluster pods to work:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["cilium"]}' -e cluster_platform_action=render
```

Inspect **`<prefix>-tier-0/secrets/cluster-platform/`**: private `*-values.yml`,
`*-manifests.yml` including CRDs, and `*-before.yml` / `*-after.yml` where present.
Files are `0600`, directories `0700`; verify Windows ACLs on WSL. Render output can contain
chart-generated keys. Bootstrap credentials are not exported as plaintext manifests.
Rendering requires chart-repository access, but no cluster access. [2]

### 6. Install the reviewed Cilium release

Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["cilium"]}' -e cluster_platform_action=apply
```

### 7. Check networking before other components

Run from **`<prefix>-tier-0/`**:

```bash
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

**Expected:** intended nodes Ready and cluster DNS healthy. Resolve networking failures before continuing.

### 8. Connect protected logging and qualify storage

If not already completed through the stage overview, install and test
[protected collector enrollment/installation](security-logging.md#enroll-node-streams), then accept
the selected [live CSI/storage checks](#persistence). Retain existing enrollment/storage evidence;
do not reinstall an accepted collector or introduce another storage owner.

<a id="8a-prepare-flux-and-managed-bootstrap-secrets--main-path"></a>

### 9a. Prepare Flux and managed bootstrap Secrets — main path

This branch is for **Tier 0**. Tier 1/2 omit Flux: satisfy their own selected Secret prerequisites and
use the render/apply commands in 9b without performing its Tier 0 Flux-source preparation.

From **`<prefix>-tier-0/`**, complete [Flux Steps 1–3](flux-sops.md): publish the encrypted canary,
provide read-only source credentials and age keys, then render/review/apply the remaining platform.
Pass the private Secrets file explicitly to both commands as shown there. Return here for action 10.

<a id="8b-use-pre-existing-bootstrap-secrets--alternative"></a>

### 9b. Use pre-existing bootstrap Secrets — alternative

Use this branch instead of 9a's Secret creation when those Secrets already have a qualified owner.
Complete [Flux source preparation](flux-sops.md#prepare-the-source) and verify the
[required Secrets](flux-sops.md#provide-bootstrap-secrets) through that owner.
Keep `cluster_platform_manage_secrets: false` in **`<prefix>-tier-0/ansible/group_vars/cluster_platform.yml`**.

Render from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=render
```

Inspect all selected resources under **`<prefix>-tier-0/secrets/cluster-platform/`**, then apply
from **the same Tier 0 root**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=apply
```

Continue at action 10. For Tier 1/2, use that tier's selections; its inputs omit Flux.

<a id="9-verify-the-selected-platform"></a>

### 10. Verify the selected platform

Complete the persistence, certificate/ingress and database checks below and
[Flux acceptance](flux-sops.md#accept-reconciliation) for Tier 0. Return to
[Stage 4, Step 3](../README.md#step-3-verify-operation-and-recovery) for protected collection and recovery acceptance.

For another selected subset, change `cluster_platform_components` explicitly.
Prerequisites for omitted products must already be accepted.
The role delegates each release to `kubernetes_applications`, then waits for
that product before the next chart. Reruns converge selected releases; removing
a component from the list does not uninstall it. CRD upgrade/adoption and
transferring existing Helm releases need product-specific review.

## Persistence

| Selection | Required inputs and behavior |
| --- | --- |
| `ceph_rbd` | Existing initialized Ceph RBD pool/API, FSID/monitors and scoped Secret; installs the official `ceph-csi-rbd` chart and a non-default retained block class |
| `existing` | Named CSI class and `cluster_platform_existing_storage_accepted: true`; no driver/class mutation |
| `nfs` | Existing NAS address/export and `cluster_platform_nfs_prerequisites_accepted: true`; installs native NFS CSI and a non-default class |

### 8a. Install Ceph RBD CSI against existing Proxmox/Ceph storage

Select this branch when Ceph already exists but the Kubernetes RBD driver does not.
The storage operator retains Ceph monitors, OSDs, pool initialization/capacity, CephX grants
and recovery. The cluster-owning tier owns the CSI Helm release, Kubernetes Secret contract
and StorageClass. Shared supplies reusable execution only. No storage gateway, new Ceph
cluster, CephFS or object API is installed. Ceph RBD does not supply the S3 endpoint used by
object/WAL backups. [12, 13]

1. Obtain the existing cluster's FSID, monitor `host:port` endpoints and initialized RBD pool
   from its storage owner. That owner supplies a dedicated non-admin CephX user with
   `mon 'profile rbd'`, `osd 'profile rbd pool=<pool>'` and `mgr 'profile rbd pool=<pool>'`.
   Use `userID` without the `client.` prefix; never reuse Proxmox/admin credentials.
   Accept this existing pool/API interface with `cluster_platform_ceph_rbd_prerequisites_accepted: true`.
   Permit CSI provisioner and consumer nodes to reach monitors **and OSDs** through the accepted
   network policy; monitor access alone cannot establish data-plane access. [13]
2. Complete [Talos RBD preparation](#ceph-rbd-node-preparation-when-selected) through the node owner.
   In the tier-local `ansible/group_vars/cluster_platform.yml`, set provider `ceph_rbd`, the desired
   new `cluster_platform_storage_class`, `cluster_platform_ceph_rbd_fsid`, `cluster_platform_ceph_rbd_monitors`,
   `cluster_platform_ceph_rbd_pool`, `cluster_platform_ceph_rbd_user_id` and `cluster_platform_ceph_rbd_secret`
   inputs from the example, and list every consumer in `cluster_platform_expected_nodes`.
   The node acknowledgement is separate from the storage owner's acceptance.
3. Pin `cluster_platform_versions.storage` to an approved exact chart version. Set
   `cluster_platform_repositories.storage: https://ceph.github.io/csi-charts` (or its qualified mirror)
   and add that exact URL to `cluster_platform_approved_repositories`. Fill all six native image
   entries in `cluster_platform_values.storage` from the example with a qualified repository and
   `tag: v<version>@sha256:<64-hex-digest>`, then set `cluster_platform_ceph_rbd_images_approved: true`.
   This covers the CSI driver, registrar, provisioner, attacher, resizer and snapshotter;
   the chart uses the driver image in multiple containers. No default/canary images are accepted. [12]
4. Choose Secret ownership. With `cluster_platform_manage_secrets: false`, its existing controller
   must supply `ceph-csi-rbd/<cluster_platform_ceph_rbd_secret>` with nonempty `userID` and `userKey`.
   Alternatively, create and encrypt a private extra-vars file using the existing
   `cluster_platform_secrets` contract below. No credential goes in Helm values or rendered manifests.

For **the cluster-owning tier's private encrypted Secret input**, use this shape before encryption:

```yaml
cluster_platform_manage_secrets: true
cluster_platform_secrets:
  ceph-csi-rbd/csi-rbd-secret:
    userID: REPLACE_WITH_SCOPED_USER_ID
    userKey: REPLACE_WITH_CEPHX_KEY
```

The scope is explicit: managed mode owns every required Secret of the selected components.
For a full Tier 0 run, merge the required Flux/issuer Secrets into the same private map or use
their existing controller ownership. Keep this file outside version control and encrypt it
with `ansible-vault`; preserve its independent recovery owner.

Render just storage after Cilium, from **the cluster-owning tier root**. With managed Secrets,
also pass `-e @ansible/group_vars/cluster_platform_secrets.yml --ask-vault-pass` to **both** commands;
unattended execution uses the established Vault password/identity input.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["storage"]}' -e cluster_platform_action=render
```

Review `secrets/cluster-platform/ceph-csi-rbd-{values,manifests,after}.yml`: matching FSID/monitors/pool,
all container digests, `/var/lib/kubelet`, `/var/lib/ceph-csi`, Secret **references** only, and a
non-default `Retain` class. Then apply from **the same tier root**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e '{"cluster_platform_components":["storage"]}' -e cluster_platform_action=apply
```

The same entry point runs the complete selected platform in fixed order: Cilium, storage,
cert-manager, ingress, CloudNativePG, optional Barman Cloud, Flux. Configuration selects this
branch; no separate installer script is required. Native health gates wait for the provisioner,
node DaemonSet, `CSIDriver`, selected class and RBD registration on every expected `CSINode`
before database creation. Finish the [persistence acceptance](#persistence-acceptance), then
return to action 9a/9b. Existing storage and NFS branches rejoin there too.

### 8b. Accept an existing CSI owner

Keep provider `existing`, set the named accepted class and acknowledge its independently tested
ownership with `cluster_platform_existing_storage_accepted: true`. No storage chart pin, Ceph
credential or NFS input is required. The role checks its class and registered CSI driver on apply.
Complete the acceptance below before consumers; return to action 9a/9b.

### 8c. Install NFS CSI for backup/shared-file claims

Set provider `nfs`, a separate class name and the NFS chart pin/repository approval.
Fill `cluster_platform_nfs_server`, `cluster_platform_nfs_share` and `cluster_platform_nfs_mount_options`;
acknowledge the prepared export with `cluster_platform_nfs_prerequisites_accepted: true`.
Remove the Ceph-native `cluster_platform_values.storage` overrides and any Ceph repository override.
Render/review/apply the `storage` subset using 8a's commands; a separate selected-component run
preserves the previously installed RBD release and class. Restore the block-class selection before
creating databases or running the remaining full platform. Return to action 9a/9b after acceptance.

NFS CSI creates subdirectories in an existing export. It does not provision a
NAS, format disks, or establish backups. [3] Prepare node-to-NAS access,
NFSv4.1 support, export ownership/root-squash behavior and capacity. The CSI
namespace allows privileged workloads for native mounts; no Talos SSH tasks run.
The class and driver deletion policy retain data. No snapshot controller is
installed. A single NAS and one CSI controller are not an HA storage design.

### Persistence acceptance

The automated gate checks the class and registered CSI driver; installed drivers also gate
controller/node rollout. Before consumers, test a disposable claim, write/read
across pod recreation and node movement, and restore to an isolated claim.
Retained volumes need a separate reviewed reclamation procedure.
For RBD, verify `ReadWriteOnce` attachment, detach/reattach on another intended node and filesystem
expansion with the selected kernel and scoped grants. Record actual results separately from chart
rendering. The native chart includes a snapshotter sidecar, but this role does not install snapshot
CRDs, a snapshot controller or a VolumeSnapshotClass; snapshot/backup acceptance is separate. [12]

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

Confirm [Flux/SOPS reconciliation](flux-sops.md#accept-reconciliation) for Tier 0, then all selected
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
11. [Talos machine kernel modules and kubelet extra mounts](https://docs.siderolabs.com/talos/v1.13/reference/configuration/v1alpha1/config).
12. [Official Ceph RBD chart values](https://github.com/ceph/ceph-csi/blob/v3.17.1/charts/ceph-csi-rbd/values.yaml)
    and [node mount implementation](https://github.com/ceph/ceph-csi/blob/v3.17.1/charts/ceph-csi-rbd/templates/nodeplugin-daemonset.yaml).
13. [Ceph RBD Kubernetes integration and scoped client grants](https://docs.ceph.com/en/reef/rbd/rbd-kubernetes/).
