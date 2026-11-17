# Deployment command cheat sheet

Choose the owning repository and changed inputs below; follow the linked guide for prerequisites and
acceptance. This is the command index for the [deployment catalog](../03-deployment/README.md#iac-capability-map)
and [recipe map](01-hosting/ansible-recipes.md#recipe-map).

**Order:** [Foundation](../03-deployment/foundation/README.md), then stages
**1 intake → 2 trust → 3 logging → 4 Kubernetes → 5 identity → 6 secrets → 7 delivery →
8 observability → 9 development → 10 lab environments**. Optional paths run only when selected.
Templates precede guests; API gateways precede their clusters. Stage numbers are not tier numbers.
Finish each selected stage's functional checks and [hardening checkpoint](01-hosting/guest-hardening.md#stage-checkpoint).

## Contents

- [Context and initialization](#context-and-initialization)
- [Offline Root CA](#offline-root-ca)
- [Linux setups](#linux-setups)
- [Templates, Kubernetes and Vault CI](#templates-kubernetes-and-vault-ci)
- [Boot-security commands](#boot-security-commands)
- [Native application recipes and GitOps](#native-application-recipes-and-gitops)
- [Selected subrecipes and optional paths](#selected-subrecipes-and-optional-paths)

## Context and initialization

**Run from the row's owning tier root:** `tier-0/`, `tier-1/` or `tier-2/` in a source checkout;
`<prefix>-tier-0/`, `<prefix>-tier-1/` or `<prefix>-tier-2/` in a generated collection.
Shared owns helpers/references, never inventory or state; Architecture owns records, not execution.
All paths are relative to that owner unless marked Shared. Replace `<...>` before copying commands.

For generated repositories only, run from **kit root**; existing fork users keep their tier roots:

```bash
bash scripts/init-tier-repos.sh
```

From **the owning tier root**, initialize missing Linux inputs; omit `--setup <setup>` for all
registered Linux setups. Native recipes with matching input examples also accept their recipe name here.
Template publication and Kubernetes use their dedicated `init` commands below.

```bash
bash scripts/init-local-files.sh --setup "<setup>"
```

Configure these common inputs once, then the row-specific files:

| Owner | Inputs |
| --- | --- |
| Each tier | `.env.local` (provider/SSH inputs), `terraform/common.tfvars`, `ansible/inventory/hosts.yml`, `ansible/group_vars/all.yml` |
| Shared | `config/platform.tfvars`, `config/guest-sizes.json`, `templates/proxmox-catalog.tfvars` |

New Linux guest examples select `vm_instances["<host>"].tpm = {}` for unique TPM 2.0 state.
The selected source catalog must explicitly report `tpm_state_present = false`. Vendor Linux
Secure Boot follows the tested template's firmware profile. Existing VMs use the
[additive maintenance path](01-hosting/proxmox-guest-security.md).

Inventory and YAML IP/network settings also feed Linux Terraform: rerun provisioning when those change.
For Linux environments, add the same `--env <name>` to init and deploy; omit it for production.
The wrapper layers `all.<name>.yml`, `<stem>.<name>.yml`, and existing `common.<name>.tfvars` /
`terraform.<name>.tfvars`. Init does not create Terraform overlays or reserve IDs/IPs;
complete [environment isolation](../08-reference/repository-scripts.md#environment-isolation) first.

## Offline Root CA

ORCA uses a separate offline machine, not a Terraform guest. See the [numbered first visit and
signing path](../03-deployment/stage-02-trust/procedures/offline-root.md). Public configuration is
`templates/offline-root/orca.conf`; secrets and original CA state stay on offline custody media.

| Run from | Action | Command |
| --- | --- | --- |
| Tier 0 on the connected preparation host | Initialize editable public inputs | `bash scripts/offline-root.sh init` |
| Same Tier 0 root | Build a new pinned public kit | `bash scripts/offline-root.sh bundle .local-archive/orca-kit` |
| Copied kit root, offline | Prepare/verify retained tools and policy | `bash scripts/offline-root.sh prepare` |
| Same offline kit root, **new root only** | Explicit initial root creation | `bash scripts/offline-root.sh create` |
| Same offline kit root | Inspect the original certificate and state | `bash scripts/offline-root.sh status` |
| Same offline kit root | Sign the independently approved CSR/key from the guide | `bash scripts/offline-root.sh sign "$ORCA_REQUEST" "$ORCA_REQUEST_KEY"` |
| Same offline kit root | Issue root CRL/export public objects | `bash scripts/offline-root.sh crl` |
| Same offline kit root, after each change | Encrypt the complete native root backup | `bash scripts/offline-root.sh backup` |

## Linux setups

**Copy commands from the table and run them from the owning tier root.** `TF` means
`terraform/deployments/<setup>/terraform.tfvars`; listed YAML filenames are inside `ansible/group_vars/`.
The setup name fixes the Terraform root/state even when an explicit Ansible playbook is selected.

| Stage / setup and owning guide | Tier | Configuration beyond common inputs | Terraform input changes | Ansible input changes |
| --- | --- | --- | --- | --- |
| 1 [outbound cache](../03-deployment/stage-01-software-intake/README.md): `cache` | 2 | TF; `cache.yml` | `bash scripts/deploy.sh cache` | `bash scripts/deploy.sh cache --ansible-only` |
| 2 [issuer](../03-deployment/stage-02-trust/README.md): `foundation` | 0 | TF; `foundation.yml`, `issuer.yml`; private policy file from guide | `bash scripts/deploy.sh foundation --terraform-only` | [Issuer command below](#issuer-runtime) |
| 2 optional [software HSM](../03-deployment/stage-02-trust/step-1a-software-hsm.md) on existing `ca-1` | 0 | `issuer.yml`, `hsm_software.yml`; selected `hsm_software_operation` and private PINs | Uses the existing `foundation` VM/data disk | `bash scripts/deploy.sh foundation --ansible-only --playbook deployment/hsm-software.yml --ansible-vars ansible/group_vars/issuer.yml --ansible-vars ansible/group_vars/hsm_software.yml` |
| 2 optional [HSM provider hosts](../03-deployment/stage-02-trust/step-1b-usb-hsm.md): `hsm` | 0 | TF; `hsm.yml`; per-host serials in inventory/host vars | `bash scripts/deploy.sh hsm` | `bash scripts/deploy.sh hsm --ansible-only` |
| 2 optional [verified intake](../03-deployment/stage-02-trust/step-15b-verified-intake.md): `intake` | 1 | TF; `intake.yml` | `bash scripts/deploy.sh intake` | `bash scripts/deploy.sh intake --ansible-only` installs; `bash scripts/deploy.sh intake --recipe maintenance` acquires/verifies/publishes |
| 3 [protected logging](../03-deployment/stage-03-logging/README.md): `syslog` | 0 | TF; `syslog.yml`, `logging_producers.yml` | `bash scripts/deploy.sh syslog` | `bash scripts/deploy.sh syslog --ansible-only`; retention recipes remain separate |
| Before 4/7/10 [API gateways](../03-deployment/stage-04-kubernetes/procedures/api-endpoint.md): `cluster-endpoint` | 0 | TF; `cluster_endpoint.yml` | `bash scripts/deploy.sh cluster-endpoint` | `bash scripts/deploy.sh cluster-endpoint --ansible-only` |
| 5 [directory](../03-deployment/stage-05-identity/README.md): `foundation` | 0 | Same TF; `foundation.yml` | `bash scripts/deploy.sh foundation --terraform-only` | `bash scripts/deploy.sh foundation --ansible-only`; external CA: `csr`, then `complete` phase |
| 6 optional [Vault VM](../03-deployment/stage-06-secrets/step-1b-vault-vm.md): `vault` | 0 | TF; `vault.yml` | `bash scripts/deploy.sh vault` | `bash scripts/deploy.sh vault --ansible-only`; API configuration below |
| 8 alternative [observability VMs](../03-deployment/stage-08-observability/step-1b-dedicated-vms.md): `observability` | 1 | TF; `observability.yml` | `bash scripts/deploy.sh observability` | `bash scripts/deploy.sh observability --ansible-only` for complete product configuration |
| 9 alternative [source-control VM](../03-deployment/stage-09-development/step-1b-source-control-vm.md): `development` | 1 | TF; `development.yml` | `bash scripts/deploy.sh development` | `bash scripts/deploy.sh development --ansible-only` |
| 9 [GitLab data VMs](../03-deployment/stage-09-development/procedures/data-services.md): `development-data` | 1 | TF; `development_data.yml`; private data secrets | `bash scripts/deploy.sh development-data --terraform-only` | Native recipe: [render](../03-deployment/stage-09-development/procedures/data-services.md#8-render-data-service-configuration), then [apply with full secret/confirmation inputs](../03-deployment/stage-09-development/procedures/data-services.md#9-review-and-apply-data-services) |
| 9 optional [Podman build runner](../03-deployment/stage-09-development/step-14b-podman-runner.md): `podman-runner` | 1 | TF; `podman_runner.yml` | `bash scripts/deploy.sh podman-runner` | `bash scripts/deploy.sh podman-runner --ansible-only` |
| 9 [trusted IaC runner](../03-deployment/stage-09-development/procedures/infrastructure-runner.md): `infrastructure-runner` | 0 | TF; `infrastructure_runner.yml` | `bash scripts/deploy.sh infrastructure-runner` | `bash scripts/deploy.sh infrastructure-runner --ansible-only` |
| 9 optional [image builder](../03-deployment/stage-09-development/step-15b-image-based-linux.md): `immutable-template` | 0 | TF; `immutable_template.yml` | `bash scripts/deploy.sh immutable-template` | `bash scripts/deploy.sh immutable-template --ansible-only`; separate publication below |
| Maintenance [staged Linux image](01-hosting/templates/template-refresh.md): `template-refresh` | 0 | TF; `template_refresh.yml` | `bash scripts/deploy.sh template-refresh`; final conversion: `bash scripts/deploy.sh template-refresh --terraform-only` | `bash scripts/deploy.sh template-refresh --ansible-only`; cleanup requires guide's explicit gates |
| 7/10 [public edge](../03-deployment/stage-07-delivery/procedures/edge-proxy.md): `edge` | 2 | TF; `edge.yml` | `bash scripts/deploy.sh edge` | `bash scripts/deploy.sh edge --ansible-only` |
| 10 [VM/LXC lab](../03-deployment/stage-10-lab-environments/README.md#step-2-provision-the-workload-runtime): `lab` | 2 | TF; `lab.yml`; selected environment definitions | `bash scripts/deploy.sh lab` | `bash scripts/deploy.sh lab --ansible-only` |

From **the owning tier root**, the common forms are:

```bash
bash scripts/deploy.sh "<setup>"
```

```bash
bash scripts/deploy.sh "<setup>" --ansible-only
```

The full Linux command shows a plan, asks for `yes`, then runs its mapped deployment recipe.
Add `--plan-only` for preview or `--terraform-only` to stop after provisioning.
Approved unattended Terraform apply/destroy uses `--auto-approve` (also disables variable prompts).
For separate review/apply jobs, use the [private saved-plan contract](../08-reference/repository-scripts.md#cheat-sheet).

`--ansible-only` reapplies deployment configuration; `--recipe maintenance` selects a different recipe
and implies Ansible-only. Maintenance rejects Terraform plan/apply/destroy modes. In particular,
`foundation` maintenance checks the directory, and `observability` maintenance covers only its host
baseline. Consult the [maintenance scopes](01-hosting/ansible-recipes.md#recipe-map).

### Issuer runtime

From **Tier 0 root**, after repository preparation/pin discovery below and the Stage 2 policy/credential gates:

```bash
bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
```

The default `foundation` playbook configures **FreeIPA**, not the issuer. Preserve the complete
issuer/directory/optional-monitor maps in that shared root; review its whole-state plan at every stage.
Key creation, offline signing, certificate installation and token activation remain separate Stage 2 actions.

## Templates, Kubernetes and Vault CI

These use dedicated entry points. Command cells are complete commands relative to the named tier root.

| Setup / guide | Tier | Configuration | Terraform input changes | Ansible/configuration changes |
| --- | --- | --- | --- | --- |
| Foundation [template publication](01-hosting/templates/template-lifecycle.md#local-workflow): `templates` | 0 | `templates/proxmox.yml`; Shared platform/catalog inputs above | `bash scripts/proxmox-templates.sh plan --env-file .env.local`, review, then `bash scripts/proxmox-templates.sh apply --env-file .env.local` | Plan/apply also reconciles policy; read-only check: `bash scripts/proxmox-templates.sh verify --env-file .env.local`; [disk replacement](01-hosting/templates/template-disk.md) is separate |
| 4 [control cluster](../03-deployment/stage-04-kubernetes/README.md), 7 [platform cluster](../03-deployment/stage-07-delivery/procedures/platform-cluster.md), 10 [workload/isolated clusters](../03-deployment/stage-10-lab-environments/procedures/isolated-clusters.md): `kubernetes` | 0 / 1 / 2, independently | `terraform/deployments/kubernetes/terraform.tfvars`, inventory and `talos.yml`; selected signed ISO/hash or Shared template catalog | `bash scripts/kubernetes-cluster.sh plan`, review, then `bash scripts/kubernetes-cluster.sh apply` | Talos machine inputs use the same plan/apply. Signed-path proof repeats with `bash scripts/kubernetes-cluster.sh verify-security` |
| 9 [Vault JWT/policies](../03-deployment/stage-09-development/procedures/vault-ci.md): `ci-auth` | 0 | `terraform/deployments/ci-auth/terraform.tfvars`; exported `VAULT_ADDR`, `VAULT_CACERT`, `VAULT_TOKEN` | Native Terraform init/plan/apply with protected `.terraform/state/ci-auth/terraform.tfstate`; [exact commands](../03-deployment/stage-09-development/procedures/vault-ci.md#configure-exact-job-authority) | No Ansible recipe; no Proxmox wrapper |

From **Tier 0 root**, initialize publication inputs once:

```bash
bash scripts/proxmox-templates.sh init
```

For existing catalog-matching templates/files, use `import --env-file .env.local` instead of `plan`;
review before `apply`. Successful apply publishes Shared references. From **each selected tier root**,
initialize its independent Talos inputs once:

```bash
bash scripts/kubernetes-cluster.sh init
```

Export Proxmox credentials for the cluster wrapper; it does not load `.env.local` or accept Linux flags.
After apply, `bash scripts/kubernetes-cluster.sh credentials` exports private client/recovery files.
Template and cluster `apply` consume saved plans without an extra Terraform approval prompt;
their preceding plan/review step remains required. Neither accepts `--auto-approve`.

## Boot-security commands

Physical-host checks use Tier 0's existing `hypervisors` inventory and SSH account through the
[host firmware/maintenance guide](01-hosting/proxmox-host-boot-security.md).
Use the [existing-VM guide](01-hosting/proxmox-guest-security.md) for private preparation records,
backups and the approved outage. Its input file selects one exact existing VM.

For **VM hardware maintenance only**, initialize the TPM inputs from **Tier 0**.

```bash
bash scripts/init-local-files.sh --setup proxmox-guest-security
```

Before the **VM hardware API operations** below, load Tier 0's existing API environment in
the protected execution shell.

```bash
set -a
source .env.local
set +a
```

| Task | Owner and configuration | Command |
| --- | --- | --- |
| Prepare physical Proxmox host inspection tools | Tier 0, existing `hypervisors` inventory; replace `<host>` and `<ssh-user>` with the accepted host/account | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/proxmox-boot-security.yml --limit "<host>" -e @ansible/group_vars/all.yml -e "ansible_user=<ssh-user>" -e proxmox_host_boot_security_operation=prepare` |
| Verify the server's Secure Boot and physical TPM 2.0 | Same Tier 0 host, using SSH | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/proxmox-boot-security.yml --limit "<host>" -e @ansible/group_vars/all.yml -e "ansible_user=<ssh-user>" -e proxmox_host_boot_security_operation=check` |
| Inspect existing VM boot hardware | Tier 0, `ansible/group_vars/proxmox_guest_security.yml` | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/proxmox-guest-security.yml -e @ansible/group_vars/proxmox_guest_security.yml -e proxmox_guest_security_operation=inspect` |
| Prepare, check or apply the missing TPM | Same Tier 0 file, private record/hash and backup/outage inputs from the guide. Replace `<operation>` with `prepare`, then `check`, then `apply` | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/proxmox-guest-security.yml -e @ansible/group_vars/proxmox_guest_security.yml -e "proxmox_guest_security_operation=<operation>"` |
| Prepare tools and verify Linux Secure Boot plus TPM | Owning tier, existing inventory and selected service group vars. Replace `<group-vars>` with the row's filename stem, such as `cache`, and `<inventory-group>` with that populated Linux group | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deployment/guest-boot-security.yml -e @ansible/group_vars/all.yml -e "@ansible/group_vars/<group-vars>.yml" -e "guest_boot_security_hosts=<inventory-group>" -e guest_boot_security_operation=apply` |
| Recheck Linux boot controls | Same owning tier and selected Linux group | `ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deployment/guest-boot-security.yml -e @ansible/group_vars/all.yml -e "@ansible/group_vars/<group-vars>.yml" -e "guest_boot_security_hosts=<inventory-group>" -e guest_boot_security_operation=check` |
| Verify signed Talos nodes | Owning tier, original Kubernetes state and selected boot policy | `bash scripts/kubernetes-cluster.sh verify-security` |
| Eject accepted signed Talos installation media | Owning tier, `secure_boot.install_media_attached = false` in the existing Kubernetes `.tfvars` | `bash scripts/kubernetes-cluster.sh plan`, review, then `bash scripts/kubernetes-cluster.sh apply` |

Linux `apply` installs only native inspection packages from the configured accepted repositories,
then verifies the running controls. `check` requires those tools already installed. Both Secure Boot
and TPM checks are enabled by default. Include any additional group-vars and encrypted inputs used
by the existing service workflow. Talos `verify-security` proves signed-path UKI boot and the
selected system-volume encryption. Template-path nodes report their retained policy.

## Native application recipes and GitOps

**No Terraform in this table.** Recipes live in `ansible/playbooks/deployment/`; YAML input names
are relative to `ansible/group_vars/`. Initialize matching examples with the common initializer above.
Choose components/phases and the explicit target kubeconfig/context from the owning guide.

| Stage / guide | Tier | Recipe | Inputs | Action variable |
| --- | --- | --- | --- | --- |
| 4/7 [cluster basics](../03-deployment/stage-04-kubernetes/README.md#step-2-establish-the-basic-platform): Cilium, storage, certificates, ingress, database operator, Flux | 0 / 1 | `cluster-platform.yml` | `cluster_platform.yml`, selected `cluster_platform_secrets.yml` | `cluster_platform_action` |
| 10 [workload cluster basics](../03-deployment/stage-10-lab-environments/README.md#step-2-provision-the-workload-runtime) | 2 | `cluster-platform.yml` | `cluster_platform.yml`; create `ansible/group_vars/cluster_platform_secrets.yml` from the selected component's contract if installer-managed | `cluster_platform_action` |
| 4/7/10 [cluster security collection](../03-deployment/stage-04-kubernetes/procedures/security-logging.md) | 0 / 1 / 2 | `cluster-security-logging.yml` | `cluster_security_logging.yml`, `cluster_security_logging_secrets.yml` | `cluster_security_logging_action` |
| 5 [Keycloak](../03-deployment/stage-05-identity/README.md), 6 [Vault / NetBox / Headlamp](../03-deployment/stage-06-secrets/README.md) | 0 | `control-applications.yml` | `control_applications.yml`, `control_applications_secrets.yml` | `control_applications_action` |
| 7 [delivery services / registry](../03-deployment/stage-07-delivery/README.md) | 1 | `delivery-platform.yml` | `delivery_platform.yml`; private `secrets/delivery-platform.yml` | `delivery_platform_action` |
| 7 [promotion pipeline import](../03-deployment/stage-07-delivery/procedures/flux-platform.md) | 1 | `delivery-promotions.yml` | `delivery_promotion.yml`; private `secrets/delivery-promotion.yml` | `delivery_promotion_action`: `render`, then `import`; existing credential migration uses `adopt` |
| 8 [observability products](../03-deployment/stage-08-observability/README.md) | 1 | `observability-platform.yml` | `observability_platform.yml`, `observability_platform_secrets.yml` | `observability_action` |
| 9 [GitLab / Kubernetes runners](../03-deployment/stage-09-development/procedures/gitlab.md) | 1 | `development-platform.yml` | `development_platform.yml`; `secrets/gitlab-secrets.yml`, main-path `secrets/development-data/platform-inputs.yml` | `development_platform_action` |
| 10 [bounded application](../03-deployment/stage-10-lab-environments/step-3a-application.md) | 2 | `lab-environment.yml` | `lab_environment.yml` | `lab_environment_action` |
| 10 optional [application telemetry](../03-deployment/stage-10-lab-environments/step-5b-telemetry.md) | 2 | `workload-telemetry.yml` | `workload_telemetry.yml` | `workload_telemetry_action` |

From **the row's tier root**, substitute its recipe/input/action names. Append the row's secret and
dependency files as additional `-e @<file>` arguments; encrypted files need `--ask-vault-pass` or an
approved unattended Vault identity. Keep those same inputs for both render and apply.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  "ansible/playbooks/deployment/<recipe>.yml" \
  -e "@ansible/group_vars/<inputs>.yml" -e "<action_variable>=render"
```

Review private output, then rerun with `=apply` for direct ownership (promotion uses `=import`).
These actions have no Terraform approval prompt. Preserve guide-specific commissioning/backup phases.
GitLab data VMs instead require their host inventory, secret inputs and confirmation flag in the guide.

For [Tier 1 Flux ownership](../03-deployment/stage-07-delivery/procedures/flux-platform.md), use the
same renderers with the documented Flux owner/export inputs, review/publish to the private
`clusters/tier1/` GitOps checkout, then let Flux reconcile. Flux-owned service renderers reject direct
apply. Bootstrap through `cluster-platform.yml`; do not give direct apply and Flux the same objects.
Use the [adoption procedure](../03-deployment/stage-07-delivery/procedures/flux-adoption.md) for existing releases.

## Selected subrecipes and optional paths

These complete selected setups; they do not create new Linux setup/state names. `deployment/` and
`maintenance/` paths below are inside `ansible/playbooks/`; `G` means `ansible/group_vars/`.
Use each guide's exact inventory, credentials and ordered extra-vars, including its manual pauses.

| Stage / guide | Tier | Inputs | Terraform changes | Ansible action |
| --- | --- | --- | --- | --- |
| 1 [bootstrap consumer](../03-deployment/stage-01-software-intake/procedures/bootstrap-consumer.md) / [managed consumers](../03-deployment/stage-01-software-intake/README.md) | 0 / owning tier | `G/bootstrap.yml` / `G/software_consumer.yml`, `G/all.yml` | None | `deployment/bootstrap-software-intake.yml` locally / `deployment/software-consumer.yml` on selected hosts |
| 1 [Proxmox update proxy](02-software-intake/host-updates.md) / [HA enrollment](01-hosting/proxmox-ha.md) | 0 | `G/all.yml` / `G/proxmox_ha.yml`; host inventory | None; initial guest placement stays in owning tier TF | `proxmox-hosts.yml` / `proxmox-ha.yml` |
| 2 [issuer repository prep and pin discovery](../03-deployment/stage-02-trust/README.md) | 0 | `G/issuer.yml` | None; retains `foundation` state | [Repository-prep command below](#issuer-repository-preparation) |
| 2 [permanent portal TLS](../03-deployment/stage-02-trust/README.md#step-16-secure-the-installation) | 0 | `G/issuer.yml`; existing controller-held portal key, returned full chain | None; retains `foundation` state | [Portal CSR command below](#permanent-issuer-portal-tls); approval and runtime reconciliation remain separate |
| 2 [HSM issuer binding](../03-deployment/stage-02-trust/step-1d-single-usb.md) / [PKCS#11 remoting](../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md) | 0 | `G/hsm.yml`, `G/issuer.yml` / `G/hsm_remoting.yml`; original-key serials | `hsm` root only for guest/USB changes | Explicit `deployment/hsm-issuer.yml`, `hsm-token.yml`; remoting server/client/check recipes in guide. Guarded same-key local-to-remote transition: [openxpki-pkcs11-migrate.yml](../../tier-0/ansible/playbooks/deployment/openxpki-pkcs11-migrate.yml), using the [migration guide's custody/secret inputs](03-cryptography/hardware-migration.md#same-key-provider-rebind), separate from routine reconciliation |
| 3 [producer enrollment and retention](../03-deployment/stage-03-logging/README.md) | 0; producer tiers 0/1/2 | `G/logging_producers.yml`, selected `logging_authority.yml`, `logging_archive.yml`, `logging_export.yml`, `logging_backup.yml` | `syslog` for receiver VM/disk changes only | Receiver workflow plus tier-local `deployment/logging-producers.yml`; selected authority/archive/export/backup recipes |
| 5 [LDAP reader](../03-deployment/stage-05-identity/README.md), [Kubernetes SSO](../03-deployment/stage-05-identity/procedures/kubernetes-sso.md) / [human access](../03-deployment/stage-05-identity/procedures/kubernetes-cli-access.md) | 0; SSO targets chosen tier | `G/freeipa_ldap_reader.yml`, control inputs/secrets; target private Talos plan/credentials; `G/kubernetes_human_access.yml` | No new root; target plan/export before serial rollout, then guarded state commit in guide | `deployment/freeipa-ldap-reader.yml`, `control-applications.yml` with `control_applications_operation=kubernetes_sso`, `kubernetes-human-access.yml` |
| 6 [Vault VM API configuration](../03-deployment/stage-06-secrets/step-1b-vault-vm.md) | 0 | `G/vault.yml`; scoped operator token | None | `deployment/vault-configure.yml` after original initialization/unseal |
| 6 optional [independent OpenBao signing](../03-deployment/stage-06-secrets/step-11b-openbao.md) | 0 | `ansible/inventory/signing.yml`, `G/all.signing.yml`, `G/vault.signing.yml`, `G/openbao_signing.yml`, vault `terraform.signing.tfvars` | `bash scripts/deploy.sh vault --env signing --inventory ansible/inventory/signing.yml --ansible-vars ansible/group_vars/openbao_signing.yml --terraform-only` | `bash scripts/deploy.sh vault --env signing --inventory ansible/inventory/signing.yml --ansible-vars ansible/group_vars/openbao_signing.yml --ansible-only`; then `deployment/openbao-signing.yml` after separate initialization/unseal; never replaces Vault |
| 6 [independent monitor](../03-deployment/stage-06-secrets/procedures/independent-monitoring.md) / [NetBox audit](../03-deployment/stage-06-secrets/procedures/netbox-audit.md) | 0 | `G/foundation.yml`, `G/infrastructure_monitoring.yml`, encrypted monitoring secrets; `G/netbox_audit.yml`, `G/netbox_audit_account.yml` | Optional `bash scripts/deploy.sh foundation --terraform-only` for monitor VM; none for accepted host | `deployment/infrastructure-monitoring.yml`: render/apply with `localhost` and prepared host limit; separate audit/account recipes |
| 7/10 optional [public HTTPS](../03-deployment/stage-10-lab-environments/step-4b-public-https.md) | 2 | `G/edge.yml`, `G/public-https.yml`; private controller schedule input | `edge` only for guest changes | Edge override, `maintenance/public-certificates.yml`, then `deployment/public-certificate-schedule.yml` |

### Issuer repository preparation

From **Tier 0 root**, before application/database/key setup, discover the three native package pins:

```bash
bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki-repository.yml --ansible-vars ansible/group_vars/issuer.yml
```

This prepares APT/key/repository prerequisites and reports `apt-cache policy`; continue through the
[Stage 2 pin selection and inactive-runtime installation](../03-deployment/stage-02-trust/README.md).

### Permanent issuer portal TLS

From **Tier 0 root**, at Stage 2's final step, retain the existing controller-held bootstrap portal key:

```bash
bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki-portal-request.yml --ansible-vars ansible/group_vars/issuer.yml
```

This creates only the public portal CSR; it performs no issuer change or issuance. Submit/approve through
the normal workflow, select the returned leaf-first full chain in `OPENXPKI_TLS_CERT_FILE`, then rerun
the [issuer runtime command](#issuer-runtime) and verify TLS before retiring the seven-day bootstrap certificate.
For option-specific initialization, product upgrades and recovery, keep the linked guide's procedure.
