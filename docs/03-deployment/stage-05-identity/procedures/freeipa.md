# FreeIPA authority contract

<a id="deploy-the-identity-authority"></a>
<a id="contents"></a>
<a id="1-initialize-the-existing-foundation-inputs"></a>
<a id="2-add-the-directory-hosts-without-removing-the-issuer"></a>
<a id="3-provision-the-pair"></a>
<a id="4-connect-logging-before-installing-the-realm"></a>
<a id="5-select-the-csr-phase-and-bootstrap-dns"></a>
<a id="6-load-the-bootstrap-passwords"></a>
<a id="7-generate-the-pending-identity-ca-request"></a>
<a id="8-sign-the-csr-offline"></a>
<a id="9-select-completion-with-the-approved-public-chain"></a>
<a id="10-complete-the-primary-then-the-replica"></a>
<a id="11-verify-replication-and-recovery"></a>

Use [Stage 5, actions 1-11](../README.md#step-1-select-and-initialize-the-directory-path) for the
continuous first installation. The existing foundation root owns both issuer and directory resources.
This reference describes the CA/adoption interface, not another provisioning workflow.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).

<a id="before-you-start"></a>
<a id="what-you-configure"></a>
<a id="step-1-configure-and-provision-the-pair"></a>
<a id="step-2-generate-and-sign-the-identity-ca-request"></a>
<a id="step-3-complete-the-primary-and-replica"></a>

## First-install locations

| Work | Stage action |
| --- | --- |
| Select owner, initialize, edit and provision | [1-3](../README.md#step-1-select-and-initialize-the-directory-path) |
| OS forwarding and CA/DNS/password inputs | [4-6](../README.md#step-4-connect-the-new-directory-hosts-to-protected-logging) |
| Public CSR and authorized signing pause | [7-8](../README.md#step-7-generate-the-pending-identity-ca-request) |
| Public-chain completion and replica acceptance | [9-11](../README.md#step-9-select-completion-with-the-approved-chain) |

## External CA integration gate

The reference uses sibling infrastructure and identity CAs signed by the offline
root, not an identity CA subordinate to OpenXPKI. The recipe now orchestrates the
upstream two-phase install; offline signing and chain acceptance remain controlled
operator actions. [1]

| Local setting | Required value / behavior |
| --- | --- |
| `foundation_freeipa_ca_mode` | Fresh examples select `external`; existing local `internal` inputs and the recipe's legacy fallback remain supported |
| `foundation_freeipa_external_phase` | `csr`, then `complete`; the CSR phase never checks incomplete services or installs replicas |
| `foundation_freeipa_csr_directory` | Protected controller handoff directory; default ignored `secrets/identity` |
| `foundation_freeipa_external_cert_files` | Absolute controller paths to the approved identity CA certificate and root/chain |
| `ipareplica_setup_ca: true` | Explicit CA replica, not just a second directory server [2] |

The identity recipe requires IPv6 support on the host even when the site's routed
networks are IPv4-only. Set `baseline_disable_ipv6: false` in existing foundation
inputs; the recipe rejects a disabled IPv6 stack rather than silently installing
an incomplete directory. Install the coordinated Shared collection requirements
(`community.general >= 10.0.0` includes the scoped Kerberos-ticket module).

The recipe maps the selected phase to `ipaserver_external_ca` and
`ipaserver_external_cert_files_from_controller`; the upstream role performs the
native installation. These inputs do not rechain an existing installed domain.

## Existing domains and alternatives

An accepted existing directory retains its original realm, owner and recovery credentials. Verify
LDAPS server name/chain, user/group search bases, a restricted reader, DNS/time, availability and
independent recovery. The supplied federation uses FreeIPA schema; qualify another product explicitly.
Select **1b** in the stage and continue at [action 12](../README.md#step-12-select-the-existing-cluster-and-identity-provider-inputs).

A **fresh internally rooted pair** selects **1c** before installation. Use `foundation_freeipa_ca_mode: internal`,
keep IPv6 localhost, accepted bootstrap DNS and protected passwords, then run the same native identity
recipe once. Skip external CSR/signing; verify CA replication and independent recovery. This retains
FreeIPA's internal root rather than the sibling-CA design. Changing a live domain's mode is not a migration.

Local state remains `.terraform/state/foundation/<env>/terraform.tfstate`. Environment inputs never
create a second writer for an accepted issuer or directory. Rechaining requires tested migration/rollback.

## IaC ownership

| Repository | Path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/](../../../../tier-0/terraform/deployments/foundation) | Identity/issuer VM resources and state |
| Tier 0 | [deployment/identity-freeipa.yml](../../../../tier-0/ansible/playbooks/deployment/identity-freeipa.yml) | Identity-only baseline, CSR pause, completion and replica sequencing |
| Tier 0 | [foundation.yml.example](../../../../tier-0/ansible/group_vars/foundation.yml.example) | Host IPs, domain, CA phase and supported upstream-role mappings |
| Shared | [baseline](../../../../shared/ansible/roles/baseline), [deployment helper](../../../../shared/scripts/deploy.sh) | Reusable preparation/execution; no inventory, CA keys or state ownership |
| External collection | `freeipa.ansible_freeipa.ipaserver`, `ipareplica` | Native product installation and CA replication interfaces |

## References

Sources checked 2026-10-22.

1. [FreeIPA Ansible server role: two-phase external signing](https://github.com/freeipa/ansible-freeipa/blob/master/roles/ipaserver/README.md)
2. [FreeIPA Ansible replica role: explicit CA setup](https://github.com/freeipa/ansible-freeipa/blob/master/roles/ipareplica/README.md)
