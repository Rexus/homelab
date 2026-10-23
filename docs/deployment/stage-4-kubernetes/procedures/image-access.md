# Kubernetes node image access

**Working repository:** the owning Tier 0, Tier 1 or Tier 2 repository. Stage 4 uses
`<prefix>-tier-0`; Shared contains no node configuration or cluster state.
**Prerequisites:** accepted [software intake](../../stage-1-software-intake/README.md),
independent bootstrap DNS/time and approved release/image pins.
**Scope:** native Talos configuration for the current Kubernetes implementation;
this procedure does not install a proxy, registry or package mirror.

## Contents

- [Configure node access](#configure-node-access)
- [Select registry mirrors](#select-registry-mirrors)
- [Accept the path](#accept-the-path)
- [References](#references)

## Configure node access

1. Select the approved proxy or retained-image path. Register the actual upstream
   registry, authentication and download/redirect domains in the intake policy.
   Review the selected release's discovery and image-factory requirements as well. [4]
   A successful RPM/APT download does not qualify container-image access.
2. Set `machine_config_patches` in the owning tier's ignored
   `terraform/deployments/kubernetes/terraform.tfvars`. The root passes these
   native patches to the provider after the inventory-derived base configuration. [1]
3. Review the selected pins, then follow the normal [plan/review/apply path](talos-terraform.md#plan-and-deploy).
   Linux Ansible and `common.tfvars` settings are not applied to Talos.

The following template uses an explicit HTTP proxy with unmodified HTTPS tunnels.
Replace every example address/domain with accepted local values. The bootstrap
resolver and time source must work before FreeIPA or this Kubernetes cluster exists. [2]

```hcl
machine_config_patches = [yamlencode({
  machine = {
    env = {
      http_proxy  = "http://cache.example.com:3128"
      https_proxy = "http://cache.example.com:3128"
      no_proxy    = "127.0.0.1,localhost,10.10.13.0/24,10.244.0.0/16,10.96.0.0/12,.example.com,.svc,.cluster.local"
    }
    network = { nameservers = ["10.10.10.53"] }
    time    = { servers = ["10.10.10.123"] }
  }
})]
```

Include all node/control endpoint addresses, node/pod/service CIDRs, internal
registry endpoints and service domains in `no_proxy`. The example is not a
network allocation. DNS and time traffic use their own firewall
rules, not HTTP forwarding. A gateway must deny unapproved direct WAN access;
environment settings alone are not an egress boundary.

Native patches apply to **every node** and can override base settings. Do not
override inventory hostnames, node roles, secrets or install disks accidentally.
Do not store registry passwords or private keys in tracked examples. Inputs,
generated configurations, plans and state require protected storage and backups.
For existing clusters, use the [maintenance constraints](talos-terraform.md#state-and-lifecycle),
not a parallel reboot rollout.

## Select registry mirrors

An approved existing registry can be configured with native Talos registry-mirror
documents in the same ordered patch list. Use the selected release's schema,
including registry authentication and CA trust where needed. To prohibit upstream
fallback for a configured mirror, select `skipFallback: true`; also enforce the
gateway policy. Do not use TLS-verification bypasses. [3]

The HTTP proxy does not retain HTTPS image bodies. Retained mirrors or preloaded
images are a different supply path. Tier 0 bootstrap/recovery must retain an
independent copy of required artifacts; a later Tier 1 Harbor deployment cannot
be its only source. Talos access needed **before** machine configuration requires
the approved image's kernel settings or preloaded artifacts, not this patch alone. [2]

## Accept the path

| Check | Required evidence |
| --- | --- |
| Generated configuration | Expected proxy, DNS/time or mirrors merged with each inventory hostname and approved disk/image |
| Bootstrap | Actual installer, system and CNI images available without unrestricted WAN |
| Internal traffic | Talos API, Kubernetes API, node and service communication remain direct and private |
| Supply policy | Approved downloads succeed; unapproved destinations and direct WAN bypass fail |
| Recovery | Required tools/images remain available with Tier 1/2 services unavailable |

The native configuration test checks provider merging locally with remote resources
overridden. It does not prove image availability, routing, firewall enforcement or
live bootstrap. Record those results before [accepting Stage 4](../README.md#step-3-verify-operation-and-recovery).

## References

Official guidance checked 2026-10-23; match the selected Talos release.

1. [Talos provider native configuration patches](https://github.com/siderolabs/terraform-provider-talos/blob/v0.11.0/docs/data-sources/machine_configuration.md).
2. [Talos proxy, DNS/time and pre-configuration access](https://docs.siderolabs.com/talos/v1.13/networking/corporate-proxies).
3. [Talos registry mirrors and fallback policy](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/images-container-runtime/pull-through-cache).
4. [Talos bootstrap egress domains](https://docs.siderolabs.com/talos/v1.13/networking/egress-domains).
