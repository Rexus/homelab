# Ansible recipes

Playbooks are recipes; roles implement reusable configuration. Deployment and
maintenance compose the same roles without owning separate inventories or state.

## Table of contents

- [Choose a recipe](#choose-a-recipe)
- [Recipe map](#recipe-map)
- [Maintenance boundaries](#maintenance-boundaries)

## Choose a recipe

From the owning tier root, the normal deployment command provisions through
Terraform and runs the deployment recipe. `--ansible-only` skips provisioning.
For existing hosts, select maintenance explicitly:

```bash
bash scripts/deploy.sh foundation --recipe maintenance
```

This Tier 0 example checks the directory services. Substitute an owned setup
from the table; use `--env test` for its existing environment vars. Maintenance
never runs Terraform. It rejects `--plan-only`, `--terraform-only`, and `--destroy`.
The local precheck does not require Terraform for maintenance or `--ansible-only`.

The wrapper supplies the same inventory, ordered group vars, roles path, and
precheck as deployment. Direct `ansible-playbook` execution is valid with those
same inputs; see [command reference](../reference/repository-scripts.md).

Use `--playbook deployment/openxpki.yml --ansible-only` with the `foundation`
setup for the issuer-only recipe, plus `--ansible-vars ansible/group_vars/issuer.yml`.
Select `maintenance/openxpki.yml` for read-only CA inspection. The override selects
only a tier-local recipe; it never creates another Terraform root or state owner.

## Recipe map

Paths are relative to the tier's `ansible/playbooks/`. Legacy `<setup>.yml`
entry points import the deployment recipe using native `import_playbook` [1].
Tier 0 standalone `proxmox-hosts.yml` and opt-in co-hosted signing `ingress.yml` retain their dedicated entry
points; they are not registered Linux VM setups in the shared deployment helper.
The signing play is a gated backend renderer, not a service, VIP or HA installer.

| Tier / setup | Deployment recipe | Maintenance recipe and scope |
| --- | --- | --- |
| 0 / `foundation` | `deployment/identity-freeipa.yml` | `maintenance/foundation.yml`: read-only directory service/API checks |
| 0 / `foundation`, issuer override | `deployment/openxpki.yml` | `maintenance/openxpki.yml`: read-only service/configuration/API checks |
| 0 / issuer, explicit custody | `deployment/openxpki-bundle.yml` (controller), `deployment/openxpki-key.yml` | `maintenance/openxpki-backup.yml` and `maintenance/openxpki-restore.yml`: separately approved recovery operations |
| 0 / `syslog` | `deployment/foundation-logging.yml` | `maintenance/syslog.yml`: baseline and isolated receiver convergence; no package upgrades, evidence/queue deletion or retention changes |
| 0 / `vault` | `deployment/vault-vm.yml` | `maintenance/vault.yml`: reconcile existing role configuration |
| 0 / `hsm` | `deployment/hsm-gateways.yml` | `maintenance/hsm.yml`: OS baseline only, no gateway/key operations |
| 0 / `immutable-template` | `deployment/immutable-template.yml` | Existing builder recipe, with its current gates |
| 0 / `template-refresh` | `deployment/template-refresh.yml` | Existing refresh recipe; replacement remains explicitly enabled |
| 2 / `edge` | `deployment/edge-proxy.yml` | `maintenance/edge.yml`: proxy configuration |
| 2 / public HTTPS, opt-in | `deployment/public-certificate-schedule.yml` (controller) | `maintenance/public-certificates.yml`: native public ACME renewal and validated proxy reload |
| 2 / `cache` | `deployment/outbound-cache.yml` | `maintenance/cache.yml`: cache configuration, no playbook-driven failover exercise |
| 1 / `development` | `deployment/source-control-vm.yml` | `maintenance/development.yml`: existing source-control role |
| 1 / `podman-runner` | `deployment/podman-runner.yml` | `maintenance/podman-runner.yml`: runner configuration |
| 1 / `observability` | `deployment/telemetry-hosts.yml` | `maintenance/observability.yml`: host baseline only |
| 2 / `lab` | `deployment/lab-vms.yml` | `maintenance/lab.yml`: host baseline |

Cluster applications use separate native recipes, not Linux Terraform setup names.
Run them from the owning tier root with its Ansible configuration, local inputs and
explicit kubeconfig. Their default action is offline `render`; `apply` is explicit.

| Working tier | Native application recipe | Authoritative guide |
| --- | --- | --- |
| 0, 1, 2 | `deployment/cluster-platform.yml` | [Kubernetes basic platform](../deployment/stage-4-kubernetes/README.md#step-2-establish-the-basic-platform); tier-local inputs, Shared execution |
| 0, 1, 2 | `deployment/cluster-security-logging.yml` | [Protected cluster-source collection](../deployment/stage-4-kubernetes/procedures/security-logging.md) |
| 0 | `deployment/control-applications.yml` | [Identity](../deployment/stage-5-identity/README.md), [Secrets](../deployment/stage-6-secrets/README.md) |
| 1 | `deployment/delivery-platform.yml` | [Delivery](../deployment/stage-7-delivery/README.md) |
| 1 | `deployment/observability-platform.yml` | [Observability](../deployment/stage-8-observability/README.md) |
| 1 | `deployment/development-platform.yml` | [GitLab and runners](../deployment/stage-9-development/procedures/gitlab.md) |
| 2 | `deployment/lab-environment.yml` | [Bounded application](../deployment/stage-10-lab-environments/application.md) |
| 2 | `deployment/workload-telemetry.yml` | [Scoped application telemetry](../deployment/stage-10-lab-environments/telemetry.md) |

Tier 0's `deployment/infrastructure-monitoring.yml` instead targets an explicitly
prepared host outside observed clusters; use the [independent monitoring guide](../deployment/stage-6-secrets/monitoring.md).
Tier 0's control-application recipe also owns the guarded
[Kubernetes API SSO operation](../deployment/stage-5-identity/procedures/kubernetes-sso.md),
which uses the selected target tier's plan and credentials, not Helm.

Reconcile the same release with the same values owner; do not run direct apply and
a GitOps controller against the same objects simultaneously. Stateful upgrades,
schema migrations and restores require the product's separate acceptance runbook.

The [domain catalog](../architecture/README.md#technical-domains) maps these variants to
the platform architecture and deployment stages. A stage can combine Terraform, Ansible, GitOps,
and manual procedures; it is not an Ansible playbook that deploys everything.

## Maintenance boundaries

Configuration reconciliation can install missing packages and restart services
through existing handlers. It is not necessarily read-only, zero-downtime, or
a product upgrade procedure. Review configured versions and backups first.
Service recipes run serially where appropriate, but that alone does not provide
application-aware rolling upgrades or failover.

No new automatic major upgrades, database migrations, Vault unseal, HSM key
replication, or root ceremonies are introduced. Keep those in approved service
runbooks. Existing customized legacy playbooks remain preserved on refresh;
review their changes before adopting the new canonical recipe paths.

## References

1. [Ansible import_playbook](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/import_playbook_module.html)
