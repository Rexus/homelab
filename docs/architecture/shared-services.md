# Shared services model

## Table of contents

- [Purpose](#purpose)
- [Why shared services matter](#why-shared-services-matter)
- [Private domain services](#private-domain-services)
- [Passwordless direction](#passwordless-direction)
- [Key custody and cloud boundaries](#key-custody-and-cloud-boundaries)
- [Shared or multiplied](#shared-or-multiplied)
- [Environment model](#environment-model)
- [Path model](#path-model)
- [References](#references)

## Purpose

Use this document to understand why the repository starts with shared
identity, PKI, secrets, and telemetry paths before larger application or lab
deployments.

The goal is modularity. You can deploy the shared services from this repository
or connect later paths to services you already operate.

## Why shared services matter

A private cloud becomes easier to secure and operate when common trust services
are shared instead of rebuilt in every project.

These services give later projects a common base:

| Shared service | What it gives other paths |
| --- | --- |
| DNS and private domain | stable names such as `idm-1.example.com` or `vault-1.corp.example.com` |
| identity | one user and group authority for operators, services, and automation |
| PKI | trusted certificates for internal TLS, mTLS, service identity, and device identity |
| Vault | one controlled place for long-lived secrets, tokens, and service credentials |
| observability and syslog | one place to see health, audit trails, security events, and capacity |

This is not only convenience. It also removes many weak defaults:

- fewer local passwords across unrelated systems
- fewer one-off certificates and self-signed exceptions
- fewer copied API tokens in project repositories
- fewer isolated logs that disappear when a host fails
- fewer teams reinventing the same trust bootstrap

## Private domain services

The private domain path creates a trust base for the environment.

In the reference implementation, that means:

| Layer | Reference implementation | Role |
| --- | --- | --- |
| identity and DNS | `FreeIPA` | shared identity authority, Kerberos, LDAP, DNS, host enrollment |
| PKI | root CA plus issuing CA | private certificate hierarchy for internal services |
| secrets | `Vault` | secret storage and later dynamic credential paths |
| telemetry | OpenTelemetry, syslog, metrics, logs, traces | operational control and audit visibility |
| cryptographic hardening | USB HSM or other HSM path | stronger protection for selected CA or seal keys |

The path is still optional. If you already have a domain, DNS, PKI, Vault, or
telemetry stack, use those systems as prerequisites and configure the later
paths to consume them instead of deploying duplicates.

## Passwordless direction

The repository should move toward public-key and token-based authentication
instead of many reusable passwords.

The preferred direction is:

```text
shared identity
  -> enrolled users, hosts, and groups
  -> certificates, Kerberos, FIDO2, PIV, or other token-backed login
  -> short-lived or scoped credentials from Vault where possible
```

This does not mean passwords disappear from every bootstrap step. It means the
long-term platform should avoid passwords as the normal operator and service
authentication model.

NIST describes passwords as not phishing-resistant, while phishing-resistant
authentication uses cryptographic protocols that prevent an impostor verifier
from reusing captured outputs.[3] CISA also recommends phishing-resistant MFA
as the strongest MFA pattern and highlights FIDO/WebAuthn and PIV-style
approaches.[4]

## Key custody and cloud boundaries

Public cloud key management is useful, but it is not the same as keeping a
private trust root under your own operational control.

Cloud customer-managed keys improve control because they let you manage the key
that protects a provider service. Azure Storage, for example, can use a
customer-managed key stored in Azure Key Vault or Managed HSM.[5] Azure Monitor
describes a model where the service uses managed identity to perform wrap and
unwrap operations against the customer's Key Vault key.[6]

Microsoft's ITAR guidance adds an important distinction: Azure Commercial can
provide controls such as region choice, encryption, customer-managed keys, and
Customer Lockbox, but the compliance boundary is customer-built. Azure
Government adds stronger environment-level commitments around US data storage
and limiting potential access to screened US persons.[13][14] That makes the
cloud choice a compliance architecture decision, not only a key-storage
feature.

AWS has similar patterns. AWS KMS customer managed keys are keys you create,
own, and manage in your AWS account.[7] AWS KMS also supports custom key stores
backed by AWS CloudHSM clusters that you own and manage, and external key
stores for regulated workloads where cryptographic operations use keys in an
external key manager outside AWS.[8][9] AWS CloudHSM is the dedicated
single-tenant HSM option for AWS workloads that need customer-managed HSM
capacity inside a VPC.[10]

That model can be the right answer for cloud workloads. For a private-cloud
trust root, this repository prefers local custody:

- root CA material can stay offline in a ceremony path
- issuing CA keys can be moved toward HSM-backed protection
- Vault seal or recovery paths can be hardened later
- private traffic and internal service identity do not depend on an external
  provider key service

The boundary is practical rather than absolute. Major cloud providers publish
controls around lawful access and government requests. Microsoft states that it
does not give governments direct or unfettered access to customer data and does
not provide governments with encryption keys or the ability to break
encryption.[11] AWS states that the CLOUD Act does not give any government
unfettered or automatic access to data, and that AWS challenges overbroad or
inappropriate requests where it can.[12] At the same time, both providers
publish reports or statements showing that providers can be legally compelled
to disclose some customer content in specific cases.[11][12]

The practical design point is simple: for workloads where key custody and
private trust anchors matter, keeping the root of trust local reduces external
dependency and gives the operator a clearer boundary.

## Shared or multiplied

Not every service should be deployed once, and not every service should be
deployed per project.

Use this split:

| Service type | Default pattern | When to multiply it |
| --- | --- | --- |
| identity and DNS | shared | isolated lab, air-gapped project, or separate administrative domain |
| root CA | shared and offline | separate legal or operational trust boundary |
| issuing CA | shared per trust boundary | project requires separate certificate policy or key custody |
| Vault | shared early | project requires separate secret administration or blast-radius boundary |
| observability | shared early | project has strict isolation, high-risk data, or separate retention policy |
| syslog/security archive | shared with clear source tagging | regulated or high-risk project needs independent archive custody |
| application platform | shared first, then multiplied where needed | teams or projects need source control, CI/CD, GitOps, Kubernetes, or isolated runtime boundaries |

The default private-cloud path is a shared service backbone with isolated
project resources on top. High-risk or air-gapped projects can still bring
their own identity, Vault, observability, or network boundaries.

## Environment model

Use the same path more than once when you need test, lab, dev, stage, or
production.

The repository pattern is:

```text
same logical inventory
same Terraform setup vars by default
separate environment overlays when needed
separate Terraform state per setup and environment
```

Use shared subnets when your network allows it. Override subnets, VLANs, IPs,
or VM sizing only when an environment needs its own network or capacity shape.

Examples:

| Environment need | Pattern |
| --- | --- |
| first validation run | `--env test`, separate state, separate Ansible IP map |
| dev or lab copy | `--env dev` or `--env lab1`, same guest shape unless overridden |
| production | omit `--env`, use the base local files |
| different subnet per environment | add `terraform/common.<env>.tfvars` and `all.<env>.yml` |
| different VM sizes per environment | add `terraform/environments/<setup>/terraform.<env>.tfvars` |

## Path model

Think of the repository as paths that consume shared services:

| Path type | Uses shared identity/PKI/Vault/telemetry | Can be standalone |
| --- | --- | --- |
| shared services path | creates or connects to the shared services | yes |
| HSM and cryptography | consumes PKI/Vault when present | yes |
| system control path | creates shared telemetry services | yes |
| application platform path | should consume shared identity, PKI, Vault, and telemetry | yes |
| isolated project lab | may consume shared services or bring its own | yes |

This keeps the repo useful for two cases:

- a new environment that starts from Proxmox and grows into shared services
- an existing environment where DNS, identity, PKI, secrets, or telemetry
  already exist and only selected paths are deployed

## References

1. [NIST SP 800-145, The NIST Definition of Cloud Computing](https://csrc.nist.gov/pubs/sp/800/145/final)
2. [NIST SP 800-207, Zero Trust Architecture](https://www.nist.gov/publications/zero-trust-architecture)
3. [NIST SP 800-63B, Digital Identity Guidelines](https://pages.nist.gov/800-63-4/sp800-63b.html)
4. [CISA, Implementing Phishing-Resistant MFA](https://www.cisa.gov/sites/default/files/2023-01/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf)
5. [Azure Storage customer-managed keys](https://learn.microsoft.com/en-us/azure/storage/common/customer-managed-keys-overview)
6. [Azure Monitor customer-managed keys](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/customer-managed-keys)
7. [AWS KMS keys](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)
8. [AWS KMS key stores](https://docs.aws.amazon.com/kms/latest/developerguide/key-store-overview.html)
9. [AWS KMS external key stores](https://docs.aws.amazon.com/kms/latest/developerguide/keystore-external.html)
10. [AWS CloudHSM](https://aws.amazon.com/cloudhsm/)
11. [Microsoft Government Requests for Customer Data Report](https://www.microsoft.com/en-us/corporate-responsibility/law-enforcement-requests-report)
12. [AWS CLOUD Act overview](https://aws.amazon.com/compliance/cloud-act/)
13. [Azure ITAR compliance guidance](https://learn.microsoft.com/en-us/azure/compliance/offerings/offering-itar)
14. [Azure and Azure Government feature availability](https://learn.microsoft.com/en-us/azure/security/fundamentals/feature-availability)
