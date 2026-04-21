# Enterprise Linux template on Proxmox

## Table of contents

- [Purpose](#purpose)
- [Choose an image](#choose-an-image)
- [Choose a CPU type](#choose-a-cpu-type)
- [Download and verify the image](#download-and-verify-the-image)
- [Upload the image to the Proxmox node](#upload-the-image-to-the-proxmox-node)
- [Create the VM shell in Proxmox](#create-the-vm-shell-in-proxmox)
- [Finalize the template](#finalize-the-template)
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

Suggested VM ID ranges:

| Range | Purpose |
| --- | --- |
| `100-199` | Templates |
| `200-299` | Infrastructure |
| `300-399` | Docker and services |
| `400-499` | Databases |
| `500-999` | User and app VMs |

Recommended image choice:

Use the most portable Generic Cloud `qcow2` image that fits the chosen
distribution.

| Distribution | Recommended image | Selection rule |
| --- | --- | --- |
| AlmaLinux | Generic Cloud `qcow2` for `x86_64` | Use the default `x86_64` image for this repository. AlmaLinux also publishes `x86_64_v2`, but that is a compatibility path for older hardware, not the repo default. Read [Choose a CPU type](#choose-a-cpu-type). |
| Rocky Linux | `GenericCloud-Base.latest.x86_64.qcow2` | Use `Base` for this repository. Rocky Linux 10 requires an `x86-64-v3` CPU baseline, so do not pair it with Proxmox CPU type `x86-64-v2-AES`. Read [Choose a CPU type](#choose-a-cpu-type). |

Official sources:

- AlmaLinux: [AlmaLinux Generic Cloud images](https://wiki.almalinux.org/cloud/Generic-cloud.html#download-images)
- Rocky Linux: [Rocky Linux cloud images](https://download.rockylinux.org/pub/rocky/10/images/x86_64/)

## Choose a CPU type

Choose the highest CPU type that every Proxmox node in the target cluster
supports. The lowest common denominator across the cluster is the type you
should set on the VM.

For EL10 in this repository:

- `x86-64-v3` is the floor for both linux distros
- AlmaLinux 10 `x86_64_v2` is a fallback path for older hardware

Check this on every Proxmox node that may host or receive the VM through
migration:

```bash
/lib64/ld-linux-x86-64.so.2 --help | grep x86-64
```

Look for the highest `x86-64-v*` line that shows `(supported, searched)`.

Use at least `x86-64-v3` when your cluster supports it so the template stays
portable for live migration. Only go below it if you intentionally download the
AlmaLinux 10 `x86_64_v2` image as the compatibility path for your cluster.

Do not use `host` as the default template CPU type. `host` exposes the current
node CPU to the guest and can keep the VM tied to that node, or to a cluster
with matching CPU types only.

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
   - set `VM ID` to `110`
   - set `Name` to `alma10-cloud-base` for AlmaLinux or
     `rocky10-cloud-base` for Rocky Linux
   - enable the `Advanced` checkbox so the `Tags` field is shown
   - add tags one by one in the GUI
   - use these common tags:
     `x86_64`
     `el10`
     `cloud-init`

   - add the distro tag that matches the image:
     AlmaLinux:
     `alma10`
     Rocky Linux:
     `rocky10`
2. `OS`
   - set `Use CD/DVD disc image file (iso)` to `Do not use any media`
   - set `Guest OS` to `Linux`
3. `System`
   - set `Machine` to `q35` as the repository default
   - set `BIOS` to `OVMF (UEFI)` as the repository default
   - when the `EFI Storage` field appears, select the VM storage
   - clear `Pre-Enroll keys`
   - set `SCSI Controller` to `VirtIO SCSI single`
   - enable `QEMU Agent`
   - leave `Display` at the default value
   - do not add a TPM device in the template itself
4. `Disks`
   - remove the default disk entry
   - click `Import`
   - choose the uploaded cloud image as the source disk
   - verify the imported disk is attached as `scsi0` on bus or device `SCSI`
     because that is the default repository path
   - set the target storage to the storage that should hold the VM disk
   - keep any extra storage or format fields at their default values
   - click `Next`
5. `CPU`
   - set `Type` to the CPU type you selected earlier in
     [Choose a CPU type](#choose-a-cpu-type), usually `x86-64-v3`
   - set `Cores` to `2`
6. `Memory`
   - set `Memory` to `2048 MiB`
7. `Network`
   - set `Model` to `VirtIO`
   - set `Bridge` to the bridge used by your network configuration, for example
     `vmbr0`
   - set a VLAN tag here when your environment uses VLAN-aware bridges and the
     template should start on a tagged network

At this stage, do not set environment-specific IP addresses, passwords, or
cloud-init user data in the template itself.

## Finalize the template

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
11. If you use `DHCP`, find the VM IP address in the `Summary` tab.
12. Connect to the VM over SSH and wait for first-boot tasks to finish:
    this can take a few minutes after the first start.

```bash
sudo cloud-init status --wait
sudo systemctl is-system-running --wait || true
```

13. Run:

```bash
sudo dnf install -y acpid qemu-guest-agent
sudo systemctl enable --now acpid qemu-guest-agent
sudo cloud-init clean
sudo shutdown -h now
```

14. After the VM stops, select `SSH public keys`, click `Edit`, remove the
    temporary key, then apply the change.
15. Convert it to a template.
16. Record the resulting template VM ID in
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
- Secure Boot when you intentionally want that path
- TPM state when a specific workload or policy requires it

## Read more

- [Proxmox reference platform](README.md)
- [Packer Proxmox templates](../../../packer/templates/proxmox/README.md)
- [Private cloud maturity path](../../getting-started/private-cloud-maturity-path.md)
- [Environment variable conventions](../../reference/environment-variables.md)
