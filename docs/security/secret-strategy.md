# Secret strategy

## Table of contents

- [Purpose](#purpose)
- [Design goal](#design-goal)
- [Bootstrap phase](#bootstrap-phase)
- [Vault target state](#vault-target-state)
- [What goes where](#what-goes-where)

## Purpose

This repository is designed to be easy to bootstrap while moving toward a
stronger secret model quickly. Vault is the preferred target state, but it is
not required for the first successful deployment.

## Design goal

The secret strategy should be:

- simple enough for first use
- safe enough to avoid publishing secrets by mistake
- compatible with local execution and self-hosted runners
- easy to transition into Vault without large repository changes

## Bootstrap phase

Before Vault is available:

- keep structured non-secret configuration in ignored local files or a private
  operational copy
- keep sensitive runtime values in local environment variables or protected
  runner variables
- commit only examples, defaults, and reusable automation

## Vault target state

As soon as the platform is stable enough to host Vault or another secret system:

- move long-lived and shared secrets into the secret system
- reduce direct use of plain environment variables for persistent secrets
- use environment variables mainly as references, bootstrap inputs, or injected
  short-lived values

## What goes where

| Type of value | Preferred location |
| --- | --- |
| API tokens | environment variables, then Vault |
| bootstrap passwords | environment variables, then Vault |
| network CIDRs | ignored local files or private operational copy |
| node and bridge names | ignored local files or private operational copy |
| inventory structure | ignored local files or private operational copy |
| shared service credentials | Vault |
| PKI material | Vault or another dedicated secure store |
