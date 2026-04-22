# Proxmox backup foundation

## Table of contents

- [Purpose](#purpose)
- [Target outcome](#target-outcome)
- [Quick steps](#quick-steps)
- [Done criteria](#done-criteria)
- [Read more](#read-more)

## Purpose

Backups come first. Before using this repository broadly, deploy Proxmox Backup
Server and verify that backup and restore both work.

## Target outcome

At the end of this phase you should have:

- a running Proxmox Backup Server
- a datastore created on PBS
- PBS added to Proxmox VE as storage
- at least one successful VM or LXC backup
- at least one successful restore test

## Quick steps

1. Install Proxmox Backup Server.
2. Log in to the PBS web UI on port `8007`.
3. Create a datastore.
4. Add PBS to Proxmox VE under `Datacenter -> Storage`.
5. Copy the PBS fingerprint from the PBS dashboard and use it when adding the
   storage entry.
6. Create a backup job in Proxmox VE under `Datacenter -> Backup`.
7. Run the backup job.
8. Restore one test VM or container from PBS.

## Done criteria

Do not continue until all of these are true:

- PBS is reachable from Proxmox VE
- the datastore is visible and usable
- a backup completes successfully
- a restore completes successfully
- the restored workload can boot or otherwise be validated

## Read more

- [Private cloud maturity path](../../getting-started/private-cloud-maturity-path.md)
- [Host networking](network-prerequisites.md)
- [Hardening baseline](hardening.md)
