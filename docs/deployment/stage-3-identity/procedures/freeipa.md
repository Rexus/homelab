# Deploy the identity authority

Deploy the dedicated FreeIPA primary and CA-enabled replica outside Kubernetes.
Keycloak is a later service in the Tier 0 cluster, not part of this recipe.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Design:** [identity authority](../../../architecture/identity/README.md),
[CA hierarchy](../../../architecture/cryptography/certificate-authority.md).
**Prerequisites:** accepted logging/trust, independent SSH/DNS/time, supported Linux
image, repository access and protected bootstrap passwords.

## Contents

- [Step 1: Configure and provision the pair](#step-1-configure-and-provision-the-pair)
- [External CA integration gate](#external-ca-integration-gate)
- [Step 2: Generate and sign the identity CA request](#step-2-generate-and-sign-the-identity-ca-request)
- [Step 3: Complete the primary and replica](#step-3-complete-the-primary-and-replica)
- [Existing domains and alternatives](#existing-domains-and-alternatives)
- [IaC ownership](#iac-ownership)
- [References](#references)

## Step 1: Configure and provision the pair

<a id="before-you-start"></a>
<a id="what-you-configure"></a>

1. Initialize local inputs, using the same context/state used for the issuer in Stage 2:

   ```bash
   bash scripts/init-local-files.sh --setup foundation
   ```

   Retain the same `--env` flag on every command if the issuer used a named environment.
2. Add `idm-1` and `idm-2` to the existing foundation desired guest map, inventory
   and IP map. Do not replace the map with an identity-only file: that would remove
   an already-managed `ca-1`. Select the supported Enterprise Linux image for the
   directory pair, not the Debian CA-specific image. Place replicas on independent
   failure domains and provide stable forward/reverse DNS before installation.
3. Review the whole state, then provision:

   ```bash
   bash scripts/deploy.sh foundation --plan-only
   ```

   After review:

   ```bash
   bash scripts/deploy.sh foundation --terraform-only
   ```

Before the CA/realm installation, register both hosts through
[Stage 1 source forwarding](../../stage-1-logging/sources.md). Verify their OS
security events at Tier 0, then add the actual identity/audit files as they appear.
The FreeIPA recipe does not install the separate log-forwarding role.

| Tier 0 input | Configuration |
| --- | --- |
| `terraform/deployments/foundation/terraform.tfvars` | Guest hardware, image IDs, storage, placement and identity network |
| `ansible/inventory/hosts.yml` | Exactly one `identity_primary`, at least one `identity_replicas` |
| `ansible/group_vars/all.yml` | SSH account/key path, internal domain and hostname decoration |
| `ansible/group_vars/foundation.yml` | Static IPs, identity realm, DNS policy and CA phase |
| Protected controller environment | `FREEIPA_DM_PASSWORD` and `FREEIPA_ADMIN_PASSWORD` |

Keep `root_ca` empty in the connected inventory. It is no longer a child of
`foundation`; the identity recipe targets only `identity`. The issuer and offline
root are never configured by the directory deployment.

Use an internal subdomain such as `internal.example.com`, distinct from the public
website. DNS forwarders, firewall policy and supported software sources must already
work; an [outbound cache](../../foundation/step-3b-outbound-cache.md) is optional.

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

The recipe maps the selected phase to `ipaserver_external_ca` and
`ipaserver_external_cert_files_from_controller`; the upstream role performs the
native installation. These inputs do not rechain an existing installed domain.

## Step 2: Generate and sign the identity CA request

1. Set `foundation_freeipa_ca_mode: external` and
   `foundation_freeipa_external_phase: csr` in local foundation vars. Inject the
   bootstrap passwords through the controller or an
   [Ansible-only secret override](../../../administration/secret-handling/ansible-vault.md).
2. Run the directory recipe against the already-provisioned guests:

   ```bash
   bash scripts/deploy.sh foundation --ansible-only
   ```

   The recipe prepares identity hosts, generates the primary's CSR and fetches it
   as `secrets/identity/<primary-fqdn>-ipa.csr`, distinct across environments. Primary health checks, replica installation
   and final health checks are deliberately deferred.
3. Verify the CSR identity and constraints, then use the separate
   [offline root ceremony](../../stage-2-trust/procedures/offline-root.md).
   Return only the signed identity CA certificate and public chain. Preserve the
   primary's pending installation and private key; never regenerate it to retry a transfer.

## Step 3: Complete the primary and replica

1. Verify the signed certificate matches the pending CSR/key, approved subject,
   subordinate constraints and expected root. Set the local phase to `complete`
   and populate `foundation_freeipa_external_cert_files` with absolute controller
   certificate/chain paths. Keep the same realm, hosts, passwords and state context.
2. Resume with the same command:

   ```bash
   bash scripts/deploy.sh foundation --ansible-only
   ```

   The upstream role completes the primary. Only after `ipactl status` and
   `ipa ping` pass does the CA-enabled replica install serially.
3. Verify directory and DNS replication, certificate issuance on **both** hosts,
   matching identity CA chain and loss of either host. Record the result before
   continuing to the [Kubernetes cluster](kubernetes.md). A passing service check
   alone does not prove CA replication or failure recovery.

For routine read-only service/API checks:

```bash
bash scripts/deploy.sh foundation --recipe maintenance
```

## Existing domains and alternatives

An existing qualified identity service can satisfy this capability without a
duplicate installation. The `internal` CA mode preserves the previous internally
rooted FreeIPA alternative and its normal `foundation` command; it is not the
selected sibling-CA reference. Never switch an existing domain's mode expecting
the installer to migrate it. Rechaining, renewal and recovery require a separately
tested migration with backups and rollback.

Local state remains `.terraform/state/foundation/<env>/terraform.tfstate`.
Environment overlays replace local allocations, not inventory ownership. Follow
[environment isolation](../../../reference/repository-scripts.md#environment-isolation)
for a disposable rehearsal; never create another state owner for the live issuer.

## IaC ownership

| Repository | Path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/](../../../../tier-0/terraform/deployments/foundation/) | Identity/issuer VM resources and state |
| Tier 0 | [deployment/identity-freeipa.yml](../../../../tier-0/ansible/playbooks/deployment/identity-freeipa.yml) | Identity-only baseline, CSR pause, completion and replica sequencing |
| Tier 0 | [foundation.yml.example](../../../../tier-0/ansible/group_vars/foundation.yml.example) | Host IPs, domain, CA phase and supported upstream-role mappings |
| Shared | [baseline](../../../../shared/ansible/roles/baseline/), [deployment helper](../../../../shared/scripts/deploy.sh) | Reusable preparation/execution; no inventory, CA keys or state ownership |
| External collection | `freeipa.ansible_freeipa.ipaserver`, `ipareplica` | Native product installation and CA replication interfaces |

## References

Sources checked 2026-10-22.

1. [FreeIPA Ansible server role: two-phase external signing](https://github.com/freeipa/ansible-freeipa/blob/master/roles/ipaserver/README.md)
2. [FreeIPA Ansible replica role: explicit CA setup](https://github.com/freeipa/ansible-freeipa/blob/master/roles/ipareplica/README.md)
