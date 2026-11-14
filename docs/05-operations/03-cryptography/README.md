# Cryptography operations

Maintain Cryptographic trust, signing custody and Secrets using the credential-owning
tier. Keep bootstrap and recovery credentials available independently of these services.

<a id="figure-cryptography-operations"></a>

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":12,"rankSpacing":4,"padding":8,"subGraphTitleMargin":{"top":2,"bottom":8}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T0["Tier 0 / cryptographic trust and Secrets"]
    direction TB
    subgraph Online["Connected runtimes / existing Proxmox"]
      direction LR
      subgraph Cluster["Control Kubernetes / Secrets"]
        direction TB
        subgraph Vault["Vault / Raft servers<br/>Own data / audit PVCs"]
          direction TB
          V0["vault-0"]
          V1["vault-1"]
          V2["vault-2"]
          V0 ~~~ V1 ~~~ V2
        end
      end
      subgraph Directory["identity network / dedicated VMs"]
        direction TB
        subgraph IPA["Existing FreeIPA CA pair"]
          direction TB
          I1["idm-1"]
          I2["idm-2"]
          I1 ~~~ I2
        end
      end
      subgraph Issuer["cryptography network / ca-1 VM"]
        direction TB
        CA["OpenXPKI / portal / publication"]
        State[("scsi1 / issuer state<br/>Database / software key / config")]
        CA -->|Persist| State
      end
      Cluster ~~~ Directory ~~~ Issuer
    end
    subgraph Offline["Separate offline custody / outside connected runtimes"]
      direction LR
      Root["clca / offline root"]
      Recovery["Original CA recovery material<br/>Vault unseal shares / recovery keys"]
      Root ~~~ Recovery
    end
    Online ~~~ Offline
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef replicas fill:#f5f6f7,stroke:#89939e,color:#273340,stroke-dasharray:5 4
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class CA,I1,I2,V0,V1,V2 control
  class Online boundary
  class Vault,IPA replicas
  class Offline,Root,Recovery custody
  class State data
  classDef kubernetes fill:#e8eef6,stroke:#6b83a3,color:#263d59
  class Cluster kubernetes
  classDef tier0 fill:#d8cbb9,stroke:#83715a,color:#352a1e
  class T0 tier0
  classDef zoneControl fill:#c9e0d5,stroke:#397366,color:#173f36
  class Directory,Issuer zoneControl
```

**IaC / Manual:** *Figure: Placement of the software issuer, existing FreeIPA CA pair and Kubernetes Vault
after their respective acceptance. Offline root and recovery custody sit below the connected runtimes;
subordinate certificate transfers are manual ceremonies, not online network routes.*
Tier 0 owns the [foundation VM inputs](../../../tier-0/terraform/deployments/foundation/terraform.tfvars.example),
[issuer inputs](../../../tier-0/ansible/group_vars/issuer.yml.example) and
[issuer installer](../../../tier-0/ansible/playbooks/deployment/openxpki.yml);
the [FreeIPA procedure](../../03-deployment/stage-5-identity/procedures/freeipa.md) owns its separate CA.
[Control-application inputs](../../../tier-0/ansible/group_vars/control_applications.yml.example) and
[Vault values](../../../tier-0/ansible/roles/control_applications/templates/vault-values.yml.j2)
define the three servers and their persistence. Custody remains manual and independently recoverable.
This is the main-path reference selection; use the project's completion records for actual acceptance.
[Hardware custody](../../03-deployment/stage-3-trust/README.md#step-1-prepare-issuer-and-key-custody),
[VM Vault](../../03-deployment/stage-6-secrets/step-1b-vault-vm.md) and
[optional OpenBao signing](../../03-deployment/stage-6-secrets/step-11b-openbao.md) have separate selections.

**Design:** [Cryptography](../../01-architecture/08-cryptography/README.md),
[certificate authorities](../../01-architecture/08-cryptography/01-certificate-authority.md)
and [Secrets](../../01-architecture/08-cryptography/08-secrets.md).
**Install:** [Stage 3: Cryptographic trust](../../03-deployment/stage-3-trust/README.md)
and [Stage 6: Secrets](../../03-deployment/stage-6-secrets/README.md).

## Find the configuration

| Owner | Inputs and supported task |
| --- | --- |
| **`<prefix>-tier-0/`** | `ansible/group_vars/issuer.yml` and protected issuer inputs: [CA controls and renewal](certificate-authority.md) |
| **`<prefix>-tier-0/`** | `ansible/group_vars/hsm.yml`, provider/remoting inputs and original key records: [HSM operations](usb-hsm.md) |
| **`<prefix>-tier-0/`**, Kubernetes Vault | `ansible/group_vars/control_applications.yml`, selected Secret owner and original unseal custody: [cluster Vault](../../03-deployment/stage-6-secrets/procedures/vault-kubernetes.md) |
| **`<prefix>-tier-0/`**, VM Vault | `ansible/group_vars/vault.yml`, original inventory/state and protected API inputs: [VM audit/SSO reconciliation](../../03-deployment/stage-6-secrets/step-1b-vault-vm.md#step-4-configure-audit-and-sso) |
| **`<prefix>-tier-0/`**, optional signing environment | `ansible/group_vars/openbao_signing.yml`, `ansible/inventory/signing.yml` and independent state: [signing API reconciliation and recovery](../../03-deployment/stage-6-secrets/step-11b-openbao.md#5-register-original-hsm-keys-and-workload-clients) |
| Credential-owning tier | Secret locations, consumers and rotation authority: [credential handling](secret-handling.md) |
| Selected Ansible repository | Existing encrypted inputs and password custody: [Ansible Vault](ansible-vault.md) |

## Choose a task

| Question | Procedure |
| --- | --- |
| Is the issuer healthy; how are certificates renewed or revoked? | [Certificate authority](certificate-authority.md) |
| How is an issuer recovered? | [Issuer recovery](issuer-recovery.md) |
| How are HSM replicas maintained or signing custody changed? | [USB HSM](usb-hsm.md), [hardware migration](hardware-migration.md) |
| How are signing clients, PIN rotation and independent recovery checked? | [Signing API acceptance](../../03-deployment/stage-6-secrets/step-11b-openbao.md#6-accept-operation-and-independent-recovery); keep original key identity and snapshots separate from hardware backups |
| Which custody controls must remain in place? | [Security controls](security-controls.md) |
| How is a password, token or encrypted input rotated? | [Credential handling](secret-handling.md), [Ansible Vault](ansible-vault.md) |
| How are control-service copies scheduled and Vault snapshots authorized? | [Control backups](../06-resilience/backups/control-applications.md), [snapshot authentication](../06-resilience/recovery/vault-backup-auth.md) |
| How are Vault or NetBox restored? | [Vault recovery](../06-resilience/recovery/vault.md), [NetBox recovery](../06-resilience/recovery/netbox.md) |
| Where are Headlamp and independent monitoring checks? | [Control applications](../../03-deployment/stage-6-secrets/procedures/control-applications.md), [independent monitoring](../../03-deployment/stage-6-secrets/procedures/independent-monitoring.md) |
| How is the Proxmox API certificate trusted or rotated? | [Proxmox TLS](../01-hosting/proxmox-tls.md) |
| How is verified publication operated after trust exists? | [Software intake](../02-software-intake/verified-publication.md) |

Use the [CA acceptance matrix](certificate-authority.md#acceptance-evidence) and selected
stage's initialization, unseal and recovery checks before recording completion.
