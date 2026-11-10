# Step 2b: Adopt an intake update with existing cache servers

**Branch from:** [Step 2](README.md#step-2-initialize-cache-inputs), option **2b**, for an existing pair.
**Change:** refresh automation and reconcile the retained cache configuration/state.
**Return:** [Step 5](README.md#step-5-test-the-selected-intake-path) after update adoption and cache reconciliation.

Update the generated collection, reconcile the existing cache pair, then register the optional
Tier 1 verified-intake setup. Existing VMs, local inputs and original state stay in place.

**Working repositories:** the upstream kit for refresh; `<prefix>-tier-2` for cache configuration;
`<prefix>-tier-0` for existing host consumers; `<prefix>-tier-1` for `intake-1`.
**Prerequisites:** recoverable copies of local inputs/state, working bootstrap tools and SSH,
and the published kit revision containing the update. The kit must be on that revision's branch.
The verified worker also needs [commissioned trust, logging and packages](../stage-3-trust/step-3b-verified-intake.md).

## Contents

- [1. Update the kit checkout](#1-update-the-kit-checkout)
- [2. Refresh the existing collection](#2-refresh-the-existing-collection)
- [3. Reconcile the existing cache](#3-reconcile-the-existing-cache)
- [4. Register the new Tier 1 setup](#4-register-the-new-tier-1-setup)
- [5. Return to the numbered path](#5-return-to-the-numbered-path)

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
backups from the [final report](../../development/generated-repositories.md#refresh-review-summary).
Refresh creates no infrastructure and does not merge new keys into live configuration.

## 3. Reconcile the existing cache

Edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**. Compare with its refreshed `.example`:

| Setting | Review |
| --- | --- |
| `cache_squid_allowed_cidrs` | Keep existing approved clients; add the selected `intake-1` IP, narrowly scoped, such as `10.30.31.40/32` |
| `cache_squid_allowed_domains` | Retain required sources; add selected repository/redirect and ClamAV definition hosts, including `database.clamav.net` for the connected updater |
| `cache_squid_refresh_patterns` | Adopt the current example's source-respecting rules; remove old expiry/privacy/reload overrides |
| `cache_squid_extra_options` | Review retained custom directives for policy/cache changes |

Select approved Galaxy API/artifact destinations or prepared archives for controller acquisition.
If the old policy blocks the collection needed to update it, follow the
[one-time controller repair](../../reference/control-node-tooling.md#recover-an-existing-cache-that-blocks-galaxy),
then continue here with cache reconciliation.

Keep only accepted client/source scopes. Review raw `cache_squid_extra_options`, which can alter
the generated policy. This is the existing-cache reconciliation procedure; the
[optional settings reference](../../reference/proxy-cache.md) supplies field and behavior details.

Run from **`<prefix>-tier-2/`**, without concurrent package jobs:

```bash
bash scripts/deploy.sh cache --ansible-only
```

**Expected:** existing VMs converge; permitted/denied requests and VIP checks pass. Configured
failover validation may move the VIP temporarily. Do not destroy caches, clear disks or discard state.

Reapply the existing [bootstrap consumer recipe](step-6-bootstrap-consumer.md#3-apply-the-local-configuration)
and [Proxmox host recipe](../../administration/hosts/update-access.md#4-apply-the-proxy-settings)
from **Tier 0** to adopt the updated package policy. Retain their accepted endpoint and bypass list.
On **each Proxmox host as root**, require the normal refresh to pass:

```bash
apt-get -o APT::Update::Error-Mode=any update
```

If signature/hash failures recur, use the [diagnostic runbook](../../administration/hosts/apt-refresh.md).
A successful normal refresh needs no permanent `No-Cache` or pipelining override.

## 4. Register the new Tier 1 setup

Refresh preserves **Tier 1 `.deployment-setups`** and **`ansible/inventory/hosts.yml`**.
Their refreshed examples/new code do not silently change the selected deployments.

Edit **`<prefix>-tier-1/.deployment-setups`**: add this line if absent, retaining every existing entry:

```text
intake
```

Edit **`<prefix>-tier-1/ansible/inventory/hosts.yml`**. Under `all.children`, add the group if absent:

```yaml
software_intake:
  hosts:
    intake-1: {}
```

Under the existing `all.children.guests.children`, add this membership if absent:

```yaml
software_intake: null
```

Keep other hosts/groups and check for existing names, VMIDs and address reservations.
This is inventory/recipe registration only, not a Terraform import or a VM creation.

## 5. Return to the numbered path

Return to [Stage 1, Step 5](README.md#step-5-test-the-selected-intake-path) to verify the cache
and its consumers, then complete Stages 2 and 3 in order. Registering the worker setup above creates
no worker VM and does not complete verified publication.

Select [Stage 3, option 3b](../stage-3-trust/README.md#3b-verified-repository-and-artifact-publication--optional)
when protected logging and the issuer are accepted. That single installer owns worker inputs,
VM/disks, service setup and consumer cutover; no later-stage service is needed.
If Stage 3 is already accepted, the option can be deployed directly from that numbered decision point.
