# HSM getting started

## Table of contents

- [Purpose](#purpose)
- [Use and scale matrix](#use-and-scale-matrix)
- [How to read the matrix](#how-to-read-the-matrix)
- [Start with the right problem](#start-with-the-right-problem)
- [Repository path](#repository-path)
- [What USB HSM active-active solves](#what-usb-hsm-active-active-solves)
- [Certification and reality](#certification-and-reality)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this guide to make a first HSM decision without getting stuck in too much
detail.

For this repository:

- `Pico HSM` is the open-source-first learning and implementation path [1][2]
- `YubiHSM 2` is the cleaner commercial step-up path [3][4]
- enterprise network HSMs are the right answer when formal compliance, vendor
  HA, or much higher signing scale matters

This guide is for getting started. Use the Pico HSM blueprint for the concrete
USB HSM deployment pattern.

## Use and scale matrix

Use this as the short planning matrix:

| Path | Typical shape | Public cost signal | Code-signing fit | Maintenance | HA | Scale |
| --- | --- | --- | --- | --- | --- | --- |
| `Pico HSM` | `1` active + `1` offline backup | less than `€4` per supported Pico-class board | `1-3` developers, offline CA, bootstrap, or low-volume signing; repo planning inference [1][2] | `*****` | `*----` | `*----` |
| `Pico HSM` active-active | `4` active across `2` hosts + `1` offline backup | less than `€20` for `5` supported Pico-class boards before hosts and accessories | `5-20` developers, small internal signing or PKI service; repo planning inference [1][2] | `*****` | `***--` | `**---` |
| `YubiHSM 2` | `1` active + `1` spare or offline backup | about `€770` standard or about `€1100` for FIPS per device | about `7` RSA-2048 or `13` ECDSA-P256 signatures per second on one otherwise idle device; usually enough for `5-20` developers sharing a signing service [3] | `**---` | `*----` | `***--` |
| replicated `YubiHSM 2` | `2-4` active devices + wrap-key backup | about `€1500-3100` standard or about `€2300-4500` for FIPS | about `14-28` RSA-2048 or `26-54` ECDSA-P256 signatures per second if requests spread cleanly across `2-4` otherwise idle devices [3] | `***--` | `***--` | `****-` |
| enterprise network HSM | `2+` units in the vendor HA model | vendor quote | heavy CI signing, larger PKI, `100+` developers, or regulated production use | `***--` | `*****` | `*****` |

All prices are based on indicative public pricing as of April 2026 and are
rounded `€` signals to show cost scale, not exact purchase prices.

Simple progression:

1. start with `Pico HSM`
2. move to `YubiHSM 2` if you want a more mature commercial path
3. move to enterprise HSMs when you need vendor-backed HA or formal compliance

## How to read the matrix

Use these rules:

- `Maintenance`: more stars means more operator work, more manual rollout, and
  more testing you must own yourself
- `HA`: more stars means stronger built-in resilience and less custom failover
  design
- `Scale`: more stars means easier growth without redesigning the service

Important planning note:

- the `YubiHSM 2` signing numbers come from Yubico's published example
  performance on an otherwise idle device [3]
- the `Pico HSM` team-size guidance is a repository planning inference, because
  Pico HSM docs publish PKCS#11 support and wrapped backup or restore features
  but not an equivalent end-to-end signing throughput table [1][2]
- the developer counts assume release or CI signing, not every local build on
  every workstation
- enterprise network HSM cost is left as vendor quote because public list
  pricing is usually not the real buying path there

## Start with the right problem

Do not start by asking which HSM is best. Start by asking what you are trying to
protect.

Pick one primary job first:

1. protect Vault bootstrap or recovery material
2. protect CA or intermediate CA keys
3. protect signing keys for code signing or service identity
4. satisfy a formal compliance requirement

Solve these risks before you buy more hardware:

- sensitive keys living only on ordinary disk
- no tested recovery path
- attaching the HSM to too many hosts
- no operator custody plan for PINs, wrap keys, or backups

## Repository path

Use this repository path:

1. bootstrap Vault with Shamir first
2. move shared secrets into Vault
3. add HSM-backed hardening later
4. use USB HSMs first for bootstrap, recovery, PKI, or signing workflows

For open-source-first hardening, the repository direction is:

- `Vault A` stays small and handles Transit auto-unseal
- `Vault B` is the main Vault for workloads
- `Pico HSM` or `YubiHSM 2` protects the bootstrap or recovery path for
  `Vault A`

## What USB HSM active-active solves

USB HSM active-active is a service design, not a native HSM cluster.

What it improves:

- one host or one device can fail without stopping the whole service
- parallel signing capacity is better than a single-device design
- you can practice real rollout, recovery, and failover procedures

What it does not give you:

- native clustered HSM behavior
- automatic replication between devices
- enterprise HSM compliance claims

Use the Pico HSM blueprint for the concrete `2` hosts, `4` active devices, and
`1` offline backup pattern.

## Certification and reality

Enterprise HSM pricing is not only about faster crypto.

A large part of the premium is the package around the device:

- certification
- vendor-backed HA features
- support contracts
- broader integration coverage
- stronger audit posture

That does not make USB HSMs pointless. It means they solve a different problem:
practical hardware-backed custody for homelabs, labs, and smaller internal
platforms.

## Read more

- [Pico HSM active-active blueprint](picohsm-active-active-blueprint.md)
- [Vault HSM hardening options](vault-hsm-hardening-options.md)
- [Vault bootstrap](../getting-started/vault-bootstrap.md)
- [Secret strategy](secret-strategy.md)

## References

1. [PicoKeys Documentation: Supported features](https://docs.picokeys.com/picohsm/features/) (accessed 2026-04-19)
2. [PicoKeys Documentation: Backup and restore](https://docs.picokeys.com/picohsm/backup-restore/) (accessed 2026-04-19)
3. [Yubico: YubiHSM 2 v2.4](https://www.yubico.com/de/product/yubihsm-2-series/yubihsm-2/) (accessed 2026-04-19)
4. [Yubico: YubiHSM 2 FIPS v2.2](https://www.yubico.com/de/product/yubihsm-2-series/yubihsm-2-fips/) (accessed 2026-04-19)
