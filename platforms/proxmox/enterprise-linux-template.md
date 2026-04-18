# Enterprise Linux template on Proxmox

## Table of contents

- [Purpose](#purpose)
- [Choose an image](#choose-an-image)
- [Check x86_64_v2 support](#check-x86_64_v2-support)
- [Choose a CPU type](#choose-a-cpu-type)
- [Download and verify the image](#download-and-verify-the-image)
- [Upload the image to the Proxmox node](#upload-the-image-to-the-proxmox-node)
- [Create the VM shell in Proxmox](#create-the-vm-shell-in-proxmox)
- [Import the disk and finalize the template](#import-the-disk-and-finalize-the-template)
- [What to keep in the template](#what-to-keep-in-the-template)
- [What to configure later](#what-to-configure-later)
- [Read more](#read-more)

## Purpose

Use this guide to create the first reusable Enterprise Linux VM template for
Proxmox in this repository. Keep it cloud-image-based so Terraform and Ansible
can configure it later.

Version note:

- this walkthrough is based on Proxmox VE `9.1.1`
- menu names, dialog wording, and available fields can shift in later releases

## Choose an image

Use an official Generic Cloud `qcow2` image from AlmaLinux or Rocky Linux.
These images already support cloud-init and fit Proxmox templates better than a
full installer ISO.

Current repository note:

- this guide is currently based on EL10 releases from AlmaLinux and Rocky Linux
- the manual Proxmox template flow in this guide works for either distribution
- the shipped Packer scaffold is currently `packer/templates/proxmox/el10.pkr.hcl`
- the Terraform examples use the neutral variable name `template_vm_id_el10`
- RHEL Generic Cloud images can follow the same mechanical process, but this
  repository does not document the Red Hat subscription-specific path here

Recommended image choice:

Use the most portable Generic Cloud `qcow2` image that fits the chosen
distribution.

| Distribution | Recommended image | Selection rule |
| --- | --- | --- |
| AlmaLinux | Generic Cloud `qcow2` for `x86_64_v2` | Use `x86_64_v2` only when every Proxmox node that may host or receive the VM supports it. Otherwise use the Generic Cloud `qcow2` image for `x86_64`. Read [Check x86_64_v2 support](#check-x86_64_v2-support). |
| Rocky Linux | `GenericCloud-Base.latest.x86_64.qcow2` | Use `Base` for this repository. Do not use `GenericCloud-LVM.latest.x86_64.qcow2` for the default path. `Base` keeps the image closer to a minimal cloud baseline and leaves the guest layout more flexible. |

Official sources:

- AlmaLinux: [AlmaLinux Generic Cloud images](https://wiki.almalinux.org/cloud/Generic-cloud.html#download-images)
- Rocky Linux: [Rocky Linux cloud images](https://download.rockylinux.org/pub/rocky/10/images/x86_64/)

## Check x86_64_v2 support

Check this before choosing an `x86_64_v2` image for AlmaLinux or any other
Enterprise Linux cloud image.

To check whether a Proxmox node supports `x86_64_v2`, open a shell on that node
and run:

```bash
/usr/lib64/ld-linux-x86-64.so.2 --help
```

On systems with a recent enough glibc, the help output includes the
`glibc-hwcaps` levels that the node can use. Look for `x86-64-v2` in that
list.

If you want a lower-level check, verify the CPU flags exposed on the node with
`lscpu` or `/proc/cpuinfo` and confirm they include the features glibc uses for
`x86-64-v2`: `cx16`, `lahf_lm`, `popcnt`, `sse3`, `ssse3`, `sse4_1`, and
`sse4_2`.

```bash
lscpu
grep -m1 '^flags' /proc/cpuinfo
```

Run this on every Proxmox node that may host or receive the VM through
migration. If you need to double-check the underlying hardware, verify the CPU
model shown by `lscpu` against the vendor specification page for that processor.
Also remember that the guest only sees the features exposed by the chosen VM
CPU type, so a capable node is necessary but not always sufficient if the VM is
configured with a conservative virtual CPU model.

## Choose a CPU type

For this repository, set the VM `CPU Type` to `x86-64-v2-AES`.

This matches the Terraform VM module, keeps a modern portable baseline, and is
safer for future migration than `host` in mixed or expanding clusters.

Use `host` only as an explicit deviation when all of these are true:

- the VM will stay on one node or on a cluster with identical CPU models
- live migration compatibility across different CPU generations is not a goal
- you intentionally want maximum host-specific feature exposure over portability

To check whether `x86-64-v2-AES` is a safe choice on a node:

1. run the `x86_64_v2` check in [Check x86_64_v2 support](#check-x86_64_v2-support)
2. verify that the node also exposes the `aes` CPU flag

```bash
lscpu
grep -m1 '^flags' /proc/cpuinfo
```

Look for `aes` in the reported flags. For cluster use, repeat this on every
node that may host or receive the VM through migration and keep the CPU type at
the lowest common supported level.

## Download and verify the image

Download the image and its checksum material from the same official directory.
Verify the vendor checksum before uploading the file anywhere else.

Use this flow:

1. Create a temporary working directory on your admin machine.
2. Download the image file.
3. Download `CHECKSUM` and `CHECKSUM.asc` from the same image directory.
4. Verify the checksum file signature when the distro provides a signed checksum.
5. Verify the image checksum before upload.

Generic verification pattern:

```bash
gpg --verify CHECKSUM.asc CHECKSUM
sha256sum -c CHECKSUM 2>&1 | grep "OK"
```

Only continue when the signature is reported as good and the selected image
shows `OK`.

## Upload the image to the Proxmox node

Use the Proxmox GUI upload or download flow. Let the node verify the file during
the transfer.

Use this flow:

1. Open the Proxmox web UI.
2. Select the target node.
3. Open the storage that will temporarily hold the downloaded or uploaded image.
4. Open the storage `Content` view.
5. Start the GUI transfer workflow you use in your environment, such as
   `Upload` or `Download from URL`.
6. Expand `Advanced` if the checksum fields are hidden.
7. Set `Checksum algorithm` to `sha256`.
8. Paste the vendor SHA256 value for the exact image file into `Checksum`.
9. Start the transfer and wait for the task to finish successfully.
10. Confirm in the task output that the checksum verification succeeded before
    you continue to disk import.

When copying the checksum from the vendor `CHECKSUM` file, paste only the hash
value itself. Do not paste the filename, spaces, or the whole line.

Example:

```text
3e...example...9b  Rocky-10-GenericCloud-Base.latest.x86_64.qcow2
```

In the Proxmox GUI:

- `Checksum algorithm`: `sha256`
- `Checksum`: `3e...example...9b`

This keeps the verification in the Proxmox task flow and shows which hash
algorithm and digest were used for the file on the node.

## Create the VM shell in Proxmox

Create an empty VM shell first. Import the cloud image after that.

Use these wizard selections:

1. `General`
   - set `VM ID` to `9010`
   - set `Name` to `alma10-cloud-base` for AlmaLinux or
     `rocky10-cloud-base` for Rocky Linux
   - set `Tags` to `x86_64,el10,cloud-init,alma10` for AlmaLinux or
     `x86_64,el10,cloud-init,rocky10` for Rocky Linux
2. `OS`
   - set `Use CD/DVD disc image file (iso)` to `Do not use any media`
   - set `Guest OS` to `Linux`
3. `System`
   - set `Machine` to `q35` as the repository default
   - set `BIOS` to `OVMF (UEFI)` as the repository default
   - when the `EFI Storage` field appears, select the VM storage
   - clear `Pre-Enroll keys`
   - set `SCSI Controller` to `VirtIO SCSI single`
   - leave `Display` at the default value
   - do not add a TPM device in the template itself
4. `Disks`
   - remove the default disk entry
   - click `Import`
   - choose the uploaded cloud image as the source disk
   - set the target storage to the storage that should hold the VM disk
   - set the bus or device to `SCSI` and attach it as `scsi0`
   - keep any extra storage or format fields at their default values
   - click `Next`
5. `CPU`
   - set `Type` to `x86-64-v2-AES` to match the repository default
   - read [Choose a CPU type](#choose-a-cpu-type) for the node-side checks
   - set `Cores` to `2`
6. `Memory`
   - set `Memory` to `2048 MiB`
7. `Network`
   - set `Model` to `VirtIO`
   - set `Bridge` to the fabric bridge, usually `vmbr0`

At this stage, do not set environment-specific IP addresses, passwords, or
cloud-init user data in the template itself.

## Import the disk and finalize the template

After the VM is created, finish the template in the Proxmox GUI from the VM
`Hardware` page.

Use this flow:

1. Open the VM and select `Hardware`.
2. In `Hardware`, select the `CD/DVD Drive` and click `Remove`.
3. Click `Add` -> `CloudInit Drive`.
4. In the CloudInit dialog, set the drive to `IDE`, use slot `2`, select the
    VM storage, then click `Add`.
5. Open the `Cloud-Init` tab.
6. Select `User`, click `Edit`, set it to `automation`, then apply the change.
7. Select `SSH public keys`, click `Edit`, paste the current admin computer's
   public SSH key as a temporary key for prepping, then apply the change.
8. Select `IP Config (net0)`, click `Edit`, set it to `DHCP` or a static
   address that matches your network strategy, then apply the change.
9. Open the `Options` tab, select `Boot Order`, click `Edit`, and verify that
   `scsi0` is enabled and listed above `net0`.
10. Start the VM.
11. Connect to the VM over SSH and run:

```bash
sudo dnf install -y acpid qemu-guest-agent
sudo systemctl enable --now acpid qemu-guest-agent
sudo cloud-init clean
sudo shutdown -h now
```

12. After the VM stops, select `SSH public keys`, click `Edit`, remove the
    temporary key, then apply the change.
13. Convert it to a template.
14. Record the resulting template VM ID in
    `terraform/environments/bootstrap/terraform.tfvars`.

## What to keep in the template

Keep the first template minimal:

- AlmaLinux or Rocky Linux base image
- cloud-init support
- `acpid`
- `qemu-guest-agent`
- no environment-specific IPs, names, or credentials

## What to configure later

Configure these at deploy time with Terraform and Ansible:

- hostname
- SSH keys
- DHCP or static IP configuration
- users beyond the initial automation path
- package and service baselines
- hardening beyond the base image
- TPM state when a specific workload or policy requires it

## Read more

- [Proxmox reference platform](README.md)
- [Packer Proxmox templates](../../packer/templates/proxmox/README.md)
- [Private cloud maturity path](../../docs/getting-started/private-cloud-maturity-path.md)
- [Environment variable conventions](../../docs/reference/environment-variables.md)
