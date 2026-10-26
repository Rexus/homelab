# Step 2a: Argo CD application GitOps

**Working repository:** `<prefix>-tier-1`.
**Branch from:** [Step 2](README.md#step-2-select-and-qualify-delivery).
**Change:** select application GitOps instead of Spinnaker release pipelines.
**Prerequisites:** accepted Tier 1 cluster, reviewed controller release, TLS,
independent bootstrap source and Keycloak. This option replaces Spinnaker ownership.

## Step 1: Install and qualify the controller

Use the [native delivery installer](procedures/delivery-installer.md), setting
`delivery_platform_controller: argocd` and an exact `delivery_platform_argocd_version`.
The recipe renders/installs the official Argo Helm chart [1], then configures native
AppProjects. It does not provision Proxmox VMs or a second cluster.

Prepare `argocd-server-tls`, `argocd-secret` and `argocd-oidc` as listed in the
[secret example](../../../tier-1/ansible/group_vars/delivery_platform_secrets.yml.example).
The persistent `argocd-secret` contains a random signing key, bcrypt administrator
password and password-modification timestamp; the chart does not generate a second owner.
The role labels `argocd-oidc` for Argo CD's native Secret reference [5].

Register the existing Keycloak client with callback `https://<argocd-host>/auth/callback`,
group claims and the selected client ID [2]. The native OIDC config uses the supplied
issuer/CA and `$argocd-oidc:clientSecret`. Supply
`delivery_platform_argocd_repository_certificates` as a hostname-to-PEM map for
private Git/chart sources whose CA is outside system trust.
Ingress terminates HTTPS using `argocd-server-tls`; server HTTP is cluster-internal.
Qualify private ingress access, controller workloads and restore before applications.

## Step 2: Restrict sources and destinations

Set exact `delivery_platform_argocd_repositories` and
`delivery_platform_argocd_destinations` namespace lists. The recipe creates a
`platform` AppProject targeting only the local Tier 1 API, disallows cluster-scoped
application resources and empties the default project's permissions [3].
It grants the selected reader group only application reads and the selected Tier 1
administrator group controller administration; unmatched users have no default access.
Those administrators can change controller policy and are trusted Tier 1 principals.
Additional Tier 2 targets require separate reviewed accounts; never register Tier 0.
Use read-only bootstrap repository credentials before Stage 9 GitLab exists.
Test denied sources/destinations and an ordinary user before enabling sync.

## Step 3: Deliver the development platform

In [Stage 9](../stage-9-development/procedures/gitlab.md), render the authoritative
GitLab/runner values with Ansible. Store reviewed **non-secret** values in the
owning Tier 1 repository. Reference the official chart with the exact tested chart
version in an Application; reference the project values file through Argo CD's
supported multi-source Helm configuration. [4]

Provision required Secrets separately from Vault or approved bootstrap inputs.
Include the rendered runner support manifests under the same application owner.
Preview the manifest diff and sync before enabling automated reconciliation.
Do not maintain a second handwritten copy of the GitLab values template.
For an existing bootstrap-installed release, qualify adoption without uninstalling
it and keep pruning disabled until resource/persistence ownership is accepted.

Record application health, rollback and original-data restore. GitLab outage must
not delete running applications. Flux continues to own Tier 0 independently.
**Return:** [Step 3](README.md#step-3-connect-approved-artifact-supply).

## References

Sources checked 2026-10-26.

1. [Official Argo Helm chart][1].
2. [Keycloak OIDC and PKCE][2].
3. [Project boundaries][3].
4. [Helm multi-source value files][4].
5. [Native SSO Secret references][5].

[1]: https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd
[2]: https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/keycloak/
[3]: https://argo-cd.readthedocs.io/en/stable/user-guide/projects/
[4]: https://argo-cd.readthedocs.io/en/stable/user-guide/multiple_sources/
[5]: https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/#sensitive-data-and-sso-client-secrets
