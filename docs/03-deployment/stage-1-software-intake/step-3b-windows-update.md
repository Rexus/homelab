# Step 3b: Optional Windows Update access

**Branch from:** [Step 3](README.md#step-3-configure-the-cache-deployment), option **3b**.
**Change:** extend the cache policy and configure an accepted Windows consumer.
**Working repository:** `<prefix>-tier-2/` for the cache; Windows client policy is managed separately.
**Choose before:** [Step 4](README.md#step-4-deploy-the-cache-pair) for a new pair, or before
[Step 2b reconciliation](step-2b-adopt-update.md#3-reconcile-the-existing-cache) for an existing pair.
**Return:** deploy or reconcile the cache, complete [Step 5](README.md#step-5-test-the-selected-intake-path),
then validate the Windows consumer below before accepting this option.

This is a candidate route for Windows Update, not an implemented Windows provisioning or patch-management
workflow. Client configuration, firewall changes and acceptance are manual. The supplied Squid policy has
not been verified end to end with Windows Update or Delivery Optimization (DO).

## Contents

- [1. Prepare the route](#1-prepare-the-route)
- [2. Extend the cache policy](#2-extend-the-cache-policy)
- [3. Configure the Windows consumer](#3-configure-the-windows-consumer)
- [4. Validate a Windows consumer](#4-validate-a-windows-consumer)
- [References](#references)

## 1. Prepare the route

Select the Windows versions, update source, client addresses and maintenance window. This example targets
direct Microsoft Windows Update; WSUS, Store, Defender, Intune and other products may need different
endpoints and policies. Check Microsoft's endpoint lists for each selected version and feature. [1] [2]
Keep the existing bootstrap, Linux and recovery routes available during the change.

Decide whether the required DO cloud-service traffic can be allowed directly to
`*.do.dsp.mp.microsoft.com` over HTTPS from the selected clients. Microsoft requires direct access for
its recommended proxy arrangement and warns that proxies changing the client IP affect peer matching;
the DO service uses certificate pinning. Do not intercept TLS or modify content. [3] This exception is
a separate, narrowly scoped firewall and proxy-bypass rule, not a general direct-WAN permit. The supplied
proxy does not configure that rule. If it cannot be approved, do not claim this route is complete; assess
Microsoft's documented Group mode alternative and validate the resulting behavior separately. [3]

Disable DO peer-to-peer sharing with the managed Download Mode `0` if peer exchange is not approved;
this does not disable update downloads. Otherwise explicitly approve the peer scope and required network
ports. [4] The Squid ACL does not control traffic between peers or direct service exceptions.

## 2. Extend the cache policy

For the supplied cache, edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**. Add only the approved
Windows client addresses or CIDRs to the existing `cache_squid_allowed_cidrs` list; retain every existing
entry. Extend the existing `cache_squid_allowed_domains` list with the following candidate entries, each
only if absent; do not paste a second key or replace the existing list:

```yaml
  - .windowsupdate.com
  - .update.microsoft.com
  - .delivery.mp.microsoft.com
  - adl.windows.com
  - tsfe.trafficshaping.dsp.mp.microsoft.com
```

The leading dot permits the base domain and all subdomains; `.delivery.mp.microsoft.com` includes
`*.dl.delivery.mp.microsoft.com`. These are broad domain grants, not URL paths or package approval.
They are candidates derived from Microsoft's Windows 11 Update endpoint list, not a complete, immutable
list for every edition or update. [1] Review observed redirect and CDN destinations against the current
Microsoft documentation and add only approved sources. Do not use wildcard `*` syntax in the Squid list.
The direct DO service exception above is configured outside this list.

The same allowed domain list applies to **all** approved client CIDRs. Adding Windows clients or domains
therefore widens access for existing clients as well; use a separately scoped endpoint or an accepted
alternative if that shared policy exceeds the trust boundary. The supplied explicit proxy uses an
unauthenticated HTTP listener; protect client-to-proxy access at the network boundary. HTTPS is passed in
CONNECT tunnels, without TLS inspection, content scanning or caching. Eligible plain HTTP responses may
be cached, subject to source and cache policy; neither a cache hit nor domain access verifies or approves a
release. Windows retains its publisher and update integrity checks; do not disable them. [5]

For a new pair, return to [Step 4](README.md#step-4-deploy-the-cache-pair). For an existing pair, retain
its inputs and state and continue [Step 2b](step-2b-adopt-update.md);
the `--ansible-only` reconciliation applies these edits. For separately owned existing supply, agree the
equivalent source/client restrictions with its owner; no Tier 2 cache configuration is implied.

## 3. Configure the Windows consumer

After deployment or reconciliation and the general Step 5 checks, configure a representative **Windows
device** through its approved management system:

1. Configure the selected proxy endpoint for Windows Update scanning and downloads. Windows Update
   uses WinHTTP for scanning and BITS or DO for downloads; DO uses Windows Proxy settings and WinHTTP
   automatic discovery. Use a device-wide Windows Proxy policy for signed-in and background contexts.
   Review any existing `netsh` proxy, which can take precedence when nobody is signed in. A `netsh`
   setting alone is not a reliable DO configuration. [3] [6]
2. Configure the approved DO cloud-service bypass and the matching restricted firewall egress from
   action 1. Preserve the site's other bypasses and block unapproved direct routes. Apply the chosen peer
   policy; do not silently open peer or general internet access.
3. Ensure the proxy passes byte-range requests and `Range`, `Content-Range` and `Accept-Ranges` headers
   without modification. DO uses partial downloads; validate this for the actual path. [3]

## 4. Validate a Windows consumer

On the **representative Windows device**, confirm effective settings and the update source through the
management policy and Windows Update settings. Inspect the machine WinHTTP configuration:

```powershell
netsh winhttp show proxy
```

This output alone does not establish the effective DO proxy. Trigger an approved Windows Update scan,
then download an applicable update during the maintenance window. Record the update, Windows version,
scan and download results, time, and any error. On the **same Windows device**, inspect DO activity while
the download is active:

```powershell
Get-DeliveryOptimizationStatus
```

An empty result after a download has finished is not proof of failure or of proxy use. Correlate the
device/time with Squid access logs for the actual content requests and with firewall logs for the DO
service exception. Verify allowed destinations work and an unapproved destination and direct-WAN bypass
are denied; also verify unauthorized client networks cannot use the proxy. Test both signed-in and
unattended service contexts when both are required. A browser request, a successful CONNECT, or the
generic Step 5 test alone does not prove Windows Update or DO is using the intended route.

For a range check, select an approved, reachable **HTTP** content URL that supports ranges. On the
**Windows device**, substitute the actual proxy and URL when prompted:

```powershell
$proxyUrl = Read-Host 'Proxy URL (for example http://10.30.30.22:3128)'
$contentUrl = Read-Host 'Approved HTTP content URL supporting byte ranges'
curl.exe --fail --noproxy "" --proxy $proxyUrl --range 0-1023 --dump-header - --output NUL $contentUrl
```

Require `206 Partial Content` and an appropriate `Content-Range`; check the full path preserves the range
headers. This probe does not prove DO itself used the proxy. If the scan, download, network boundaries or
range behavior fail, retain the existing working route, review client policy and proxy/firewall logs, and
leave the option unaccepted. Record any approved exception and operational evidence in the project
deployment record; installing updates and rebooting remain separate maintenance decisions.

## References

1. [Windows 11 connection endpoints](https://learn.microsoft.com/en-us/windows/privacy/windows-11-endpoints-non-enterprise-editions).
2. [Microsoft Connected Cache content and services endpoints](https://learn.microsoft.com/en-us/windows/deployment/do/delivery-optimization-endpoints).
3. [Using a proxy with Delivery Optimization](https://learn.microsoft.com/en-us/windows/deployment/do/delivery-optimization-proxy).
4. [Delivery Optimization FAQ](https://learn.microsoft.com/en-us/windows/deployment/do/waas-delivery-optimization-faq).
5. [How Delivery Optimization works](https://learn.microsoft.com/en-us/windows/deployment/do/delivery-optimization-workflow).
6. [How the Windows Update client determines its proxy](https://learn.microsoft.com/en-us/troubleshoot/windows-server/installing-updates-features-roles/windows-update-client-determines-proxy-server-connect).
