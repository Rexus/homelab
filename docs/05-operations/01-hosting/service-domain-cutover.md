# Change cache and logging DNS domains

Move existing service endpoints to the internal namespace using retained local configuration.
Start from accepted [cache](../02-software-intake/README.md) and
[logging](../06-resilience/protected-logging.md) deployments. The
[DNS convention](../../02-conventions/service-dns.md) defines host membership and stable service names.

**Work from the bootstrap/controller.** Keep the current host IPs, inventory keys, VMIDs,
disk UUIDs, logging authority and producer queues in their existing inputs and recovery records.
Retain working SSH access by the accepted IP/host mapping during the change.

## Contents

1. [Refresh the existing collection](#1-refresh-the-existing-collection)
2. [Prepare domains and overlapping DNS](#2-prepare-domains-and-overlapping-dns)
3. [Update cache and its consumers](#3-update-cache-and-its-consumers)
4. [Update the logging service](#4-update-the-logging-service)
5. [Optionally change machine hostnames](#5-optionally-change-machine-hostnames)
6. [Retire old names after verification](#6-retire-old-names-after-verification)

## 1. Refresh the existing collection

Follow [update adoption, actions 1–2](../../03-deployment/stage-01-software-intake/step-2b-adopt-update.md#1-update-the-kit-checkout)
using the original prefix and collection parent. Return here before applying changed service names.
Refresh replaces examples and automation. Local `all.yml`, service inputs and state are preserved.

## 2. Prepare domains and overlapping DNS

Edit **each affected tier's `ansible/group_vars/all.yml`**, preserving its existing settings.
Add the internal suffix and retain the directory domain. This generic example selects
`internal.example.com`; a site can use `example.internal` instead.

```yaml
platform_internal_domain: internal.example.com
platform_domain: corp.example.com
platform_host_domain: >-
  {{ platform_domain
     if platform_domain_role | default('standalone') in ['member', 'authority']
     else platform_internal_domain | default(platform_domain) }}
platform_fqdn: "{{ platform_hostname }}.{{ platform_host_domain }}"
baseline_manage_hostname: false
```

Add the internal suffix to any selected `all.<env>.yml` too.
Replace the old `platform_fqdn` formula with the two expressions above. Retain hostname
prefix/suffix generation and other local inputs.

Leave `platform_domain_role` out of `all.yml` and extra-var files. Its default is `standalone`.
Set `member` in an enrolled host's inventory-adjacent `host_vars/<host>.yml` only after actual enrollment.
For existing directory servers, add `platform_domain_role: authority` to the `identity` inventory
group's `vars` before reapplying foundation. Preserve their directory FQDNs and realm.
DNS naming and hostname configuration do not enroll a host.

In **the independent DNS service**, create the new records alongside the accepted old records.
Substitute the actual site addresses and domains.

| New record | Type | Value |
| --- | --- | --- |
| `cache-1.internal.example.com` | A | Existing cache-1 IP |
| `cache-2.internal.example.com` | A | Existing cache-2 IP |
| `cache.internal.example.com` | A | Existing cache VIP |
| `log-1.internal.example.com` | A | Existing receiver IP |
| `logs.internal.example.com` | CNAME | `log-1.internal.example.com` |

For a directory member, use its current machine record as the CNAME target. Keep the `logs`
service alias in the internal namespace. Keep old aliases resolving through the cutover and DNS TTL.
For an existing qualified logging VIP, retain its routing and point the service A record at that VIP.

Run on **the bootstrap/controller and representative consumers**.

```bash
getent ahostsv4 cache.internal.example.com
getent ahostsv4 logs.internal.example.com
```

Expect the accepted VIP and receiver addresses before applying any endpoint change.

## 3. Update cache and its consumers

Edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**. Update only the service-name formula
or explicit FQDN. Retain the VIP, disks, approved destination policy and existing client CIDRs.
Include every actual bootstrap, host and logging consumer network in `cache_squid_allowed_cidrs`.

```yaml
cache_proxy_fqdn: "{{ cache_proxy_name }}.{{ platform_internal_domain | default(platform_domain) }}"
```

Reconcile from **`<prefix>-tier-2/`**.

```bash
bash scripts/deploy.sh cache --recipe maintenance
```

Then edit the proxy consumers in **their owning tier's `ansible/group_vars/all.yml`**.
Update any explicit service-level or environment override too. If temporary hosts entries are managed,
set `repository_proxy_fqdn` to the new name and retain `repository_proxy_ip` as the accepted VIP.

```yaml
repository_proxy_enabled: true
repository_proxy_url: "http://cache.{{ platform_internal_domain | default(platform_domain) }}:3128"
```

In **Tier 0 `ansible/group_vars/bootstrap.yml`**, set the literal accepted URL, such as
`http://cache.internal.example.com:3128`. Keep old and new internal HTTP/HTTPS names that require
direct access in `shell_proxy_no_proxy_extra`, including the actual Proxmox endpoint.
Reapply and load the bootstrap settings through [bootstrap reconfiguration, actions 3–5](../../03-deployment/stage-01-software-intake/procedures/bootstrap-consumer.md#3-apply-the-local-configuration).
The current shell needs `source /etc/profile.d/shell-proxy.sh`, or a fresh login.

Reconcile each existing guest through its owning setup's Ansible recipe. Logging receivers are
reapplied in action 4 below. Reapply registered Proxmox consumers through
[Stage 1, actions 14–16](../../03-deployment/stage-01-software-intake/README.md#step-14-configure-proxmox-update-inputs).
Update explicitly configured proxy URLs in CI/jobs and restart their managed consumer when required.

Verify the new endpoint on **the bootstrap/controller**, using an allowed download URL.

```bash
read -r -p 'Approved download URL (example: https://github.com/): ' APPROVED_URL
curl --fail --noproxy '' --proxy http://cache.internal.example.com:3128 --output /dev/null "$APPROVED_URL"
```

Require successful retrieval and the existing denied-destination/direct-WAN checks.

## 4. Update the logging service

The connection address `log_forwarder_target` and verified certificate name `log_forwarder_peer`
are separate inputs. A DNS alias alone does not authorize a new TLS name.

1. Inspect the current receiver certificate and record its existing DNS SAN. While that certificate
   remains installed, producers can connect through the new DNS name and verify the old SAN.
   In **each producer tier's `ansible/group_vars/logging_producers.yml`**, the transitional values are

   ```yaml
   log_forwarder_target: logs.internal.example.com
   log_forwarder_peer: logs.corp.example.com
   ```

   Replace `logs.corp.example.com` with the actual SAN of the currently installed certificate.
   Reapply only when ready, using the producer's existing ordered setup/host inputs.

2. In the **Tier 0 producer catalog**, set `log_forwarder_peer` to the new DNS SAN and
   `log_forwarder_target` to the accepted reachable service endpoint. Select an intentional new
   `logging_workflow_generation` in **`syslog.yml`**. Run request preparation from **`<prefix>-tier-0/`**:

   ```bash
   bash scripts/deploy.sh syslog --ansible-only --playbook deployment/logging-prepare.yml
   ```

   This retains the original receiver key. Complete the selected [authority's issuance](../../03-deployment/stage-03-logging/procedures/producer-trust.md)
   before the scheduled listener change. The supplied request has one DNS SAN; a simultaneous dual-name
   cutover needs a qualified dual-SAN issuer handoff rather than an assumed second alias.
3. In the change window, run from **`<prefix>-tier-0/`**:

   ```bash
   bash scripts/deploy.sh syslog --ansible-only
   ```

   The combined workflow resumes approval, verifies the new leaf and installs receiver/selected
   Tier 0 producers. Preserve the original workspace, authority, queues and stream identities.
   Producers in other owning tiers retain their separately accepted public handoff and must be
   reapplied with the new peer name before retiring the old DNS name.
4. Repeat the [retained-event acceptance](../../03-deployment/stage-03-logging/README.md#step-5-verify-collection)
   and monitor TLS errors/backlogs. Existing direct receiver installations continue their original
   certificate paths and explicit recipe until reviewed custody adoption; refreshing the generated
   code alone does not migrate a CA or its private key.

## 5. Optionally change machine hostnames

After DNS and the local hostname formulas are ready, set `baseline_manage_hostname: true` in
**each selected setup's local inputs** to make its OS hostname follow `platform_fqdn`.
Run its deployment recipe with `--ansible-only` so the baseline is included; the cache maintenance
recipe only reconciles the cache role. The baseline applies the FQDN and sets Cloud-Init
`preserve_hostname: true` when Cloud-Init is present. The legacy default preserves existing hostnames.
Keep inventory keys and SSH IP mappings stable. Check host-specific monitoring, certificates and
backup records before changing an operating machine's name.
Existing Kerberos/FreeIPA identity material blocks a hostname change. Retain that host's current
FQDN or leave hostname management disabled until its separate directory migration is planned.

## 6. Retire old names after verification

Retain old DNS aliases until all consumers, saved proxy settings and logging TLS peers have moved,
the previous TTL has elapsed and queued logging events have arrived. Record the accepted service names,
certificate expiry and recovery inputs. Then remove obsolete aliases and temporary bypass entries.

For rollback, restore accepted local service inputs and reapply the same recipes. Keep old DNS resolving.
Logging rollback pairs the previously accepted receiver leaf with its original key and the matching
producer peer name. Retain queue/state directories throughout rollback.
