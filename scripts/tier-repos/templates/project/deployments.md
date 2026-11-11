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
  - [ ] **Option:** ProxLB instead of native rebalancing — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/step-4c-proxlb.md).
  - [ ] **Option:** SDN applied on the hosts — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/step-1c-sdn.md).
- [ ] Bootstrap VM, tooling and API trust ready — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/README.md).
  - [ ] Workspace 3a: separate data filesystem — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3a-bootstrap-storage.md).
  - [ ] **Alternative 3b:** expanded LVM root — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md).
  - [ ] **Option 3c:** home on the data disk — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md).
  - [ ] Acquisition 3d: connected tooling — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/README.md#2a-install-git-terraform-and-ansible).
  - [ ] **Alternative 3e:** offline bundle — [Guide](docs/auto-docs/03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
- [ ] Hosts registered for Ansible management — [Guide](docs/auto-docs/05-operations/hosts/management.md).
- [ ] Templates adopted/published and clone-tested — [Guide](docs/auto-docs/03-deployment/foundation/proxmox/templates.md).

## 1. Software Intake

Cache: [Tier 2](../${repo_prefix}-tier-2/README.md).
Bootstrap and host consumers: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Selected software-intake path accepted — [Stage 1 Software Intake](docs/auto-docs/03-deployment/stage-1-software-intake/README.md).
  - [ ] **Path 1a:** cache servers deployed — [Cache path](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#1a-create-the-proxycache-pair--main-path).
    - [ ] **Option 2b:** existing cache pair updated — [Update adoption](docs/auto-docs/03-deployment/stage-1-software-intake/step-2b-adopt-update.md).
    - [ ] **Option 3b:** Windows Update route validated — [Guide](docs/auto-docs/03-deployment/stage-1-software-intake/step-3b-windows-update.md).
    - [ ] **Option 4b:** Linux security profile applied — [Guide](docs/auto-docs/05-operations/hosts/linux-security.md).
  - [ ] **Alternative 1b:** existing approved supply selected — [Existing supply](docs/auto-docs/03-deployment/stage-1-software-intake/README.md#1b-use-existing-approved-supply--alternative).
- [ ] Bootstrap consumer configured — [Guide](docs/auto-docs/03-deployment/stage-1-software-intake/step-6-bootstrap-consumer.md).
- [ ] Proxmox update access configured — [Guide](docs/auto-docs/05-operations/hosts/update-access.md).

## 2. Protected Logging

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Independent logging authority and identities prepared — [Trust](docs/auto-docs/03-deployment/stage-2-logging/procedures/producer-trust.md).
- [ ] Log host and receiver deployed — [Stage 2 Protected Logging](docs/auto-docs/03-deployment/stage-2-logging/README.md).
- [ ] Producers connected — [Sources](docs/auto-docs/03-deployment/stage-2-logging/procedures/sources.md).
- [ ] NAS checkpoints and independent backup configured — [NAS archive](docs/auto-docs/03-deployment/stage-2-logging/step-3c-nas-archive.md).
  - [ ] **Alternative:** retention-locked object archive — [Locked storage](docs/auto-docs/03-deployment/stage-2-logging/step-3d-retention-lock.md).
- [ ] **Option:** second receiver deployed — [Redundant intake](docs/auto-docs/03-deployment/stage-2-logging/step-3b-redundant-intake.md).

## 3. Trust

Run from [Tier 0](../${repo_prefix}-tier-0/README.md); offline signing remains manual.

- [ ] Root custody established — [Stage 3 Trust](docs/auto-docs/03-deployment/stage-3-trust/README.md).
  - [ ] Software custody selected — [Software PKI](docs/auto-docs/03-deployment/stage-3-trust/procedures/software-pki.md).
  - [ ] **Alternative:** USB HSM hosts and provider commissioned — [USB HSM](docs/auto-docs/03-deployment/stage-3-trust/step-1b-usb-hsm.md).
  - [ ] **Alternative:** network HSM integrated — [Network HSM](docs/auto-docs/03-deployment/stage-3-trust/step-1c-network-hsm.md).
  - [ ] **Alternative:** single USB HSM with offline backup — [Single USB](docs/auto-docs/03-deployment/stage-3-trust/step-1d-single-usb.md).
- [ ] Infrastructure issuer deployed and signed — [Issuer](docs/auto-docs/03-deployment/stage-3-trust/procedures/issuer.md).
- [ ] **Option 3a:** Proxmox API certificates moved to platform PKI — [Transition](docs/auto-docs/05-operations/hosts/proxmox-tls.md#step-2-adopt-the-platform-pki).
- [ ] **Option 3b:** verified intake deployed in [Tier 1](../${repo_prefix}-tier-1/README.md) — [Installer](docs/auto-docs/03-deployment/stage-3-trust/step-3b-verified-intake.md).
  - [ ] Consumers switched to selected accepted repositories — [Consumer guide](docs/auto-docs/03-deployment/stage-3-trust/step-3b-verified-consumers.md).

## 4. Kubernetes

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Control cluster deployed — [Stage 4 Kubernetes](docs/auto-docs/03-deployment/stage-4-kubernetes/README.md).
  - [ ] **Alternative:** existing/manual cluster accepted — [Manual path](docs/auto-docs/03-deployment/stage-4-kubernetes/step-1b-manual-cluster.md).
  - [ ] **Option:** separate API endpoint VMs deployed — [API endpoint](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/api-endpoint.md).
- [ ] Base platform add-ons installed — [Basic platform](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/basic-platform.md).
- [ ] Flux and SOPS configured — [Flux/SOPS](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/flux-sops.md).
- [ ] Cluster logs forwarded to Tier 0 receivers — [Security logging](docs/auto-docs/03-deployment/stage-4-kubernetes/procedures/security-logging.md).

## 5. Identity

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Directory pair deployed — [Stage 5 Identity](docs/auto-docs/03-deployment/stage-5-identity/README.md).
- [ ] Keycloak federation deployed — [Keycloak](docs/auto-docs/03-deployment/stage-5-identity/procedures/keycloak.md).
- [ ] Human SSO and administrative roles connected — [Service SSO](docs/auto-docs/03-deployment/stage-5-identity/procedures/service-sso.md).

## 6. Secrets

Run from [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Cluster Vault deployed — [Stage 6 Secrets](docs/auto-docs/03-deployment/stage-6-secrets/README.md).
  - [ ] **Alternative:** dedicated Vault VMs deployed — [VM path](docs/auto-docs/03-deployment/stage-6-secrets/step-1b-vault-vm.md).
  - [ ] **Option:** seal provider integrated — [Seal integration](docs/auto-docs/03-deployment/stage-6-secrets/step-1c-seal-integration.md).
- [ ] NetBox and control UI deployed — [Control applications](docs/auto-docs/03-deployment/stage-6-secrets/procedures/control-applications.md).
- [ ] Independent critical monitoring configured — [Monitoring](docs/auto-docs/03-deployment/stage-6-secrets/procedures/independent-monitoring.md).
  - [ ] Runtime selected: managed `mon-1` or accepted existing host — [Host preparation](docs/auto-docs/03-deployment/stage-6-secrets/procedures/independent-monitoring.md#step-1-prepare-the-monitoring-runtime).
- [ ] **Option:** hardware-backed human authentication — [Hardware authentication](docs/auto-docs/03-deployment/stage-6-secrets/step-3b-hardware-authentication.md).

## 7. Delivery

Run from [Tier 1](../${repo_prefix}-tier-1/README.md); Flux remains in Tier 0.

- [ ] Platform cluster and add-ons deployed — [Stage 7 Delivery](docs/auto-docs/03-deployment/stage-7-delivery/README.md).
- [ ] Delivery controller installed; select one:
  - [ ] Argo CD — [Argo CD path](docs/auto-docs/03-deployment/stage-7-delivery/step-2a-argocd.md).
  - [ ] Spinnaker — [Spinnaker path](docs/auto-docs/03-deployment/stage-7-delivery/step-2b-spinnaker.md).
- [ ] Harbor deployed — [Registry](docs/auto-docs/03-deployment/stage-7-delivery/procedures/registry.md).
- [ ] **Option:** edge proxy deployed in [Tier 2](../${repo_prefix}-tier-2/README.md) — [Edge proxy](docs/auto-docs/03-deployment/stage-7-delivery/procedures/edge-proxy.md).

## 8. Observability

Platform: [Tier 1](../${repo_prefix}-tier-1/README.md).
Infrastructure collection and protected log originals: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Netdata, OpenTelemetry, VictoriaMetrics, OpenSearch and UIs installed — [Stage 8 Observability](docs/auto-docs/03-deployment/stage-8-observability/README.md).
- [ ] Proxmox/BMC and host coverage connected — [Infrastructure monitoring](docs/auto-docs/03-deployment/stage-8-observability/step-3-infrastructure-monitoring.md).
- [ ] **Option:** authorized protected-log projections connected — [Scoped search](docs/auto-docs/03-deployment/stage-8-observability/step-4b-protected-log-search.md).
- [ ] **Alternative:** dedicated VM baseline prepared; product installation remains separate — [VM option](docs/auto-docs/03-deployment/stage-8-observability/step-1b-dedicated-vms.md).

## 9. Development Platform

Applications: [Tier 1](../${repo_prefix}-tier-1/README.md). Infrastructure executor: [Tier 0](../${repo_prefix}-tier-0/README.md).

- [ ] Data services and backups configured — [Data services](docs/auto-docs/03-deployment/stage-9-development/procedures/data-services.md).
- [ ] GitLab and SSO deployed — [Stage 9 Development Platform](docs/auto-docs/03-deployment/stage-9-development/README.md).
  - [ ] **Alternative:** source-control VM — [VM path](docs/auto-docs/03-deployment/stage-9-development/step-1b-source-control-vm.md).
- [ ] Kubernetes runner and on-demand job pods configured — [Kubernetes runners](docs/auto-docs/03-deployment/stage-9-development/procedures/kubernetes-runners.md).
  - [ ] **Alternative:** Podman runner — [Podman path](docs/auto-docs/03-deployment/stage-9-development/step-2b-podman-runner.md).
  - [ ] **Option 2c:** image-based Linux builder — [Image path](docs/auto-docs/03-deployment/stage-9-development/step-2c-image-based-linux.md).
- [ ] Vault CI authorization configured — [Vault CI](docs/auto-docs/03-deployment/stage-9-development/procedures/vault-ci.md).
- [ ] Infrastructure runner deployed — [Protected executor](docs/auto-docs/03-deployment/stage-9-development/procedures/infrastructure-runner.md).
- [ ] Direct-CI trust, Vault and original-state handover completed — [Handover](docs/auto-docs/03-deployment/stage-9-development/procedures/handover.md).

## 10. Lab Environments

Run from [Tier 2](../${repo_prefix}-tier-2/README.md).

- [ ] Selected lab runtime deployed — [Stage 10 Lab Environments](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md).
  - [ ] Linux VM/LXC labs — [Linux path](docs/auto-docs/03-deployment/stage-10-lab-environments/README.md#step-2a-linux-vmlxc-labs).
  - [ ] Isolated Kubernetes environments — [Cluster path](docs/auto-docs/03-deployment/stage-10-lab-environments/procedures/isolated-clusters.md).
- [ ] Application deployed — [Application](docs/auto-docs/03-deployment/stage-10-lab-environments/step-3a-application.md).
  - [ ] **Option:** application telemetry connected — [Telemetry](docs/auto-docs/03-deployment/stage-10-lab-environments/step-3c-telemetry.md).
  - [ ] **Option:** public HTTPS exposed — [Public HTTPS](docs/auto-docs/03-deployment/stage-10-lab-environments/step-3b-public-https.md).
