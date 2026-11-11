# APT signature or hash errors through the proxy

Diagnose a failed repository refresh before installing Proxmox updates.
Keep signature, hash and TLS checks enabled; do not add keys or clear caches just to suppress an error.

**Working repository:** `<prefix>-tier-0` owns host configuration; `<prefix>-tier-2` owns the cache pair.
**Run on:** the affected Proxmox host as root, unless another location is named.
**Prerequisites:** the [configured update path](host-updates.md), no concurrent package operation,
and access to the actual cache nodes if the failure persists.

## Contents

- [1. Read the failure](#1-read-the-failure)
- [2. Retry with temporary transport options](#2-retry-with-temporary-transport-options)
- [3. Check the normal path](#3-check-the-normal-path)
- [4. If failures persist](#4-if-failures-persist)

## 1. Read the failure

| Message | Meaning / next action |
| --- | --- |
| Release `Version` changed | Repository metadata changed; this notice alone is not a failed refresh or proof of an OS upgrade [1] |
| `Splitting ... InRelease into data and signature failed` | APT could not split the signed file; malformed/incomplete content or local read/write errors are possible, rather than simply a missing key [2] |
| `Hash Sum mismatch` | Received bytes disagree with authenticated metadata; equal file sizes do not establish integrity [1] |
| Old indexes used / failed files ignored | The refresh is incomplete; stop before package installation |

Retain the failing command/output and its time. A proxy/cache problem is one hypothesis;
these messages alone do not identify which hop or local file failed.

## 2. Retry with temporary transport options

On the **affected Proxmox host**, request fresh responses without HTTP pipelining:

```bash
apt-get -o APT::Update::Error-Mode=any \
  -o Acquire::http::No-Cache=true \
  -o Acquire::https::No-Cache=true \
  -o Acquire::http::Pipeline-Depth=0 \
  -o Acquire::https::Pipeline-Depth=0 update
```

This retains the configured proxy and verification. APT asks the proxy not to reuse cached
responses and sends no pipelined requests. The options apply only to this command. [3]
No reboot or cache deletion is required.

**Expected:** a clean refresh. Success shows this route can deliver acceptable metadata;
it does not distinguish the two options or rule out a transient failure.

## 3. Check the normal path

On the **same Proxmox host**:

```bash
apt-get -o APT::Update::Error-Mode=any update
```

If clean, keep the normal configuration and return to [planned updates](host-updates.md#how-are-proxmox-updates-installed).
Do not make `No-Cache` permanent: it defeats the HTTP cache's purpose. Watch subsequent refreshes;
one successful retry does not prove a recurring problem is fixed.

If the normal command fails again, test **only pipelining disabled**, on the same host:

```bash
apt-get -o APT::Update::Error-Mode=any \
  -o Acquire::http::Pipeline-Depth=0 \
  -o Acquire::https::Pipeline-Depth=0 update
```

Repeated failure with normal settings and success with this option supports a transport-compatibility
workaround. Record that evidence before changing managed inputs; it does not prove every cache entry is sound.

## 4. If failures persist

Check local capacity and the effective configuration on the **affected Proxmox host**:

```bash
df -h /var/lib/apt/lists /tmp /var/tmp
df -i /var/lib/apt/lists /tmp /var/tmp
apt-config dump | grep -Ei 'Proxy|Pipeline-Depth|No-Cache|Error-Mode'
```

Proxy URLs may contain credentials in older local configuration; redact those before sharing output.
Investigate local filesystem/read/write errors as well as the network path.

On the **cache nodes**, correlate `/var/log/squid/access.log` and `/var/log/squid/cache.log` with the
failure time. Compare the same failed URL through each node's approved proxy endpoint, retaining
response headers and downloaded hashes. Do not open direct Internet access on the consumer.

For retained deployments, review **Tier 2 `ansible/group_vars/cache.yml`** against the
[cache migration instructions](../../03-deployment/stage-1-software-intake/step-2b-adopt-update.md#3-reconcile-the-existing-cache).
Local configuration survives refresh; old forced-cache rules may therefore remain until corrected.
Keep diagnostics and failed bytes before any targeted cleanup. `apt-get clean` clears downloaded
package archives, not remote Squid objects; deleting all APT lists or the whole proxy cache is not the first step. [4]

## References

Sources checked 2026-11-10.

1. [APT repository authentication and metadata](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html)
2. [APT signed-file parsing and I/O failures](https://github.com/Debian/apt/blob/main/apt-pkg/contrib/gpgv.cc)
3. [APT HTTP cache controls and pipelining](https://manpages.debian.org/trixie/apt/apt-transport-http.1.en.html)
4. [APT update and clean operations](https://manpages.debian.org/trixie/apt/apt-get.8.en.html)
