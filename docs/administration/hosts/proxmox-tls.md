# Proxmox API certificate tasks

Keep API certificate verification enabled independently of the platform PKI.
Proxmox creates a cluster CA and node certificates during installation; trusting
that CA provides a verified bootstrap path before the issuing service exists. [1]
A later platform-issued API certificate is an optional trust-policy change, not
a prerequisite for removing `insecure = true`.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for Proxmox certificates.
Each consuming tier owns its provider settings; trust must also exist on every
execution host and runner container. Shared owns neither credentials nor CA private keys.
**Prerequisites:** independent console access, authorized host administration,
Linux/WSL tooling with OpenSSL, curl and `ca-certificates`, and a change window.

<a id="contents"></a>

## Find the task

| Question | Task |
| --- | --- |
| Trust the initial Proxmox CA? | [Step 1](#step-1-trust-the-bootstrap-ca), then [Step 3](#step-3-remove-exceptions-and-verify-callers) |
| Install or renew a custom API certificate? | [Step 2](#step-2-adopt-the-platform-pki), then [Step 3](#step-3-remove-exceptions-and-verify-callers) |
| Diagnose rejected TLS or stale bypass settings? | [Caller checks](#step-3-remove-exceptions-and-verify-callers) |
| Check expiry or recover a failed cutover? | [Renewal and rollback](#renewal-and-recovery) |

**Why:** [certificate authority design](../../architecture/cryptography/certificate-authority.md).
Verified bootstrap trust does not require an online platform issuer.

## Step 1: Trust the bootstrap CA

This step assumes the default node certificate is served. If a custom API
certificate is already installed, obtain its approved issuer trust instead.

1. Obtain `/etc/pve/pve-root-ca.pem` through an authenticated administrative channel,
   not an unverified HTTPS download. Compare its SHA-256 fingerprint with the
   value read at the node console. Transfer the public certificate only, never
   the CA private key. [1][7]

   On the selected Proxmox host's console, run as an authorized root operator:

   ```bash
   openssl x509 -in /etc/pve/pve-root-ca.pem -noout -sha256 -fingerprint
   ```

   Console-only transfer is also valid: run `cat /etc/pve/pve-root-ca.pem` there,
   then save the complete public PEM block as
   `$HOME/.config/homelab/trust/pve-root-ca.pem` on the execution host (create the
   directory with `mkdir -p "$HOME/.config/homelab/trust"`). Compare the fingerprint
   on both machines before installing it. Copy no private-key file.

   On the execution host, after independently verifying the SSH host key:

   ```bash
   # Run on boot-1 as automation.
   read -r -p "Verified Proxmox SSH destination (user@host): " PVE_SSH
   mkdir -p "$HOME/.config/homelab/trust"
   scp "$PVE_SSH:/etc/pve/pve-root-ca.pem" "$HOME/.config/homelab/trust/pve-root-ca.pem"
   openssl x509 -in "$HOME/.config/homelab/trust/pve-root-ca.pem" -noout -sha256 -fingerprint
   ```

2. After the fingerprints match, install the approved CA into the execution host's
   trust store. Select **one** operating-system block. System-wide installation
   expands trust for that host; limit it to approved administration environments. [3][4]

   AlmaLinux/Rocky/RHEL-family execution host:

   ```bash
   # Run on boot-1 as automation.
   sudo install -m 0644 "$HOME/.config/homelab/trust/pve-root-ca.pem" \
     /etc/pki/ca-trust/source/anchors/homelab-pve.crt
   sudo update-ca-trust extract
   ```

   Debian/Ubuntu execution host:

   ```bash
   # Run on boot-1 as automation.
   sudo install -m 0644 "$HOME/.config/homelab/trust/pve-root-ca.pem" \
     /usr/local/share/ca-certificates/homelab-pve.crt
   sudo update-ca-certificates
   ```

   WSL and runner containers need their own trust installation; changing the
   Windows or container-host trust store is not the same operation.

3. Select an endpoint whose DNS name or IP is in the certificate's subject
   alternative names (SANs). An arbitrary cluster alias is not automatically
   covered. Check the node certificate from its console with
   `openssl x509 -in /etc/pve/local/pve-ssl.pem -noout -ext subjectAltName`. [5][7]
   Complete [Step 3](#step-3-remove-exceptions-and-verify-callers) now; the platform
   issuer, FreeIPA, Vault and Kubernetes are not required for this bootstrap trust.

The supplied entry points reject TLS bypasses. If bootstrap verification fails,
check the selected endpoint/SAN and installed CA rather than restoring an insecure flag.

## Step 2: Adopt the platform PKI

Skip this step when the verified Proxmox CA remains the selected API trust.
Otherwise, after Stage 3 issuance is accepted:

1. Approve node/API names, renewal ownership and a rollback certificate. Distribute
   the verified platform root to callers **before** changing the server certificate,
   using the same OS trust-store method as Step 1. Retain both approved roots during
   the transition. Keep CA signing keys with their existing custodians.
2. Use the selected issuer's procedure to obtain a server certificate and chain
   with the required SANs and matching node-owned key. Keep API access private;
   this does not require publishing Proxmox through Tier 2 edge services.
3. On each node, install the custom API certificate through the supported
   certificate interface, then verify that node before continuing. Proxmox's
   `pvenode cert set` accepts a PEM chain and an unencrypted PEM server key. [6]

   With approved files already staged on that node, run as an authorized administrator:

   ```bash
   # Run on the selected Proxmox host as an authorized root operator.
   read -r -p "Approved PEM certificate chain file: " API_CHAIN
   read -r -p "Matching protected PEM server key file: " API_KEY
   pvenode cert set "$API_CHAIN" "$API_KEY" --force 1 --restart 1
   ```

   This replaces an existing custom certificate and restarts `pveproxy`; API/GUI
   sessions may be interrupted. Preserve approved rollback material beforehand. [6]
   Protect the server key as a local secret, never in Git or job artifacts.
   Coordinate existing renewal jobs so that only one certificate lifecycle owns this endpoint.

Do not replace Proxmox's internal `pve-ssl.pem` / `pve-ssl.key` or cluster CA files.
Custom API certificates use the separate `pveproxy-ssl` files; the internal cluster
CA remains a different trust boundary. [1] Complete Step 3 before closing the change.

## Step 3: Remove exceptions and verify callers

1. In every consuming tier, review `terraform/deployments/<setup>/providers.tf`.
   Set the Linux provider's explicit argument to:

   ```hcl
   insecure = false
   ```

   All supplied roots now use this setting. Refresh preserves local project edits,
   so review older/customized provider files rather than assuming they changed.
   Remove source-level bypasses as well as stale runner/environment exceptions. The pinned provider's SDK
   path can retain an environment bypass even with explicit HCL `false`; clear both
   `PROXMOX_VE_INSECURE` and the legacy `PM_VE_INSECURE` from inherited settings. [2][8]

   In the current shell:

   Run on `boot-1` as automation.

   ```bash
   unset PROXMOX_VE_INSECURE PM_VE_INSECURE
   ```

   Remove the same overrides from ignored environment files and runner configuration;
   a shell unset does not prevent the deployment wrapper from loading them again.
   Supplied Linux, template and Kubernetes provisioning entry points reject true or
   malformed values before Terraform. Initialization and offline credential export do
   not require an API bypass. Direct Terraform/Packer calls still need their own review.
   No automatic insecure bootstrap flag is supplied; verified Proxmox CA trust is the
   normal bootstrap path, independent of the future platform PKI.

   | Caller | Review |
   | --- | --- |
   | Tier-local Linux roots | Provider argument, ignored environment files and protected runner inputs |
   | Tier 0 template publisher; tier-local Kubernetes | Existing verified-TLS settings and actual execution-host trust |
   | Provider-native environment | Remove both current and legacy insecure flags; review inherited job settings |
   | Packer and other API clients | Their separate verification settings and execution-host trust |

2. On each execution host, test the actual endpoint without a TLS bypass or API token:

   ```bash
   # Run on boot-1 as automation.
   read -r -p "Proxmox API FQDN covered by the certificate: " PVE_FQDN
   curl -q --silent --show-error --output /dev/null --write-out 'HTTP %{http_code}\n' \
     "https://$PVE_FQDN:8006/api2/json/version"
   ```

   A nonzero curl exit or certificate error blocks the change. An HTTP `401` can
   mean TLS succeeded but authentication is required; it is not an access test. [5]
   Test every eligible node and any private API alias used during failover, not
   just the node used for the first plan.

3. Run each caller's existing **plan-only** workflow from its owning tier, with the
   same inputs, environment and state as before. See [deployment commands](../../reference/repository-scripts.md#run-a-deployment),
   [template plans](../virtual-machines/template-lifecycle.md#local-workflow) and
   [cluster plans](../../deployment/stage-4-kubernetes/procedures/talos-terraform.md#plan-and-deploy).
   Certificate cutover needs no VM replacement, state migration or fresh bootstrap.
   Stop on unrelated resource changes. In a disposable TLS test, confirm an
   untrusted CA and a wrong hostname are rejected before recording acceptance.

<a id="renewal-and-recovery"></a>

## How are certificates renewed or a failed cutover recovered?

### Check expiry

On the certificate custodian's host, inspect the retained public leaf/chain:

```bash
# Run on the certificate custodian's host.
read -r -p "Public API certificate/chain file: " API_CHAIN
openssl x509 -in "$API_CHAIN" -noout -dates -subject -issuer -ext subjectAltName
```

Record expiry alerts, renewal/reload ownership and tested rollback in Tier 0 records.
Recheck trust after replacing a host, runner image or Proxmox cluster.

### Renew an accepted endpoint

1. Obtain the approved renewed leaf/chain and matching protected node key using the
   selected issuer. Confirm SANs, expiry and the caller trust path.
2. Repeat [Step 2](#step-2-adopt-the-platform-pki) on one node at a time. Distribute
   new caller trust first if the issuing chain changes; retain approved rollback material.
3. Complete [Step 3](#step-3-remove-exceptions-and-verify-callers) for every affected caller.
   Require verified API access and expected plans before closing the change.

### Roll back a failed change

1. Keep independent console access. Preserve the error and identify the affected node.
2. Reinstall its retained approved API certificate/chain and matching key through the
   supported certificate interface in Step 2. Do not replace/delete the internal
   Proxmox cluster CA or `pve-ssl` files.
3. Repeat the verified caller checks. Stop if the rollback certificate is expired,
   its key is missing or no retained trust accepts it; use the authorized reissuance path.

Keep public roots/fingerprints, endpoint names, independent DNS mappings, tools and
protected certificate/key backups in the recovery kit. A valid retained chain can be
verified without an online issuer, subject to the selected revocation-check policy.
Retire an old caller root only after no required endpoint or recovery path needs it.

## References

Sources checked 2026-10-16.

1. [Proxmox certificate management](https://github.com/proxmox/pve-docs/blob/master/certificate-management.adoc)
2. [BPG provider TLS configuration](https://raw.githubusercontent.com/bpg/terraform-provider-proxmox/v0.112.0/docs/index.md)
3. [RHEL shared certificate trust](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/using-shared-system-certificates_securing-networks)
4. [Debian update-ca-certificates](https://manpages.debian.org/bookworm/ca-certificates/update-ca-certificates.8.en.html)
5. [curl certificate verification](https://curl.se/docs/sslcerts.html)
6. [Proxmox node certificate commands](https://github.com/proxmox/pve-docs/blob/master/generated/pvenode.1-synopsis.adoc)
7. [OpenSSL certificate inspection](https://docs.openssl.org/3.3/man1/openssl-x509/)
8. [BPG SDK provider configuration precedence](https://raw.githubusercontent.com/bpg/terraform-provider-proxmox/v0.112.0/proxmoxtf/provider/provider.go)
