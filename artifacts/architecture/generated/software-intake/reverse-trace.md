# Reverse software-intake trace

Generated from the built model and its trace records.
Potential review scope is not a failure prediction, requirement satisfaction or test result.

[How to use this](../../../../docs/01-architecture/07-software-intake/03-http-walkthrough.md#follow-a-file-or-test-backwards)

## Contents

- [architecture/README.md](#asset-418b800c7970cb70)
- [architecture/models/HomelabSystemDesign.sysml](#asset-bd477e96b50782ed)
- [architecture/models/platform/SharedPlatform.sysml](#asset-b2dac1c3cfc77bd4)
- [architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml](#asset-f03a3c5946860038)
- [architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml](#asset-175e11f63c90449c)
- [architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml](#asset-2c0596dfe5be28f6)
- [docs/01-architecture/04-hosting/01-runtime.md](#asset-a04266f0e4d143b5)
- [docs/01-architecture/05-networking/01-firewall-policy.md](#asset-87f7d556b1e3a4a6)
- [docs/01-architecture/06-data/README.md](#asset-75c0fafef7898622)
- [docs/01-architecture/07-software-intake/README.md](#asset-0b8248a044bd1a89)
- [docs/01-architecture/08-cryptography/README.md](#asset-a42e88d3f6b40504)
- [docs/01-architecture/09-identity/README.md](#asset-3577990f94cd289b)
- [docs/01-architecture/10-delivery/README.md](#asset-c4b670ee042d095d)
- [docs/01-architecture/11-operations/04-backup-recovery.md](#asset-3212e50d6d27eb97)
- [docs/01-architecture/11-operations/README.md](#asset-e9697f10070118ed)
- [docs/03-deployment/foundation/bootstrap/README.md](#asset-f311949e46479c95)
- [docs/03-deployment/foundation/proxmox/network.md](#asset-d253e29a2f635de0)
- [docs/03-deployment/stage-01-software-intake/README.md](#asset-9009008b14267e83)
- [scripts/architecture/intake_execution.py](#asset-9f0d9a8b6c371af9)
- [shared/ansible/roles/baseline/tasks/package_policy.yml](#asset-47e83cf13c7932c5)
- [shared/ansible/roles/baseline/tasks/repository_proxy.yml](#asset-543b654a2f036539)
- [shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2](#asset-06a8bdffdb0e4919)
- [shared/ansible/roles/baseline/templates/shell-proxy.sh.j2](#asset-bb7c4926b5f1d3c9)
- [shared/ansible/roles/data_volume/tasks/inspect.yml](#asset-88237b3162ff5513)
- [shared/ansible/roles/data_volume/tasks/prepare.yml](#asset-c17f8111083acd29)
- [shared/ansible/roles/data_volume/tasks/validate.yml](#asset-ef35885561e7cd98)
- [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](#asset-d44b6d52e63a3b58)
- [shared/ansible/roles/shared/templates/keepalived.conf.j2](#asset-c6b3512be4afa3c7)
- [tests/apt_repository_fixture.py](#asset-513dd9fb5d6b1143)
- [tests/intake_model_fixture.py](#asset-c8dd6df3e273992c)
- [tests/test_tier_bootstrap_intake.py](#asset-a62c77ccce0c2d9b)
- [tests/test_tier_bootstrap_use_case.py](#asset-6cd21d7b7174987c)
- [tests/test_tier_cache_policy.py](#asset-21a1aae893055343)
- [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](#asset-e03e600d8a738509)
- [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](#asset-3386139f3540e203)
- [tests/test_tier_cache_storage.py](#asset-72a90d0a4543c948)
- [tests/test_tier_deployment_views.py](#asset-b58faa47e4ab6a77)
- [tests/test_tier_intake_behavior.py](#asset-66be6b2175732542)
- [tests/test_tier_intake_comparison.py](#asset-6c284db91da6e75a)
- [tests/test_tier_intake_execution.py](#asset-26e2b56981022125)
- [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](#asset-55c276017e6832cf)
- [tests/test_tier_intake_language.py](#asset-c58290116c204618)
- [tests/test_tier_intake_model.py](#asset-5843495b9f219e02)
- [tests/test_tier_intake_product.py](#asset-0ac0cd75e0962c86)
- [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](#asset-c31ddea0609c8ed0)
- [tests/test_tier_intake_use_cases.py](#asset-addcd3dcff08457e)
- [tests/test_tier_package_policy.py](#asset-0d5aea7abc5cddf4)
- [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](#asset-16dec847c6a173d4)
- [tests/test_tier_software_intake.py](#asset-6806b694d4488385)
- [tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml](#asset-30dda9a37d7d6422)
- [tier-0/ansible/playbooks/proxmox-hosts.yml](#asset-b82436f7ebd18896)
- [tier-0/ansible/roles/proxmox_host/tasks/main.yml](#asset-dda19f9ee3323c39)
- [tier-2/ansible/group_vars/cache.yml.example](#asset-ebba1a30f2dc7fc4)
- [tier-2/ansible/inventory/hosts.yml.example](#asset-b9e92de8207393e0)
- [tier-2/ansible/playbooks/cache.yml](#asset-e8f226cade3ab177)
- [tier-2/ansible/playbooks/deployment/outbound-cache.yml](#asset-7e85dd7d37a52bc8)
- [tier-2/ansible/roles/cache_proxy/defaults/main.yml](#asset-46f1b86a5f364684)
- [tier-2/ansible/roles/cache_proxy/tasks/keepalived.yml](#asset-6e09abed5e677823)
- [tier-2/ansible/roles/cache_proxy/tasks/main.yml](#asset-40706de5f66fc876)
- [tier-2/ansible/roles/cache_proxy/tasks/preflight.yml](#asset-ab18aab7c17d1322)
- [tier-2/ansible/roles/cache_proxy/tasks/services.yml](#asset-adda9e8aba7a56e6)
- [tier-2/ansible/roles/cache_proxy/tasks/squid.yml](#asset-c8eaceaefbdaebd6)
- [tier-2/ansible/roles/cache_proxy/tasks/storage.yml](#asset-bbc988b8b9827065)
- [tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2](#asset-37c09c0559e8e583)
- [tier-2/terraform/common.tfvars.example](#asset-f359ffcc7f4d7ef6)
- [tier-2/terraform/deployments/cache/main.tf](#asset-4c1d3cb35c347615)
- [tier-2/terraform/deployments/cache/terraform.tfvars.example](#asset-bf0d9312d2d757ab)
- [tier-2/terraform/modules/environment_guests/main.tf](#asset-9971688239bead99)
- [tier-2/terraform/modules/vm/main.tf](#asset-198fe597d856e2fb)

<a id="asset-418b800c7970cb70"></a>
## architecture/README.md

[Source asset](../../../../architecture/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-homelab (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: None recorded..


<a id="asset-bd477e96b50782ed"></a>
## architecture/models/HomelabSystemDesign.sysml

[Source asset](../../../../architecture/models/HomelabSystemDesign.sysml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-delivery (source; documented-context); SYS-homelab (source; documented-context); SYS-intake (source; documented-context); SYS-operations (source; documented-context); SYS-platform (source; documented-context); SYS-trust (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-b2dac1c3cfc77bd4"></a>
## architecture/models/platform/SharedPlatform.sysml

[Source asset](../../../../architecture/models/platform/SharedPlatform.sysml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-context (source; documented-context); SYS-platform (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-f03a3c5946860038"></a>
## architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml

[Source asset](../../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-intake (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-175e11f63c90449c"></a>
## architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml

[Source asset](../../../../architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: H-stop (source; implementation-source); VC-http-cache-untrusted (source; implementation-source); VC-http-cache-untrusted (source; implementation-source); VC-http-source-failure (source; implementation-source); VC-http-source-failure (source; implementation-source); VC-http-untrusted (source; implementation-source); VC-http-untrusted (source; implementation-source); X-HTTP (source; implementation-source); X-HTTP (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | H-stop →[depends-on] F-verify |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-stop →[reverse uses-message] SC-http-source-failure |
| Use case | `UC-update` Retrieve and verify software | H-stop →[reverse uses-message] SC-http-source-failure →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-stop →[depends-on] F-verify →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | VC-http-source-failure →[verifies] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | VC-http-cache-untrusted (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | VC-http-source-failure (direct trace) |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | VC-http-untrusted (direct trace) |

Related checks: [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-2c0596dfe5be28f6"></a>
## architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml

[Source asset](../../../../architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-context (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-a04266f0e4d143b5"></a>
## docs/01-architecture/04-hosting/01-runtime.md

[Source asset](../../../../docs/01-architecture/04-hosting/01-runtime.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-servers (source; documented-context); P-virtualization (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-servers →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-virtualization →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | P-virtualization →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-87f7d556b1e3a4a6"></a>
## docs/01-architecture/05-networking/01-firewall-policy.md

[Source asset](../../../../docs/01-architecture/05-networking/01-firewall-policy.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: REQ-egress (source; manual-acceptance); VC-egress (source; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | REQ-egress (direct trace) |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-egress` Demonstrate bypass prevention | VC-egress (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-75c0fafef7898622"></a>
## docs/01-architecture/06-data/README.md

[Source asset](../../../../docs/01-architecture/06-data/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-drives (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-drives →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | P-drives →[reverse depends-on] P-storage →[reverse depends-on] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-0b8248a044bd1a89"></a>
## docs/01-architecture/07-software-intake/README.md

[Source asset](../../../../docs/01-architecture/07-software-intake/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: REQ-custody (source; external-custody); VC-custody (source; external-custody).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | REQ-custody →[reverse depends-on] F-cache |
| Function | `F-http` Fetch content from source | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | REQ-custody (direct trace) |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-custody` Demonstrate independent recovery | VC-custody (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-a42e88d3f6b40504"></a>
## docs/01-architecture/08-cryptography/README.md

[Source asset](../../../../docs/01-architecture/08-cryptography/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-trust (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: None recorded..


<a id="asset-3577990f94cd289b"></a>
## docs/01-architecture/09-identity/README.md

[Source asset](../../../../docs/01-architecture/09-identity/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-trust (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: None recorded..


<a id="asset-c4b670ee042d095d"></a>
## docs/01-architecture/10-delivery/README.md

[Source asset](../../../../docs/01-architecture/10-delivery/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-delivery (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: None recorded..


<a id="asset-3212e50d6d27eb97"></a>
## docs/01-architecture/11-operations/04-backup-recovery.md

[Source asset](../../../../docs/01-architecture/11-operations/04-backup-recovery.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: REQ-custody (source; external-custody); VC-custody (source; external-custody).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | REQ-custody →[reverse depends-on] F-cache |
| Function | `F-http` Fetch content from source | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | REQ-custody (direct trace) |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-custody` Demonstrate independent recovery | VC-custody (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-custody →[reverse depends-on] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | REQ-custody →[reverse depends-on] DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-e9697f10070118ed"></a>
## docs/01-architecture/11-operations/README.md

[Source asset](../../../../docs/01-architecture/11-operations/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: SYS-operations (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: None recorded..


<a id="asset-f311949e46479c95"></a>
## docs/03-deployment/foundation/bootstrap/README.md

[Source asset](../../../../docs/03-deployment/foundation/bootstrap/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: UC-clone (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | UC-clone (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-d253e29a2f635de0"></a>
## docs/03-deployment/foundation/proxmox/network.md

[Source asset](../../../../docs/03-deployment/foundation/proxmox/network.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-cabling (source; documented-context); P-fabric (source; documented-context); P-storage-network (source; documented-context); P-switches (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-fabric →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | P-fabric →[reverse depends-on] P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-9009008b14267e83"></a>
## docs/03-deployment/stage-01-software-intake/README.md

[Source asset](../../../../docs/03-deployment/stage-01-software-intake/README.md)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: REQ-egress (source; manual-acceptance); REQ-integrity (source; manual-acceptance); VC-egress (source; manual-acceptance); VC-integrity (source; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-integrity →[reverse depends-on] F-tunnel |
| Function | `F-verify` Verify before use | REQ-integrity →[reverse depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | REQ-integrity →[reverse depends-on] F-tunnel →[reverse depends-on] S-established →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | REQ-integrity →[reverse depends-on] F-tunnel →[reverse depends-on] S-established →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | REQ-egress →[reverse depends-on] DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | REQ-egress (direct trace) |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-integrity (direct trace) |
| Verification case | `VC-egress` Demonstrate bypass prevention | VC-egress (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | REQ-integrity →[reverse depends-on] F-tunnel →[reverse depends-on] S-established →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-integrity` Assess source and publisher trust | VC-integrity (direct trace) |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-9f0d9a8b6c371af9"></a>
## scripts/architecture/intake_execution.py

[Source asset](../../../../scripts/architecture/intake_execution.py)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: VC-http-cache-untrusted (source; implementation-source); VC-http-source-failure (source; implementation-source); VC-http-untrusted (source; implementation-source); X-HTTP (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Guardrail to recheck | `REQ-integrity` consumerVerification | VC-http-cache-untrusted →[verifies] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | VC-http-source-failure →[verifies] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | VC-http-cache-untrusted (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | VC-http-source-failure (direct trace) |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | VC-http-untrusted (direct trace) |

Related checks: [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py).


<a id="asset-47e83cf13c7932c5"></a>
## shared/ansible/roles/baseline/tasks/package_policy.yml

[Source asset](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-client (source; implementation-source); H-accepted (source; implementation-source); H-rejected (source; implementation-source); H-verify (source; implementation-source); REQ-integrity (source; manual-acceptance); S-verify (source; implementation-source); VC-integrity (source; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-integrity →[reverse depends-on] F-tunnel |
| Function | `F-verify` Verify before use | REQ-integrity →[reverse depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-integrity (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-integrity →[reverse depends-on] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-integrity` Assess source and publisher trust | VC-integrity (direct trace) |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-543b654a2f036539"></a>
## shared/ansible/roles/baseline/tasks/repository_proxy.yml

[Source asset](../../../../shared/ansible/roles/baseline/tasks/repository_proxy.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-client (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-06a8bdffdb0e4919"></a>
## shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2

[Source asset](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: H-accepted (source; implementation-source); H-rejected (source; implementation-source); H-verify (source; implementation-source); S-verify (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py).


<a id="asset-bb7c4926b5f1d3c9"></a>
## shared/ansible/roles/baseline/templates/shell-proxy.sh.j2

[Source asset](../../../../shared/ansible/roles/baseline/templates/shell-proxy.sh.j2)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: UC-clone (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | UC-clone (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-88237b3162ff5513"></a>
## shared/ansible/roles/data_volume/tasks/inspect.yml

[Source asset](../../../../shared/ansible/roles/data_volume/tasks/inspect.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-cache (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-c17f8111083acd29"></a>
## shared/ansible/roles/data_volume/tasks/prepare.yml

[Source asset](../../../../shared/ansible/roles/data_volume/tasks/prepare.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-cache (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-ef35885561e7cd98"></a>
## shared/ansible/roles/data_volume/tasks/validate.yml

[Source asset](../../../../shared/ansible/roles/data_volume/tasks/validate.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-cache (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-d44b6d52e63a3b58"></a>
## shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml

[Source asset](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-c6b3512be4afa3c7"></a>
## shared/ansible/roles/shared/templates/keepalived.conf.j2

[Source asset](../../../../shared/ansible/roles/shared/templates/keepalived.conf.j2)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-513dd9fb5d6b1143"></a>
## tests/apt_repository_fixture.py

[Source asset](../../../../tests/apt_repository_fixture.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: X-HTTP (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py).


<a id="asset-c8dd6df3e273992c"></a>
## tests/intake_model_fixture.py

[Source asset](../../../../tests/intake_model_fixture.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-a62c77ccce0c2d9b"></a>
## tests/test_tier_bootstrap_intake.py

[Source asset](../../../../tests/test_tier_bootstrap_intake.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-client (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-6cd21d7b7174987c"></a>
## tests/test_tier_bootstrap_use_case.py

[Source asset](../../../../tests/test_tier_bootstrap_use_case.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: UC-clone (check; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Use case | `UC-clone` Clone a Git repository over HTTPS | UC-clone (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py).


<a id="asset-21a1aae893055343"></a>
## tests/test_tier_cache_policy.py

[Source asset](../../../../tests/test_tier_cache_policy.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (check; implementation-source); H-cache-rules (check; implementation-source); H-cached (check; implementation-source); H-check (check; implementation-source); H-denied (check; implementation-source); H-fetch (check; implementation-source); H-lookup (check; implementation-source); H-origin (check; implementation-source); H-request (check; implementation-source); H-response (check; implementation-source); H-source-failure (check; implementation-source); H-unavailable (check; implementation-source); REQ-policy (check; implementation-source); S-check (check; implementation-source); S-connect (check; implementation-source); S-denied (check; implementation-source); VC-http-denied (check; implementation-source); VC-http-hit (check; implementation-source); VC-http-miss (check; implementation-source); VC-https (check; manual-acceptance); VC-https-denied (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-policy →[reverse depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | REQ-policy →[reverse depends-on] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-cache-rules →[reverse uses-message] SC-http-miss →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-policy (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | VC-http-denied (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | VC-http-hit (direct trace) |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | VC-http-miss (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | VC-https (direct trace) |
| Verification case | `VC-https-denied` Assess CONNECT denial | VC-https-denied (direct trace) |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/playbooks/deployment/outbound-cache.yml](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-e03e600d8a738509"></a>
## tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy

[Source asset](../../../../tests/test_tier_cache_policy.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-cache-rules (test method; implementation-source); H-cached (test method; implementation-source); H-check (test method; implementation-source); H-denied (test method; implementation-source); H-fetch (test method; implementation-source); H-origin (test method; implementation-source); H-request (test method; implementation-source); H-response (test method; implementation-source); S-check (test method; implementation-source); S-connect (test method; implementation-source); S-denied (test method; implementation-source); VC-http-denied (test method; implementation-source); VC-http-hit (test method; implementation-source); VC-http-miss (test method; implementation-source); VC-https (test method; manual-acceptance); VC-https-denied (test method; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | H-check →[depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | H-cache-rules →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-fetch →[depends-on] F-http |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-cache-rules →[reverse uses-message] SC-http-miss →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-cache-rules →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-policy` admittedSources | H-check →[depends-on] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | VC-http-denied (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | VC-http-hit (direct trace) |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | VC-http-miss (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | VC-https (direct trace) |
| Verification case | `VC-https-denied` Assess CONNECT denial | VC-https-denied (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-3386139f3540e203"></a>
## tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy

[Source asset](../../../../tests/test_tier_cache_policy.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-cache-rules (test method; implementation-source); H-cached (test method; implementation-source); H-check (test method; implementation-source); H-denied (test method; implementation-source); H-fetch (test method; implementation-source); H-origin (test method; implementation-source); H-request (test method; implementation-source); H-response (test method; implementation-source); S-check (test method; implementation-source); S-connect (test method; implementation-source); S-denied (test method; implementation-source); VC-http-denied (test method; implementation-source); VC-http-hit (test method; implementation-source); VC-http-miss (test method; implementation-source); VC-https (test method; manual-acceptance); VC-https-denied (test method; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | H-check →[depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | H-cache-rules →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-fetch →[depends-on] F-http |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-cache-rules →[reverse uses-message] SC-http-miss →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-cache-rules →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-policy` admittedSources | H-check →[depends-on] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | VC-http-denied (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | VC-http-hit (direct trace) |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | VC-http-miss (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | VC-https (direct trace) |
| Verification case | `VC-https-denied` Assess CONNECT denial | VC-https-denied (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-72a90d0a4543c948"></a>
## tests/test_tier_cache_storage.py

[Source asset](../../../../tests/test_tier_cache_storage.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-cache (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-b58faa47e4ab6a77"></a>
## tests/test_tier_deployment_views.py

[Source asset](../../../../tests/test_tier_deployment_views.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-66be6b2175732542"></a>
## tests/test_tier_intake_behavior.py

[Source asset](../../../../tests/test_tier_intake_behavior.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-6c284db91da6e75a"></a>
## tests/test_tier_intake_comparison.py

[Source asset](../../../../tests/test_tier_intake_comparison.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: X-HTTP (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py).


<a id="asset-26e2b56981022125"></a>
## tests/test_tier_intake_execution.py

[Source asset](../../../../tests/test_tier_intake_execution.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-accepted (check; implementation-source); H-lookup (check; implementation-source); H-rejected (check; implementation-source); H-source-failure (check; implementation-source); H-stop (check; implementation-source); H-unavailable (check; implementation-source); VC-http-cache-untrusted (check; implementation-source); VC-http-source-failure (check; implementation-source); VC-http-untrusted (check; implementation-source); X-HTTP (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-cache` Reuse fresh cached content | H-lookup →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-source-failure →[depends-on] F-http |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-lookup →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-lookup →[reverse uses-message] SC-http-untrusted |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-lookup →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | H-source-failure →[depends-on] F-http →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | VC-http-cache-untrusted (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | VC-http-source-failure (direct trace) |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | VC-http-untrusted (direct trace) |

Related checks: [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-55c276017e6832cf"></a>
## tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths

[Source asset](../../../../tests/test_tier_intake_execution.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-accepted (test method; implementation-source); H-lookup (test method; implementation-source); H-rejected (test method; implementation-source); H-source-failure (test method; implementation-source); H-stop (test method; implementation-source); H-unavailable (test method; implementation-source); VC-http-cache-untrusted (test method; implementation-source); VC-http-source-failure (test method; implementation-source); VC-http-untrusted (test method; implementation-source); X-HTTP (test method; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-cache` Reuse fresh cached content | H-lookup →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-source-failure →[depends-on] F-http |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-lookup →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-lookup →[reverse uses-message] SC-http-untrusted |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-lookup →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | H-source-failure →[depends-on] F-http →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | VC-http-cache-untrusted (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | VC-http-source-failure (direct trace) |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | VC-http-untrusted (direct trace) |

Related checks: [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-c58290116c204618"></a>
## tests/test_tier_intake_language.py

[Source asset](../../../../tests/test_tier_intake_language.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: X-HTTP (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |

Related checks: [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py).


<a id="asset-5843495b9f219e02"></a>
## tests/test_tier_intake_model.py

[Source asset](../../../../tests/test_tier_intake_model.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-0ac0cd75e0962c86"></a>
## tests/test_tier_intake_product.py

[Source asset](../../../../tests/test_tier_intake_product.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-accepted (check; implementation-source); H-cached (check; implementation-source); H-denied (check; implementation-source); H-fetch (check; implementation-source); H-origin (check; implementation-source); H-rejected (check; implementation-source); H-request (check; implementation-source); H-response (check; implementation-source); H-stop (check; implementation-source); H-unavailable (check; implementation-source); H-verify (check; implementation-source); X-HTTP (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | H-denied →[depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | H-cached →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-fetch →[depends-on] F-http |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-denied →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-fetch →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-fetch →[reverse uses-message] SC-http-untrusted |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-cached →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | H-denied →[depends-on] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | H-denied →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-fetch →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-fetch →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |

Related checks: [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py).


<a id="asset-c31ddea0609c8ed0"></a>
## tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model

[Source asset](../../../../tests/test_tier_intake_product.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-accepted (test method; implementation-source); H-cached (test method; implementation-source); H-denied (test method; implementation-source); H-fetch (test method; implementation-source); H-origin (test method; implementation-source); H-rejected (test method; implementation-source); H-request (test method; implementation-source); H-response (test method; implementation-source); H-stop (test method; implementation-source); H-unavailable (test method; implementation-source); H-verify (test method; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | H-denied →[depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | H-cached →[depends-on] F-cache |
| Function | `F-http` Fetch content from source | H-fetch →[depends-on] F-http |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-denied →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-fetch →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-fetch →[reverse uses-message] SC-http-untrusted |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | H-cached →[depends-on] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | H-denied →[depends-on] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | H-denied →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-fetch →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-fetch →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |

Related checks: [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py).


<a id="asset-addcd3dcff08457e"></a>
## tests/test_tier_intake_use_cases.py

[Source asset](../../../../tests/test_tier_intake_use_cases.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-member (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-0d5aea7abc5cddf4"></a>
## tests/test_tier_package_policy.py

[Source asset](../../../../tests/test_tier_package_policy.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-accepted (check; implementation-source); H-rejected (check; implementation-source); H-verify (check; implementation-source); S-verify (check; implementation-source); VC-integrity (check; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | H-accepted →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-accepted →[reverse uses-message] SC-http-hit →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-accepted →[depends-on] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-integrity` Assess source and publisher trust | VC-integrity (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py).


<a id="asset-16dec847c6a173d4"></a>
## tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception

[Source asset](../../../../tests/test_tier_package_policy.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: H-verify (test method; implementation-source); S-verify (test method; implementation-source); VC-integrity (test method; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | H-verify →[depends-on] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-verify →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-verify →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-verify →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-verify →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-verify →[reverse uses-message] SC-http-cache-untrusted →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-integrity` consumerVerification | H-verify →[depends-on] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-verify →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | H-verify →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | H-verify →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-verify →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-integrity` Assess source and publisher trust | VC-integrity (direct trace) |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py).


<a id="asset-6806b694d4488385"></a>
## tests/test_tier_software_intake.py

[Source asset](../../../../tests/test_tier_software_intake.py)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-client (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-30dda9a37d7d6422"></a>
## tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml

[Source asset](../../../../tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-client (source; implementation-source); UC-clone (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | UC-clone (direct trace) |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-b82436f7ebd18896"></a>
## tier-0/ansible/playbooks/proxmox-hosts.yml

[Source asset](../../../../tier-0/ansible/playbooks/proxmox-hosts.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-client (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-dda19f9ee3323c39"></a>
## tier-0/ansible/roles/proxmox_host/tasks/main.yml

[Source asset](../../../../tier-0/ansible/roles/proxmox_host/tasks/main.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-client (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-verify` Verify before use | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-client →[reverse typed-by] ACT-client →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-egress` noBypass | DEF-client →[depends-on] REQ-egress |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[depends-on] REQ-integrity |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-accepted →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-stop →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] H-rejected →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-client →[reverse typed-by] L-Consumers →[reverse allocated-to] F-verify →[reverse depends-on] S-verify →[reverse uses-message] SC-https →[reverse depends-on] VC-https |

Related checks: [tests/test_tier_bootstrap_intake.py](../../../../tests/test_tier_bootstrap_intake.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_package_policy.py::PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception](../../../../tests/test_tier_package_policy.py); [tests/test_tier_software_intake.py](../../../../tests/test_tier_software_intake.py).


<a id="asset-ebba1a30f2dc7fc4"></a>
## tier-2/ansible/group_vars/cache.yml.example

[Source asset](../../../../tier-2/ansible/group_vars/cache.yml.example)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-b9e92de8207393e0"></a>
## tier-2/ansible/inventory/hosts.yml.example

[Source asset](../../../../tier-2/ansible/inventory/hosts.yml.example)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-e8f226cade3ab177"></a>
## tier-2/ansible/playbooks/cache.yml

[Source asset](../../../../tier-2/ansible/playbooks/cache.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-7e85dd7d37a52bc8"></a>
## tier-2/ansible/playbooks/deployment/outbound-cache.yml

[Source asset](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source); REQ-policy (check; implementation-source); S-established (source; manual-acceptance); S-fetch (source; manual-acceptance); S-open (source; manual-acceptance); S-ready (source; manual-acceptance); S-response (source; manual-acceptance).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-policy →[reverse depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | REQ-policy →[reverse depends-on] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-established →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-established →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | S-established →[reverse uses-message] SC-https →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-policy (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | S-established →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/playbooks/deployment/outbound-cache.yml](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-46f1b86a5f364684"></a>
## tier-2/ansible/roles/cache_proxy/defaults/main.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source); H-cache-rules (source; implementation-source); H-cached (source; implementation-source); H-check (source; implementation-source); H-denied (source; implementation-source); H-fetch (source; implementation-source); H-lookup (source; implementation-source); H-origin (source; implementation-source); H-request (source; implementation-source); H-response (source; implementation-source); H-source-failure (source; implementation-source); H-unavailable (source; implementation-source); S-check (source; implementation-source); S-connect (source; implementation-source); S-denied (source; implementation-source); VC-http-denied (source; implementation-source); VC-http-hit (source; implementation-source); VC-http-miss (source; implementation-source); VC-https (source; manual-acceptance); VC-https-denied (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-cache-rules →[reverse uses-message] SC-http-miss →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | VC-http-denied (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | VC-http-hit (direct trace) |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | VC-http-miss (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | VC-https (direct trace) |
| Verification case | `VC-https-denied` Assess CONNECT denial | VC-https-denied (direct trace) |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-6e09abed5e677823"></a>
## tier-2/ansible/roles/cache_proxy/tasks/keepalived.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/keepalived.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-40706de5f66fc876"></a>
## tier-2/ansible/roles/cache_proxy/tasks/main.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/main.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-ab18aab7c17d1322"></a>
## tier-2/ansible/roles/cache_proxy/tasks/preflight.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/preflight.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: REQ-policy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-policy →[reverse depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | REQ-policy →[reverse depends-on] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | REQ-policy →[reverse depends-on] DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-policy (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | REQ-policy →[reverse depends-on] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/playbooks/deployment/outbound-cache.yml](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-adda9e8aba7a56e6"></a>
## tier-2/ansible/roles/cache_proxy/tasks/services.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml)

Association: **verification**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (check; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-c8eaceaefbdaebd6"></a>
## tier-2/ansible/roles/cache_proxy/tasks/squid.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/squid.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-proxy →[reverse typed-by] SYS-intake-proxy →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-proxy →[reverse typed-by] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-bbc988b8b9827065"></a>
## tier-2/ansible/roles/cache_proxy/tasks/storage.yml

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/tasks/storage.yml)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-cache (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-cache →[reverse typed-by] SYS-intake-cache →[reverse contains] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-cache →[reverse typed-by] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-cache →[reverse typed-by] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-cache →[reverse typed-by] DISK-cache-1 →[reverse contains] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_storage.py](../../../../tests/test_tier_cache_storage.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-37c09c0559e8e583"></a>
## tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2

[Source asset](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-proxy (source; implementation-source); H-cache-rules (source; implementation-source); H-cached (source; implementation-source); H-check (source; implementation-source); H-denied (source; implementation-source); H-fetch (source; implementation-source); H-lookup (source; implementation-source); H-origin (source; implementation-source); H-request (source; implementation-source); H-response (source; implementation-source); H-source-failure (source; implementation-source); H-unavailable (source; implementation-source); REQ-policy (source; implementation-source); S-check (source; implementation-source); S-connect (source; implementation-source); S-denied (source; implementation-source); S-established (source; manual-acceptance); S-fetch (source; manual-acceptance); S-open (source; manual-acceptance); S-ready (source; manual-acceptance); S-response (source; manual-acceptance); VC-http-denied (source; implementation-source); VC-http-hit (source; implementation-source); VC-http-miss (source; implementation-source); VC-https (source; manual-acceptance); VC-https-denied (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | REQ-policy →[reverse depends-on] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | REQ-policy →[reverse depends-on] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | H-cache-rules →[reverse uses-message] SC-http-miss →[reverse contains] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-proxy →[reverse typed-by] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | REQ-policy (direct trace) |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | VC-http-denied (direct trace) |
| Verification case | `VC-http-hit` Assess admitted cache reuse | VC-http-hit (direct trace) |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | VC-http-miss (direct trace) |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | VC-https (direct trace) |
| Verification case | `VC-https-denied` Assess CONNECT denial | VC-https-denied (direct trace) |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py); [tier-2/ansible/playbooks/deployment/outbound-cache.yml](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml); [tier-2/ansible/roles/cache_proxy/tasks/services.yml](../../../../tier-2/ansible/roles/cache_proxy/tasks/services.yml).


<a id="asset-f359ffcc7f4d7ef6"></a>
## tier-2/terraform/common.tfvars.example

[Source asset](../../../../tier-2/terraform/common.tfvars.example)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: P-network (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-network →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | P-network →[reverse depends-on] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py).


<a id="asset-4c1d3cb35c347615"></a>
## tier-2/terraform/deployments/cache/main.tf

[Source asset](../../../../tier-2/terraform/deployments/cache/main.tf)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-bf0d9312d2d757ab"></a>
## tier-2/terraform/deployments/cache/terraform.tfvars.example

[Source asset](../../../../tier-2/terraform/deployments/cache/terraform.tfvars.example)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source); P-storage (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-storage →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-9971688239bead99"></a>
## tier-2/terraform/modules/environment_guests/main.tf

[Source asset](../../../../tier-2/terraform/modules/environment_guests/main.tf)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] UC-clone |
| Use case | `UC-update` Retrieve and verify software | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).


<a id="asset-198fe597d856e2fb"></a>
## tier-2/terraform/modules/vm/main.tf

[Source asset](../../../../tier-2/terraform/modules/vm/main.tf)

Association: **implementation/context**. Test changes affect the recorded evidence first.

Direct links: DEF-member (source; implementation-source); P-network (source; documented-context); P-storage (source; documented-context); P-virtualization (source; documented-context).

| Concern | Potential review target | Why it appears |
| --- | --- | --- |
| Function | `F-admit` Check request access | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit |
| Function | `F-cache` Reuse fresh cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache |
| Function | `F-http` Fetch content from source | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-http |
| Function | `F-tunnel` Forward HTTPS traffic | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel |
| Scenario | `SC-http-cache-untrusted` Reject untrusted cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted |
| Scenario | `SC-http-denied` Reject a disallowed HTTP request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied |
| Scenario | `SC-http-hit` Reuse a fresh HTTP response | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit |
| Scenario | `SC-http-miss` Retrieve or revalidate HTTP content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss |
| Scenario | `SC-http-source-failure` Stop when the source is unavailable | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure |
| Scenario | `SC-http-untrusted` Reject untrusted source content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted |
| Scenario | `SC-https` Retrieve through source TLS | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https |
| Scenario | `SC-https-denied` Reject a disallowed CONNECT request | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied |
| Use case | `UC-clone` Clone a Git repository over HTTPS | P-network →[reverse contains] P-context →[reverse bound-to] SYS-platform →[reverse depends-on] SYS-intake →[reverse bound-to] ACT-intake →[reverse contains] UC-clone |
| Use case | `UC-update` Retrieve and verify software | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse contains] L-context →[reverse depends-on] UC-update |
| Guardrail to recheck | `REQ-custody` independentRecovery | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[depends-on] REQ-custody |
| Guardrail to recheck | `REQ-integrity` consumerVerification | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-tunnel →[depends-on] REQ-integrity |
| Guardrail to recheck | `REQ-policy` admittedSources | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[depends-on] REQ-policy |
| Verification case | `VC-http-cache-untrusted` Reject untrusted cached content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-cache-untrusted →[reverse depends-on] VC-http-cache-untrusted |
| Verification case | `VC-http-denied` Assess HTTP admission denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] H-check →[reverse uses-message] SC-http-denied →[reverse depends-on] VC-http-denied |
| Verification case | `VC-http-hit` Assess admitted cache reuse | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cached →[reverse uses-message] SC-http-hit →[reverse depends-on] VC-http-hit |
| Verification case | `VC-http-miss` Assess admitted HTTP retrieval | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-miss →[reverse depends-on] VC-http-miss |
| Verification case | `VC-http-source-failure` Return a retrieval error on source failure | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-lookup →[reverse uses-message] SC-http-source-failure →[reverse depends-on] VC-http-source-failure |
| Verification case | `VC-http-untrusted` Reject untrusted retrieved content | P-storage →[reverse depends-on] DISK-cache-1 →[reverse allocated-to] L-Cache →[reverse allocated-to] F-cache →[reverse depends-on] H-cache-rules →[reverse uses-message] SC-http-untrusted →[reverse depends-on] VC-http-untrusted |
| Verification case | `VC-https` Assess CONNECT admission | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https →[reverse depends-on] VC-https |
| Verification case | `VC-https-denied` Assess CONNECT denial | DEF-member →[reverse typed-by] VM-cache-1 →[reverse contains] R-Pair →[reverse allocated-to] L-Proxy →[reverse allocated-to] F-admit →[reverse depends-on] S-check →[reverse uses-message] SC-https-denied →[reverse depends-on] VC-https-denied |

Related checks: [shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml](../../../../shared/ansible/roles/shared/tasks/keepalived_vip_validation.yml); [tests/intake_model_fixture.py](../../../../tests/intake_model_fixture.py); [tests/test_tier_bootstrap_use_case.py](../../../../tests/test_tier_bootstrap_use_case.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_generated_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy](../../../../tests/test_tier_cache_policy.py); [tests/test_tier_deployment_views.py](../../../../tests/test_tier_deployment_views.py); [tests/test_tier_intake_behavior.py](../../../../tests/test_tier_intake_behavior.py); [tests/test_tier_intake_execution.py::IntakeExecutionContracts.test_observed_failure_and_verification_paths](../../../../tests/test_tier_intake_execution.py); [tests/test_tier_intake_model.py](../../../../tests/test_tier_intake_model.py); [tests/test_tier_intake_product.py::NativeIntakeScenarios.test_signed_package_retrieval_matches_model](../../../../tests/test_tier_intake_product.py); [tests/test_tier_intake_use_cases.py](../../../../tests/test_tier_intake_use_cases.py).
