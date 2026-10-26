# Kubernetes human SSO after identity

Add the existing Keycloak issuer to the Kubernetes API without replacing X509
authentication, the cluster issuer, service-account issuer or Talos administration.
Headlamp forwards each human's token; Kubernetes RBAC remains the authorization
boundary. Tier 0's IdP runs inside the cluster it authenticates, so independent
certificate access and recovery during an issuer outage are mandatory.

**Working repositories:** the selected `<prefix>-tier-0`, `<prefix>-tier-1` or
`<prefix>-tier-2` owns its plan/resources/state. The authorized identity operator
runs the single recipe from `<prefix>-tier-0` (source: `tier-0/`); this does not
transfer target-tier resource or state ownership.
**Prerequisites:** accepted Stage 4 platform and [Keycloak](keycloak.md), its public
CA bundle under independent custody, three healthy control planes, matching
`talosctl` 1.13, `kubectl`, and retained Talos/X509 recovery credentials. The
selected schema is Talos **1.13 v1alpha1**, as in the
[basic platform](../../stage-4-kubernetes/procedures/basic-platform.md).
Do not apply this document to 1.14's split configuration schema. [1]

## Table of contents

- [Identity contract](#identity-contract)
- [Preserve the authoritative configuration](#preserve-the-authoritative-configuration)
- [Render and apply serially](#render-and-apply-serially)
- [Commit the reviewed state](#commit-the-reviewed-state)
- [Outage and recovery acceptance](#outage-and-recovery-acceptance)
- [References](#references)

## Identity contract

| Setting | Selected contract |
| --- | --- |
| Issuer | Exact existing `https://sso.lab.example.com/realms/platform`; replace the example DNS name everywhere |
| Audience/client | `headlamp`; API server needs no client secret |
| Human identity | `sub`, prefixed `oidc:`; never mutable display name/email |
| Groups | `groups` array with `oidc:` prefix; `platform-viewers` becomes `oidc:platform-viewers` |
| Signatures | `RS256`; qualify the realm's signing key/algorithm and rotation |
| Trust file | Host `/var/kubernetes-oidc/issuer-ca.crt`, directory mounted read-only at `/etc/kubernetes/oidc` |
| Authorization | Existing namespaces only, built-in `view` via RoleBinding; no `system:masters` or broad ClusterRoleBinding |

The [native client configuration](../../../../tier-0/ansible/roles/control_applications/tasks/clients.yml)
registers confidential `headlamp`, exact HTTPS `/oidc-callback`, standard code
flow with PKCE S256, no password grant/service account, and the `groups` scope.
Its mapper uses `full.path: false` and includes groups in the ID token. Verify
that token's `iss`, `aud`, `sub` and group values; a same-named nested directory
group must not accidentally grant access. Retain stable Keycloak realm/database
state because recreating identities changes their subjects. [2][3]

Set the same issuer and private client secret in Headlamp. The
[control-applications inputs](../../../../tier-0/ansible/group_vars/control_applications.yml.example)
select `oidc:platform-viewers` and namespace `view` bindings. No cluster-wide
RBAC is implied. For another cluster, separately review its permitted groups,
namespace bindings and Headlamp registration. [2][4]

## Preserve the authoritative configuration

1. In the selected tier's `terraform/deployments/kubernetes/`, copy the public
   `oidc-machine-config.yaml.example` into private working input. Replace its
   issuer DNS and PEM placeholder with the **existing public CA chain**. Never
   paste a CA private key, admin credential or client secret. Do not fetch trust
   from Vault at API startup. Validate DNS/HTTPS from every control plane.
2. Append that document as **one dedicated heredoc string** to the existing
   `machine_config_patches` in `terraform.tfvars`. Retain every existing CNI,
   proxy, KubePrism, mirror, DNS, audit and Talos logging patch. This root already
   passes the list to `data.talos_machine_configuration.node`; applying a patch
   only through Talos would let a later Terraform run remove it. Do not regenerate
   machine secrets, kubeconfigs, cluster CA, default Talos admin or signing keys.
3. From the **selected tier repository root**, produce an OIDC-only saved plan
   using the existing helper context. Do not initialize another Terraform root,
   change backend/state paths or apply the bootstrap plan in parallel.

```bash
bash scripts/kubernetes-cluster.sh plan
bash scripts/kubernetes-cluster.sh export-plan
```

The helper retains its original `TF_DATA_DIR` and backend and exports the current
saved plan to **`secrets/talos/plan.json`** privately. It requires a saved plan;
fresh plan/apply actions invalidate the old JSON. Do not export from another
workspace or substitute stale JSON after re-planning.

Plan JSON and planned machine configurations contain cluster administrator
credentials. Keep them outside Git/artifacts/logs, with `0600` files and `0700`
parent directories. Review using a protected local terminal, never public CI.
The plan must expose known `planned_values.outputs.machine_configurations.value`
and `nodes.value`; resolve unknown data before proceeding. Stop on unrelated
VM, storage, network, credential or version changes.

The examples are provided in
[Tier 0](../../../../tier-0/terraform/deployments/kubernetes/oidc-machine-config.yaml.example),
[Tier 1](../../../../tier-1/terraform/deployments/kubernetes/oidc-machine-config.yaml.example) and
[Tier 2](../../../../tier-2/terraform/deployments/kubernetes/oidc-machine-config.yaml.example).
They add only `machine.files`, OIDC `extraArgs` and one `extraVolumes` entry.
Talos merges mappings but appends these lists; blindly repeating this patch
duplicates entries. Changing an existing OIDC deployment/CA requires a separately
reviewed replacement patch, not another append. Machine files are processed at
boot and need a reboot; `try`/`no-reboot` is not a substitute. [1][5]

## Render and apply serially

Use the dedicated `kubernetes_sso` operation of the
[Tier 0 recipe](../../../../tier-0/ansible/playbooks/deployment/control-applications.yml).
It invokes no Helm, Terraform apply, key generation, initialization or unseal.
Execution is implemented once in
[the owner role](../../../../tier-0/ansible/roles/control_applications/tasks/kubernetes-sso.yml);
Tier 0 owns identity/control authority. Other tiers retain their own plan,
inputs, resources and state; their authorized operator supplies those inputs to
this workflow without copying execution tasks or transferring state ownership.

Create a private input file with explicit paths and contexts:

```yaml
control_applications_sso_plan: /absolute/selected-tier/secrets/talos/plan.json
control_applications_sso_output: /absolute/private/oidc-rollout
control_applications_oidc_issuer: https://sso.lab.example.com/realms/platform
control_applications_sso_talosconfig: /absolute/private/talosconfig
control_applications_sso_talos_context: selected-cluster
control_applications_kubeconfig: /absolute/private/recovery.kubeconfig
control_applications_context: retained-x509-admin-context
control_applications_sso_maintenance_accepted: false
```

From the Tier 0 checkout, prepare its usual local public group vars, then render:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/control-applications.yml \
  -e @/absolute/private/oidc-inputs.yml \
  -e control_applications_operation=kubernetes_sso
```

Render is offline: it reads the plan, parses the imported CA with native
`community.crypto.x509_certificate_info`, writes private planned configurations,
and runs `talosctl validate --mode metal --strict` and native configuration
canonicalization. It does not contact Kubernetes, Talos or the IdP. Dependencies
are existing `community.crypto`, `kubernetes.core`, `ansible.utils`, Python
`cryptography`/`netaddr`/`kubernetes`, plus the two native product CLIs.

After reviewing maintenance, quorum, application disruption budgets, current
etcd snapshot/recovery custody and direct certificate access, explicitly apply:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/control-applications.yml \
  -e @/absolute/private/oidc-inputs.yml \
  -e control_applications_operation=kubernetes_sso \
  -e control_applications_action=apply \
  -e control_applications_sso_maintenance_accepted=true
```

The workflow rejects non-certificate kubeconfig identities, then processes
control planes before workers, **one node at a time**. Workers are included
because the root's global patch list also affects their generated configurations.
For each node it requires all nodes Ready and a matching running Talos minor,
captures current authenticated Talos configuration, and uses native merging to prove `current + OIDC == Terraform
planned`. Any unrelated difference, including lost CNI/proxy/audit or altered
X509/Talos credentials, stops the operation. Already matching nodes are not
patched again. A different persisted/staged configuration also blocks rollout.
Keep rollout output under recovery custody; do not overwrite a
failed run's snapshots when investigating.

It stages the OIDC-only patch with `talosctl patch machineconfig --mode staged`,
reboots that node with `--wait`, verifies the local CA bytes, then checks direct
control-plane certificate-authenticated namespace reads and `/readyz`, and Node
Ready before proceeding. A failed gate stops before the next node. This proves
normal recovery only; it does **not** simulate an issuer outage. [6]

## Commit the reviewed state

The pinned provider's `talos_machine_configuration_apply.Read` does not read live
configuration. CLI rollout therefore leaves the old applied input in Terraform
state. `refresh-only` is insufficient; a reviewed provider **Update** must commit
the desired input. Update calls the Talos apply API, so this is not a state-only
edit. Never use `state rm`, import, manual state editing or parallel bootstrap to
hide that difference. [9]

1. Freeze other machine-configuration writers. From the selected tier root,
   rerun the helper `plan` then `export-plan` commands above. Review the fresh
   plan: only expected `talos_machine_configuration_apply.node` updates are
   allowed, with unchanged API credentials and complete inputs including all
   CNI/proxy/audit/OIDC patches. No forced `reboot` mode or additional resource
   patch list is allowed. Discard the pre-rollout saved plan.
2. From Tier 0, repeat the serial Ansible apply command with both
   `-e control_applications_sso_require_installed=true` and a **new private output
   directory**. This refuses any node not already equal to the fresh plan; it
   must perform no patch/reboot and must pass all certificate/readiness gates.
3. For **every** target node, inspect the native full-configuration dry run
   below in a protected terminal. It must report no configuration change or
   reboot requirement. Any difference, reboot request, unavailable node or
   unreviewed plan stops the state commit. Exit status alone is not sufficient.

```bash
umask 077
talosctl --talosconfig /absolute/private/talosconfig --context selected-cluster \
  --endpoints NODE_IP --nodes NODE_IP apply-config --dry-run --mode auto \
  --file /absolute/private/oidc-commit/NODE_NAME.desired.yaml \
  > /absolute/private/oidc-commit/NODE_NAME.commit-dryrun.txt
```

4. From the **selected tier root**, commit that reviewed saved plan through the
   same helper, explicitly serializing provider operations:

```bash
TF_CLI_ARGS_apply=-parallelism=1 bash scripts/kubernetes-cluster.sh apply
bash scripts/kubernetes-cluster.sh plan
bash scripts/kubernetes-cluster.sh export-plan
```

Terraform accepts the apply argument through its native environment option. [10]
This reapplies the already-installed **full** configuration, not the append-only
OIDC patch, and records the applied input/hash. No reboot is expected after the
equality and dry-run gates; `-parallelism=1` additionally prevents simultaneous
node updates. Keep the maintenance freeze until complete, monitor API/Node
health, and stop on any unexpected reboot or apply failure. The final fresh
plan must show no remaining machine-configuration updates. Archive recovery
evidence and retain the full input patch list. This procedure has not been
exercised against a live cluster.

## Outage and recovery acceptance

Upstream Kubernetes 1.35 and 1.36 source initializes remote OIDC discovery
asynchronously and retries failed discovery at a ten-second polling interval.
Its authentication chain retains X509 independently and before bearer-token
methods. This supports self-hosted issuers, but is not proof of the selected
cluster's availability: malformed local CA/configuration can still prevent
startup, and key-cache, network and load-balancer behavior require testing. [7][8]

Keep `control_applications_headlamp_api_oidc_accepted: false` until recording:

| Gate | Required evidence |
| --- | --- |
| Allowed identity | Fresh human login, correct subject/group and permitted namespace reads through Headlamp and API |
| Denied identity | Unbound user/namespace and writes are denied; group removal takes effect after token expiry/reissue |
| Issuer outage | With approved isolated issuer/discovery/JWKS failure, retained X509 reads still work directly and through the API endpoint |
| Cold start | During that outage, reboot **one** control plane; verify certificate-authenticated namespace reads and workload/control-plane recovery before touching another |
| Directory outage | Stop/isolate the approved LDAP test path; show new federation login failure does not remove API certificate access |
| Recovery | Restore issuer/LDAP; fresh OIDC login and API access recover without rebootstrap, CA replacement or restarting every API server |
| Evidence | API audit and Keycloak authentication/admin events arrive at protected intake, including denied requests |

Run the certificate check with the retained credential, not an impersonated
identity or OIDC plugin, against the rebooted control plane and then the normal
endpoint. For example, using approved private IP/SAN values:

```bash
kubectl --kubeconfig /absolute/private/recovery.kubeconfig \
  --context retained-x509-admin-context --server https://CONTROL_PLANE_IP:6443 \
  --request-timeout=15s get namespaces
```

Also record `/livez`, `/readyz` and load-balancer membership. A health response
alone does not prove authenticated recovery, and direct-node access alone does
not prove the normal endpoint remains reachable. Do not automate outage
injection against a live cluster here. **Cold-start/outage behavior has not been
verified by local rendering and remains manual acceptance.**

On failure stop the rollout, preserve the current/desired snapshots, use the
retained `talosconfig` and console/recovery route, and restore the affected node's
last-known-good **complete** configuration only after checking staged state and
boot-time files. Reboot and verify certificate access before proceeding. Never
reset the cluster, rotate CA/secrets, disable X509 or delete the default Talos
admin to fix OIDC. Reconcile the same rollback in Terraform inputs before its
next apply. CA rotation requires an overlap bundle and a separately reviewed
file replacement/serial reboot, not `op: create` over the existing file.

Return to [Stage 5](../README.md#capability-available). NetBox's complete audited
change export and Vault's scheduled off-cluster snapshot transport remain
[explicit Stage 6 integrations](../../stage-6-secrets/procedures/control-applications.md#service-access-and-logging),
not outcomes of Kubernetes SSO.

## References

Guidance and upstream initialization behavior checked 2026-10-26.

1. [Talos 1.13 MachineConfig schema and file lifecycle](https://docs.siderolabs.com/talos/v1.13/reference/configuration/v1alpha1/config).
2. [Headlamp OIDC](https://headlamp.dev/docs/latest/installation/in-cluster/oidc/).
3. [Keycloak client scopes and protocol mappers](https://www.keycloak.org/docs/latest/server_admin/#_client_scopes).
4. [Kubernetes OIDC authentication and claims](https://kubernetes.io/docs/reference/access-authn-authz/authentication/).
5. [Talos native patch merging](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/system-configuration/patching).
6. [Talos CLI patch, staged mode and reboot](https://docs.siderolabs.com/talos/v1.13/reference/cli).
7. [Kubernetes 1.35 OIDC initialization/retry](https://github.com/kubernetes/kubernetes/blob/v1.35.0/staging/src/k8s.io/apiserver/plugin/pkg/authenticator/token/oidc/oidc.go) and [authentication chain](https://github.com/kubernetes/kubernetes/blob/v1.35.0/pkg/kubeapiserver/authenticator/config.go).
8. [Kubernetes 1.36 OIDC initialization/retry](https://github.com/kubernetes/kubernetes/blob/v1.36.0/staging/src/k8s.io/apiserver/plugin/pkg/authenticator/token/oidc/oidc.go).
9. [Pinned Talos provider Read/Update implementation](https://github.com/siderolabs/terraform-provider-talos/blob/v0.11.0/pkg/talos/talos_machine_configuration_apply_resource.go).
10. [Terraform native CLI argument environment](https://developer.hashicorp.com/terraform/cli/config/environment-variables#tf_cli_args-and-tf_cli_args_name).
