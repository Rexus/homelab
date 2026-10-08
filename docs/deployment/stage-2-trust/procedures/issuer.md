# Establish the issuing service

**Design:** [certificate trust](../../../architecture/reference-platform.md#certificate-trust)
and [key-protection variant](../../../architecture/cryptography/hsm-selection.md).
**Prerequisites:** accepted compute foundation, authorized custodians, selected issuer software and approved
recovery storage. This is an integration procedure, not a complete automated CA installer.

| Step | Action | Evidence |
| --- | --- | --- |
| 1 | Record root and intermediate scope, validity policy, names, consumers and revocation requirements | Approved certificate and custody policy |
| 2 | Select an existing issuer or one independent of the future cluster | Issuer can start and recover with bootstrap inputs |
| 3 | Apply its supported provider integration for the selected A-D custody option | Required algorithms and key attributes work in a disposable test |
| 4 | Perform the authorized root/intermediate ceremony using the selected CA procedure | Approved intermediate certificate, chain and custody record; no connected root route |
| 5 | Configure issuer authorization and distribute public trust material | Approved consumer succeeds; unauthorized consumer fails |
| 6 | Test issuance, renewal, revocation and recovery without the root online | Results retained with the project deployment record |

The foundation Terraform example can supply an issuer host; VM creation does not
install its CA. FreeIPA's directory CA and the shared issuer must follow the chosen
trust design rather than silently creating competing roots.

For a new staged rollout, the `foundation` example contains both identity and CA
hosts. Configure its initial desired VM set for the issuer before applying; use
the [plan and Terraform-only modes](../../../reference/repository-scripts.md#run-a-deployment)
to provision without running the FreeIPA recipe. Install the CA through the chosen
product procedure. The identity stage adds the directory pair to the same root and state;
retain the existing issuer definition. Stage boundaries are not separate state files
or a reason to remove already-managed resources from configuration.

A later move into Kubernetes requires a planned certificate/data migration.
Retain the bootstrap issuer and recovery path until the replacement is accepted.
Select custody in [Step 1](../README.md#step-1-prepare-issuer-and-key-custody), then complete
[Steps 2 and 3](../README.md#step-2-establish-the-certificate-hierarchy) for the hierarchy and issuer acceptance.
