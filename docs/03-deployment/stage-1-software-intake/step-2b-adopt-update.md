# Step 2b: Adopt an intake update with existing cache servers

**Branch from:** [Step 2](README.md#step-2-initialize-cache-inputs), option **2b**, for an existing pair.
**Change:** refresh automation and reconcile the retained cache configuration/state.
**Return:** [Step 9](README.md#step-9-test-the-accepted-supply) after update adoption and cache reconciliation.

Update the generated collection and reconcile the existing cache pair.
Existing VMs, local inputs and original state stay in place.

**Working repositories:** the upstream kit for refresh; `<prefix>-tier-2` for cache configuration;
`<prefix>-tier-0` for existing host consumers.
**Prerequisites:** recoverable copies of local inputs/state, working bootstrap tools and SSH,
and the published kit revision containing the update. The kit must be on that revision's branch.

## Contents

- [1. Update the kit checkout](#1-update-the-kit-checkout)
- [2. Refresh the existing collection](#2-refresh-the-existing-collection)
- [3. Reconcile the existing cache](#3-reconcile-the-existing-cache)
- [4. Return to the numbered path](#4-return-to-the-numbered-path)

## 1. Update the kit checkout

From the **upstream kit root** on `boot-1`, inspect the checkout:

```bash
git status --short
git branch --show-current
```

Preserve any local changes first. Require the branch containing the published update; pulling
another branch will not install it. Then, from the **same upstream checkout**:

```bash
git pull --ff-only
```

Use the existing approved Git proxy/source route. HTTPS Git uses the shell proxy environment;
an SSH Git remote requires its own approved SSH route. Do not open general WAN access to update the kit.
For a proxy-configured bootstrap terminal opened before configuration, load the existing profile
with `source /etc/profile.d/shell-proxy.sh` before pulling; a new login normally loads it automatically.

## 2. Refresh the existing collection

From the **updated upstream kit root**, reuse the original prefix and collection parent:

```bash
read -r -p 'Original project prefix: ' PROJECT_PREFIX
read -r -p 'Parent directory containing the existing collection (absolute path): ' PROJECT_PARENT
bash scripts/init-tier-repos.sh --prefix "$PROJECT_PREFIX" --root "$PROJECT_PARENT" --refresh
```

For `/srv/tier0/src/homelab-iac/`, the parent is `/srv/tier0/src`, not `homelab-iac` itself.
Use the actual original prefix, not a new one. Optional preview: add `--dry-run`.

**Expected:** kit automation and examples update; local inputs, state and project READMEs remain
protected. Missing generated files are restored. Review configuration differences and replacement
backups from the [final report](../../04-development/generated-repositories.md#refresh-review-summary).
Refresh creates no infrastructure and does not merge new keys into live configuration.

## 3. Reconcile the existing cache

Edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**. Compare with its refreshed `.example`:

| Setting | Review |
| --- | --- |
| `cache_squid_allowed_cidrs` | Keep existing approved clients; include bootstrap and Proxmox consumers, plus selected Windows clients for option 7b |
| `cache_squid_allowed_domains` | Retain required repository/tool sources and redirect destinations; include the selected Windows sources for option 7b |
| `cache_squid_refresh_patterns` | Adopt the current example's source-respecting rules; remove old expiry/privacy/reload overrides |
| `cache_squid_extra_options` | Review retained custom directives for policy/cache changes |

Approve the default [pinned Git sources](../../08-reference/control-node-tooling.md#collection-sources),
or the API/artifact route for explicit Galaxy acquisition; use prepared archives offline.
If an older kit's policy blocks the collection needed to update it, follow the
[one-time controller repair](../../08-reference/control-node-tooling.md#recover-an-existing-cache-that-blocks-galaxy),
then continue here with cache reconciliation.

Keep only accepted client/source scopes. Review raw `cache_squid_extra_options`, which can alter
the generated policy. This is the existing-cache reconciliation procedure; the
[optional settings reference](../../08-reference/proxy-cache.md) supplies field and behavior details.

Run from **`<prefix>-tier-2/`**, without concurrent package jobs:

```bash
bash scripts/deploy.sh cache --ansible-only
```

**Expected:** existing VMs converge; permitted/denied requests and VIP checks pass. Configured
failover validation may move the VIP temporarily. Do not destroy caches, clear disks or discard state.

## 4. Return to the numbered path

<a id="5-return-to-the-numbered-path"></a>

Return to [Stage 1, Step 9](README.md#step-9-test-the-accepted-supply) to verify the cache
and its consumers. Steps 10–17 reapply the retained bootstrap and Proxmox settings to adopt updated
package policy, then verify retrieval and bypass denial. Keep the accepted endpoint and bypass list.
For recurring APT signature/hash failures, use the [diagnostic runbook](../../05-operations/02-software-intake/apt-refresh.md).
A successful normal refresh needs no permanent `No-Cache` or pipelining override.

Select [Stage 3, option 15b](../stage-3-trust/README.md#15b-verified-repository-and-artifact-publication-optional)
when protected logging and the issuer are accepted. That installer owns setup registration, worker inputs,
VM/disks, service setup and consumer cutover; no later-stage service is needed.
If Stage 3 is already accepted, the option can be deployed directly from that numbered decision point.
