# Secrets

Secrets provides scoped credential storage, access, audit and independent recovery.
Its deployment also adds control tools and independent monitoring; those services
have their own operational and recovery boundaries.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Consumers["Authorized consumers"] -->|"Scoped access"| Service["Tier 0 secret service"]
  Service -->|"Service state"| State[("Persistent state")]
  Service -->|"Audit events"| Logs["Protected logging"]
  Recovery["Independent recovery custody<br/>Credentials and startup material"] -.->|"Authorized recovery"| Service
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class Consumers actor
  class Service,Logs control
  class State data
  class Recovery custody
```
*Figure: Authorized consumers access the Tier 0 secret service, which retains state and emits protected audit
events; independent custody supports recovery.*

Seal and recovery choices are separate from certificate-signing key custody.

| View | Guide |
| --- | --- |
| Secret-service interfaces and custody | [Cryptography and secrets](../16-cryptography/README.md) |
| Seal choices and independent recovery | [Secret-service seals](../16-cryptography/06-vault-seal.md) |
| Control visibility, inventory and recovery | [Operations and resilience](../24-operations/README.md) |
| Deploy secrets and supporting control services | [Secrets deployment](../../03-deployment/stage-6-secrets/README.md) |
| Operate secret and control services | [Secrets operations](../../05-operations/secrets/README.md) |
