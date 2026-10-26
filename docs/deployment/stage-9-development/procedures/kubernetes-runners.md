# On-demand Kubernetes runners

**Working repository:** `<prefix>-tier-1`. Continue
[Stage 9, Step 2](../README.md#step-2-add-on-demand-build-execution).
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

## Step 2: Render and apply

In Tier 1's local `development_platform.yml`, select:

```yaml
development_platform_components: [runners]
development_platform_runner_concurrent: 4
```

Pin the runner chart and compatible build/helper image digests. Configure exact
GitLab/artifact/proxy endpoint CIDRs and Tier 1 API service/backend CIDRs.
The manager alone may reach that API; jobs use a tokenless `ci-job` identity.
Do not allow broad LAN or Tier 0 ranges. Test actual service-DNAT behavior for the CNI.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/development-platform.yml -e @ansible/group_vars/development_platform.yml
```

Review values, manifests and `gitlab-runner-support.yml` under
`secrets/development-platform/`. Then apply the same inputs:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/development-platform.yml -e @ansible/group_vars/development_platform.yml -e development_platform_action=apply
```

The native chart installs one manager; the Kubernetes executor creates a separate
pod per job. It does not create a new runner manager or worker VM per job. [2]
The supplied config limits concurrency, images, resources and namespace-scoped RBAC;
it uses non-root jobs without privilege escalation, host mounts or Docker sockets.

## Step 3: Qualify execution and isolation

Run an approved job with the exact allowed image digest and tag `tier1-build`.
Verify job pods appear and disappear, failed jobs clean up, limits apply and
unapproved images are rejected. Test denied Tier 0/API access from a job, not
only the existence of NetworkPolicy objects. No job should mount a Kubernetes API token.
NetworkPolicy does not replace gateway/host controls or prevent node escape.

Use dedicated build nodes or a separate build cluster for untrusted jobs; do not
mix hostile code with privileged platform administration merely because namespaces differ.
Capacity scaling and failure/recovery remain explicit operations; no node autoscaler is supplied.
Return to [Stage 9, Step 3](../README.md#step-3-authorize-ci-through-vault).

## References

1. [GitLab runner creation and authentication tokens](https://docs.gitlab.com/runner/register/).
2. [Official Kubernetes runner chart](https://docs.gitlab.com/runner/install/kubernetes/),
   [Kubernetes executor and permissions](https://docs.gitlab.com/runner/executors/kubernetes/).
