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

## Recipe map

Paths are relative to the tier's `ansible/playbooks/`. Legacy `<setup>.yml`
entry points import the deployment recipe using native `import_playbook` [1].
Standalone `proxmox-hosts.yml` and `ingress.yml` retain their dedicated entry
points; they are not registered Linux VM setups in the shared deployment helper.

| Tier / setup | Deployment recipe | Maintenance recipe and scope |
| --- | --- | --- |
| 0 / `foundation` | `deployment/identity-freeipa.yml` | `maintenance/foundation.yml`: read-only directory service/API checks |
| 0 / `vault` | `deployment/vault-vm.yml` | `maintenance/vault.yml`: reconcile existing role configuration |
| 0 / `hsm` | `deployment/hsm-gateways.yml` | `maintenance/hsm.yml`: OS baseline only, no gateway/key operations |
| 0 / `immutable-template` | `deployment/immutable-template.yml` | Existing builder recipe, with its current gates |
| 0 / `template-refresh` | `deployment/template-refresh.yml` | Existing refresh recipe; replacement remains explicitly enabled |
| 1 / `edge` | `deployment/edge-proxy.yml` | `maintenance/edge.yml`: proxy configuration |
| 1 / `cache` | `deployment/outbound-cache.yml` | `maintenance/cache.yml`: cache configuration, no playbook-driven failover exercise |
| 1 / `development` | `deployment/source-control-vm.yml` | `maintenance/development.yml`: existing source-control role |
| 1 / `podman-runner` | `deployment/podman-runner.yml` | `maintenance/podman-runner.yml`: runner configuration |
| 1 / `observability` | `deployment/telemetry-hosts.yml` | `maintenance/observability.yml`: host baseline only |
| 2 / `lab` | `deployment/lab-vms.yml` | `maintenance/lab.yml`: host baseline |

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
