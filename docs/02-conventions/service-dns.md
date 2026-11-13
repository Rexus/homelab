# Service DNS names

Clients should know a service by a stable, familiar fully qualified domain name (FQDN), such as
`ldap.corp.example.com` or `git.corp.example.com`. Individual machines keep
their own names, such as `idm-1.corp.example.com`.

The service name follows the interface as its hosting changes. A machine name
identifies one instance for administration, replication and diagnosis.

## Contents

- [Choose the service label](#choose-the-service-label)
- [Choose the domain and scope](#choose-the-domain-and-scope)
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

The default pattern is **`<service>.<internal-domain>`**, for example
`ldap.corp.example.com`. A published service can use the selected external domain,
such as `git.example.com`.

Add a scope only when needed to distinguish services: `<service>.<env>.<domain>`
or `<service>.<project>.<domain>`, such as `db.test.corp.example.com`.
An environment label is optional; it is not required for every production service.
The short-label preference applies to the service label, not the full FQDN.

| Name | Meaning |
| --- | --- |
| `ldap.corp.example.com` | Stable directory-service endpoint for supported clients |
| `idm-1.corp.example.com` | A particular directory server, with its own host identity |

Record domains and service-name patterns in the generated architecture repository's
`platform-standards.md`. Exact records and targets belong to the owning DNS configuration;
machine names remain in inventory and IaC.

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

## References

Sources checked 2026-11-13.

1. [RFC 2181: aliases, MX targets and DNS label limits](https://www.rfc-editor.org/rfc/rfc2181.html).
2. [RFC 2782: service discovery and SRV targets](https://www.rfc-editor.org/rfc/rfc2782.html).
