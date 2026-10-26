# Step 2b: Spinnaker release pipelines

**Working repository:** `<prefix>-tier-1`.
**Branch from:** [Step 2](README.md#step-2-select-and-qualify-delivery).
**Change:** select release pipelines instead of Argo CD application GitOps.
**Prerequisites:** qualified Tier 1 capacity, external pipeline metadata storage,
reviewed releases, private TLS access and supported identity integration.
This option replaces Argo CD ownership of the selected resources.

## Contents

- [Prepare the native installation](#step-1-prepare-the-native-installation)
- [Create bounded deployment accounts](#step-2-create-bounded-deployment-accounts)
- [Render, review and install](#step-3-render-review-and-install)
- [Deliver the development platform](#step-4-deliver-the-development-platform)
- [References](#references)

## Step 1: Prepare the native installation

Follow the current [native Kustomize installation][1]. Pin its component images
and configuration in the Tier 1 project. Halyard is deprecated; older guides that
recommend `hal deploy apply` are not the selected installation path.
Spinnaker has a larger component/dependency footprint; qualify capacity and
external storage before selecting it for a small installation. [1]

The Tier 1 delivery role supplies a native Kustomize render/apply executor, not a
prequalified site configuration. The official example has cluster-admin bindings,
demo authentication and moving images [4]; the role rejects those defaults.
There is no fallback installation when the local overlay is absent or incomplete.

Follow the [common installer prerequisites](procedures/delivery-installer.md).
Check out an independently reviewed exact official revision inside Tier 1, with
`SPINNAKER_REVISION` set to its full commit ID:

```bash
: "${SPINNAKER_REVISION:?Set the reviewed official Spinnaker commit ID}"
git clone --no-checkout https://github.com/spinnaker/spinnaker.git \
  clusters/tier1/platform/spinnaker-upstream
git -C clusters/tier1/platform/spinnaker-upstream checkout --detach "$SPINNAKER_REVISION"
```

Keep the revision and local overlay under Tier 1 ownership. Create the selected
overlay from that revision's `spinnaker-kustomize/` resources; pin every application,
database, cache and init image to a release or digest. Replace demo configuration
before running the recipe. Do not commit private YAML, account kubeconfigs or passwords.

The runnable overlay contract is:

| Area | Required native configuration |
| --- | --- |
| Resource scope | One selected namespace; namespaced Roles/RoleBindings, no ClusterRole/ClusterRoleBinding or embedded Secret resources |
| Services | Deployments named `clouddriver`, `deck`, `echo`, `fiat`, `front50`, `gate`, `orca`, `rosco`; include any other enabled service dependencies |
| Images/pods | Exact release tags or SHA256 digests, disabled privilege escalation, no host networking/mounts or mounted API tokens |
| Runtime config | Project `spinnaker-runtime` Secret files into every service's `/opt/spinnaker/config/` alongside its native ConfigMaps |
| HTTPS | Ingress for the selected hostname with `spinnaker-tls`; route `/api/v1` to Gate and `/` to Deck as in the upstream native example |
| Identity | Current Spring OAuth2 client registration/provider named `platform` in `gate-local.yml`, exact issuer, authorization-code flow and private client secret [5] |
| Authorization | Enable Fiat in `fiat-local.yml` and `spinnaker-local.yml`; map approved IdP groups and pipeline/account permissions [2] |
| Persistence | Pre-created SQL databases/users/grants and native connection/migration settings for Front50, Orca, Echo, Fiat and Clouddriver; approved cache and backup [6] |
| Trust | Approved IdP/database/API trust, including the JVM truststore where private CA chains are used; no verification bypass |

Use the [secret example](../../../tier-1/ansible/group_vars/delivery_platform_secrets.yml.example)
for the required runtime file keys. Add text database/account Secrets to
`delivery_platform_spinnaker_required_secrets`; provision binary JVM truststores
independently and reference their existing Secret in the overlay. Kustomize must
not generate private Secrets into the rendered resource set.

For current Gate versions, the native identity fragment inside private
`gate-local.yml` is [5]:

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          platform:
            client-id: spinnaker
            client-secret: ${SPINNAKER_OIDC_SECRET}
            scope: openid, profile, email
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/platform"
        provider:
          platform:
            issuer-uri: https://sso.internal.example.com/realms/platform
```

Mount/inject `SPINNAKER_OIDC_SECRET` from the declared private Secret, configure the
exact external Gate URL/forwarded headers, and register its callback with Keycloak.
This fragment alone does not configure service endpoints, Fiat, SQL or accounts.

## Step 2: Create bounded deployment accounts

Register only the intended Tier 1 and selected Tier 2 application destinations.
Use namespace-scoped Kubernetes credentials and separate artifact-source credentials.
Do not give the delivery account Tier 0, hypervisor or infrastructure-state access.
Test allowed actions and denied destinations before ordinary pipeline execution.

## Step 3: Render, review and install

Set `delivery_platform_controller: spinnaker`, the private hostname and
`delivery_platform_spinnaker_overlay` to the absolute tier-local overlay directory.
Follow the [common render command](procedures/delivery-installer.md#render-and-apply).
Review `spinnaker-manifests.yml` and all private runtime settings; set
`delivery_platform_spinnaker_review_sha256` to the value in `spinnaker.sha256`.

Use the same inputs with `delivery_platform_action=apply`. The role rebuilds and
checks that exact hash, validates required Secrets and native OIDC/Fiat/SQL settings,
then applies the complete resources before waiting for workloads and Gate HTTPS.
It does not generate missing application configuration, databases or account grants.

Test SSO with accepted/denied users, direct APIs, pipeline permissions, rejected
accounts and restoration of persistent metadata. The output hash binds rendered
resources; separately owned Secret changes require their own review and pod rollout.

## Step 4: Deliver the development platform

In [Stage 9](../stage-9-development/procedures/gitlab.md), render the same pinned
GitLab chart/values used by the native installer. Configure the selected release
pipeline to obtain the approved chart/values, bake manifests, deploy to the scoped
account and wait for health. Review the native [pipeline stages][3] and artifact
requirements; no site-specific pipeline JSON is invented by this guide.

Prepare required Secrets separately and include runner support manifests in the
same release ownership. A selected pipeline may instead invoke the native
Ansible apply recipe on an authorized **Tier 1** deployment worker.
It must not invoke the privileged Tier 0 infrastructure runner.
Keep one owner per object; stop direct Ansible apply before pipeline ownership.

Test promotion, rejected artifacts/accounts, failed-release behavior, rollback
and restoration of original product data. Bootstrap sources remain independent
until later GitLab source migration is accepted. Tier 0 remains on Flux.
**Return:** [Step 3](README.md#step-3-connect-approved-artifact-supply).

## References

Sources checked 2026-10-26.

1. [Current installation and Halyard deprecation][1].
2. [Authentication configuration][2].
3. [Pipeline concepts and stages][3].
4. [Official Kustomize resources and demo limits][4].
5. [Current Gate Spring OAuth2 configuration][5].
6. [Native SQL configuration and grants][6].

[1]: https://spinnaker.io/docs/setup/install/
[2]: https://spinnaker.io/docs/setup/other_config/security/authentication/
[3]: https://spinnaker.io/docs/concepts/pipelines/
[4]: https://github.com/spinnaker/spinnaker/tree/main/spinnaker-kustomize
[5]: https://spinnaker.io/docs/setup/other_config/security/authentication/oauth/azure/
[6]: https://spinnaker.io/docs/setup/install/storage/
