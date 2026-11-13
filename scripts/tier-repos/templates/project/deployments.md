# ${prefix} Deployment Checklist

Check `- [x]` after completing the linked deployment path. Strike through unselected options with `~~text~~`.
After Terraform-only, note **VMs ready; configuration pending** until Ansible/service setup is complete.
Link acceptance evidence from the [platform record](docs/README.md).

## Contents

[Foundation](#foundation) · [Software Intake](#1-software-intake) · [Logging](#2-protected-logging) ·
[Trust](#3-trust) · [Kubernetes](#4-kubernetes) · [Identity](#5-identity) · [Secrets](#6-secrets) ·
[Delivery](#7-delivery) · [Observability](#8-observability) · [Development](#9-development-platform) ·
[Lab Environments](#10-lab-environments)

## Foundation

Run from [Tier 0](../${repo_prefix}-tier-0/README.md); hardware and bootstrap preparation are manual.

- [ ] Hosts, networks and storage prepared — [Foundation](docs/auto-docs/03-deployment/foundation/README.md).
  - [ ] **Option:** native cluster HA/rebalancing — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/step-1b-cluster-ha.md).
  - [ ] **Option:** SDN applied on the hosts — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/step-1c-sdn.md).
- [ ] Bootstrap VM, tooling and API trust ready — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/README.md).
  - [ ] Workspace 3a: separate data filesystem — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3a-bootstrap-storage.md).
  - [ ] **Alternative 3b:** expanded LVM root — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md).
  - [ ] **Option 3c:** home on the data disk — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md).
  - [ ] Acquisition 5a: connected tooling — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/README.md#step-5-select-tool-acquisition).
  - [ ] **Alternative 5b:** offline bundle — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
- [ ] Hosts registered for Ansible management — [Guide](docs/auto-docs/05-operations/01-hosting/README.md).
- [ ] Templates adopted/published, clone-tested and recovery qualified — [Steps 4-10](docs/auto-docs/03-deployment/foundation/README.md#step-4-configure-the-template-catalog).
  - [ ] Selected HA/balancing qualified — [Step 10](docs/auto-docs/03-deployment/foundation/README.md#step-10-qualify-selected-ha-and-balancing).
  - [ ] **Alternative 10b:** ProxLB instead of native rebalancing — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/step-10b-proxlb.md).

## 1. Software Intake

Cache: [Tier 2](../${repo_prefix}-tier-2/README.md).
Bootstrap and host consumers: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Selected software-intake path accepted — [Stage 1 Software Intake](docs/auto-docs/03-deployment/stage-1-software-intake/README.md).
  - [ ] **Path 1a:** cache servers deployed — [Cache path](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#1a-create-the-proxycache-pair--main-path).
    - [ ] **Option 2b:** existing cache pair updated — [Update adoption](docs/auto-docs/03-deployment/stage-1-software-intake/step-2b-adopt-update.md).
    - [ ] **Option 7b:** Windows Update route validated — [Guide](docs/auto-docs/03-deployment/stage-1-software-intake/step-7b-windows-update.md).
    - [ ] **Option 8b:** Linux security profile applied — [Guide](docs/auto-docs/05-operations/01-hosting/linux-security.md).
  - [ ] **Alternative 1b:** existing approved supply selected — [Existing supply](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#1b-use-existing-approved-supply).
- [ ] Bootstrap consumer configured — [Steps 10–13](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#step-10-configure-bootstrap-intake).
- [ ] Proxmox update access configured — [Steps 14–16](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#step-14-configure-proxmox-update-inputs).

## 2. Protected Logging

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Log host and guarded storage ready — [Steps 1–4](docs/auto-docs/03-deployment/stage-2-logging/README.md).
- [ ] Reviewed receiver/producer identities signed — [Steps 5–10](docs/auto-docs/03-deployment/stage-2-logging/README.md#step-5-configure-the-first-producer).
  - [ ] **Path 9a:** independent authority initialized, or **9b:** original authority reused.
- [ ] Receiver and first source verified; existing Linux coverage extended — [Steps 11–13](docs/auto-docs/03-deployment/stage-2-logging/README.md#step-11-install-the-receiver).
- [ ] Receiver topology selected — [Step 14](docs/auto-docs/03-deployment/stage-2-logging/README.md#step-14-select-the-receiver-topology).
  - [ ] **Path 14a:** single receiver retained, or **14b:** [redundant intake](docs/auto-docs/03-deployment/stage-2-logging/step-14b-redundant-intake.md) qualified.
- [ ] Retention configured — [Step 15](docs/auto-docs/03-deployment/stage-2-logging/README.md#step-15-protect-retained-records).
  - [ ] **Path 15a:** NAS checkpoints and independent backup configured — [NAS archive](docs/auto-docs/03-deployment/stage-2-logging/step-15a-nas-archive.md).
  - [ ] **Alternative or addition 15b:** retention-locked object archive — [Locked storage](docs/auto-docs/03-deployment/stage-2-logging/step-15b-retention-lock.md).
- [ ] Failure and independent restore accepted — [Step 16](docs/auto-docs/03-deployment/stage-2-logging/README.md#step-16-verify-recovery-and-record-completion).

## 3. Trust

Run from [Tier 0](../${repo_prefix}-tier-0/README.md); offline signing remains manual.

- [ ] Root custody established — [Steps 1-6](docs/auto-docs/03-deployment/stage-3-trust/README.md#step-1-prepare-issuer-and-key-custody).
  - [ ] Software custody selected — [Software PKI](docs/auto-docs/03-deployment/stage-3-trust/procedures/software-pki.md).
  - [ ] **Alternative:** USB HSM hosts and provider commissioned — [USB HSM](docs/auto-docs/03-deployment/stage-3-trust/step-1b-usb-hsm.md).
    - [ ] **Option:** restricted PKCS#11 remoting and every original key verified — [Native remoting](docs/auto-docs/03-deployment/stage-3-trust/procedures/pkcs11-remoting.md).
  - [ ] **Alternative:** network HSM integrated — [Network HSM](docs/auto-docs/03-deployment/stage-3-trust/step-1c-network-hsm.md).
  - [ ] **Alternative:** single USB HSM with offline backup — [Single USB](docs/auto-docs/03-deployment/stage-3-trust/step-1d-single-usb.md).
- [ ] Infrastructure issuer deployed and signed — [Steps 7-14](docs/auto-docs/03-deployment/stage-3-trust/README.md#step-7-provision-the-issuer-and-attached-storage).
- [ ] **Option 15a:** Proxmox API certificates moved to platform PKI — [Transition](docs/auto-docs/05-operations/01-hosting/proxmox-tls.md#step-2-adopt-the-platform-pki).
- [ ] **Option 15b:** verified intake deployed in [Tier 1](../${repo_prefix}-tier-1/README.md) — [Installer](docs/auto-docs/03-deployment/stage-3-trust/step-15b-verified-intake.md).
  - [ ] Consumers switched to selected accepted repositories — [Consumer guide](docs/auto-docs/03-deployment/stage-3-trust/step-15b-verified-consumers.md).

## 4. Kubernetes

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Control cluster deployed — [Steps 1-10](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-1-select-the-cluster-owner).
  - [ ] **Alternative:** existing IaC-managed cluster accepted — [Existing-cluster path](docs/auto-docs/03-deployment/stage-4-kubernetes/step-1b-existing-cluster.md).
  - [ ] **Option:** separate API endpoint VMs deployed — [API endpoint](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/api-endpoint.md).
- [ ] CNI and private networking installed — [Steps 11-13](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-11-configure-the-platform-target).
- [ ] Cluster logs forwarded to Tier 0 receivers — [Step 14](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-14-enroll-and-install-protected-node-collection).
- [ ] Live storage qualified — [Step 15](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-15-qualify-live-storage).
  - [ ] **Path 15a:** Ceph RBD CSI installed against the accepted pool — [Block CSI](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/basic-platform.md#8a-install-ceph-rbd-csi-against-existing-proxmoxceph-storage).
  - [ ] **Alternative 15b:** existing block CSI owner accepted — [Existing CSI](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/basic-platform.md#8b-accept-an-existing-csi-owner).
  - [ ] **Option 15c:** NFS CSI added for selected backup/shared-file claims — [File CSI](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/basic-platform.md#8c-install-nfs-csi-for-backupshared-file-claims).
- [ ] Flux, SOPS and remaining platform installed — [Steps 16-18](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-16-prepare-flux-and-bootstrap-secrets).
- [ ] Operation and independent recovery accepted — [Step 19](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md#step-19-accept-operation-and-recovery).

## 5. Identity

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Directory pair deployed — [Steps 1-11](docs/auto-docs/03-deployment/stage-5-identity/README.md#step-1-select-and-initialize-the-directory-path).
- [ ] Keycloak federation deployed — [Steps 12-20](docs/auto-docs/03-deployment/stage-5-identity/README.md#step-12-select-the-existing-cluster-and-identity-provider-inputs).
- [ ] Kubernetes API OIDC and independent certificate recovery verified — [Step 21](docs/auto-docs/03-deployment/stage-5-identity/README.md#step-21-roll-out-kubernetes-api-human-sso).
- [ ] Public CLI client and namespace RBAC accepted with real allowed/denied logins — [Steps 22-23](docs/auto-docs/03-deployment/stage-5-identity/README.md#step-22-commission-human-cli-login-and-namespace-access).
- [ ] Human SSO and administrative roles connected — [Steps 20-23](docs/auto-docs/03-deployment/stage-5-identity/README.md#step-20-accept-federation-audit-and-restoration).

## 6. Secrets

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Selected Vault placement, audit, SSO and independent recovery accepted — [Stage 6 Secrets](docs/auto-docs/03-deployment/stage-6-secrets/README.md).
  - [ ] **Path 1a:** cluster Vault deployed — [Cluster path](docs/auto-docs/03-deployment/stage-6-secrets/procedures/vault-kubernetes.md).
  - [ ] **Alternative 1b:** dedicated Vault VMs deployed — [VM path](docs/auto-docs/03-deployment/stage-6-secrets/step-1b-vault-vm.md).
  - [ ] **Option:** seal provider integrated — [Seal integration](docs/auto-docs/03-deployment/stage-6-secrets/step-1c-seal-integration.md).
- [ ] **Option 11b:** independent hardware signing API accepted — [OpenBao signing](docs/auto-docs/03-deployment/stage-6-secrets/step-11b-openbao.md).
- [ ] Independent monitoring host prepared — [Step 12](docs/auto-docs/03-deployment/stage-6-secrets/README.md#step-12-prepare-the-independent-monitoring-host).
- [ ] NetBox and control UI deployed — [Steps 13-19](docs/auto-docs/03-deployment/stage-6-secrets/README.md#step-13-configure-netbox-and-its-private-inputs).
- [ ] Independent critical monitoring configured — [Step 20](docs/auto-docs/03-deployment/stage-6-secrets/README.md#step-20-install-independent-monitoring-and-alerts).
  - [ ] Runtime selected: managed `mon-1` or accepted existing host — [Host preparation](docs/auto-docs/03-deployment/stage-6-secrets/procedures/independent-monitoring.md#step-1-prepare-the-monitoring-runtime).
- [ ] **Option 21b:** hardware-backed human authentication — [Hardware authentication](docs/auto-docs/03-deployment/stage-6-secrets/step-21b-hardware-authentication.md).

## 7. Delivery

Run from [Tier 1](../${repo_prefix}-tier-1/README.md); Flux remains in Tier 0.

- [ ] Platform cluster and add-ons deployed — [Step 1](docs/auto-docs/03-deployment/stage-7-delivery/README.md#step-1-create-or-accept-the-tier-1-runtime).
- [ ] Delivery controller installed; select one:
  - [ ] Argo CD — [Argo CD path](docs/auto-docs/03-deployment/stage-7-delivery/step-2a-argocd.md).
  - [ ] Spinnaker — [Spinnaker path](docs/auto-docs/03-deployment/stage-7-delivery/step-2b-spinnaker.md).
- [ ] Approved artifact source accepted; select one:
  - [ ] **Path 8a:** Harbor deployed — [Registry](docs/auto-docs/03-deployment/stage-7-delivery/procedures/registry.md#install-harbor).
  - [ ] **Alternative 8b:** existing registry accepted — [Registry choices](docs/auto-docs/03-deployment/stage-7-delivery/procedures/registry.md#select-the-procedure).
  - [ ] **Option 12a:** registry acceleration integrated and qualified — [Integration boundary](docs/auto-docs/03-deployment/stage-7-delivery/procedures/registry.md#select-the-procedure).
- [ ] **Option:** edge proxy deployed in [Tier 2](../${repo_prefix}-tier-2/README.md) — [Edge proxy](docs/auto-docs/03-deployment/stage-7-delivery/procedures/edge-proxy.md).

## 8. Observability

Platform: [Tier 1](../${repo_prefix}-tier-1/README.md).
Infrastructure collection and protected log originals: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Netdata, OpenTelemetry, VictoriaMetrics, OpenSearch and UIs installed — [Stage 8 Observability](docs/auto-docs/03-deployment/stage-8-observability/README.md).
  - [ ] **Path 1a:** Kubernetes stack and selected database backup commissioned — [Platform installation](docs/auto-docs/03-deployment/stage-8-observability/procedures/observability-platform.md).
  - [ ] **Alternative 1b:** dedicated observability VMs, products and recovery accepted — [VM option](docs/auto-docs/03-deployment/stage-8-observability/step-1b-dedicated-vms.md).
- [ ] Proxmox/BMC and host coverage connected — [Step 13](docs/auto-docs/03-deployment/stage-8-observability/step-13-infrastructure-monitoring.md).
- [ ] **Option 14b:** authorized protected-log projections connected — [Scoped search](docs/auto-docs/03-deployment/stage-8-observability/step-14b-protected-log-search.md).

## 9. Development Platform

Applications: [Tier 1](../${repo_prefix}-tier-1/README.md). Infrastructure executor: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] GitLab and SSO deployed — [Stage 9 Development Platform](docs/auto-docs/03-deployment/stage-9-development/README.md).
  - [ ] **Path 1a:** Kubernetes GitLab, data VMs, tenant object access and joint recovery accepted — [Data services](docs/auto-docs/03-deployment/stage-9-development/procedures/data-services.md).
  - [ ] **Alternative 1b:** source-control VM with its bundled data and encrypted backups — [VM path](docs/auto-docs/03-deployment/stage-9-development/step-1b-source-control-vm.md).
  - [ ] **Option 12b for 1a:** chart ownership transferred to the selected delivery controller — [Ownership](docs/auto-docs/03-deployment/stage-9-development/procedures/gitlab.md#delivery-ownership).
- [ ] General build execution accepted; select one:
  - [ ] **Path 14a:** Kubernetes runner and on-demand job pods configured — [Kubernetes runners](docs/auto-docs/03-deployment/stage-9-development/step-14a-kubernetes-runners.md).
  - [ ] **Alternative 14b:** Podman runner — [Podman path](docs/auto-docs/03-deployment/stage-9-development/step-14b-podman-runner.md).
- [ ] **Option 15b:** image-based Linux builder and rollback qualified — [Image path](docs/auto-docs/03-deployment/stage-9-development/step-15b-image-based-linux.md).
- [ ] Vault CI authorization configured — [Step 17](docs/auto-docs/03-deployment/stage-9-development/README.md#step-17-configure-exact-vault-job-authority).
- [ ] Infrastructure runner deployed — [Step 18](docs/auto-docs/03-deployment/stage-9-development/README.md#step-18-install-the-dedicated-infrastructure-runner).
- [ ] Direct-CI trust, Vault and original-state handover completed — [Step 20](docs/auto-docs/03-deployment/stage-9-development/README.md#step-20-transfer-original-state-and-enable-one-protected-writer).

## 10. Lab Environments

Run from [Tier 2](../${repo_prefix}-tier-2/README.md).

- [ ] Selected lab runtime deployed — [Stage 10 Lab Environments](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md).
  - [ ] Linux VM/LXC labs — [Linux path](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md#step-2a-linux-vmlxc-labs).
  - [ ] Isolated Kubernetes environments — [Cluster path](docs/auto-docs/03-deployment/stage-10-lab-environments/procedures/isolated-clusters.md).
  - [ ] **Option 2c:** separately implemented bounded dispatcher accepted — [Integration contract](docs/auto-docs/03-deployment/stage-10-lab-environments/procedures/isolated-clusters.md#step-3-introduce-bounded-automation).
- [ ] Selected application's access, update, rollback and restore accepted — [Stage 10, Step 3](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md#step-3-install-the-private-application).
  - [ ] Kubernetes application reference installed, when selected — [Application](docs/auto-docs/03-deployment/stage-10-lab-environments/step-3a-application.md).
  - [ ] **Option 4b:** public HTTPS exposed — [Public HTTPS](docs/auto-docs/03-deployment/stage-10-lab-environments/step-4b-public-https.md).
  - [ ] **Option 5b:** application telemetry connected — [Telemetry](docs/auto-docs/03-deployment/stage-10-lab-environments/step-5b-telemetry.md).
- [ ] Update, rollback and independent restore accepted — [Step 6](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md#step-6-rehearse-update-rollback-and-recovery).
