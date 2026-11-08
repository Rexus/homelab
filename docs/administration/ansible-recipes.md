# Ansible recipes

Playbooks are recipes; roles implement reusable configuration. Deployment and
maintenance compose the same roles without owning separate inventories or state.

<a id="table-of-contents"></a>

## Find a task

- [How is maintenance run on an existing service?](#choose-a-recipe)
- [How is only the issuing CA inspected?](#inspect-the-issuer)
- [Which recipe owns each operation?](#recipe-map)
- [Does maintenance upgrade products or roll back failures?](#maintenance-boundaries)

<a id="choose-a-recipe"></a>

## How is maintenance run on an existing service?

**Work from:** the owning tier's repository root; never Shared.
**Prerequisites:** existing hosts, tier-local inventory/inputs, approved SSH/sudo and control-node tooling.

1. Choose the setup and maintenance scope from the table below. Switch to its owning tier.
2. Review `ansible/inventory/hosts.yml`, `ansible/group_vars/all.yml` and the setup's
   `ansible/group_vars/<setup>.yml`; keep the accepted inputs and any environment overlay.
3. Run the selected recipe. For Tier 0 directory health checks:

```bash
bash scripts/deploy.sh foundation --recipe maintenance
```

4. Check the service result and protected logs before expanding the maintenance scope.

**Expected:** this example runs directory checks, not Terraform. Other recipes can change
configuration or restart services; their scope is listed below. Use `--env test` only for
an already configured test environment. Maintenance rejects `--plan-only`, `--terraform-only`
and `--destroy`; its precheck does not require Terraform.

The wrapper supplies the same inventory, ordered group vars, roles path, and
precheck as deployment. Direct `ansible-playbook` execution is valid with those
same inputs; see [command reference](../reference/repository-scripts.md).

**Stop/rollback:** investigate the first failure before retrying. No generic undo exists;
restore approved configuration using the product's runbook. Normal deployment without
`--recipe maintenance` provisions through Terraform; `--ansible-only` skips that provisioning.

<a id="inspect-the-issuer"></a>

## How is only the issuing CA inspected?

**Work from:** Tier 0 root, with existing `foundation` and `issuer.yml` inputs.

1. Review `ansible/group_vars/issuer.yml` and the `issuing_ca` inventory group.
2. Run the read-only service/configuration/API checks:

   ```bash
   bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

3. Expect running issuer services, valid native configuration and a successful local API ping.
   On failure, preserve logs and follow [issuer recovery](cryptography/issuer-recovery.md);
   inspection never initializes or activates a token.

The override selects only a tier-local recipe; it creates no new Terraform root/state owner.
Initial deployment uses the separate [issuer procedure](../deployment/stage-3-trust/procedures/issuer.md).

<a id="recipe-map"></a>

## Which recipe owns each operation?

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

The [domain catalog](../architecture/README.md#foundational-capabilities) maps these variants to
the platform architecture and deployment stages. A stage can combine Terraform, Ansible, GitOps,
and manual procedures; it is not an Ansible playbook that deploys everything.

<a id="maintenance-boundaries"></a>

## Does maintenance upgrade products or roll back failures?

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
