# Step 14a: On-demand Kubernetes runners

**Expected result — IaC:** one manager and bounded ephemeral job pods share the existing cluster with
GitLab, as shown in the [execution view](README.md#figure-kubernetes-runners). The installer creates
runner policy; GitLab registration and accepted build/helper images are existing inputs.

**Branch from:** [Step 14](README.md#step-14-select-and-install-general-build-execution).
**Change:** install the Kubernetes runner manager and bounded job policy in the existing cluster.
**Working repository:** `<prefix>-tier-1`.
**Return:** to [Stage 9 Step 15](README.md#step-15-select-the-linux-image-lifecycle) after bounded-job checks.
**Prerequisites:** accepted GitLab, CNI policy enforcement, worker capacity and
approved non-root build/helper images. General jobs never receive Tier 0 credentials.
Verify node access to the approved image mirror and its pull credentials first;
pod egress policy does not configure kubelet image pulls. Any private pull-secret
or node-level registry integration remains an explicit cluster prerequisite.

## Step 1: Create the runner identity

Create a project/group runner in GitLab with the modern authentication-token flow.
Keep `tier1-build` as its tag, configure whether untagged jobs are permitted and
scope it to approved projects. These server settings are not encoded in the token
or inferred from a pod label. Store its `glrt-` token in `gitlab-runner-auth`,
key `runner-token`; retain an empty `runner-registration-token` compatibility key. [1]

Provide `gitlab-runner-ca`, containing the trusted GitLab CA certificate under
the GitLab hostname's `.crt` filename as well as `ca.crt` if used by local tooling.
Never use certificate-verification bypasses.

Choose one Secret owner before rendering:

- **1a: existing controller** - provision those two Secrets in the selected runner namespace and keep
  `development_platform_manage_secrets: false`. Use the normal commands in Steps 3-4.
- **1b: encrypted bootstrap file** - create the private input below, then use the corresponding
  private-input commands in Steps 3-4. GitLab's earlier Secret file does not implicitly provide runner Secrets.

Run from **`<prefix>-tier-1/`** for 1b:

```bash
umask 077
mkdir -p secrets
cp -n ansible/group_vars/development_platform_secrets.yml.example secrets/runner-secrets.yml
```

Edit **`<prefix>-tier-1/secrets/runner-secrets.yml`**: retain `development_platform_manage_secrets: true`
and only `gitlab-runner-auth` / `gitlab-runner-ca` in its Secret map. Fill the real token and CA,
then encrypt from **the same Tier 1 root**:

```bash
ansible-vault encrypt secrets/runner-secrets.yml
```

Keep decryption material independently. Both choices continue at Step 2; no second runner identity is created.

## Step 2: Configure the runner

In Tier 1's local `development_platform.yml`, select:

```yaml
development_platform_components: [runners]
development_platform_runner_concurrent: 4
```

The file is **`ansible/group_vars/development_platform.yml`**. Preserve accepted GitLab
settings; `[runners]` reconciles the runner only, without reinstalling GitLab.

| Field in the same file | Set |
| --- | --- |
| `development_platform_kubeconfig`, `development_platform_context` | Accepted Tier 1 kubeconfig and its exact context, used for Secrets, policies and Helm |
| `development_platform_runner_version` | Exact qualified Runner chart version |
| `development_platform_runner_image`, `development_platform_runner_helper_image` | Compatible approved non-root image digests |
| `development_platform_runner_allowed_cidrs` | Actual GitLab/artifact/intake endpoint CIDRs |
| `development_platform_runner_api_cidrs` | Tier 1 API service/backend CIDRs; manager access only |

Pin the runner chart and compatible build/helper image digests. Configure exact
GitLab/artifact/proxy endpoint CIDRs and Tier 1 API service/backend CIDRs.
The manager alone may reach that API; jobs use a tokenless `ci-job` identity.
Do not allow broad LAN or Tier 0 ranges. Test actual service-DNAT behavior for the CNI.

## Step 3: Render the manager and job policy

With **1a**, run from **`<prefix>-tier-1/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml -e development_platform_action=render
```

With **1b** instead, run from **the same Tier 1 root**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/runner-secrets.yml --ask-vault-pass -e development_platform_action=render
```

Review values, manifests and `gitlab-runner-support.yml` under
`secrets/development-platform/`.

## Step 4: Apply the reviewed runner

Use the same accepted kubeconfig/context and Secret inputs as the render:

With **1a**, run from **`<prefix>-tier-1/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml -e development_platform_action=apply
```

With **1b** instead, run from **the same Tier 1 root**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/runner-secrets.yml --ask-vault-pass -e development_platform_action=apply
```

The native chart installs one manager; the Kubernetes executor creates a separate
pod per job. It does not create a new runner manager or worker VM per job. [2]
The supplied config limits concurrency, images, resources and namespace-scoped RBAC;
it uses non-root jobs without privilege escalation, host mounts or Docker sockets.

## Step 5: Qualify execution and isolation

Run an approved job with the exact allowed image digest and tag `tier1-build`.
Verify job pods appear and disappear, failed jobs clean up, limits apply and
unapproved images are rejected. Test denied Tier 0/API access from a job, not
only the existence of NetworkPolicy objects. No job should mount a Kubernetes API token.
NetworkPolicy does not replace gateway/host controls or prevent node escape.

For an approved unattended run, supply an Ansible Vault identity instead of `--ask-vault-pass`.

Use dedicated build nodes or a separate build cluster for untrusted jobs; do not
mix hostile code with privileged platform administration merely because namespaces differ.
Capacity scaling and failure/recovery remain explicit operations; no node autoscaler is supplied.
Return to [Stage 9, Step 15](README.md#step-15-select-the-linux-image-lifecycle).

## References

1. [GitLab runner creation and authentication tokens](https://docs.gitlab.com/runner/register/).
2. [Official Kubernetes runner chart](https://docs.gitlab.com/runner/install/kubernetes/),
   [Kubernetes executor and permissions](https://docs.gitlab.com/runner/executors/kubernetes/).
