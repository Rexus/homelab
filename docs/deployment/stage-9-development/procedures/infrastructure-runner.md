# Dedicated infrastructure runner

**Working repository:** `<prefix>-tier-0`. Branch from
[Stage 9, Step 4](../README.md#step-4-hand-over-infrastructure-execution).
The reference adds `iac-1` on the management network, outside Kubernetes.
It survives a control-cluster outage, but not loss of its hypervisor/storage;
retain the independent recovery workstation.

## Step 1: Accept direct-CI trust

Approve the [trusted-CI decision](../../../architecture/delivery/development-platform.md#privileged-ci).
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

```bash
bash scripts/init-local-files.sh --setup infrastructure-runner
```

Review VMID, management attachment, `iac-1` address and approved Linux image.
The runner role intentionally supports the RedHat family only.
Prepare signed RPM repositories and approved versions of GitLab Runner,
Terraform, Vault CLI, Ansible and optional cluster/image tools.
Add pinned packages to `infrastructure_runner_tool_packages` where needed.
No vendor `curl | bash` setup script is executed.

```bash
bash scripts/deploy.sh infrastructure-runner --plan-only
```

Review before deployment. Set the explicit trust acknowledgement to true,
approved runner version, local GitLab CA path and the new runner authentication
token through `INFRASTRUCTURE_RUNNER_TOKEN` or encrypted local inputs.

```bash
bash scripts/deploy.sh infrastructure-runner
```

The role installs a serialized shell executor using native packages and a managed
TOML file. Shell jobs are trusted code with the runner user's host access; this is
not a sandbox for ordinary builds. [2] No Proxmox credential is embedded in its config.

## Step 3: Qualify the host

Register OS, authentication and CI events with
[protected logging](../../stage-2-logging/sources.md). Enforce the approved host
and gateway policies: GitLab/Vault HTTPS, approved software sources and only required
infrastructure APIs/SSH. Do not expose a public runner listener.

Install the approved public CA chains in the runner OS/tool trust stores too.
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
