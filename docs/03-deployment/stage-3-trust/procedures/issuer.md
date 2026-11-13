# Infrastructure issuer runtime contract

<a id="deploy-the-infrastructure-issuer"></a>
<a id="contents"></a>

Follow [Stage 3](../README.md) for the continuous first installation. The same foundation state,
issuer input file and native runtime recipes serve software and qualified hardware custody.
This reference supplies runtime constraints; it is not a second installation.

**Working repository:** `<prefix>-tier-0/`.

<a id="step-1-provision-the-host"></a>
<a id="step-2-install-the-runtime"></a>
<a id="step-3-activate-and-accept-issuance"></a>
<a id="1-select-the-issuer-image"></a>
<a id="2-initialize-foundation-inputs"></a>
<a id="3-edit-the-host-inputs"></a>
<a id="4-provision-the-host-and-data-disk"></a>
<a id="5-build-the-policy-and-prepare-storage"></a>
<a id="6-set-the-runtime-inputs"></a>
<a id="7-load-stable-credentials-and-portal-tls-paths"></a>
<a id="8-install-the-runtime-without-activating-signing"></a>
<a id="9-create-and-sign-the-issuer-request"></a>
<a id="10-start-the-prepared-backend"></a>
<a id="11-activate-the-token-and-accept-issuance"></a>

## Installation handoffs

| Required state | Stage 3 action |
| --- | --- |
| Approved image, inventory and attached disk | [2-3, then 7](../README.md#step-2-initialize-the-issuer-inputs) |
| Reviewed bundle, stable credentials and inactive runtime | [4-9](../README.md#step-4-prepare-the-private-policy) |
| Retained software or hardware key and CSR | [10](../README.md#step-10-prepare-the-issuing-request) |
| Signed public identity installed by IaC | [12](../README.md#step-12-install-public-certificates-and-start-the-prepared-backend) |
| Token activation and acceptance | [13-14](../README.md#step-13-activate-the-selected-token-and-publish) |

## OS and storage qualification

**OS exception:** this native package path requires Debian 12 amd64, not the EL10 image used for
other Linux services. Its LTS end is 2028-06-30; revalidate support and the upgrade milestone. [1][2]

The installer prepares the dedicated stable-by-id data disk, persists its UUID mount and binds
`mysql` beneath it to `/var/lib/mysql` before MariaDB installation. It rejects conflicting mounts,
unregistered existing state and an unmounted database directory containing files. No guest formatting
or manual database copy is required. See the [storage contract](../../../08-reference/openxpki.md#storage).

The role refuses lost/partial schemas, changed package/configuration bindings and changed stable
database/session secrets. Initial database creation is explicit and one-time. It does not migrate
a live database or silently adopt an existing CA. Recovery restores the original state.

## Activation and enrollment boundary

The normal installer never creates signing keys or imports tokens. Public certificate installation
checks pinned fingerprints and the public chain. Runtime activation checks the original mounted
identity, required signer/provider and DataVault recovery paths; a started daemon is not an active token.

The software policy supplies approval workflows, one TLS-server profile and CRL publication. Its
RPC, ACME and SCEP routes are initially denied. OpenXPKI Community does not supply the Enterprise
native ACME feature; an acme2certifier authenticated RPC adapter requires separate qualification. [4][5]
Imported application leaves are valid before such an enrollment integration is accepted.

## IaC ownership

| Repository | Path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/](../../../../tier-0/terraform/deployments/foundation) | Issuer and identity VM resources/state; per-guest image and extra disks |
| Tier 0 | [ansible/roles/openxpki/](../../../../tier-0/ansible/roles/openxpki) | Native package, local database, TLS portal, storage binding and activation checks |
| Tier 0 | [deployment/openxpki.yml](../../../../tier-0/ansible/playbooks/deployment/openxpki.yml), [maintenance/openxpki.yml](../../../../tier-0/ansible/playbooks/maintenance/openxpki.yml) | Issuer-only deployment and read-only inspection |
| Tier 0 | [issuer.yml.example](../../../../tier-0/ansible/group_vars/issuer.yml.example) | Local production input contract |
| Shared | [scripts/deploy.sh](../../../../shared/scripts/deploy.sh) | Reusable execution only; `--playbook` does not select new Terraform state |

## References

Sources checked 2026-10-17.

[1]: https://github.com/openxpki/openxpki/blob/master/QUICKSTART.md
[3]: https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md

1. [OpenXPKI native packages and production configuration][1]
2. [Debian Bookworm lifecycle](https://www.debian.org/releases/bookworm/)
3. [OpenXPKI configuration, schema, token and DataVault setup][3]
4. [OpenXPKI endpoint and edition boundaries](https://openxpki.readthedocs.io/en/master/frontend/endpoints.html)
5. [acme2certifier OpenXPKI integration](https://github.com/grindsa/acme2certifier/blob/master/docs/openxpki.md)
