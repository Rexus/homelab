# Identity and access

Identity establishes subjects and exposes authentication interfaces. Authorization
remains local to each service: a successful login is not permission to administer
the platform. This domain supplies directory authority and federated access to the
[platform architecture](../README.md).

**Deploy:** [Identity](../../03-deployment/stage-5-identity/README.md).
**Operate:** [Identity operations](../../05-operations/04-identity.md).

## Table of contents

- [Terminology](#terminology)
- [Completed design](#completed-design)
- [Service access](#service-access)
- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Administrative authentication](#administrative-authentication)
- [Design constraints](#design-constraints)
- [Detailed views](#detailed-views)
- [Realization](#realization)

## Terminology

Identity and access management (IAM) is the overall capability, not the name of
one VM or product. It includes identity lifecycle, authentication and access
policy. [1] The reference separates these responsibilities:

| Term | Meaning in this design | Reference realization |
| --- | --- | --- |
| Identity management (IdM) / directory authority | Maintain users, groups and enrolled hosts; supply directory, DNS and Kerberos services | FreeIPA primary and replica on dedicated VMs [3] |
| Identity provider (IdP) | Authenticate subjects and provide identity information to relying applications [2] | Keycloak in Tier 0 Kubernetes [4] |
| Single sign-on (SSO) | Reuse a sign-in session across participating services | IdP sessions and configured application integrations [4] |
| Service authorization | Decide which actions an authenticated identity may perform | Each application or cluster's roles and policies |

Keycloak acts as the IdP for the applications. Its connection to the directory is
**LDAP user federation**. **Identity brokering** is a different integration:
delegating authentication to another IdP, such as an upstream OIDC or SAML
provider. [4] The terms are not interchangeable.

## Completed design

This view expands **directory authority (IdM)** and **identity provider (IdP / SSO)**
from the [capability map](../README.md#functional-structure). Ownership, runtime
and service consumption are shown separately.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / applications"]
    Apps["Workload relying parties"]
  end
  subgraph T1["Tier 1 / shared services"]
    Shared["Shared relying parties"]
  end
  Hosts["Other enrolled hosts<br/>DNS / LDAP / Kerberos"]
  subgraph T0[" "]
    direction TB
    T0Title["Tier 0 / Control layer"]
    subgraph Placement[" "]
      direction LR
      subgraph Cluster["Kubernetes / control_cluster network"]
        direction TB
        IdP["Identity provider<br/>IdP / SSO"]
        Data[("IdP state")]
        IdP --> Data
      end
      subgraph Directory["Directory authority / identity network"]
        direction TB
        Primary["Directory primary"] <--> Replica["Directory replica"]
      end
      Cluster -->|Protected LDAP federation| Directory
    end
    T0Title ~~~ Placement
  end
  T2 ~~~ T1
  T1 -->|OIDC to the IdP| T0
  T2 -->|OIDC to the IdP| T0
  Hosts -->|Directory protocols| T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class T2,T1 services
  class T0,Directory control
  class T0Title,Placement controlHeading
  class Cluster runtime
  class Data data
  class Hosts actor
```
*Figure: Tier 1 and Tier 2 relying parties use the Tier 0 identity provider, which federates with the
replicated directory; enrolled hosts use directory protocols.*

In the reference allocation, FreeIPA implements IdM on two dedicated Tier 0 VMs;
Keycloak implements the IdP in the Tier 0 cluster. Their hosting and recovery
remain separate. The IdP's database, TLS and directory failover are explicit
integration requirements, not implied by a replica count or installed by this diagram.

FreeIPA retains one replicated identity CA under the offline root, as a sibling of
the infrastructure issuer. Its certificate inventory and custody remain separate
from the OpenXPKI portal; see the [CA design](../08-cryptography/01-certificate-authority.md).

Arrows identify logical consumers and dependencies, not every browser redirect
or token exchange. [Service access](#service-access) expands
the login interaction. Enrolled hosts consume directory services directly;
applications consume the IdP and retain their own authorization.

## Service access

Published services expose named application endpoints. For an OIDC-capable
service, the IdP uses directory authority and the service applies
its own authorization. This is a logical authentication scenario; exact token
exchanges depend on the selected application integration.

```mermaid
sequenceDiagram
  participant Client as Client
  participant Service as Published service
  participant IdP as Identity provider
  participant Directory as Directory authority
  rect rgba(77, 113, 155, 0.12)
  Client->>Service: HTTPS application request
  Service-->>Client: Authentication required
  end
  rect rgba(57, 115, 102, 0.12)
  Client->>IdP: Authentication through selected OIDC flow
  IdP->>Directory: Configured LDAP user federation or identity lookup
  Directory-->>IdP: Authoritative identity information
  IdP-->>Client: Authentication response
  end
  rect rgba(77, 113, 155, 0.12)
  Client->>Service: Complete the selected login flow
  Service->>Service: Validate identity and apply local authorization
  Service-->>Client: Authorized application response
  end
```

*Figure: A service delegates authentication to an identity provider and applies its own authorization.*

The service endpoint may be reached through the shared edge proxy and application
ingress. This does not publish its administrative interfaces. Direct directory
protocols, machine credentials and non-OIDC services use their own explicit
integration contracts.

## Components and interfaces

| Capability | Reference placement | Supplied interface |
| --- | --- | --- |
| Directory authority (IdM) | Tier 0 / Control; dedicated VMs on `identity` | Host enrollment, directory, DNS and Kerberos |
| Identity provider (IdP / SSO) | Tier 0 / Control; Kubernetes on `control_cluster` | Approved application-facing OIDC endpoints |
| Service authorization | Consuming service and its owning tier | Scoped application or cluster permissions |
| Operator access | Protected administration and independent recovery arrangements | Separately authorized control interfaces |

An IdP is an application-facing service with high-impact identity authority.
Its login endpoint can be consumed from Tier 1 and Tier 2 without exposing its
administration or moving its runtime into the Services zone. The `access`
network can host a deliberately selected front end; it is not the reference
placement of the IdP. A published front end does not bridge networks or grant
directory administration.

| Boundary | Interface and connected function |
| --- | --- |
| Supplied to hosts | Directory enrollment, DNS, LDAP and Kerberos within the selected authority scope |
| Supplied to applications | OIDC identity and group claims; each service owns its permission mappings |
| Consumed from hosting | Dedicated directory runtime and IdP runtime, with scoped lifecycle control |
| Consumed from data services | Directory persistence and the IdP's database/storage contract; [data ownership](../06-data/README.md) remains explicit |
| Consumed from cryptography | Certificate trust, service TLS and supported operator credential integration |
| Consumed from operations | Independent recovery records, backup targets and access/audit visibility |

## Design choices

| Decision | Variants | Consequence |
| --- | --- | --- |
| Authority | A: new dedicated directory pair; B: existing approved authority | B replaces installation with an interface, ownership and recovery contract |
| Normal operator access | Bootstrap credentials; hardware-backed OTP/PIV or appropriate phishing-resistant mechanisms | Credential capability and application support must be verified separately |
| Windows clients | Selected service interoperability; optional [AD-compatible extension](01-windows-integration.md) | An extension does not silently replace the primary identity authority |
| Instance boundary | Shared identity; isolated project/domain authority where justified | Isolation adds enrollment, trust and recovery responsibilities |

User authentication devices and server HSMs have different purposes.
A server's key custody does not by itself provide strong user authentication.

<a id="maturity"></a>

## Administrative authentication

Keep user authentication separate from machine credentials. Constrain Kerberos
delegation, use service principals rather than forwarded user passwords, and prefer
scoped or short-lived SSH/API credentials. A compromised host must not acquire a
reusable identity that grants unrelated service administration.

Hardware-backed OTP/PIV and phishing-resistant FIDO2/WebAuthn are explicit integration
choices, with different supported protocols. Harden privileged users first and retain
the separately authorized recovery path; selecting an identity service does not
configure every application or eliminate bootstrap/recovery passwords.
See [hardware authentication choices](../../03-deployment/stage-6-secrets/step-3b-hardware-authentication.md)
for supplied integration and acceptance boundaries.

## Design constraints

| Concern | Required property |
| --- | --- |
| Authority | Defined namespaces and replication boundaries; one owner for each identity source |
| Authorization | Each consumer maps identity to its own scoped permissions |
| Availability | Directory replication and IdP persistence have separate failure and recovery contracts |
| Recovery | The IdP cannot be the only means to recover itself or replace lost operator credentials |

## Detailed views

- [Windows and AD-compatible integration](01-windows-integration.md) details the optional client extension.
- [Service boundaries](../02-organization/README.md) defines shared and isolated authority consumption.
- [Component allocation](../03-reference-platform.md#service-placement) locates IdM, the IdP and its database.
- [Runtime flows](../README.md) connects authentication to complete service access.

## Realization

Implementation procedures: [directory authority](../../03-deployment/stage-5-identity/procedures/freeipa.md)
and [IdP integration](../../03-deployment/stage-5-identity/README.md#step-2-deploy-identity-federation).
Windows integration is an explicit project option, not a supplied domain installer.

## References

Sources checked 2026-10-09.

1. [NIST: Identity and access management](https://csrc.nist.gov/glossary/term/Identity_and_access_management)
2. [NIST: Identity provider](https://csrc.nist.gov/glossary/term/Identity_Provider)
3. [FreeIPA: About](https://www.freeipa.org/page/About)
4. [Keycloak: Server administration](https://www.keycloak.org/docs/latest/server_admin/index.html)
