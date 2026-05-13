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
- [Refresh the template](#refresh-the-template)
- [Read more](#read-more)
- [References](#references)

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
- Terraform uses the neutral variable name `default_linux_vm_template_id`
- you can point that variable at another Linux cloud-init template, but review
  Ansible service roles when you leave the Enterprise Linux family
- RHEL Generic Cloud images can follow the same mechanical process, but this
  repository does not document the Red Hat subscription-specific path here

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
   - use [Proxmox planning guidelines](conventions.md#vm-and-template-id-ranges)
     when you reserve VM IDs by role
   - set `VM ID` to a template-range value such as `110`
   - keep the shared template name aligned to
     [Template names](conventions.md#template-names)
   - set `Name` to `alma-10-tmpl` for AlmaLinux or `rocky-10-tmpl` for Rocky
     Linux
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
   - leave `Graphic card` at the default value
   - set `Machine` to `q35` as the repository default
   - set `BIOS` to `OVMF (UEFI)` as the repository default
   - when the `EFI Storage` field appears, select the VM storage
   - clear `Pre-Enroll keys`
   - set `SCSI Controller` to `VirtIO SCSI single`
   - enable `QEMU Agent`
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
15. Right click on the VM and chose `Convert to template`.
16. Record the resulting template VM ID in `terraform/common.tfvars`.

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

## Refresh the template

Use the `template-refresh` setup when you want to maintain the mutable
Enterprise Linux templates created by this guide.

The default refresh path maintains one staged template. Add more entries when
you maintain both AlmaLinux, Rocky Linux, RHEL, or multiple major releases.

What the automation uses:

| File | What you edit |
| --- | --- |
| `terraform/environments/template-refresh/terraform.tfvars` | staged template VM ID, source template, size, storage, and tags |
| `ansible/group_vars/template_refresh.yml` | package refresh, cleanup, and same-ID replacement settings |
| `ansible/inventory/hosts.yml` | `template_refresh_builders` and the Proxmox host used for replacement |
| `ansible/group_vars/template_refresh.yml` or `template_refresh.<env>.yml` | staged template IP address |

Refresh flow:

1. Clone the current template into a staged VM with a temporary template-range
   VM ID, such as `190`.
2. Let Ansible update packages and verify `acpid`, `qemu-guest-agent`, and
   cloud-init behavior.
3. Set `template_refresh_prepare_for_template: true` and rerun Ansible to clean
   cloud-init state, SSH host keys, and package cache.
4. Set the staged VM to `template = true` and `started = false` in
   `terraform/environments/template-refresh/terraform.tfvars`.
5. Run Terraform only to convert the staged VM into a staged Proxmox template.
6. Enable `template_refresh_replace_enabled: true`, set
   `template_refresh_prepare_builders: false`, and run Ansible only.

The final replacement deletes the old target template ID, clones the staged
template into that same ID, and converts the clone back into a Proxmox
template. Existing Terraform deployments can keep referencing the same
`default_linux_vm_template_id` after the replacement.

Keep the matching `linux_vm_template_catalog` entry in
`terraform/common.tfvars` aligned with the final template ID. Deployments use
that catalog to copy source-image tags, such as architecture, OS family, and
distro, onto cloned VMs. The staged refresh VM should use
`template_catalog_id` for the final target template ID so its tags also come
from the shared catalog.

Run sequence:

| Step | Edit first | Command |
| --- | --- | --- |
| Plan staged VM | template-refresh Terraform and Ansible vars | `bash scripts/deploy.sh template-refresh --env test --plan-only` |
| Create and update staged VM | reviewed plan | `bash scripts/deploy.sh template-refresh --env test` |
| Clean staged VM | `template_refresh_prepare_for_template: true` | `bash scripts/deploy.sh template-refresh --env test --ansible-only` |
| Convert staged VM to template | staged VM `template = true` and `started = false` | `bash scripts/deploy.sh template-refresh --env test --terraform-only` |
| Replace old template ID | `template_refresh_replace_enabled: true` and `template_refresh_prepare_builders: false` | `bash scripts/deploy.sh template-refresh --env test --ansible-only` |

The same-ID replacement is intentionally a separate final step. Do not enable
it until the staged template has been tested, the `hypervisors` inventory group
points at the Proxmox host that will run `qm`, and no VM clones should start
from the old template during the replacement window.

This repository provisions full clones from templates. If you create linked
clones outside this repository, confirm that those clones do not block deletion
of the old template before you enable the replacement step.

## Read more

- [Proxmox planning guidelines](conventions.md)
- [Proxmox reference platform](README.md)
- [Image-based Linux path](../../paths/application-platform/image-based-linux.md)
- [Infrastructure automation layout](../../reference/infrastructure-automation-layout.md)
- [Private cloud maturity path](../../paths/private-cloud-maturity.md)
- [Environment variable conventions](../../reference/environment-variables.md)

## References

1. [BPG Proxmox provider VM resource](https://bpg.sh/docs/resources/virtual_environment_vm/)
2. [Proxmox `qm` command reference](https://pve.proxmox.com/pve-docs/qm.1.html)
