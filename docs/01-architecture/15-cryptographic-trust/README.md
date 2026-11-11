# Cryptographic trust

Cryptographic trust covers offline root custody, online issuance and certificate
consumption. Key-protection choices and verified publication are distinct selections;
the latter is an optional Stage 3 extension of [Software intake](../13-software-intake/README.md).

**Tier 0 trust authority:**

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":30}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart BT
  subgraph Tier0[" "]
    Root["Offline root<br/>Separate custody"]
    Issuer["Infrastructure issuer"]
    Identity["Identity issuing CA"]
    Root -.->|"Ceremony: signs"| Issuer
    Root -.->|"Ceremony: signs"| Identity
  end
  Issuer -->|"Infrastructure certificates"| Consumers["Infrastructure consumers"]
  Identity -->|"Identity certificates"| Hosts["Hosts and identity services"]
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class Tier0,Issuer,Identity control
  class Root custody
  class Consumers,Hosts actor
```
*Figure: An offline root signs certificates for two separately administered Tier 0 issuers, which serve
infrastructure and identity consumers.*

Dashed links are offline signing ceremonies, not network routes. Issuers retain separate administration.

| View | Guide |
| --- | --- |
| Root, issuers, enrollment and publication | [Certificate authority](../16-cryptography/01-certificate-authority.md) |
| Custody choices and constraints | [Key protection](../16-cryptography/03-hsm-selection.md) and [cryptography domain](../16-cryptography/README.md) |
| Verified repository and artifact publication | [Artifact verification](../13-software-intake/02-verification.md) |
| Deploy the selected path and optional verified intake | [Cryptographic trust deployment](../../03-deployment/stage-3-trust/README.md) |
| Operate the selected trust services | [Cryptographic trust operations](../../05-operations/cryptographic-trust/README.md) |
