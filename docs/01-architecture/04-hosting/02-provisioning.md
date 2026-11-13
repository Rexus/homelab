# Infrastructure control

Tier 0 owns the hardware-facing control plane. Workload owners describe what
they need; Tier 0 controls how infrastructure operations are authorized and run.
This applies across all tiers, not only to the machines hosting Tier 0 itself.

```mermaid
sequenceDiagram
  actor Operator as Authorized operator
  participant Execute as Protected execution host
  participant State as Owning tier inputs / state
  participant Platform as Proxmox / guests
  Operator->>Execute: Select accepted code and deployment scope
  Execute->>State: Read definitions and existing resource bindings
  Execute->>Platform: Inspect resources and prepare plan
  Execute-->>Operator: Proposed changes
  Operator->>Execute: Accept reviewed scope
  Execute->>Platform: Apply scoped infrastructure changes
  Execute->>State: Record resulting resource bindings
  Execute->>Platform: Configure guests with selected Ansible recipe
  Execute-->>Operator: Results and verification evidence
```

*Figure: Current operator execution uses protected credentials with the owning tier's inputs and
state. Infrastructure creation and guest configuration are separate parts of the same workflow.*

The execution host may be an independent workstation, a bootstrap VM or a protected
runner. Its credentials determine infrastructure authority; the selected repository
determines which resources and state it operates on. The
[deployment helper](../../../shared/scripts/deploy.sh) implements this operator path.
Delegating requests to a controller is a further capability, described below.

## Table of contents

- [Ownership](#ownership)
- [Execution contexts](#execution-contexts)
- [Delegated provisioning](#delegated-provisioning)
- [Request boundary](#request-boundary)
- [Independent operation](#independent-operation)
- [Trusted CI option](#trusted-ci-option)
- [Implementation boundary](#implementation-boundary)

## Ownership

[Tier ownership](../02-organization/01-tier-ownership.md#repository-role) defines the repository split.
Tier 0 controls hardware, networks, templates, credentials, and privileged
execution. Other tiers retain their workload definitions and state roots.

A workload VM does not become Tier 0 just because it runs on a hypervisor.
Conversely, a provisioning controller remains Tier 0 even when every VM it
manages belongs to Tier 2. Guest network attachments consume approved networks;
they do not grant permission to administer the underlying fabric.

Keep the existing tier-local definitions, inventory, and separate state roots.
Workload ownership does not imply access to infrastructure credentials or raw
state. Under delegated execution, Tier 0 must protect the state backend and
serialize writes for each existing root; never create a second state owner.

<a id="bootstrap-before-workloads"></a>

<a id="bootstrap-execution"></a>

## Execution contexts

Protected workstations and protected runner VMs are Tier 0 execution contexts.
Both use the owning tier's definitions and state. Template publication remains
possible without hosted CI or the guests built from those templates. The initial
bootstrap is an independently recoverable execution host, not a permanent hosted CI dependency.

A runner belongs in the management network with separately controlled credentials
and accepted code. In the independently authorized request pattern, Tier 1 source
control coordinates requests while Tier 0 authorizes changes separately. The
[trusted-CI option](#trusted-ci-option) instead accepts its GitLab control plane
as Tier 0 trusted authority. Protecting a Tier 1 branch alone does not protect
Tier 0 from compromise of that service. [Deployment](../../03-deployment/README.md)
defines the bootstrap and runner handover sequence.

<a id="infrastructure-changes"></a>

## Delegated provisioning

The target capability is **Tier 2 self-service through Tier 0-owned automation**.
Tier 0 operators enable and configure the provisioning service in their own
GitOps definitions. Tier 2 users may then request approved VM creation and
updates without administering the infrastructure or changing the controller.

```mermaid
sequenceDiagram
  actor Request as Tier 2 requester
  participant Policy as Tier 0 request policy
  participant Execute as Protected executor
  participant Platform as Infrastructure APIs
  Request->>Policy: Bounded create or update request
  Policy->>Policy: Authorize caller and validate requested scope
  alt Rejected or incomplete request
    Policy-->>Request: Refuse the operation
  else Accepted operation
    Policy->>Execute: Accepted bounded operation
    Execute->>Execute: Select scoped credentials and tier-owned state
    Execute->>Platform: Authorized resource changes
    Platform-->>Execute: Operation result
    Execute-->>Request: Result within the granted scope
  end
  Note over Policy,Platform: Proposed delegation service - project integration, not a supplied controller
```

*Figure: Proposed delegation admits bounded requests before protected execution can reach infrastructure
APIs. The requester receives project-scoped status, never execution credentials or raw state.*

Arrows show the request contract, not a dependency on Tier 2 for control-plane
operation. No implementation or request API is shipped yet.

## Request boundary

Tier 0 defines the permitted request fields and operations. The controller contract is:

| Function | Required guarantee |
| --- | --- |
| Admission | Authenticated requester with verified project/resource ownership |
| Policy | Approved size, quota, image revision, storage and network |
| Planning | Accepted request revision and plan produced with Tier 0-reviewed code |
| Execution | Scoped credentials, state locking and sanitized result |

Preapproved operations may run automatically. Destructive, privileged, or
out-of-policy changes require a separate approval or rejection. A request is
data, not permission to run arbitrary Terraform, providers, provisioners,
Ansible tasks, shell commands, or cluster manifests with Tier 0 credentials.
Do not execute untrusted repository hooks or workload-controlled CI definitions.

| Requested change | Required boundary |
| --- | --- |
| Create or resize a workload VM | approved image/size, project quota, and assigned network/storage |
| Update a guest OS or application | workload-scoped configuration/credentials and maintenance policy |
| Rebuild or replace a VM | explicit lifecycle action, data protection, and rollback/recovery plan |
| Publish a new base template | separate Tier 0 image lifecycle, never a workload user's publish right |
| Alter hosts, networks, policy, or controller permissions | Tier 0 administration, not workload self-service |

A new template version does not update running VMs. Guest patching, rebuilding,
and infrastructure changes remain distinct operations with recorded outcomes.
Return project-scoped status, not infrastructure tokens, raw plans, or state.

## Independent operation

Tier 0 must start, operate, update, and recover without Tier 2 services.
Requests are optional inputs, not runtime or bootstrap dependencies.

- Keep controller definitions, policy, credentials, approved code, and recovery material under Tier 0 control.
- Retain accepted intent and resource records independently of the request source.
- An unavailable request source pauses new requests; it does not stop Tier 0 or delete workloads.
- Missing request files are not deletion approval; require an explicit authorized lifecycle operation.
- Keep local administrative execution available when the controller or hosted tooling is unavailable.

Normal request delivery can use a higher-tier service, but Tier 0 recovery and
existing-resource control must not require that service. Do not let its users
edit the privileged controller, acceptance policy, or shared execution revision.

## Implementation boundary

### Trusted CI option

The selected [development-platform variant](../10-delivery/03-development-platform.md#privileged-ci)
permits direct IaC from a dedicated GitLab project. GitLab and administrators able
to alter its hosting are Tier 0 trusted principals in that option.
It does not provide the independent authorization guarantee described above.
Ordinary lab users still require the bounded request interface; trusted CI is
not permission to execute their code with infrastructure credentials.

Today, the kit provides Tier 0 template publication, control-cluster bootstrap,
and operator-run, per-tier Terraform/Ansible workflows. Those workflows are not
a safe self-service API. Host/network administration still includes manual work.
The `clusters/tierN/` GitOps manifests are adoption starters; tier-owned Ansible
installers separately configure the supported cluster platform and services.
No provisioning controller is enabled by generation.

Retain these roots while developing delegation; do not relocate live inputs or
state as part of a documentation or generator refresh. Before enabling a
controller, choose the request schema, native execution integration, authorization,
state handoff, and outage tests. Validate tenant isolation and reject arbitrary
code before admitting Tier 2 requests. See [Tier 0 bootstrap](../../03-deployment/README.md).
