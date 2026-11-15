# Service DNS names

Clients should know a service by a stable, familiar fully qualified domain name (FQDN), such as
`ldap.internal.example.com` or `git.internal.example.com`. Individual machines keep
their own names, such as `idm-1.corp.example.com`.

The service name follows the interface as its hosting changes. A machine name
identifies one instance for administration, replication and diagnosis.

## Contents

- [Choose the service label](#choose-the-service-label)
- [Choose the domain and scope](#choose-the-domain-and-scope)
- [Select each host's domain](#select-each-hosts-domain)
- [Connect the name to the service](#connect-the-name-to-the-service)
- [Maintain existing names](#maintain-existing-names)
- [References](#references)

## Choose the service label

Prefer familiar lowercase labels, usually **2–8 characters**. Use the service's
function or protocol rather than a VM number, physical location, tier or current
implementation. This is a readability preference, not a DNS restriction: a DNS
label can contain up to 63 octets. [1]

| Function | Familiar labels |
| --- | --- |
| Identity and sign-in | `iam`, `auth`, `idp`, `sso`; select the name matching the interface |
| Directory access | `ldap`; `dc` for a domain-controller interface where present |
| Mail | `smtp`, `imap`, `pop` or `pop3`, `mx` |
| Source control | `git` |
| Outbound proxy | `proxy`, `cache` |
| Database | `db`, or a more specific role such as `pg` |
| File service | `nfs` |
| Certificates and secrets | `ca`, `secrets` |
| Artifact supply | `registry` |
| Logs and metrics | `logs`, `metrics` |
| Release delivery | `cd`, `release` |
| Cluster/API access | `api` |

These are choices for actual service interfaces, not mandatory aliases or a list
of installed capabilities. Existing familiar names such as `vault` or `grafana`
can remain canonical. Choose one canonical name per interface; synonyms do not
need to become additional endpoints.
This convention covers platform-controlled service names; upstream destinations,
protocol discovery labels and native Kubernetes resource names retain their own contracts.

## Choose the domain and scope

The default pattern is **`<service>.<platform_internal_domain>`**, for example
`logs.internal.example.com`. Internal service aliases keep this namespace when their
backend hosts join a directory. A published service can use the selected external
domain, such as `git.example.com`.

Choose either a private subdomain of a registered domain under site control, such as
`internal.example.com`, or a private-use name such as `example.internal`.
IANA selected `.internal` and ICANN permanently reserved it from delegation in the
public DNS root. Both patterns require site-managed internal DNS records and resolution.
`example.com` is reserved for documentation, so replace it with the actual site domain in
a real deployment. [3][4]

Avoid `.local` for the platform's conventional DNS zones. RFC 6762 assigns that
suffix to link-local Multicast DNS, which can conflict with conventional DNS lookup. [5]
This concerns site DNS suffixes; retain filenames such as `.env.local` and the native
Kubernetes `cluster.local` service-discovery namespace.

Add a scope only when needed to distinguish services: `<service>.<env>.<domain>`
or `<service>.<project>.<domain>`, such as `db.test.internal.example.com`.
An environment label is optional; it is not required for every production service.
The short-label preference applies to the service label, not the full FQDN.

| Name | Meaning |
| --- | --- |
| `logs.internal.example.com` | Stable internal logging endpoint |
| `cache.internal.example.com` | Stable internal proxy endpoint |
| `ldap.internal.example.com` | Stable directory-service endpoint for supported clients |
| `idm-1.corp.example.com` | A particular directory server, with its own host identity |

Record domains and service-name patterns in the generated architecture repository's
`platform-standards.md`. Exact records and targets belong to the owning DNS configuration;
machine names remain in inventory and IaC.

## Select each host's domain

Use the host's actual administrative relationship to choose its namespace.

| `platform_domain_role` | Host namespace | Set when |
| --- | --- | --- |
| `standalone` or unset | `platform_internal_domain` | The host is independently administered |
| `member` | `platform_domain` | The host is enrolled in the selected directory domain |
| `authority` | `platform_domain` | Commissioning a directory server or replica |

Fresh inputs use `internal.example.com` for `platform_internal_domain` and
`corp.example.com` for `platform_domain`. A standalone host can therefore be
`log-1.internal.example.com`, while a directory member can be `vm-1.corp.example.com`.
The computed `platform_host_domain` selects the suffix and `platform_fqdn` combines
it with `platform_hostname`. Older inputs without `platform_internal_domain` fall
back to `platform_domain`.

Set the role in inventory, `host_vars`, or the appropriate inventory group. The
directory-authority group declares `authority`. Keep `platform_domain_role` out of
the common `all.yml` extra-var file so per-host selection takes effect.
The naming role records an actual enrollment or commissioning decision. Enrollment
uses the selected directory workflow. Independently administered hosts retain their
approved administrative and recovery access.
Verify domain enrollment and the effective access policy through the directory's
management tools when assessing a host's security.

The input locations and hostname-management switch are documented in the
[platform input contract](../08-reference/platform-inputs.md#host-and-service-domains).

## Connect the name to the service

1. Point the name at the accepted service endpoint: a qualified VIP/balancer or
   an explicitly selected server. A DNS name alone supplies neither failover nor access policy.
2. Configure the listener/ingress, TLS certificate names and client URLs for that
   endpoint. Identity-provider issuer URLs and application callbacks must remain coordinated.
3. Keep protocol-specific server identities and discovery records. A service alias
   does not replace every LDAP/Kerberos/domain-controller member name or native SRV lookup.

Use A/AAAA records or a CNAME only where appropriate for the protocol. MX and SRV
targets must have address records rather than being CNAME aliases. [1][2]
A friendly LDAP alias is usable only when the selected listener, certificate and
authentication method support it; otherwise retain the qualified member/discovery endpoint.

Guest hostname generation does not create these DNS records or service routes.
Use the owning deployment's service-host/URL inputs and its DNS/TLS prerequisites.

## Maintain existing names

Keep working canonical names unless a deliberate change coordinates DNS, certificates,
listeners and consumers. Refresh preserves project-owned inputs; a new example label
does not rename an existing service. Machine identity migration remains a separate
[operation](proxmox-conventions.md#existing-installations).
For existing cache and logging endpoints, follow the
[service-domain cutover](../05-operations/01-hosting/service-domain-cutover.md).

## References

Sources checked 2026-11-15.

1. [RFC 2181: aliases, MX targets and DNS label limits](https://www.rfc-editor.org/rfc/rfc2181.html).
2. [RFC 2782: service discovery and SRV targets](https://www.rfc-editor.org/rfc/rfc2782.html).
3. [ICANN resolution 2024.07.29.06, following IANA's selection of `.internal`](https://www.icann.org/en/board-activities-and-meetings/materials/approved-resolutions-special-meeting-of-the-icann-board-29-07-2024-en).
4. [IANA reserved example domains](https://www.iana.org/domains/reserved).
5. [RFC 6762, Section 3, Multicast DNS names](https://www.rfc-editor.org/rfc/rfc6762.html#section-3).
