# Software intake

Software intake supplies selected software sources to consumers in every tier.
It is part of the broader [software lifecycle](../05-software-lifecycle.md), which also
covers source control, builds, artifacts and delivery.

The request sequence applies to any permitted consumer. Cache hits require a fresh,
eligible HTTP response; a miss may populate the cache if the response permits it.

```mermaid
%%{init: {"theme":"base","themeVariables":{"actorBkg":"#edf0f3","actorBorder":"#697682","actorTextColor":"#293642","actorLineColor":"#627581","signalColor":"#627581","signalTextColor":"#1f2937","labelBoxBkgColor":"#f8fafc","labelBoxBorderColor":"#64748b","labelTextColor":"#1f2937","loopTextColor":"#1f2937","noteBkgColor":"#fff2d1","noteBorderColor":"#926820","noteTextColor":"#584013"}}}%%
sequenceDiagram
  participant Consumer as Permitted consumer
  participant Proxy as Policy proxy / HTTP cache
  participant Source as Approved source
  rect rgb(248, 250, 252)
  Consumer->>Proxy: HTTP request or HTTPS CONNECT
  Proxy->>Proxy: Check client, destination and port policy
  alt Denied
    Proxy-->>Consumer: Deny request
  else Allowed cacheable HTTP
    alt Fresh cache hit
      Proxy-->>Consumer: Cached response
    else Cache miss or revalidation
      Proxy->>Source: HTTP request
      Source-->>Proxy: HTTP response
      Proxy-->>Consumer: Response and store if eligible
    end
  else Allowed HTTPS
    Proxy->>Source: Establish tunnel
    Proxy-->>Consumer: Tunnel established
    Consumer->>Source: TLS request through tunnel
    Source-->>Consumer: Encrypted response through tunnel
    Note over Consumer,Source: Encrypted payload is not cached by the proxy
  end
  end
```

*Figure: A consumer’s request is denied or served according to policy; only eligible HTTP responses can be
cached.*

**Architecture:** the [proxy design](01-design.md#transport-and-integrity) describes
transport limits and the [Squid configuration](../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)
defines the reference listener and access policy.

| View | Guide |
| --- | --- |
| Placement, flows and supply choices | [Controlled software intake](01-design.md) |
| Quarantine, verification and publication | [Artifact verification](02-verification.md) |
| Approved images and registries | [Artifact supply](../20-delivery/01-artifact-supply.md) |
| Build the selected path | [Software intake deployment](../../03-deployment/stage-1-software-intake/README.md) |
| Maintain the deployed services | [Software intake operations](../../05-operations/software-intake/README.md) |
