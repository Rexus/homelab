# Vault bootstrap

## Table of contents

- [Purpose](#purpose)
- [Recommended pattern](#recommended-pattern)
- [Bootstrap inputs](#bootstrap-inputs)
- [Day 1 flow](#day-1-flow)
- [Handoff to the next deployment](#handoff-to-the-next-deployment)
- [On-prem HSM notes](#on-prem-hsm-notes)
- [Path to higher availability](#path-to-higher-availability)
- [Read more](#read-more)

## Purpose

Use the first managed VM to establish Vault as early as possible so bootstrap
secrets stay short-lived and the next deployment can move onto a real secret
system instead of extending environment-variable sprawl.

```mermaid
flowchart LR
  A[Local bootstrap shell] --> B[Terraform creates first managed VM]
  B --> C[Ansible bootstrap playbook]
  C --> D[Vault service installed and sealed]
  D --> E[Operator init and unseal]
  E --> F[Shared secrets move into Vault]
  F --> G[Continue broader deployment]
```

Figure: the first managed VM becomes the handoff point from bootstrap-only
secrets to the long-term secret platform.

## Recommended pattern

For this repository, the preferred bootstrap pattern is:

- one dedicated Vault VM in the management zone
- Vault with Integrated Storage (Raft), not Consul storage
- TLS enabled from the first startup
- package and systemd based installation, not background shell processes
- default Shamir seal for the first node unless a supported cloud KMS or HSM is
  already available
- later expansion to a three-node or five-node Raft cluster when higher
  availability is needed

The current Ansible scaffold targets the AlmaLinux or RHEL-family reference
image because that is the repository's current guest operating system path.

## Bootstrap inputs

Keep the off-Vault bootstrap material as small as possible:

- Proxmox API access for Terraform
- DNS name and IP address for the first Vault node
- TLS certificate, private key, and CA file for the Vault listener
- operator plan for initialization, unseal shares, and root-token handling
- ignored local files such as `ansible/group_vars/vault.yml`

The repository includes these relevant paths:

- `terraform/environments/bootstrap/terraform.tfvars.example`
- `ansible/inventory/hosts.yml.example`
- `ansible/group_vars/vault.yml.example`
- `ansible/playbooks/bootstrap.yml`

## Day 1 flow

1. Use the Terraform bootstrap environment to provision the first VM as a
   dedicated Vault host.
2. Place that host in the Ansible `vault` inventory group.
3. Copy `ansible/group_vars/vault.yml.example` to
   `ansible/group_vars/vault.yml` and set the listener addresses and TLS file
   paths.
4. Run `ansible-playbook -i inventory/hosts.yml playbooks/bootstrap.yml` from
   the `ansible/` directory.
5. Verify the Vault service is running but still sealed.
6. Initialize Vault with an operator-reviewed command, for example:

```bash
vault operator init -key-shares=3 -key-threshold=2
```

7. Unseal the first node and enable an audit device before storing shared
   secrets:

```bash
vault operator unseal
vault operator unseal
vault audit enable file file_path=/var/log/vault/audit.log
```

For stronger operator handling, use PGP encryption for unseal shares and the
initial root token during `vault operator init`.

## Handoff to the next deployment

After Vault is initialized:

- move shared service credentials and long-lived tokens into Vault
- keep root tokens and unseal material out of the repository and out of normal
  automation
- use environment variables mainly for bootstrap references or short-lived
  injected values
- treat local Ansible Vault files as a fallback path, not the primary system of
  record

## On-prem HSM notes

An on-premises HSM is not required for the first Vault bootstrap in this
repository.

For the shortest path, keep Day 1 simple:

- use Shamir seal on the first dedicated Vault VM
- move shared secrets into Vault immediately after initialization
- treat on-premises HSM integration as a later hardening step

Use [Vault HSM hardening options](../security/vault-hsm-hardening-options.md)
as the authoritative repository note for Community Edition versus Enterprise
paths, device choices, and the later `Vault A` plus `Vault B` hardening model.

## Path to higher availability

When the environment is ready for more resilience:

- add two or four more Vault nodes with the same TLS and seal configuration
- use Raft `retry_join` entries and join nodes one at a time
- keep backup and restore tested before treating the cluster as critical
- if you need on-premises auto-unseal without cloud KMS or HSM, evaluate a
  separate transit-based unseal service rather than changing the primary Vault
  cluster into its own dependency chain

## Read more

- [Bootstrap path](bootstrap-path.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Vault HSM hardening options](../security/vault-hsm-hardening-options.md)
- [Ansible Vault bootstrap fallback](../reference/ansible-vault-bootstrap.md)
