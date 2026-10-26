# Bounded application environment

**Working repository:** `<prefix>-tier-2`. Return to [Stage 10, Step 3](README.md#step-3-deploy-and-verify-applications).
**Prerequisites:** accepted cluster networking/storage/ingress, at least two schedulable
nodes, trusted DNS/TLS and the selected identity group's authentication into Kubernetes.
The runtime must enforce NetworkPolicy and Pod Security Admission.

## 1. Prepare inputs

```bash
umask 077
cp -n ansible/group_vars/lab_environment.yml.example ansible/group_vars/lab_environment.yml
python3 -m pip install -r ansible/requirements.txt
ansible-galaxy collection install -r ansible/requirements.yml
```

Set an approved image digest, private hostname, owner group and existing ingress
class/namespace. The reference image must serve `/` on port 8080 as UID 10001 with
a read-only root filesystem and writable `/tmp`. Adapt the tier-owned template for
applications needing different probes, volumes or carefully scoped outbound access.
An arbitrary image is not guaranteed to fit this contract.

## 2. Render and install

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/lab-environment.yml -e @ansible/group_vars/lab_environment.yml
```

Review `secrets/lab-environment/lab-demo.yml`. Render does not contact Kubernetes.
Before apply, prepare the selected namespace and its `lab-tls` Secret using the
accepted certificate owner. It must contain the private hostname's trusted chain/key;
no self-signed certificate or CA key is silently generated. Set the private kubeconfig path.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/lab-environment.yml -e @ansible/group_vars/lab_environment.yml -e lab_environment_action=apply
```

The [recipe](../../../tier-2/ansible/playbooks/deployment/lab-environment.yml) applies
namespace restrictions, quota, default-deny policy, ingress allowance and read-only
group access before the application. It waits for readiness. No privileged pods,
host mounts, API token, unrestricted egress or hypervisor credentials are granted.
Two replicas require capacity; they do not establish storage or physical failover.

## 3. Verify the boundary

1. Verify private HTTPS, both replicas and an update/rollback with an approved digest.
2. Test the reader group: its namespace logs are readable; other namespaces, Secrets
   and mutations are denied. Identity authentication does not itself grant this role.
3. Prove default-deny isolation and quota enforcement, then connect selected
   [telemetry](telemetry.md). Protected evidence remains outside this namespace.

Namespace isolation is not a hard boundary for hostile tenants. Use dedicated
[cluster isolation](isolated-clusters.md) where required. Keep automatic allocation,
expiry and portal integration separate; no such controller is installed by this recipe.
