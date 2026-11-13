# Bootstrap Tier 0 Flux and SOPS

The [basic platform installer](basic-platform.md) installs Flux controllers,
a GitRepository pinned to an approved commit and a SOPS-enabled Kustomization.
It does not create a Git repository, commit, push, or depend on later Tier 1 GitLab.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`); run from the repository root.

**Prerequisites:** working CNI/DNS/images; an approved independently recoverable
Git source; read-only source credentials; an age identity protected outside the
cluster; SOPS and age tools on the independent operator host.

## Table of contents

- [Step 1: Prepare the source](#prepare-the-source)
- [Step 2: Provide bootstrap Secrets](#provide-bootstrap-secrets)
- [Step 3: Render and apply](#render-and-apply)
- [Step 4: Accept reconciliation](#accept-reconciliation)
- [References](#references)

<a id="prepare-the-source"></a>

## Step 1: Prepare the source

Populate the chosen Git path with reviewed manifests and `kustomization.yaml`.
The repository's `clusters/tier0/` folders are empty starters. Keep Ansible-owned
charts/resources out of that path unless an explicit ownership transfer has
been reviewed; installing Flux does not transfer their lifecycle.

Create **`clusters/tier0/platform-sops-canary.yaml`** in the selected source checkout
with the following content. Encrypt it locally with SOPS,
and list it in that path's `kustomization.yaml` before publishing through the
project's reviewed Git workflow:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: platform-sops-canary
  namespace: flux-system
type: Opaque
stringData:
  accepted: platform-sops-ok
```

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p 'Public age recipient (age1...): ' AGE_RECIPIENT
sops --encrypt --in-place --age "$AGE_RECIPIENT" --encrypted-regex '^(data|stringData)$' clusters/tier0/platform-sops-canary.yaml
```

Use the public age recipient in `$AGE_RECIPIENT`; the private identity remains
outside Git. Flux detects identity entries whose names end in `.agekey`. [1]
Set `cluster_platform_flux_canary_sha256` to the SHA-256 of the exact decrypted
value, excluding a trailing newline. For the example:

Run from **`<prefix>-tier-0/`**.

```bash
printf %s platform-sops-ok | sha256sum
```

Set the independent URL, approved full commit hash, path and
`cluster_platform_flux_source_approved: true` in local platform inputs.
The role accepts authenticated HTTPS or `ssh://user@host/path.git`, and pins
`spec.ref.commit`; moving branches are not selected automatically. [2]

In **`ansible/group_vars/cluster_platform.yml`**, set:

| Field | Enter |
| --- | --- |
| `cluster_platform_flux_url` | Independently reachable HTTPS or SSH Git URL |
| `cluster_platform_flux_commit` | Full approved commit containing the encrypted canary and its Kustomization entry |
| `cluster_platform_flux_path` | `./clusters/tier0`, or the actual published source path |
| `cluster_platform_flux_canary_sha256` | Digest printed by the command above |
| `cluster_platform_flux_source_approved` | `true` after source/content review |

<a id="provide-bootstrap-secrets"></a>

## Step 2: Provide bootstrap Secrets

| Secret in `flux-system` | Required fields |
| --- | --- |
| `flux-git` over HTTPS | `username`, `password`; optional qualified private-CA field `ca.crt` |
| `flux-git` over SSH | `identity`, `identity.pub`, `known_hosts`; optional key `password` |
| `sops-age` | `age.agekey`, containing the private age identity |

For HTTPS configure required fields `[username, password]`; for SSH set
`cluster_platform_flux_git_secret_keys: [identity, identity.pub, known_hosts]`.
List additional fields such as `ca.crt` when they are required for the selected
source. Keep host verification and certificate verification enabled. [2]

By default the shared role requires existing nonempty Secrets and does not own
them. An independent authorized bootstrap operator can create those Secrets,
or explicitly use the encrypted extra-vars example:

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ansible/group_vars/cluster_platform_secrets.yml.example ansible/group_vars/cluster_platform_secrets.yml
ansible-vault encrypt ansible/group_vars/cluster_platform_secrets.yml
ansible-vault edit ansible/group_vars/cluster_platform_secrets.yml
```

In the encrypted file, supply actual read-only credentials/age identity and set
`cluster_platform_manage_secrets: true`. Pass it with `--ask-vault-pass
-e @ansible/group_vars/cluster_platform_secrets.yml`. This explicitly enables managed
bootstrap Secrets. Rendering validates managed fields but never contacts the
cluster or writes plaintext Secret manifests. Store recovery keys independently;
no Vault or identity integration is required to decrypt this bootstrap file.

<a id="render-and-apply"></a>

## Step 3: Render and apply

Use the [platform commands](basic-platform.md#render-and-apply), optionally
selecting only `flux` after accepting the other prerequisites. Review chart
provenance: `flux2` is maintained by **fluxcd-community**, rather than the Flux
core installation project. Explicitly approve that chart repository or a
qualified mirror and pin its version. [3]

After Cilium and storage prerequisites are ready, render the selected full platform
with the private Secrets file:

Run from **`<prefix>-tier-0/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e @ansible/group_vars/cluster_platform_secrets.yml --ask-vault-pass -e cluster_platform_action=render
```

Inspect the private values/manifests under `secrets/cluster-platform/`, then apply:

Run from **`<prefix>-tier-0/`**.

```bash
export KUBECONFIG="${KUBECONFIG:-$PWD/secrets/talos/kubeconfig}"
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/cluster-platform.yml -e @ansible/group_vars/cluster_platform.yml -e @ansible/group_vars/cluster_platform_secrets.yml --ask-vault-pass -e cluster_platform_action=apply
```

Retain the selected lifecycle's exported `KUBECONFIG`; existing externally managed clusters use their existing
`secrets/<cluster-name>/kubeconfig`. Do not create another cluster or copy another tier's credentials
to satisfy the Terraform-path fallback.

The installer disables image automation/reflection controllers, requires native
source/Kustomization CRDs and waits for the four selected controller deployments.
The root Kustomization uses SOPS decryption, `wait: true` and `prune: false`.
Use separate reviewed Flux Kustomizations with dependencies and health checks
for future controllers, custom resources and consumers. A Kustomize resource
list alone does not establish dependency readiness. [4]

<a id="accept-reconciliation"></a>

## Step 4: Accept reconciliation

The role requires GitRepository and Kustomization `Ready` for their current
generation, the approved commit fetched/applied, the canary in the current
reconciliation inventory and its value matching the configured digest. Secret
values are suppressed from Ansible output. The source review must verify that
the canary manifest is encrypted; the live value alone does not prove encryption.
An empty source, unavailable key or unchanged starter cannot satisfy that gate.

Record live results separately. Offline Helm rendering cannot establish source
reachability, decryption, least privilege or recovery. Test restoring the Git
source, read-only credentials and age key without normal identity login. Advance
the pinned commit only after reviewing the proposed source changes.

Return to [basic platform acceptance](basic-platform.md#acceptance-and-recovery),
then [Stage 4, action 19](../README.md#step-19-accept-operation-and-recovery).

## References

1. [Flux SOPS and age integration](https://fluxcd.io/flux/guides/mozilla-sops/).
2. [Flux GitRepository commit/authentication contract](https://fluxcd.io/flux/components/source/gitrepositories/).
3. [Flux community Helm charts](https://github.com/fluxcd-community/helm-charts).
4. [Flux Kustomization dependencies, decryption and readiness](https://fluxcd.io/flux/components/kustomize/kustomizations/).
