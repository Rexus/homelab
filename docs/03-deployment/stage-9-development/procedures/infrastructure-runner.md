# Dedicated infrastructure runner

**Working repository:** `<prefix>-tier-0`. Branch from
[Stage 9, Step 4](../README.md#step-4-hand-over-infrastructure-execution).
**Return:** to Step 4 for Vault credential/job tests and original-state handover before routine apply.
Its direct-CI trust decision is also required at Stage 9 Step 3, before creating the Vault policy.
The reference adds `iac-1` on the management network, outside Kubernetes.
It survives a control-cluster outage, but not loss of its hypervisor/storage;
retain the independent recovery workstation.

## Step 1: Accept direct-CI trust

Approve the [trusted-CI decision](../../../01-architecture/10-delivery/03-development-platform.md#privileged-ci).
The infrastructure project, GitLab administrators and administrators able to modify
GitLab's cluster, data, signing keys or backups are Tier 0 authorities in this option.
Do not grant those rights to ordinary platform developers. Argo CD/Spinnaker and
general runners still have no infrastructure credentials.

Create a **project runner**, not a group/instance runner. Mark it protected,
disable untagged jobs, assign only `tier0-iac`, lock it to the dedicated project
and prevent ordinary developers from changing its jobs/includes. Record server-side
settings and test them; tags alone are not access control. [1]

## Step 2: Provision and configure

From Tier 0:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/init-local-files.sh --setup infrastructure-runner
```

Review VMID, management attachment, `iac-1` address and approved Linux image.
The runner role intentionally supports the RedHat family only.
Prepare signed RPM repositories and approved versions of GitLab Runner,
Terraform, Vault CLI, Ansible and optional cluster/image tools.
Add pinned packages to `infrastructure_runner_tool_packages` where needed.
No vendor `curl | bash` setup script is executed.

Edit in **`<prefix>-tier-0/`**.

- `terraform/deployments/infrastructure-runner/terraform.tfvars`: iac-1 VMID, image, placement, management
  attachment and disk/size
- `ansible/inventory/hosts.yml`: Matching iac-1 in `infrastructure_runner`
- `ansible/group_vars/infrastructure_runner.yml`: `platform_host_ips.iac-1`, actual GitLab URL, pinned
  runner version, local CA path and tool packages. Set `infrastructure_runner_trust_ci_control_plane: true`
  only after Step 1's trust decision.

For approved package sources absent from the template, set `baseline_rpm_repositories`
in the same file to their HTTPS base URLs, public-key URLs and pinned fingerprints.
The [Shared input definitions](../../../../shared/ansible/roles/baseline/defaults/main.yml)
also provide `baseline_trust_anchors` for internal repository CAs. The role installs
Terraform, Vault, Ansible, Git and rsync from those sources; no manual guest tool installation is required.

Enter the newly created **project runner** token without recording it in shell history:

Run from **`<prefix>-tier-0/`**.

```bash
read -r -s -p "Protected infrastructure runner authentication token: " INFRASTRUCTURE_RUNNER_TOKEN
export INFRASTRUCTURE_RUNNER_TOKEN
```

Deploy from Tier 0:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/deploy.sh infrastructure-runner
unset INFRASTRUCTURE_RUNNER_TOKEN
```

Review Terraform's inline plan and enter `yes` only for the intended changes.
`--plan-only` is an optional preview. Approved unattended jobs can use `--auto-approve`
with the token supplied by the accepted secret source; trust/registration gates still apply.

The role installs a serialized shell executor using native packages and a managed
TOML file. Shell jobs are trusted code with the runner user's host access; this is
not a sandbox for ordinary builds. [2] No Proxmox credential is embedded in its config.

## Step 3: Qualify the host

Register OS, authentication and CI events with
[protected logging](../../stage-2-logging/procedures/sources.md). Enforce the approved host
and gateway policies: GitLab/Vault HTTPS, approved software sources and only required
infrastructure APIs/SSH. Do not expose a public runner listener.

Set `baseline_trust_anchors` in the same runner inputs to the approved controller-side
public root certificate files (one CA per file), then reapply the runner deployment.
Shared installs them in the native EL/Debian OS trust store; no guest login is required.
The Runner-specific `ca.crt` does not by itself configure persistent `git fetch`,
Terraform, Vault CLI or other HTTPS clients. Verify GitLab cloning and Proxmox/Vault
connections as the `gitlab-runner` user without disabling certificate verification.

Verify package trust, configuration permissions, one-job concurrency, rejected
unprotected/foreign jobs and CLI trust. The generated `/srv/iac` directory is empty:
it does not contain a restored collection or original state.
Continue with [handover](handover.md) before enabling an infrastructure apply job.

## References

1. [Runner protection and project controls](https://docs.gitlab.com/ci/runners/configure_runners/).
2. [Shell executor security](https://docs.gitlab.com/runner/executors/shell/).
