# Secret strategy

## Table of contents

- [Purpose](#purpose)
- [Design goal](#design-goal)
- [Bootstrap minimum](#bootstrap-minimum)
- [Secret-platform deployment milestone](#secret-platform-deployment-milestone)
- [Secret-platform operating target](#secret-platform-operating-target)
- [What goes where](#what-goes-where)

## Purpose

This repository is designed to be easy to bootstrap while adopting a stronger
secret model quickly. Vault is the current reference secret platform and should
be introduced as early as the shared identity and PKI layer can support it
safely.

## Design goal

The secret strategy should be:

- simple enough for first use
- safe enough to avoid publishing secrets by mistake
- compatible with local execution and self-hosted runners
- easy to transition into a secret platform without large repository changes
- explicit about which small bootstrap secrets must still exist outside the
  secret platform

## Bootstrap minimum

Before the secret platform is available:

- keep structured non-secret configuration in ignored local files or a private
  operational copy
- keep sensitive runtime values in local environment variables or protected
  runner variables
- limit off-platform secrets to the minimum needed to create the bootstrap
  shared identity and PKI layer, or to connect to existing shared services
- commit only examples, defaults, and reusable automation

## Secret-platform deployment milestone

Once the shared identity, DNS, and PKI prerequisites are ready:

- install the secret platform as a dedicated early shared service
- initialize and unseal it before broader service deployment when required
- enable an audit device and store the first shared secrets there
- treat Ansible Vault and plain environment variables as fallback bootstrap
  mechanisms, not the long-term system of record

Read more in [Vault foundation deployment](../paths/shared-services/vault.md).

## Secret-platform operating target

After the first secret-platform deployment is online:

- move long-lived and shared secrets into the secret system
- reduce direct use of plain environment variables for persistent secrets
- use environment variables mainly as references, bootstrap inputs, or injected
  short-lived values

## What goes where

| Type of value | Preferred location |
| --- | --- |
| platform API tokens | environment variables during bootstrap, then the secret platform |
| secret-platform TLS private keys | local untracked secret files or private PKI workflow |
| unseal or recovery material | encrypted offline storage, never in Git |
| bootstrap passwords | environment variables during bootstrap, then the secret platform |
| network CIDRs | ignored local files or private operational copy |
| node and bridge names | ignored local files or private operational copy |
| inventory structure | ignored local files or private operational copy |
| shared service credentials | secret platform |
| PKI material | secret platform or another dedicated secure store |
