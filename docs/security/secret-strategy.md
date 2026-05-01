# Secret strategy

## Table of contents

- [Purpose](#purpose)
- [Design goal](#design-goal)
- [Bootstrap minimum](#bootstrap-minimum)
- [Vault foundation deployment milestone](#vault-foundation-deployment-milestone)
- [Vault operating target](#vault-operating-target)
- [What goes where](#what-goes-where)

## Purpose

This repository is designed to be easy to bootstrap while moving toward a
stronger secret model quickly. Vault is the preferred target state and should be
introduced as early as the shared identity and PKI layer can support it safely.

## Design goal

The secret strategy should be:

- simple enough for first use
- safe enough to avoid publishing secrets by mistake
- compatible with local execution and self-hosted runners
- easy to transition into Vault without large repository changes
- explicit about which small set of bootstrap secrets must still exist outside Vault

## Bootstrap minimum

Before Vault is available:

- keep structured non-secret configuration in ignored local files or a private
  operational copy
- keep sensitive runtime values in local environment variables or protected
  runner variables
- limit off-Vault secrets to the minimum needed to create the bootstrap
  shared identity and PKI layer, or to connect to existing shared services
- commit only examples, defaults, and reusable automation

## Vault foundation deployment milestone

Once the shared identity, DNS, and PKI prerequisites are ready:

- install Vault as a dedicated early shared service
- initialize and unseal Vault before broader service deployment
- enable an audit device and store the first shared secrets there
- treat Ansible Vault and plain environment variables as fallback bootstrap
  mechanisms, not the long-term system of record

Read more in [Vault foundation deployment](../paths/shared-services/vault.md).

## Vault operating target

After the first Vault deployment is online:

- move long-lived and shared secrets into the secret system
- reduce direct use of plain environment variables for persistent secrets
- use environment variables mainly as references, bootstrap inputs, or injected
  short-lived values

## What goes where

| Type of value | Preferred location |
| --- | --- |
| platform API tokens | environment variables during bootstrap, then Vault |
| Vault TLS private keys | local untracked secret files or private PKI workflow |
| Vault unseal or recovery material | encrypted offline storage, never in Git |
| bootstrap passwords | environment variables during bootstrap, then Vault |
| network CIDRs | ignored local files or private operational copy |
| node and bridge names | ignored local files or private operational copy |
| inventory structure | ignored local files or private operational copy |
| shared service credentials | Vault |
| PKI material | Vault or another dedicated secure store |
