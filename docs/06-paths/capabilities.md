# Find a capability

Choose a capability, then open its design, installation or operations. Architecture
describes the completed system; deployment stages describe the order in which the
reference is built. An operations link may cover only part of a capability.

| Capability | Architecture | Deployment | Operations |
| --- | --- | --- | --- |
| Software intake | [Intake design](../01-architecture/07-software-intake/README.md) | [Stage 1](../03-deployment/stage-1-software-intake/README.md) | [Intake operations](../05-operations/02-software-intake/README.md) |
| Protected logging | [Logging design](../01-architecture/11-operations/01-protected-logging.md) | [Stage 2](../03-deployment/stage-2-logging/README.md) | [Logging operations](../05-operations/06-resilience/protected-logging.md) |
| Cryptographic trust | [Trust design](../01-architecture/08-cryptography/01-certificate-authority.md) | [Stage 3](../03-deployment/stage-3-trust/README.md) | [Trust operations](../05-operations/03-cryptography/README.md) |
| Kubernetes | [Kubernetes design](../01-architecture/04-hosting/03-kubernetes.md) | [Stage 4](../03-deployment/stage-4-kubernetes/README.md) | [Kubernetes operations](../05-operations/01-hosting/kubernetes-and-labs.md) |
| Identity | [Identity design](../01-architecture/09-identity/README.md) | [Stage 5](../03-deployment/stage-5-identity/README.md) | [Identity operations](../05-operations/04-identity.md) |
| Secrets | [Secrets design](../01-architecture/08-cryptography/08-secrets.md) | [Stage 6](../03-deployment/stage-6-secrets/README.md) | [Secrets operations](../05-operations/03-cryptography/README.md) |
| Delivery | [Delivery design](../01-architecture/10-delivery/README.md) | [Stage 7](../03-deployment/stage-7-delivery/README.md) | [Delivery operations](../05-operations/05-delivery.md) |
| Observability | [Observability design](../01-architecture/11-operations/03-observability.md) | [Stage 8](../03-deployment/stage-8-observability/README.md) | [Observability operations](../05-operations/06-resilience/observability.md) |
| Development platform | [Development design](../01-architecture/10-delivery/03-development-platform.md) | [Stage 9](../03-deployment/stage-9-development/README.md) | [Development operations](../05-operations/05-delivery.md) |
| Lab environments | [Lab design](../01-architecture/04-hosting/04-lab-environments.md) | [Stage 10](../03-deployment/stage-10-lab-environments/README.md) | [Lab operations](../05-operations/01-hosting/kubernetes-and-labs.md) |

For the system as a whole, start with the [platform architecture](../01-architecture/README.md).
The unnumbered [Foundation](../03-deployment/foundation/README.md) prepares hosts,
networks, storage, the bootstrap and templates; its supporting design and operating
guides are linked there.
For implementation ownership and code changes, use the [development map](../04-development/README.md).

[Hardware provider hosts](../03-deployment/stage-3-trust/step-1b-usb-hsm.md) and optional
[PKCS#11 remoting](../03-deployment/stage-3-trust/procedures/pkcs11-remoting.md) belong to Cryptographic trust.
They expose qualified key operations, not an application API. The independent
[signing API](../03-deployment/stage-6-secrets/step-1d-openbao.md) is a separate Stage 6 choice;
neither it nor a different Vault seal is required by the initial PKI/HashiCorp Vault path.
