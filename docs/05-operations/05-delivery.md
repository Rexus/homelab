# Delivery and development operations

Maintain the selected controller, approved artifact interfaces, source control and runners.
Use the existing installation inputs; changing a release pin also requires the product's
version-specific migration and rollback procedure.

<a id="figure-delivery-operating-scope"></a>

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":12,"rankSpacing":4,"padding":8,"subGraphTitleMargin":{"top":2,"bottom":8}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T1["Tier 1 / Argo CD and Kubernetes development selection"]
    direction TB
    subgraph Runtime["Existing Tier 1 Kubernetes / platform cluster"]
      direction LR
      subgraph Consumers["Delivery and build execution"]
        direction TB
        CD["argocd<br/>Approved Tier 1 destinations"]
        Runner["gitlab-runner<br/>Manager / isolated job pods"]
        CD ~~~ Runner
      end
      subgraph Supply["Source and artifact services"]
        direction TB
        Git["gitlab<br/>Webservice x2 / Sidekiq x1"]
        Harbor["harbor<br/>Registry / native data services"]
        Git ~~~ Harbor
      end
      Consumers -->|Git / OCI / job API| Supply
    end
    subgraph Data["Dedicated GitLab data VMs / application network"]
      direction TB
      subgraph Services["Three independent data services / TLS"]
        direction LR
        DB["db-1 / PostgreSQL"]
        Cache["kv-1 / Redis"]
        Repo["repo-1 / Gitaly repositories"]
        Repo ~~~ Cache ~~~ DB
      end
      Disks[("Separate live VM disks<br/>Proxmox / Ceph-backed storage")]
      Services -->|Persist| Disks
    end
    Runtime -->|GitLab data interfaces / TLS| Data
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef replicas fill:#f5f6f7,stroke:#89939e,color:#273340,stroke-dasharray:5 4
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class CD,Runner,Git,Harbor,DB,Cache,Repo services
  class Disks data
  classDef group fill:#f5f6f7,stroke:#89939e,color:#273340
  class Consumers,Supply,Services group
  classDef kubernetes fill:#e8eef6,stroke:#6b83a3,color:#263d59
  class Runtime kubernetes
  classDef tier1 fill:#e9e2d8,stroke:#968976,color:#44382a
  class T1 tier1
  classDef zoneServices fill:#e1eaf6,stroke:#4d719b,color:#203a5b
  class Data zoneServices
```

**IaC / Integration:** *Figure: Operating view of the selected Argo CD, Harbor and Kubernetes GitLab/build services,
including GitLab's dedicated data VMs. Chart boxes aggregate their native component sets;
each of the three data VMs retains its own live disk.*
In **`<prefix>-tier-1/`**, [delivery inputs](../../tier-1/ansible/group_vars/delivery_platform.yml.example)
and the [delivery installer](../../tier-1/ansible/playbooks/deployment/delivery-platform.yml) own Argo CD/Harbor;
[development inputs](../../tier-1/ansible/group_vars/development_platform.yml.example) and the
[development installer](../../tier-1/ansible/playbooks/deployment/development-platform.yml) own GitLab/runners.
The [data VM inputs](../../tier-1/terraform/deployments/development-data/terraform.tfvars.example) and
[data installer](../../tier-1/ansible/playbooks/deployment/development-data.yml) own the three data guests.
Existing identity, object storage and backup services retain their own custody.
[Spinnaker](../03-deployment/stage-7-delivery/step-2b-spinnaker.md),
[standalone GitLab](../03-deployment/stage-9-development/step-1b-source-control-vm.md) and
[Podman builds](../03-deployment/stage-9-development/step-14b-podman-runner.md) are replacement selections.
Protected Tier 0 infrastructure execution has its own
[runtime and explicit CI-trust boundary](../03-deployment/stage-9-development/README.md#figure-infrastructure-handover).

**Design:** [Delivery](../01-architecture/10-delivery/README.md) and the
[Development platform](../01-architecture/10-delivery/03-development-platform.md).
**Install:** [Stage 7: Delivery](../03-deployment/stage-7-delivery/README.md) and
[Stage 9: Development platform](../03-deployment/stage-9-development/README.md).

## Find the configuration

In **`<prefix>-tier-1/`**, retain the accepted cluster context and protected inputs:

| Service | Configuration | Implementing playbook |
| --- | --- | --- |
| Harbor and selected Argo CD or Spinnaker | `ansible/group_vars/delivery_platform.yml` and its selected secret inputs | [`deployment/delivery-platform.yml`](../../tier-1/ansible/playbooks/deployment/delivery-platform.yml) |
| GitLab and Kubernetes build runners | `ansible/group_vars/development_platform.yml` and `development_platform_secrets.yml` | [`deployment/development-platform.yml`](../../tier-1/ansible/playbooks/deployment/development-platform.yml) |
| Standalone GitLab VM | `ansible/group_vars/development.yml` and its protected SSO/backup inputs | [`deployment/source-control-vm.yml`](../../tier-1/ansible/playbooks/deployment/source-control-vm.yml) |
| Kubernetes GitLab's data VMs | `ansible/group_vars/development_data.yml` and its protected credentials | [`deployment/development-data.yml`](../../tier-1/ansible/playbooks/deployment/development-data.yml) |
| Podman build runner | `ansible/group_vars/podman_runner.yml` and protected runner credentials | [`deployment/podman-runner.yml`](../../tier-1/ansible/playbooks/deployment/podman-runner.yml) |

Tier 0's protected infrastructure runner has separate ownership and credentials:
use the [infrastructure-runner procedure](../03-deployment/stage-9-development/procedures/infrastructure-runner.md).
Cluster integration directories are separate from these native Ansible installers.

## Choose a task

| Question | Procedure |
| --- | --- |
| How is an accepted installation reconciled? | Repeat the selected [Stage 7](../03-deployment/stage-7-delivery/README.md#main-path) or [Stage 9](../03-deployment/stage-9-development/README.md#main-path) procedure with its existing inputs and render/apply review |
| How are upgrades and rollback prepared? | [Upgrade gate](01-hosting/maintenance.md#upgrade-gate) |
| Which VM or edge maintenance recipe applies? | [Recipe map](01-hosting/ansible-recipes.md#recipe-map) |
| How are GitLab data VMs backed up? | [GitLab data backups](06-resilience/backups/gitlab-data.md) |
| How is the standalone GitLab VM backed up or restored? | [Run its commissioned backup](../03-deployment/stage-9-development/step-1b-source-control-vm.md#5-accept-sso-and-the-first-independent-recovery-set), then [restore an isolated matching-image target](../03-deployment/stage-9-development/step-1b-source-control-vm.md#recover-an-isolated-matching-image-target) |
| How are registry, controller or GitLab data recovered? | [Tier 1 product recovery](06-resilience/recovery/tier-1-products.md) |
| How are shared credentials rotated? | [Credential handling](03-cryptography/secret-handling.md) |
| How are user and administrator rights changed? | [Identity operations](04-identity.md) |

The standalone GitLab recipe owns native OIDC configuration, scheduled encrypted backups and
controller-driven recovery. Its bundled data is separate from the Kubernetes alternative's data VMs;
use the recovery procedure for the selected realization. These recipes reconcile configuration;
product upgrades still require their version-specific migration and rollback checks.
Record access, supply and restore evidence in the project deployment record.
