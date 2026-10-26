# Bootstrap Tier 0 Flux and SOPS

The [basic platform installer](basic-platform.md) installs Flux controllers,
a GitRepository pinned to an approved commit and a SOPS-enabled Kustomization.
It does not create a Git repository, commit, push, or depend on later Tier 1 GitLab.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`); run commands from `ansible/`.

**Prerequisites:** working CNI/DNS/images; an approved independently recoverable
Git source; read-only source credentials; an age identity protected outside the
cluster; SOPS and age tools on the independent operator host.

## Table of contents

- [Prepare the source](#prepare-the-source)
- [Provide bootstrap Secrets](#provide-bootstrap-secrets)
- [Render and apply](#render-and-apply)
- [Accept reconciliation](#accept-reconciliation)
- [References](#references)

## Prepare the source

Populate the chosen Git path with reviewed manifests and `kustomization.yaml`.
The repository's `clusters/tier0/` folders are empty starters. Keep Ansible-owned
charts/resources out of that path unless an explicit ownership transfer has
been reviewed; installing Flux does not transfer their lifecycle.

Add this acceptance Secret in the selected path, encrypt it locally with SOPS,
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

```bash
sops --encrypt --in-place --age "$AGE_RECIPIENT" \
  --encrypted-regex '^(data|stringData)$' platform-sops-canary.yaml
```

Use the public age recipient in `$AGE_RECIPIENT`; the private identity remains
outside Git. Flux detects identity entries whose names end in `.agekey`. [1]
Set `cluster_platform_flux_canary_sha256` to the SHA-256 of the exact decrypted
value, excluding a trailing newline. For the example:

```bash
printf %s platform-sops-ok | sha256sum
```

Set the independent URL, approved full commit hash, path and
`cluster_platform_flux_source_approved: true` in local platform inputs.
The role accepts authenticated HTTPS or `ssh://user@host/path.git`, and pins
`spec.ref.commit`; moving branches are not selected automatically. [2]

## Provide bootstrap Secrets

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

```bash
cp -n group_vars/cluster_platform_secrets.yml.example group_vars/cluster_platform_secrets.yml
ansible-vault encrypt group_vars/cluster_platform_secrets.yml
```

Edit that encrypted file with `ansible-vault edit`, supply actual read-only
credentials/age identity, and pass it with `--ask-vault-pass
-e @group_vars/cluster_platform_secrets.yml`. This explicitly enables managed
bootstrap Secrets. Rendering validates managed fields but never contacts the
cluster or writes plaintext Secret manifests. Store recovery keys independently;
no Vault or identity integration is required to decrypt this bootstrap file.

## Render and apply

Use the [platform commands](basic-platform.md#render-and-apply), optionally
selecting only `flux` after accepting the other prerequisites. Review chart
provenance: `flux2` is maintained by **fluxcd-community**, rather than the Flux
core installation project. Explicitly approve that chart repository or a
qualified mirror and pin its version. [3]

The installer disables image automation/reflection controllers, requires native
source/Kustomization CRDs and waits for the four selected controller deployments.
The root Kustomization uses SOPS decryption, `wait: true` and `prune: false`.
Use separate reviewed Flux Kustomizations with dependencies and health checks
for future controllers, custom resources and consumers. A Kustomize resource
list alone does not establish dependency readiness. [4]

## Accept reconciliation

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

## References

1. [Flux SOPS and age integration](https://fluxcd.io/flux/guides/mozilla-sops/).
2. [Flux GitRepository commit/authentication contract](https://fluxcd.io/flux/components/source/gitrepositories/).
3. [Flux community Helm charts](https://fluxcd-community.github.io/helm-charts/).
4. [Flux Kustomization dependencies, decryption and readiness](https://fluxcd.io/flux/components/kustomize/kustomizations/).
